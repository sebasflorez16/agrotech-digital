"""
Sentinel-2 óptico — índices REALES (NDVI/NDMI/SAVI/NDRE) desde Planetary Computer.

Mismo patrón que sentinel1.py: STAC search + firma SAS + rasterio (lectura por
rango, sin descargar el COG completo). Solo datos reales; si no hay escena o el
muestreo falla, se devuelve None (NUNCA se inventan valores).
"""
import logging
from datetime import datetime, timedelta

import requests
import numpy as np

from django.core.cache import cache

try:
    import rasterio
    from rasterio.warp import transform as _warp_transform
except ImportError:
    rasterio = None

from .sentinel1 import _sign_url, _geometry_bbox_lonlat, PLANETARY_STAC_URL

logger = logging.getLogger(__name__)

S2_COLLECTION = "sentinel-2-l2a"

# Banda Sentinel-2 L2A → rol (resolución nativa)
S2_BANDS = {
    "B04": "red",     # 10m  (NDVI, SAVI)
    "B05": "rededge", # 20m  (NDRE)
    "B08": "nir",     # 10m  (NDVI, SAVI, NDRE)
    "B8A": "nir08",   # 20m  (NDMI)
    "B11": "swir16",  # 20m  (NDMI)
}

INDICES_CACHE_TTL = 7 * 86400  # 7 días


def search_sentinel2_scenes(geometry, scene_date=None, max_results=10, date_from=None, date_to=None):
    """Busca escenas Sentinel-2 L2A que cubran la geometría.

    Si se pasan date_from/date_to se usa ese rango; si no, ±10 días alrededor
    de scene_date. Devuelve lista ordenada de menor a mayor nubosidad.
    """
    if date_from and date_to:
        d_from = date_from
        d_to = date_to
    else:
        try:
            dt = datetime.strptime(str(scene_date)[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            dt = datetime.utcnow()
        d_from = (dt - timedelta(days=10)).strftime("%Y-%m-%d")
        d_to = (dt + timedelta(days=10)).strftime("%Y-%m-%d")

    body = {
        "collections": [S2_COLLECTION],
        "intersects": geometry,
        "datetime": f"{d_from}T00:00:00Z/{d_to}T23:59:59Z",
        "limit": max_results,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}],
        "query": {"eo:cloud_cover": {"lt": 90}},
    }
    try:
        r = requests.post(PLANETARY_STAC_URL, json=body, timeout=30)
        if r.status_code != 200:
            logger.warning(f"[S2] STAC search failed: {r.status_code}")
            return []
    except Exception as e:
        logger.error(f"[S2] Error STAC search: {e}")
        return []

    features = r.json().get("features", [])
    if not features:
        return []

    scenes = []
    for f in features:
        pr = f.get("properties", {})
        assets = f.get("assets", {})
        scene = {
            "id": f.get("id", ""),
            "date": (pr.get("datetime") or "")[:10],
            "cloud_cover": pr.get("eo:cloud_cover"),
            "platform": pr.get("platform", "S2"),
        }
        ok = True
        for band, role in S2_BANDS.items():
            href = (assets.get(band) or {}).get("href", "")
            if href:
                scene[f"{role}_href"] = href
            else:
                ok = False
                break
        if ok:
            # SCL (Scene Classification) para enmascarar nubes/sombras/cirros
            scl_href = (assets.get("SCL") or {}).get("href", "")
            if scl_href:
                scene["scl_href"] = scl_href
            scenes.append(scene)

    # Deduplicar por fecha: Sentinel-2A y 2C pueden pasar el mismo día.
    # Quedarnos con la escena de MENOR nubosidad de cada fecha.
    best_by_date = {}
    for scene in scenes:
        d = scene.get("date")
        if not d:
            continue
        if d not in best_by_date or (scene.get("cloud_cover") or 100) < (best_by_date[d].get("cloud_cover") or 100):
            best_by_date[d] = scene
    scenes = list(best_by_date.values())

    scenes.sort(key=lambda s: s.get("date", ""), reverse=True)
    return scenes


