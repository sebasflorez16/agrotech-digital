"""
Sentinel-1 SAR — Monitoreo radar real (sin datos simulados).

AgroTech usa Sentinel-1 como sistema COMPLEMENTARIO de vigilancia (no sustituye
el análisis óptico de Sentinel-2). Cuando la nubosidad bloquea la observación
óptica, el radar mantiene la continuidad y puede señalar cambios que requieren
revisión.

FUENTE DE DATOS
---------------
- Fuente principal: **Microsoft Planetary Computer — Sentinel-1 RTC**
  (Radiometric Terrain Corrected).
  * Búsqueda: STAC público `https://planetarycomputer.microsoft.com/api/stac/v1/search`
    (sin credenciales).
  * Datos: Cloud-Optimized GeoTIFF (COG) + firma SAS pública
    `https://planetarycomputer.microsoft.com/api/sas/v1/sign` (sin credenciales).
  * Se lee SOLO la ventana de la AOI (por rango HTTP), sin descargar ~1GB.
- Producto: GRD (Ground Range Detected), modo IW, polarizaciones VV + VH.
  RTC ya viene como sigma0 calibrado (corrección radiométrica + terreno + ángulo
  de incidencia), lo que permite COMPARAR observaciones entre fechas.

POR QUÉ RTC Y NO SLC / GRD CRUDO
--------------------------------
- SLC conserva fase (interferometría); no es para monitoreo agrícola.
- GRD crudo requiere aplicar calibración y descargar ~1GB por producto.
- RTC es sigma0 listo, en COG, y solo se lee el área de interés.

COMPARABILIDAD
--------------
Para comparar observaciones se usa la MISMA órbita relativa (`sat:relative_orbit`),
de modo que los cambios se miden sobre geometría de adquisición comparable.

REGLAS
------
- NUNCA se inventan valores. Si no hay sigma0 real, se devuelve
  "Datos radar no disponibles para esta fecha".
- Un cambio se clasifica como "Cambio detectado — requiere revisión", NUNCA como
  "cultivo enfermo".
"""

import logging
import math
import hashlib
import time
from collections import Counter

import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache

import numpy as np

try:
    import rasterio
    from rasterio.windows import from_bounds, Window
    from rasterio.warp import transform_bounds
except ImportError:
    rasterio = None

logger = logging.getLogger(__name__)

PLANETARY_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PLANETARY_SAS_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
S1_COLLECTION = "sentinel-1-rtc"

SAS_CACHE_TTL = 600            # 10 min (los tokens SAS tienen TTL corto)
SIGMA0_CACHE_TTL = 7 * 86400  # 7 días: sigma0 medio por parcela+escena es estable


# ---------------------------------------------------------------- firma SAS

def _sign_url(href):
    """Firma pública del COG (SAS) con caché breve y reintentos."""
    key = f"s1:sas:{href[-80:]}"
    signed = cache.get(key)
    if signed:
        return signed
    for attempt in range(4):
        try:
            r = requests.get(PLANETARY_SAS_URL, params={"href": href}, timeout=30)
            if r.status_code == 200:
                signed = r.json().get("href")
                if signed:
                    cache.set(key, signed, SAS_CACHE_TTL)
                    return signed
            logger.warning(f"[S1] SAS sign intento {attempt + 1} status={r.status_code}")
            if r.status_code == 429:
                # Límite de tasa: respetar Retry-After y esperar con backoff.
                retry_after = r.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else (2 ** attempt)
                except (TypeError, ValueError):
                    wait = 2 ** attempt
                time.sleep(min(max(wait, 1.0), 10.0))
                continue
        except Exception as e:
            logger.warning(f"[S1] Error firmando URL (intento {attempt + 1}): {e}")
        time.sleep(min(2 ** attempt, 8))
    return None


def _invalidate_sas(href):
    """Invalida la firma SAS cacheada para reintentar con una nueva."""
    try:
        cache.delete(f"s1:sas:{href[-80:]}")
    except Exception:
        pass


# --------------------------------------------------------------- geometría