def search_sentinel2_scene(geometry, scene_date, max_results=10, exact_date=False):
    """Devuelve la MEJOR escena (menor nubosidad) o None.

    Si exact_date=True, devuelve la escena de EXACTAMENTE scene_date
    (para ver la imagen de una fecha concreta, no la mejor de ±10 días).
    """
    if exact_date:
        scenes = search_sentinel2_scenes(
            geometry, date_from=scene_date, date_to=scene_date, max_results=max_results
        )
        exact = [s for s in scenes if s.get("date") == scene_date]
        return exact[0] if exact else (scenes[0] if scenes else None)

    scenes = search_sentinel2_scenes(geometry, scene_date, max_results=max_results)
    return scenes[0] if scenes else None


def _sample_band(href, points_lonlat):
    """Muestrea los valores de una banda COG en los puntos (lon, lat) dados.

    Usa reproyección EPSG:4326 → CRS del raster y vecino más cercano.
    Retorna array de la misma longitud que points_lonlat (NaN para fuera).
    """
    if rasterio is None:
        return None
    signed = _sign_url(href)
    if not signed:
        return None
    try:
        with rasterio.Env(
            GDAL_HTTP_MULTIRANGE="YES",
            CPL_VSIL_CURL_USE_HEAD="NO",
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        ):
            with rasterio.open(signed) as ds:
                lons = [p[0] for p in points_lonlat]
                lats = [p[1] for p in points_lonlat]
                xs, ys = _warp_transform("EPSG:4326", ds.crs, lons, lats)
                out = np.full(len(points_lonlat), np.nan, dtype="float64")
                for i, (x, y) in enumerate(zip(xs, ys)):
                    try:
                        row, col = ds.index(x, y)
                        if 0 <= row < ds.height and 0 <= col < ds.width:
                            v = ds.read(1, window=((row, row + 1), (col, col + 1)))
                            out[i] = v[0, 0]
                    except Exception:
                        continue
                return out
    except Exception as e:
        logger.error(f"[S2] Error muestreando banda: {e}")
        return None


def get_real_indices(geometry, points_lonlat, scene_date):
    """Devuelve (ndvi, ndmi, savi, ndre, scene_date) REALES en los puntos dados, o None.

    Los valores se muestrean de una escena Sentinel-2 L2A real. Si la fecha pedida
    no tiene escena (±10 días), se usa la escena real más reciente (últimos 90 días).
    Si no hay escena o el muestreo falla, devuelve None (NUNCA se inventan valores).
    """
    if not points_lonlat or rasterio is None:
        return None

    scene = search_sentinel2_scene(geometry, scene_date)
    if not scene:
        # Fallback: escena real más reciente de los últimos 90 días
        try:
            dt = datetime.strptime(str(scene_date)[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            dt = datetime.utcnow()
        recent = search_sentinel2_scenes(
            geometry,
            date_from=(dt - timedelta(days=90)).strftime("%Y-%m-%d"),
            date_to=dt.strftime("%Y-%m-%d"),
            max_results=5,
        )
        scene = recent[0] if recent else None
    if not scene:
        return None

    effective_date = scene.get("date") or str(scene_date)[:10]
    cache_key = (
        f"s2:indices:{hashlib_md5_geometry(geometry)}:{effective_date}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    red = _sample_band(scene.get("red_href"), points_lonlat)
    rededge = _sample_band(scene.get("rededge_href"), points_lonlat)
    nir = _sample_band(scene.get("nir_href"), points_lonlat)
    nir08 = _sample_band(scene.get("nir08_href"), points_lonlat)
    swir16 = _sample_band(scene.get("swir16_href"), points_lonlat)

    if any(a is None for a in (red, rededge, nir, nir08, swir16)):
        return None

    def _idx(a, b):
        with np.errstate(divide="ignore", invalid="ignore"):
            v = (a - b) / (a + b)
        return np.where(np.isfinite(v), v, np.nan)

    ndvi = _idx(nir, red)
    ndmi = _idx(nir08, swir16)
    ndre = _idx(nir, rededge)
    with np.errstate(divide="ignore", invalid="ignore"):
        savi = (nir - red) / (nir + red + 0.5) * 1.5
    savi = np.where(np.isfinite(savi), savi, np.nan)

    result = (ndvi, ndmi, savi, ndre, effective_date)
    cache.set(cache_key, result, INDICES_CACHE_TTL)
    logger.info(f"[S2] Índices reales muestreados: escena {scene.get('id')} (nubes {scene.get('cloud_cover')}%)")
    return result


def hashlib_md5_geometry(geometry):
    import hashlib
    return hashlib.md5(str(geometry).encode()).hexdigest()[:16]


# ---------------------------------------------------- imágenes de color (mapas)

# Colormaps de 5 categorías (leyenda: Atención→Bajo→Intermedio→Bueno→Excelente).
# Extremos intensos (significado agronómico) con transición lineal continua.

# NDVI / SAVI: RdYlGn
_CMAP_STOPS = np.array([
    [0.00, 175, 55, 45],    # 🔴 rojo suave (atención / suelo desnudo)
    [0.25, 244, 109, 67],   # 🟠 naranja (bajo)
    [0.50, 254, 224, 139],  # 🟡 amarillo (intermedio)
    [0.75, 161, 215, 106],  # 🟢 verde claro (bueno)
    [1.00, 0, 109, 44],     # 🟢 verde intenso (excelente / muy alto)
], dtype=float)

# NDMI: Blues (blanco → azul suave → azul medio → azul oscuro → azul profundo)
_CMAP_STOPS_NDMI = np.array([
    [0.00, 247, 251, 255],  # blanco (muy baja humedad)
    [0.25, 198, 219, 239],  # azul suave
    [0.50, 107, 174, 214],  # azul medio
    [0.75, 33, 113, 181],   # azul oscuro
    [1.00, 8, 48, 107],     # azul profundo (mayor humedad)
], dtype=float)

# NDRE: YlGn (amarillo pálido → verde claro → verde medio → verde oscuro → verde profundo)
_CMAP_STOPS_NDRE = np.array([
    [0.00, 255, 255, 204],  # amarillo pálido (bajo)
    [0.25, 173, 221, 142],  # verde claro
    [0.50, 120, 198, 121],  # verde medio
    [0.75, 35, 132, 67],    # verde oscuro
    [1.00, 0, 69, 41],      # verde profundo (alto)
], dtype=float)


def _apply_colormap(normalized, stops=None):
    """Aplica un colormap (RdYlGn por defecto; escala de agua para NDMI)."""
    if stops is None:
        stops = _CMAP_STOPS
    h, w = normalized.shape
    img = np.zeros((h, w, 4), dtype=np.uint8)
    valid = np.isfinite(normalized)
    n = np.clip(normalized, 0.0, 1.0)
    for i in range(len(stops) - 1):
        t0, c0 = stops[i][0], stops[i][1:]
        t1, c1 = stops[i + 1][0], stops[i + 1][1:]
        mask = valid & (n >= t0) & (n <= t1)
        if not mask.any():
            continue
        k = ((n[mask] - t0) / (t1 - t0))[:, None]
        img[mask, :3] = (c0[None, :] + k * (c1[None, :] - c0[None, :])).astype(np.uint8)
    img[valid, 3] = 210
    return img


# Pares de bandas por índice (banda alta, banda baja)
_BAND_PAIRS = {
    'ndvi': ('nir_href', 'red_href'),
    'ndmi': ('nir08_href', 'swir16_href'),
    'savi': ('nir_href', 'red_href'),
    'ndre': ('nir_href', 'rededge_href'),
}


def _read_band_window(href, geometry):
    """Lee la ventana del COG de una banda en resolución nativa, enmascarada al polígono."""
    if rasterio is None:
        return None
    bbox = _geometry_bbox_lonlat(geometry)
    if not bbox:
        return None
    from rasterio.features import geometry_mask
    from rasterio.warp import transform_geom, transform_bounds as _tb
    from rasterio.windows import from_bounds, Window

    signed = _sign_url(href)
    if not signed:
        return None
    try:
        with rasterio.Env(
            GDAL_HTTP_MULTIRANGE="YES",
            CPL_VSIL_CURL_USE_HEAD="NO",
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        ):
            with rasterio.open(signed) as ds:
                bb = _tb("EPSG:4326", ds.crs, *bbox)
                window = from_bounds(*bb, ds.transform).intersection(Window(0, 0, ds.width, ds.height))
                if window.width <= 0 or window.height <= 0:
                    return None
                arr = ds.read(1, window=window).astype("float64")
                arr = np.where(arr > 0, arr, np.nan)  # no-data (0) → NaN
                wt = ds.window_transform(window)
                geom_crs = transform_geom("EPSG:4326", ds.crs, geometry)
                mask = geometry_mask([geom_crs], out_shape=arr.shape, transform=wt, invert=True)
                arr = np.where(mask, arr, np.nan)
                return arr, wt, ds.crs
    except Exception as e:
        logger.error(f"[S2] Error leyendo ventana de banda: {e}")
        return None


def _align(a, b):
    """Alinea dos arrays a la misma forma, reescalando el MENOR al MAYOR (10m).

    Así NDMI/NDRE (bandas 20m) se remuestrean a 10m usando la banda 10m de
    referencia, igual que hace EOSDA. Los valores siguen siendo reales.
    """
    if a.shape == b.shape:
        return a, b
    from scipy.ndimage import zoom
    target_h = max(a.shape[0], b.shape[0])
    target_w = max(a.shape[1], b.shape[1])
    if a.shape[0] < target_h or a.shape[1] < target_w:
        a = zoom(a, (target_h / a.shape[0], target_w / a.shape[1]), order=1)
    if b.shape[0] < target_h or b.shape[1] < target_w:
        b = zoom(b, (target_h / b.shape[0], target_w / b.shape[1]), order=1)
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    return a[:h, :w], b[:h, :w]


def _normalize_percentile(arr, low=2, high=98):
    """Estiramiento robusto 2-98 percentil para ver toda la variación de color."""
    valid = arr[np.isfinite(arr)]
    if valid.size == 0:
        return np.full_like(arr, np.nan)
    vmin = np.percentile(valid, low)
    vmax = np.percentile(valid, high)
    if vmax <= vmin:
        vmax = vmin + 1e-6
    return np.clip((arr - vmin) / (vmax - vmin), 0.0, 1.0)


def _normalize_standard(arr, vmin=-1.0, vmax=1.0):
    """Escala FIJA (ej. -1..1 para NDVI) → [0,1]. Comparable entre fechas/parcelas."""
    return np.clip((arr - vmin) / (vmax - vmin), 0.0, 1.0)


def _normalize_contrast(arr):
    """Estiramiento por cuartiles robustos (P5→0, P25→0.25, P50→0.5, P75→0.75, P95→1).

    Aumenta la separación visual entre valores cercanos usando el rango interno
    de la parcela, sin modificar el valor NDVI original. No usa min/max.
    """
    mask = np.isfinite(arr)
    valid = arr[mask]
    if valid.size < 10:
        return np.full_like(arr, np.nan)
    xp = [np.percentile(valid, 5), np.percentile(valid, 25), np.percentile(valid, 50),
          np.percentile(valid, 75), np.percentile(valid, 95)]
    fp = [0.0, 0.25, 0.5, 0.75, 1.0]
    # np.interp espera xp estrictamente creciente; asegurarlo
    if len(set(xp)) < 5:
        return np.full_like(arr, np.nan)
    mapped = np.interp(valid, xp, fp)
    out = np.full_like(arr, np.nan)
    out[mask] = np.clip(mapped, 0.0, 1.0)
    return out


def _compute_percentiles(arr):
    """Percentiles de la distribución de valores válidos (para Contrast View)."""
    valid = arr[np.isfinite(arr)]
    if valid.size == 0:
        return None
    return {
        'p2': round(float(np.percentile(valid, 2)), 4),
        'p5': round(float(np.percentile(valid, 5)), 4),
        'p10': round(float(np.percentile(valid, 10)), 4),
        'median': round(float(np.percentile(valid, 50)), 4),
        'p90': round(float(np.percentile(valid, 90)), 4),
        'p95': round(float(np.percentile(valid, 95)), 4),
        'p98': round(float(np.percentile(valid, 98)), 4),
    }


def _read_scl_mask(scl_href, geometry):
    """Lee SCL (Scene Classification L2A) y devuelve máscara bool (True = píxel válido).

    Enmascara: nubes, sombras de nubes, cirros, píxeles saturados/defectuosos
    y no-data, tal como documenta EOSDA para reproducir sus resultados.
    """
    if not scl_href:
        return None
    res = _read_band_window(scl_href, geometry)
    if res is None:
        return None
    scl, _, _ = res
    # Clases válidas: 2=área oscura, 4=vegetación, 5=no vegetado, 6=agua, 7=sin clasificar
    valid = np.isin(scl, [2, 4, 5, 6, 7]) & np.isfinite(scl)
    return valid


def _resample_mask(mask, target_shape):
    """Reescala una máscara bool a target_shape (nearest, sin interpolación)."""
    from scipy.ndimage import zoom
    if mask.shape[:2] == target_shape[:2]:
        return mask
    zh = target_shape[0] / mask.shape[0]
    zw = target_shape[1] / mask.shape[1]
    resampled = zoom(mask.astype(np.uint8), (zh, zw), order=0)
    h = min(resampled.shape[0], target_shape[0])
    w = min(resampled.shape[1], target_shape[1])
    return resampled[:h, :w] > 0


def _smooth(arr, method):
    """Agrupa valores parecidos en manchas uniformes (como el render de EOSDA).

    - 'median': filtro de mediana 5x5 (quita ruido de píxel individual, conserva bordes).
    - 'gaussian': desenfoque gaussiano (más uniforme y suave).
    """
    from scipy import ndimage
    mask = np.isfinite(arr)
    if mask.sum() < 10:
        return arr
    fill = float(np.nanmean(arr))
    work = np.where(mask, arr, fill)
    if method == 'median':
        work = ndimage.median_filter(work, size=3)
    elif method == 'gaussian':
        work = ndimage.gaussian_filter(work, sigma=1.0)
    return np.where(mask, work, np.nan)


def _apply_premium_finish(img):
    """Acabado fotográfico premium sobre el render (solo colores, NO el índice).

    Aumenta levemente vibrancia/saturación, profundiza sombras, mejora el
    contraste tonal y aplica nitidez muy ligera. Los valores científicos
    originales del índice permanecen intactos.
    """
    from PIL import Image, ImageEnhance
    rgba = img.convert('RGBA')
    r, g, b, a = rgba.split()
    rgb = Image.merge('RGB', (r, g, b))

    rgb = ImageEnhance.Color(rgb).enhance(1.18)       # vibrancia/saturación
    rgb = ImageEnhance.Contrast(rgb).enhance(1.06)    # contraste tonal (no del índice)
    rgb = ImageEnhance.Brightness(rgb).enhance(0.97)  # profundizar sombras
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.25)   # nitidez muy ligera

    r2, g2, b2 = rgb.split()
    return Image.merge('RGBA', (r2, g2, b2, a))


def _compute_index_arrays(scene, geometry):
    """Lee las bandas + SCL y devuelve {indice: array} con máscara de nubes/sombras."""
    scl_mask = _read_scl_mask(scene.get('scl_href'), geometry)
    arrays = {}
    for name, (hi_key, lo_key) in _BAND_PAIRS.items():
        hi_href = scene.get(hi_key)
        lo_href = scene.get(lo_key)
        if not hi_href or not lo_href:
            continue
        hi_res = _read_band_window(hi_href, geometry)
        lo_res = _read_band_window(lo_href, geometry)
        if hi_res is None or lo_res is None:
            continue
        hi, _, _ = hi_res
        lo, _, _ = lo_res
        hi, lo = _align(hi, lo)
        with np.errstate(divide='ignore', invalid='ignore'):
            if name == 'savi':
                idx = (hi - lo) / (hi + lo + 0.5) * 1.5
            else:
                idx = (hi - lo) / (hi + lo)
        idx = np.where(np.isfinite(idx), idx, np.nan)
        # Enmascarar nubes/sombras/cirros/saturados (SCL L2A, como EOSDA)
        if scl_mask is not None:
            m = _resample_mask(scl_mask, idx.shape)
            idx = np.where(m, idx, np.nan)
        arrays[name] = idx
    return arrays


def get_index_images(geometry, scene_date, mode='contrast', smoothing='none', exact_date=False):
    """Genera imágenes de color (base64 PNG) de NDVI/NDMI/SAVI/NDRE.

    mode: 'contrast' (adaptativo por percentiles) o 'standard' (escala fija).
    smoothing: 'none' | 'median' | 'gaussian'.
    exact_date: si True, usa la escena EXACTA de scene_date (no la mejor de ±10 días).
    """
    import io
    import base64
    from PIL import Image

    scene = search_sentinel2_scene(geometry, scene_date, exact_date=exact_date)
    if not scene:
        return None
    arrays = _compute_index_arrays(scene, geometry)

    out = {}
    for name, idx in arrays.items():
        if smoothing in ('median', 'gaussian'):
            idx = _smooth(idx, smoothing)
        if np.isfinite(idx).sum() < 10:
            continue

        if mode == 'standard':
            norm = _normalize_standard(idx, -1.0, 1.0)
        else:
            norm = _normalize_contrast(idx)

        if name == 'ndmi':
            cmap = _CMAP_STOPS_NDMI
        elif name == 'ndre':
            cmap = _CMAP_STOPS_NDRE
        else:
            cmap = _CMAP_STOPS  # ndvi, savi
        img_arr = _apply_colormap(norm, cmap)
        # rasterio read() ya viene norte-arriba (NO flipud)
        img = Image.fromarray(img_arr, 'RGBA')
        # Interpolación bilinear suave (resolución real, sin difuminado excesivo)
        target_side = 500
        w, h = img.size
        scale = target_side / max(w, h)
        if scale > 1:
            img = img.resize((int(w * scale), int(h * scale)), Image.BILINEAR)
        img = _apply_premium_finish(img)
        buf = io.BytesIO()
        img.save(buf, format='PNG', optimize=True)
        out[name] = base64.b64encode(buf.getvalue()).decode('utf-8')

    return out or None


def get_index_analysis(geometry, scene_date, exact_date=False):
    """Estadísticas + percentiles de cada índice (mismos valores que las imágenes).

    Retorna dict {indice: {mean, min, max, std, percentiles: {...}}} o None.
    """
    scene = search_sentinel2_scene(geometry, scene_date, exact_date=exact_date)
    if not scene:
        return None
    arrays = _compute_index_arrays(scene, geometry)

    analysis = {}
    for name, arr in arrays.items():
        valid = arr[np.isfinite(arr)]
        if valid.size == 0:
            analysis[name] = None
            continue
        analysis[name] = {
            'mean': round(float(np.nanmean(valid)), 4),
            'min': round(float(np.nanmin(valid)), 4),
            'max': round(float(np.nanmax(valid)), 4),
            'std': round(float(np.nanstd(valid)), 4),
            'percentiles': _compute_percentiles(valid),
        }
    return analysis or None


# Categorías agronómicas NDVI (umbrales estándar de cultivos)
NDVI_CATEGORIES = [
    ('vegetacion_escasa', 'Vegetación Escasa', -np.inf, 0.25),
    ('estres_moderado', 'Estrés Moderado', 0.25, 0.40),
    ('vigor_bajo', 'Vigor Bajo', 0.40, 0.50),
    ('vegetacion_densa', 'Vegetación Densa', 0.50, 0.65),
    ('vegetacion_muy_densa', 'Vegetación Muy Densa', 0.65, 0.75),
    ('vigor_optimo', 'Vigor Óptimo', 0.75, np.inf),
]


def get_index_categories(geometry, scene_date, index='ndvi', exact_date=False):
    """Clasifica los píxeles válidos del índice en categorías agronómicas REALES.

    Retorna {index, total_pixels, mean, categories: [{key, label, pct, count}],
             alerts: [...], recommendations: [...]} o None.
    """
    scene = search_sentinel2_scene(geometry, scene_date, exact_date=exact_date)
    if not scene:
        return None
    arrays = _compute_index_arrays(scene, geometry)
    arr = arrays.get(index)
    if arr is None:
        return None
    valid = arr[np.isfinite(arr)]
    total = valid.size
    if total == 0:
        return None

    categories = []
    for key, label, lo, hi in NDVI_CATEGORIES:
        count = int(((valid >= lo) & (valid < hi)).sum())
        categories.append({
            'key': key,
            'label': label,
            'pct': round(count / total * 100, 1),
            'count': count,
        })

    pct_map = {c['key']: c['pct'] for c in categories}
    alerts = []
    recommendations = []
    if pct_map['vegetacion_escasa'] > 30:
        alerts.append('Atención requerida: se detectan zonas con vegetación escasa o suelo expuesto.')
        recommendations.append('Inspeccionar en campo las áreas con menor NDVI.')
    if pct_map['estres_moderado'] + pct_map['vigor_bajo'] > 40:
        alerts.append('Posible estrés nutricional o hídrico en algunas zonas.')
        recommendations.append('Revisar el plan de fertilización y riego en las zonas de estrés.')
    if pct_map['vegetacion_densa'] + pct_map['vegetacion_muy_densa'] + pct_map['vigor_optimo'] > 50:
        recommendations.append('El cultivo presenta buena cobertura en la mayor parte de la parcela.')

    return {
        'index': index,
        'total_pixels': int(total),
        'mean': round(float(np.nanmean(valid)), 4),
        'categories': categories,
        'alerts': alerts,
        'recommendations': recommendations,
    }


def get_index_time_series(geometry, date_from=None, date_to=None, days_back=180, max_scenes=12):
    """Serie temporal de NDVI/NDMI/SAVI/NDRE por escena (evolución del cultivo).

    Retorna lista de {date, cloud_cover, ndvi_mean, ndmi_mean, savi_mean,
    ndre_mean} ordenada por fecha, o lista vacía.

    Optimización: filtra escenas con nubosidad >60% (inútiles) y cachea el
    resultado 7 días (la lectura de COGs reales es costosa, ~1-2 min la primera vez).
    """
    if not date_to:
        date_to = datetime.utcnow().strftime('%Y-%m-%d')
    if not date_from:
        date_from = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')

    cache_key = f"s2:series:{hashlib_md5_geometry(geometry)}:{date_from}:{date_to}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Buscar más escenas de las que usaremos, para poder filtrar por nubosidad.
    # `max_results` alto (250) para cubrir un año completo de pasadas (~3 satélites).
    scenes = search_sentinel2_scenes(
        geometry, date_from=date_from, date_to=date_to, max_results=250
    )
    # Solo escenas con nubosidad <= 30% (calidad para el gráfico)
    scenes = [s for s in scenes if s.get('cloud_cover') is not None and s['cloud_cover'] <= 30]

    # Agrupar por mes y quedarnos con la MEJOR escena (menor nubosidad) de cada mes.
    # Así el gráfico no se satura: 1 punto limpio por mes.
    by_month = {}
    for s in scenes:
        month = (s.get('date') or '')[:7]
        if month not in by_month or (s['cloud_cover'] or 100) < (by_month[month]['cloud_cover'] or 100):
            by_month[month] = s

    scenes_sorted = sorted(by_month.values(), key=lambda s: s.get('date', ''))[:max_scenes]

    series = []
    for scene in scenes_sorted:
        arrays = _compute_index_arrays(scene, geometry)
        if not arrays:
            continue
        point = {
            'date': scene.get('date'),
            'cloud_cover': round(scene['cloud_cover'], 1) if scene.get('cloud_cover') is not None else None,
        }
        for name in ['ndvi', 'ndmi', 'savi', 'ndre']:
            arr = arrays.get(name)
            if arr is not None:
                valid = arr[np.isfinite(arr)]
                if valid.size > 0:
                    point[f'{name}_mean'] = round(float(np.nanmean(valid)), 4)
        series.append(point)

    cache.set(cache_key, series, INDICES_CACHE_TTL)
    return series


def get_bounds(geometry):
    """Devuelve [west, south, east, north] (bbox lon/lat) del polígono."""
    bbox = _geometry_bbox_lonlat(geometry)
    if not bbox:
        return None
    min_lon, min_lat, max_lon, max_lat = bbox
    return [min_lon, min_lat, max_lon, max_lat]


# ---------------------------------------------------- estadísticas y cambio a radar


# Umbral de nubosidad por encima del cual se recomienda radar
CLOUD_THRESHOLD = 30.0


def _public_scene_list(scenes):
    """Convierte escenas internas (con hrefs) a una lista pública sin URLs firmadas."""
    return [
        {
            "id": s.get("id"),
            "date": s.get("date"),
            "cloud_cover": round(s["cloud_cover"], 1) if s.get("cloud_cover") is not None else None,
            "platform": s.get("platform"),
        }
        for s in scenes
    ]


def get_observation_recommendation(geometry, scene_date):
    """Recomendación de observación: óptica (S2) o radar (S1) según nubosidad."""
    scenes = search_sentinel2_scenes(geometry, scene_date, max_results=10)
    if not scenes:
        return {
            "available": False,
            "satellite": None,
            "cloud_cover": None,
            "message": "No hay escenas Sentinel-2 disponibles en el rango de fechas.",
            "s2_scenes": [],
        }

    best = scenes[0]
    cloud = best.get("cloud_cover")

    if cloud is not None and cloud > CLOUD_THRESHOLD:
        return {
            "available": True,
            "satellite": "sentinel1",
            "cloud_cover": cloud,
            "message": (
                f"La mejor escena óptica tiene {cloud:.0f}% de nubosidad (más del {CLOUD_THRESHOLD:.0f}%). "
                "Se recomienda radar Sentinel-1: atraviesa las nubes y detecta cambios, "
                "pero no mide vigor NDVI."
            ),
            "s2_scenes": _public_scene_list(scenes[:5]),
        }

    return {
        "available": True,
        "satellite": "sentinel2",
        "cloud_cover": cloud,
        "message": (
            f"Escena óptica disponible con {cloud:.0f}% de nubosidad."
            if cloud is not None else "Escena óptica disponible."
        ),
        "s2_scenes": _public_scene_list(scenes[:5]),
    }


# ------------------------------------------------------------------- endpoint

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


class Sentinel2IndexImagesView(APIView):
    """Imágenes de color + estadísticas (NDVI/NDMI/SAVI/NDRE) desde Sentinel-2 real.

    GET /api/parcels/parcel/<parcel_id>/sentinel2-images/?scene_date=YYYY-MM-DD
    → { "images": {ndvi, ndmi, savi, ndre}, "statistics": {...}, "scene": {...} }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, parcel_id):
        from datetime import date
        from django.shortcuts import get_object_or_404
        from .models import Parcel

        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
        if not parcel.geom or not isinstance(parcel.geom, dict):
            return Response(
                {"error": "La parcela no tiene geometría."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scene_date = request.query_params.get("scene_date") or str(date.today())
        smoothing = request.query_params.get("smoothing", "none")
        mode = request.query_params.get("mode", "contrast")
        exact_date = request.query_params.get("exact_date", "false").lower() in ("1", "true", "yes")
        images = get_index_images(parcel.geom, scene_date, mode=mode, smoothing=smoothing, exact_date=exact_date)
        if not images:
            return Response(
                {"error": "No se encontró una escena Sentinel-2 real para esta fecha."},
                status=status.HTTP_404_NOT_FOUND,
            )
        analysis = get_index_analysis(parcel.geom, scene_date, exact_date=exact_date)
        analysis_index = request.query_params.get("analysis_index", "ndvi")
        categories = get_index_categories(parcel.geom, scene_date, index=analysis_index, exact_date=exact_date)
        scene = search_sentinel2_scene(parcel.geom, scene_date, exact_date=exact_date)
        return Response({
            "images": images,
            "statistics": analysis,
            "analysis": categories,
            "scene": _public_scene_list([scene])[0] if scene else None,
            "bounds": get_bounds(parcel.geom),
        }, status=status.HTTP_200_OK)


class Sentinel2ScenesView(APIView):
    """Lista de escenas Sentinel-2 con nubosidad, ordenadas de menor a mayor.

    GET /api/parcels/parcel/<parcel_id>/sentinel2-scenes/?scene_date=YYYY-MM-DD
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, parcel_id):
        from datetime import date
        from django.shortcuts import get_object_or_404
        from .models import Parcel

        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
        if not parcel.geom or not isinstance(parcel.geom, dict):
            return Response(
                {"error": "La parcela no tiene geometría."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        scene_date = request.query_params.get("scene_date")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if date_from and date_to:
            scenes = search_sentinel2_scenes(
                parcel.geom, date_from=date_from, date_to=date_to, max_results=50
            )
        else:
            scenes = search_sentinel2_scenes(parcel.geom, scene_date or str(date.today()), max_results=20)
        return Response({"scenes": _public_scene_list(scenes), "total": len(scenes)}, status=status.HTTP_200_OK)


class Sentinel2ObservationView(APIView):
    """Recomendación de observación (óptica vs radar) según nubosidad.

    GET /api/parcels/parcel/<parcel_id>/observation/?scene_date=YYYY-MM-DD
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, parcel_id):
        from datetime import date
        from django.shortcuts import get_object_or_404
        from .models import Parcel

        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
        if not parcel.geom or not isinstance(parcel.geom, dict):
            return Response(
                {"error": "La parcela no tiene geometría."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        scene_date = request.query_params.get("scene_date") or str(date.today())
        rec = get_observation_recommendation(parcel.geom, scene_date)
        return Response(rec, status=status.HTTP_200_OK)


class Sentinel2HistoryView(APIView):
    """Serie temporal de índices Sentinel-2 (evolución del cultivo).

    GET /api/parcels/parcel/<parcel_id>/sentinel2-history/?days_back=180
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, parcel_id):
        from django.shortcuts import get_object_or_404
        from .models import Parcel

        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
        if not parcel.geom or not isinstance(parcel.geom, dict):
            return Response(
                {"error": "La parcela no tiene geometría."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        days_back = int(request.query_params.get("days_back", 180))
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        series = get_index_time_series(
            parcel.geom, date_from=date_from, date_to=date_to, days_back=days_back
        )
        return Response({"series": series, "total": len(series)}, status=status.HTTP_200_OK)