def _geometry_bbox_lonlat(geometry):
    coords = geometry.get('coordinates', [[]])[0]
    if not coords or len(coords) < 3:
        return None
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return (min(lngs), min(lats), max(lngs), max(lats))


# --------------------------------------------------------------- búsqueda

def search_sentinel1_scenes(geometry, date_from, date_to, max_results=10):
    """
    Búsqueda STAC de escenas Sentinel-1 RTC sobre una geometría.

    Retorna lista de dicts: id, date, polarisation, relative_orbit, platform,
    vv_href, vh_href. Lista vacía si no hay escenas o la búsqueda falla.
    """
    try:
        body = {
            "collections": [S1_COLLECTION],
            "intersects": geometry,
            "datetime": f"{date_from}T00:00:00Z/{date_to}T23:59:59Z",
            "limit": max_results,
            "sortby": [{"field": "properties.datetime", "direction": "desc"}],
        }
        r = requests.post(PLANETARY_STAC_URL, json=body, timeout=30)
        if r.status_code != 200:
            logger.warning(f"[S1] STAC search failed: {r.status_code}")
            return []

        scenes = []
        for f in r.json().get("features", []):
            pr = f.get("properties", {})
            assets = f.get("assets", {})
            vv = (assets.get("vv") or {}).get("href", "")
            vh = (assets.get("vh") or {}).get("href", "")
            if not vv or not vh:
                continue
            scenes.append({
                "id": f.get("id", ""),
                "date": (pr.get("datetime") or "")[:10],
                "polarisation": "VV+VH",
                "relative_orbit": pr.get("sat:relative_orbit"),
                "platform": pr.get("platform", "S1"),
                "vv_href": vv,
                "vh_href": vh,
            })
        return scenes
    except Exception as e:
        logger.error(f"[S1] Error STAC search: {e}")
        return []


# --------------------------------------------------- extracción real de sigma0

def _mean_sigma0_db(href, bbox_lonlat):
    """
    Lee el COG SOLO en la ventana del bbox y devuelve sigma0 medio en dB.

    El raster RTC está en EPSG UTM; se transforma el bbox lon/lat al CRS del
    raster antes de leer la ventana. Se usa lectura por rango HTTP (no descarga
    completa). Retorna None si no es posible (sin rasterio, error, fuera de área).
    """
    if rasterio is None:
        return None
    for attempt in range(2):
        signed = _sign_url(href)
        if not signed:
            _invalidate_sas(href)
            continue
        try:
            with rasterio.Env(
                GDAL_HTTP_MULTIRANGE="YES",
                CPL_VSIL_CURL_USE_HEAD="NO",
                GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            ):
                with rasterio.open(signed) as ds:
                    bb = transform_bounds("EPSG:4326", ds.crs, *bbox_lonlat)
                    w = from_bounds(*bb, ds.transform).intersection(Window(0, 0, ds.width, ds.height))
                    if w.width <= 0 or w.height <= 0:
                        return None
                    arr = ds.read(1, window=w).astype("float64")
                    arr = arr[arr > 0]  # descartar no-data (0)
                    if arr.size == 0:
                        return None
                    return 10.0 * math.log10(float(np.mean(arr)))
        except Exception as e:
            logger.warning(f"[S1] Error leyendo sigma0 (intento {attempt + 1}): {e}")
            _invalidate_sas(href)
    return None


def _sigma0_for_scene(scene, bbox_lonlat):
    """Extrae vv/vh sigma0 de una escena (con caché por escena+bbox)."""
    key = f"s1:sigma0:{scene['id']}:{hashlib.md5(str(bbox_lonlat).encode()).hexdigest()[:16]}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    vv = _mean_sigma0_db(scene["vv_href"], bbox_lonlat)
    vh = _mean_sigma0_db(scene["vh_href"], bbox_lonlat)
    if vv is None or vh is None:
        return None

    result = {"vv_db": round(vv, 3), "vh_db": round(vh, 3)}
    cache.set(key, result, SIGMA0_CACHE_TTL)
    return result


# ------------------------------------------------------------- serie temporal

def _dominant_orbit(scenes):
    """Órbita relativa con más escenas (para comparabilidad)."""
    orbits = [s.get("relative_orbit") for s in scenes if s.get("relative_orbit")]
    if not orbits:
        return None
    return Counter(orbits).most_common(1)[0][0]


def get_radar_time_series(geometry, date_from, date_to, max_results=10):
    """
    Serie temporal de observaciones radar REALES (sigma0 VV/VH), ordenada por
    fecha y restringida a la órbita relativa dominante (comparabilidad).

    Cada elemento: {date, scene_id, relative_orbit, vv_db, vh_db, available, source}.
    `available=False` significa "Datos radar no disponibles para esta fecha".
    """
    bbox = _geometry_bbox_lonlat(geometry)
    if not bbox:
        return []

    try:
        scenes = search_sentinel1_scenes(geometry, date_from, date_to, max_results=max_results)
    except Exception as e:
        logger.error(f"[S1] Error buscando escenas: {e}")
        return []

    if not scenes:
        return []

    best_orbit = _dominant_orbit(scenes)
    if best_orbit:
        scenes = [s for s in scenes if s.get("relative_orbit") == best_orbit]

    series = []
    for scene in scenes:
        try:
            vals = _sigma0_for_scene(scene, bbox)
        except Exception as e:
            logger.error(f"[S1] Error extrayendo sigma0 para {scene.get('id')}: {e}")
            vals = None
        series.append({
            "date": scene.get("date", ""),
            "scene_id": scene.get("id", ""),
            "relative_orbit": scene.get("relative_orbit"),
            "polarisation": "VV+VH",
            "vv_db": vals["vv_db"] if vals else None,
            "vh_db": vals["vh_db"] if vals else None,
            "available": vals is not None,
            "source": "radar",
        })
    series.sort(key=lambda x: x["date"])
    return series


# ------------------------------------------------------------ capas raster
# Lectura de la ventana COMPLETA del COG → grilla real de sigma0 por píxel,
# para colorear la parcela (como el heatmap de elevación, pero datos radar reales).

def read_aoi_sigma0(scene, geometry, max_side=800):
    """
    Lee la ventana del COG sobre la AOI y devuelve la grilla de sigma0 (lineal)
    para VV y VH, enmascarada al polígono de la parcela (NaN fuera).

    Retorna (vv, vh, bounds_lonlat) con vv/vh = numpy arrays; None si no es posible.
    """
    if rasterio is None:
        return None
    bbox = _geometry_bbox_lonlat(geometry)
    if not bbox:
        return None

    from rasterio.features import geometry_mask
    from rasterio.warp import transform_geom

    def _read(href):
        for attempt in range(2):
            signed = _sign_url(href)
            if not signed:
                _invalidate_sas(href)
                continue
            try:
                with rasterio.Env(
                    GDAL_HTTP_MULTIRANGE="YES",
                    CPL_VSIL_CURL_USE_HEAD="NO",
                    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                ):
                    with rasterio.open(signed) as ds:
                        bb = transform_bounds("EPSG:4326", ds.crs, *bbox)
                        window = from_bounds(*bb, ds.transform).intersection(Window(0, 0, ds.width, ds.height))
                        if window.width <= 0 or window.height <= 0:
                            return None
                        if window.width > max_side or window.height > max_side:
                            return None
                        arr = ds.read(1, window=window).astype("float64")
                        arr = np.where(arr > 0, arr, np.nan)
                        # Enmascarar al polígono (reproyectado al CRS del raster)
                        wt = ds.window_transform(window)
                        geom_crs = transform_geom("EPSG:4326", ds.crs, geometry)
                        mask = geometry_mask([geom_crs], out_shape=arr.shape, transform=wt, invert=True)
                        arr = np.where(mask, arr, np.nan)
                        return arr
            except Exception as e:
                logger.warning(f"[S1] Error leyendo raster AOI (intento {attempt + 1}): {e}")
                _invalidate_sas(href)
        return None

    vv = _read(scene.get("vv_href"))
    vh = _read(scene.get("vh_href"))
    if vv is None or vh is None:
        return None
    if vv.shape != vh.shape:
        h = min(vv.shape[0], vh.shape[0])
        w = min(vv.shape[1], vh.shape[1])
        vv, vh = vv[:h, :w], vh[:h, :w]
    return vv, vh, bbox


def _linear_to_db(arr):
    """Convierte sigma0 lineal a dB (NaN se conserva)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return 10.0 * np.log10(arr)


def compute_rvi(vv_linear, vh_linear):
    """
    Radar Vegetation Index: 4*VH/(VV+VH), en [0,1].
    Recibe sigma0 LINEAL (no dB). NaN donde no hay dato.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = vv_linear + vh_linear
        rvi = np.where(denom > 0, 4.0 * vh_linear / denom, np.nan)
    return np.clip(rvi, 0.0, 1.0)


def _grid_to_png(arr, vmin, vmax, colormap):
    """
    Convierte una grilla 2D a PNG base64 con colormap.
    arr: numpy array (NaN = transparente).
    colormap: 'sigma0' (backscatter), 'rvi' (vegetación) o 'change'.
    """
    import io
    import base64
    from PIL import Image

    valid = arr[~np.isnan(arr)]
    if valid.size == 0:
        return None

    lo = vmin if vmin is not None else float(np.nanmin(valid))
    hi = vmax if vmax is not None else float(np.nanmax(valid))
    span = hi - lo if hi > lo else 1e-9
    norm = np.clip((arr - lo) / span, 0.0, 1.0)

    if colormap == "rvi":
        stops = [(0.0, (120, 60, 20)), (0.5, (200, 180, 60)), (1.0, (20, 120, 40))]
    elif colormap == "change":
        stops = [(0.0, (255, 220, 60)), (0.5, (240, 140, 20)), (1.0, (200, 30, 30))]
    else:  # sigma0 VV/VH
        stops = [(0.0, (20, 30, 60)), (0.4, (60, 140, 200)), (0.7, (120, 180, 80)), (1.0, (230, 210, 40))]

    lut = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        t = i / 255.0
        for k in range(len(stops) - 1):
            t0, c0 = stops[k]
            t1, c1 = stops[k + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0) if t1 > t0 else 0
                lut[i] = [int(c0[c] + (c1[c] - c0[c]) * f) for c in range(3)]
                break
        else:
            lut[i] = stops[-1][1]

    idx = (np.nan_to_num(norm, nan=0.0) * 255).astype(np.uint8)
    rgb = lut[idx]
    alpha = np.where(np.isnan(arr), 0, 220).astype(np.uint8)[..., None]
    rgba = np.concatenate([rgb, alpha], axis=-1).astype(np.uint8)

    img = Image.fromarray(rgba, "RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _change_grid_to_png(mag, threshold_db=2.0):
    """Heatmap de cambio: transparente sin cambio, naranja→rojo con cambio."""
    import io
    import base64
    from PIL import Image

    valid = mag[~np.isnan(mag)]
    if valid.size == 0:
        return None

    # alpha solo donde hubo cambio (> umbral)
    changed = np.where(np.isnan(mag), False, mag > threshold_db)
    # color según intensidad relativa del cambio
    hi = float(np.nanmax(valid)) if valid.size else threshold_db
    span = hi - threshold_db if hi > threshold_db else 1e-9
    intensity = np.nan_to_num(np.clip((mag - threshold_db) / span, 0.0, 1.0), nan=0.0)

    lut = np.zeros((256, 3), dtype=np.uint8)
    for i in range(256):
        t = i / 255.0
        # naranja → rojo
        lut[i] = [int(255 - 55 * t), int(140 - 110 * t), int(30)]

    idx = (intensity * 255).astype(np.uint8)
    rgb = lut[idx]
    alpha = np.where(changed, 190, 0).astype(np.uint8)[..., None]
    rgba = np.concatenate([rgb, alpha], axis=-1).astype(np.uint8)

    img = Image.fromarray(rgba, "RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _change_threshold_db():
    """Umbral de cambio significativo por píxel (dB) — configurable en settings."""
    try:
        return float(getattr(settings, "SENTINEL1_CHANGE_THRESHOLD_DB", 6.0))
    except (TypeError, ValueError):
        return 6.0


def _compute_radar_layers(geometry, date_from, date_to, target_date=None):
    """
    Calcula (sin caché) las capas radar + el cambio entre la última y la anterior
    observación. Siempre genera las imágenes; `get_radar_layers` decide qué
    devolver y se encarga de la caché compartida.

    target_date: si se indica, elige la observación MÁS CERCANA a esa fecha (para
    la cadena "sin óptico → radar más cercano") en vez de la más reciente.

    Retorna:
    {
        'available': bool,
        'layers': {'date': ..., 'vv': {image_base64, bounds}, 'vh': {...}, 'rvi': {...}} | None,
        'change': {'change_detected', 'changed_cells', 'mean_magnitude_db',
                   'max_magnitude_db', 'change_heatmap', 'bounds', 'from_date', 'to_date'} | None,
    }
    """
    try:
        scenes = search_sentinel1_scenes(geometry, date_from, date_to, max_results=8)
    except Exception as e:
        logger.error(f"[S1] Error search en capas: {e}")
        scenes = []

    if not scenes:
        return {"available": False, "layers": None, "change": None}

    best_orbit = _dominant_orbit(scenes)
    if best_orbit:
        scenes = [s for s in scenes if s.get("relative_orbit") == best_orbit]
    if not scenes:
        return {"available": False, "layers": None, "change": None}

    # Escena a mostrar y su comparación.
    if target_date:
        def _proximity(scene):
            try:
                sd = datetime.strptime(str(scene.get("date"))[:10], "%Y-%m-%d").date()
                td = datetime.strptime(str(target_date)[:10], "%Y-%m-%d").date()
                return abs((sd - td).days)
            except (TypeError, ValueError):
                return 10 ** 6
        latest = min(scenes, key=_proximity)
        earlier = [s for s in scenes if s.get("date", "") < latest.get("date", "")]
        later = [s for s in scenes if s.get("date", "") > latest.get("date", "")]
        if earlier:
            prev = max(earlier, key=lambda s: s.get("date", ""))
        elif later:
            prev = min(later, key=lambda s: s.get("date", ""))
        else:
            prev = None
    else:
        latest = scenes[0]
        prev = scenes[1] if len(scenes) > 1 else None

    result = read_aoi_sigma0(latest, geometry)
    if result is None:
        return {"available": False, "layers": None, "change": None}

    vv, vh, bounds = result
    vv_db = _linear_to_db(vv)
    vh_db = _linear_to_db(vh)

    rvi = compute_rvi(vv, vh)
    o = list(bounds)
    layers = {
        "date": latest.get("date", ""),
        "scene_id": latest.get("id", ""),
        "vv": {"image_base64": _grid_to_png(vv_db, -25, 0, "sigma0"), "bounds": o},
        "vh": {"image_base64": _grid_to_png(vh_db, -30, -5, "sigma0"), "bounds": o},
        "rvi": {"image_base64": _grid_to_png(rvi, 0, 1, "rvi"), "bounds": o},
    }

    change = None
    change_error = False
    if prev is not None:
        prev_result = read_aoi_sigma0(prev, geometry)
        if prev_result is None:
            # Fallo transitorio (p. ej. 429 de SAS): NO cachear el resultado
            # incompleto para permitir que el siguiente intento se recupere.
            change_error = True
        else:
            pvv, pvh, _ = prev_result
            pvv_db = _linear_to_db(pvv)
            pvh_db = _linear_to_db(pvh)
            h = min(vv_db.shape[0], pvv_db.shape[0])
            w = min(vv_db.shape[1], pvv_db.shape[1])
            dv = vv_db[:h, :w] - pvv_db[:h, :w]
            dh = vh_db[:h, :w] - pvh_db[:h, :w]
            threshold = _change_threshold_db()
            mag = np.abs(dv) + np.abs(dh)
            changed = np.where(np.isnan(mag), False, mag > threshold)
            changed_pct = round(float(np.sum(changed) / max(1, np.sum(~np.isnan(mag))) * 100.0), 1)
            # Niveles calibrados: <5% estable; 5–30% revisar; >=30% revisar pronto
            # (el evento real medido fue ~50% del lote).
            if changed_pct < 5:
                attention = "none"
            elif changed_pct >= 30:
                attention = "high"
            else:
                attention = "moderate"
            change = {
                "from_date": min(prev.get("date", ""), latest.get("date", "")),
                "to_date": max(prev.get("date", ""), latest.get("date", "")),
                "threshold_db": threshold,
                "metric": "por_pixel",
                "kind": "cambio_reciente",
                "change_detected": bool(np.any(changed)),
                "attention_level": attention,
                "changed_cells": int(np.sum(changed)),
                "total_cells": int(np.sum(~np.isnan(mag))),
                "changed_percent": changed_pct,
                "mean_magnitude_db": round(float(np.nanmean(mag)), 2),
                "max_magnitude_db": round(float(np.nanmax(mag)), 2) if np.any(~np.isnan(mag)) else 0.0,
                "change_heatmap": _change_grid_to_png(mag, threshold),
                "bounds": list(bounds),
            }

    return {"available": True, "layers": layers, "change": change, "change_error": change_error}


# Caché del cálculo radar por geometría + rango de fechas. Compartida por
# /radar/ (solo resumen) y /radar-layers/ (imágenes), para leer los COGs una vez.
RADAR_LAYERS_CACHE_TTL = 3600  # 1 hora


def _radar_layers_cache_key(geometry, date_from, date_to, target_date=None):
    h = hashlib.md5(str(geometry).encode()).hexdigest()[:16]
    return f"s1:core:{h}:{date_from}:{date_to}:{target_date or '-'}:{_change_threshold_db()}"


def get_radar_layers(geometry, date_from, date_to, include_images=True, force=False, target_date=None):
    """Capa radar + cambio por píxel, con caché compartida entre endpoints.

    El cálculo pesado (lectura de los dos COGs) se ejecuta UNA vez por geometría y
    rango de fechas y queda en caché. `include_images=False` devuelve el mismo
    resumen sin los PNGs (para el texto del monitoreo). `force=True` ignora la
    caché (botón "Actualizar radar").
    """
    key = _radar_layers_cache_key(geometry, date_from, date_to, target_date)
    core = None if force else cache.get(key)
    if core is None:
        core = _compute_radar_layers(geometry, date_from, date_to, target_date=target_date)
        change_error = bool(core.pop("change_error", False))
        # Solo cachear resultados completos: si no hubo datos o falló la lectura
        # de la pasada anterior, se reintenta en la siguiente petición.
        if core.get("available") and not change_error:
            try:
                cache.set(key, core, RADAR_LAYERS_CACHE_TTL)
            except Exception:
                pass

    if include_images:
        return core

    # Versión ligera (sin PNGs) para el endpoint de monitoreo.
    layers = core.get("layers")
    light_layers = None
    if layers:
        light_layers = {"date": layers.get("date"), "scene_id": layers.get("scene_id")}
    change = core.get("change")
    if change:
        change = {k: v for k, v in change.items() if k != "change_heatmap"}
    return {"available": core.get("available"), "layers": light_layers, "change": change}


# ------------------------------------------------------ detección de cambio

def _classify_change(vv_diff, vh_diff):
    """
    Clasifica el TIPO de cambio radar a partir de los deltas VV/VH.

    Interpretación cautelosa (hipótesis, nunca diagnóstico):
      - VV (co-polar): sensible a humedad/rugosidad del suelo y estructura.
      - VH (cross-polar): sensible al volumen del dosel (biomasa).

    Devuelve una lista de frases cortas en español.
    """
    reasons = []
    if vv_diff < -2.0:
        reasons.append("disminuyó VV (posible cosecha, pérdida de biomasa o mayor humedad)")
    elif vv_diff > 2.0:
        reasons.append("aumentó VV (posible crecimiento vegetal o mayor rugosidad del suelo)")
    if vh_diff < -1.5:
        reasons.append("disminuyó VH (posible pérdida de estructura del dosel)")
    elif vh_diff > 1.5:
        reasons.append("aumentó VH (posible mayor volumen vegetal)")
    return reasons or ["variación moderada de la señal radar"]


def detect_radar_change(series, threshold_db=None):
    """
    Compara las observaciones reales de la serie temporal.

    Un cambio de backscatter puede deberse a humedad, estructura de la
    vegetación, suelo, manejo o agua. Por eso el resultado es SIEMPRE
    "Cambio detectado — requiere revisión" (nunca "cultivo enfermo").

    threshold_db=None usa el umbral calibrado de settings (mismo que la capa).
    """
    if threshold_db is None:
        threshold_db = _change_threshold_db()

    available = [o for o in series if o.get("available")]
    if len(available) < 2:
        return {"change_detected": False, "reason": "insufficient_data"}

    first = available[0]
    last = available[-1]
    vv_diff = (last["vv_db"] or 0) - (first["vv_db"] or 0)
    vh_diff = (last["vh_db"] or 0) - (first["vh_db"] or 0)
    magnitude = abs(vv_diff) + abs(vh_diff)

    # Contexto SIEMPRE presente (también cuando no hay cambio): así el cliente ve
    # desde qué fecha hasta qué fecha se comparó y con qué umbral.
    base = {
        "from_date": first["date"],
        "to_date": last["date"],
        "observations": len(available),
        "threshold_db": threshold_db,
        "metric": "media_del_lote",
        "kind": "tendencia",
    }

    if magnitude < threshold_db:
        return {
            **base,
            "change_detected": False,
            "magnitude": round(magnitude, 2),
            "vv_diff": round(vv_diff, 2),
            "vh_diff": round(vh_diff, 2),
            "status": "stable",
        }

    attention = "moderate" if magnitude < 2 * threshold_db else "high"
    change_types = _classify_change(vv_diff, vh_diff)

    return {
        **base,
        "change_detected": True,
        "magnitude": round(magnitude, 2),
        "vv_diff": round(vv_diff, 2),
        "vh_diff": round(vh_diff, 2),
        "change_types": change_types,
        "attention_level": attention,
        "status": "review",
        "interpretation": (
            "Se detectó una variación respecto a observaciones anteriores. El cambio "
            "puede estar relacionado con humedad, estructura de la vegetación o "
            "condiciones del terreno. Se recomienda revisar esta zona cuando exista "
            "una observación óptica disponible."
        ),
    }


# ----------------------------------------------------- orquestador principal

def get_radar_monitoring(parcel_geom, days_back=None, zones=None, force=False, target_date=None):
    """
    Monitoreo radar completo para una parcela (y, opcionalmente, sus sectores).

    Retorna:
    {
        'source': 'radar',
        'available': bool,
        'message': str,
        'last_observation': {...} | None,
        'time_series': [...],
        'change': {...} | None,
        'attention_level': 'none'|'moderate'|'high',
        'sectors': [...] | [],
        'data_nature': 'real' | 'unavailable',
    }
    """
    from datetime import date

    if days_back is None:
        days_back = getattr(settings, "SENTINEL1_LOOKBACK_DAYS", 60)

    today = date.today()
    target = None
    if target_date:
        try:
            target = datetime.strptime(str(target_date)[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            target = None
    if target:
        # Ventana simétrica alrededor de la fecha pedida (para la cadena
        # "sin óptico → radar más cercano").
        half = max(14, min(days_back, 60))
        date_from = (target - timedelta(days=half)).isoformat()
        date_to = (target + timedelta(days=half)).isoformat()
    else:
        date_to = today.isoformat()
        date_from = (today - timedelta(days=days_back)).isoformat()

    series = get_radar_time_series(parcel_geom, date_from, date_to, max_results=10)
    available = [o for o in series if o.get("available")]

    if not available:
        return {
            "source": "radar",
            "available": False,
            "message": "Datos radar no disponibles para esta fecha.",
            "last_observation": None,
            "time_series": series,
            "change": None,
            "attention_level": "none",
            "sectors": [],
            "data_nature": "unavailable",
        }

    # Tendencia (secundaria): media del lote, primera vs última observación.
    change = detect_radar_change(series)

    # Métrica PRINCIPAL (una sola línea base): cambio reciente POR PÍXEL entre las
    # dos últimas pasadas. Es exactamente la misma que pinta la capa de cambio, así
    # el texto y el mapa nunca se contradicen.
    recent_change = None
    try:
        layers = get_radar_layers(
            parcel_geom, date_from, date_to, include_images=False,
            force=force, target_date=target_date,
        )
        if layers.get("available"):
            recent_change = layers.get("change")
    except Exception as e:
        logger.warning(f"[S1] No se pudo calcular el cambio reciente por píxel: {e}")

    primary = recent_change or change
    attention_level = "none"
    if primary and primary.get("change_detected"):
        attention_level = primary.get("attention_level") or "moderate"

    # La detección visual por celda es la capa principal. Ya no se atribuye a
    # "sectores" (zonas): la grilla de celdas es la fuente visual.
    sectors = []

    # Observación a destacar: la más cercana a la fecha pedida, o la última.
    if target:
        def _obs_proximity(o):
            try:
                od = datetime.strptime(str(o.get("date"))[:10], "%Y-%m-%d").date()
                return abs((od - target).days)
            except (TypeError, ValueError):
                return 10 ** 6
        last_obs = min(available, key=_obs_proximity)
    else:
        last_obs = available[-1]

    if target:
        message = (
            f"{len(available)} observaciones radar alrededor de {target.isoformat()} "
            f"(observación usada: {last_obs.get('date')})."
        )
    else:
        message = f"{len(available)} observaciones radar en los últimos {days_back} días."

    return {
        "source": "radar",
        "available": True,
        "message": message,
        "last_observation": last_obs,
        "target_date": target.isoformat() if target else None,
        "used_date": last_obs.get("date"),
        "time_series": series,
        "change": change,                 # tendencia 60 días (media del lote)
        "recent_change": recent_change,   # cambio reciente por píxel (principal)
        "change_metric": "por_pixel" if recent_change else "media_del_lote",
        "attention_level": attention_level,
        "sectors": sectors,
        "data_nature": "real",
    }


def _attribute_change_to_sectors(zones, date_from, date_to):
    """
    Atribuye el cambio radar a sectores (ParcelZone) comparando sigma0 por sector.

    Finca → Lote → Sector → Cambio radar → Revisión.
    """
    sectors = []
    for zone in zones:
        geom = getattr(zone, "geometry_geojson", None) or getattr(zone, "geometry", None)
        if not geom:
            continue
        zone_series = get_radar_time_series(geom, date_from, date_to, max_results=6)
        zone_available = [o for o in zone_series if o.get("available")]
        if len(zone_available) < 2:
            continue
        zone_change = detect_radar_change(zone_series)
        sectors.append({
            "zone_id": getattr(zone, "cluster_id", None) or getattr(zone, "id", None),
            "label": getattr(zone, "label", "") or f"Sector {getattr(zone, 'cluster_id', '')}",
            "change_detected": zone_change.get("change_detected", False),
            "attention_level": zone_change.get("attention_level", "none"),
        })
    return [s for s in sectors if s["change_detected"]]


# ----------------------------------------------- compatibilidad (sin simulación)

def get_crop_status_from_radar(parcel_geometry, days_back=30, ndvi_value=None):
    """
    Compatibilidad: devuelve el monitoreo radar REAL (ignora `ndvi_value`, que
    ya no se usa para estimar backscatter).
    """
    result = get_radar_monitoring(parcel_geometry, days_back=days_back)
    result["radar_status"] = "data_available" if result["available"] else "no_data"
    result["scenes_found"] = len(result["time_series"])

    # Alertas: solo cuando el cambio reciente por píxel es ALTO (>=30% del lote) o
    # cuando la tendencia de la media supera el umbral. Evita avisar por la
    # variabilidad normal (humedad/geometría) que antes generaba ruido.
    recent = result.get("recent_change") or {}
    trend = result.get("change") or {}
    result["change_detected"] = bool(
        recent.get("attention_level") == "high" or trend.get("change_detected")
    )
    result["change_info"] = recent or trend
    result["data_nature"] = result["data_nature"]
    return result
