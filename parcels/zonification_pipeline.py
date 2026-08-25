"""
Pipeline de zonificación de manejo (precision farming).

Genera una grilla densa de puntos dentro del polígono de la parcela, muestrea
índices REALES (NDVI/NDMI/SAVI/NDRE) de Sentinel-2 L2A vía Planetary Computer,
ejecuta K-means y vectoriza los clusters como polígonos GeoJSON.

Si no hay escena real disponible, el pipeline falla honestamente (NUNCA inventa
valores).
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon, Point, box, mapping
from shapely.ops import unary_union
from shapely.validation import make_valid
from sklearn.cluster import KMeans

from .models import ParcelZone


CATEGORY_ORDER_BY_K = {
    2: ['low', 'high'],
    3: ['low', 'mid', 'high'],
    4: ['low', 'mid_low', 'mid_high', 'high'],
    5: ['low', 'mid_low', 'mid', 'mid_high', 'high'],
}

# Columna del índice dentro del vector de features [ndvi, ndmi, savi, ndre]
INDEX_COLUMN = {'ndvi': 0, 'ndmi': 1, 'savi': 2, 'ndre': 3}

VIGOR_LABELS = {
    'low': 'Bajo vigor',
    'mid_low': 'Vigor medio-bajo',
    'mid': 'Vigor medio',
    'mid_high': 'Vigor medio-alto',
    'high': 'Alto vigor',
}

HUMIDITY_LABELS = {
    'low': 'Muy seco',
    'mid_low': 'Seco',
    'mid': 'Humedad media',
    'mid_high': 'Húmedo',
    'high': 'Muy húmedo',
}

LABELS_BY_INDEX = {
    'ndvi': VIGOR_LABELS,
    'savi': VIGOR_LABELS,
    'ndre': VIGOR_LABELS,
    'ndmi': HUMIDITY_LABELS,
}


def run_zonification(zonification) -> dict:
    """Ejecuta el pipeline completo y persiste las zonas.

    Devuelve un dict con el resumen, además de mutar el objeto `zonification`.
    """
    parcel = zonification.parcel
    geom = parcel.geom or {}

    if geom.get('type') != 'Polygon' or not geom.get('coordinates'):
        zonification.status = 'failed'
        zonification.notes = 'La parcela no tiene un GeoJSON Polygon válido.'
        zonification.save(update_fields=['status', 'notes', 'updated_at'])
        return {'ok': False, 'reason': zonification.notes}

    poly = Polygon(geom['coordinates'][0])
    if not poly.is_valid:
        poly = make_valid(poly)
        if poly.geom_type != 'Polygon':
            # toma el polígono más grande
            polys = [p for p in poly.geoms if p.geom_type == 'Polygon']
            if not polys:
                zonification.status = 'failed'
                zonification.notes = 'Polígono inválido tras reparar.'
                zonification.save(update_fields=['status', 'notes', 'updated_at'])
                return {'ok': False, 'reason': zonification.notes}
            poly = max(polys, key=lambda p: p.area)

    zonification.status = 'processing'
    zonification.save(update_fields=['status', 'updated_at'])

    minx, miny, maxx, maxy = poly.bounds
    nx = ny = 40  # grilla 40x40 = 1600 candidatos
    xs = np.linspace(minx, maxx, nx)
    ys = np.linspace(miny, maxy, ny)

    pts = []
    for x in xs:
        for y in ys:
            if poly.contains(Point(x, y)):
                pts.append((x, y))
    if len(pts) < zonification.k_zones * 8:
        zonification.status = 'failed'
        zonification.notes = (
            f'Polígono demasiado pequeño para la grilla actual: '
            f'{len(pts)} puntos dentro del polígono.'
        )
        zonification.save(update_fields=['status', 'notes', 'updated_at'])
        return {'ok': False, 'reason': zonification.notes}

    coords = np.asarray(pts)

    # Índices REALES de Sentinel-2 (nunca simulados)
    from .sentinel2 import get_real_indices
    pts_lonlat = [(float(p[0]), float(p[1])) for p in coords]
    real = get_real_indices(geom, pts_lonlat, zonification.scene_date)
    if real is None:
        zonification.status = 'failed'
        zonification.notes = (
            'No se encontró una escena Sentinel-2 real para esta fecha/geometría. '
            'Reintenta con otra fecha de escena.'
        )
        zonification.save(update_fields=['status', 'notes', 'updated_at'])
        return {'ok': False, 'reason': zonification.notes}
    ndvi, ndmi, savi, ndre, effective_scene_date = real
    zonification.scene_date = effective_scene_date

    # Descartar puntos sin dato real (fuera de escena / nubes)
    valid_mask = (
        np.isfinite(ndvi) & np.isfinite(ndmi) & np.isfinite(savi) & np.isfinite(ndre)
    )
    if valid_mask.sum() < zonification.k_zones * 8:
        zonification.status = 'failed'
        zonification.notes = 'Puntos válidos insuficientes en la escena Sentinel-2 real.'
        zonification.save(update_fields=['status', 'notes', 'updated_at'])
        return {'ok': False, 'reason': zonification.notes}
    coords = coords[valid_mask]
    ndvi = ndvi[valid_mask]
    ndmi = ndmi[valid_mask]
    savi = savi[valid_mask]
    ndre = ndre[valid_mask]

    features = np.column_stack([ndvi, ndmi, savi, ndre])

    # Resolver el índice base (define orden, etiquetas y colores)
    index_base = zonification.index_base or 'ndvi'
    if index_base not in INDEX_COLUMN:
        index_base = 'ndvi'
    col = INDEX_COLUMN[index_base]
    index_labels = LABELS_BY_INDEX.get(index_base, VIGOR_LABELS)
    index_values = {'ndvi': ndvi, 'ndmi': ndmi, 'savi': savi, 'ndre': ndre}[index_base]
    field_mean_index = float(np.nanmean(index_values))

    try:
        from .elevation import get_parcel_drainage_direction
        drainage_direction = get_parcel_drainage_direction(parcel)
    except Exception:
        drainage_direction = None

    k = max(2, min(int(zonification.k_zones or 5), 5))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(features)
    centers = km.cluster_centers_

    # Ordenar clusters por el índice base para asignar categorías
    order = np.argsort(centers[:, col])
    cat_order = CATEGORY_ORDER_BY_K.get(k, CATEGORY_ORDER_BY_K[5])

    # Limpiar zonas previas (re-run idempotente)
    zonification.zones.all().delete()

    step_x = (maxx - minx) / (nx - 1)
    step_y = (maxy - miny) / (ny - 1)
    cell_buf_x = step_x * 0.55
    cell_buf_y = step_y * 0.55

    # Conversión deg → m aproximada (para área en hectáreas)
    cy = (miny + maxy) / 2.0
    deg_to_m_x = 111320.0 * np.cos(np.deg2rad(cy))
    deg_to_m_y = 110540.0
    pixel_area_m2 = (step_x * deg_to_m_x) * (step_y * deg_to_m_y)

    for rank, cluster_idx in enumerate(order):
        mask = labels == cluster_idx
        if not mask.any():
            continue
        category = cat_order[rank] if rank < len(cat_order) else 'mid'
        label_name = index_labels.get(category, 'Zona media')

        cluster_pts = coords[mask]
        cells = [
            box(p[0] - cell_buf_x, p[1] - cell_buf_y, p[0] + cell_buf_x, p[1] + cell_buf_y)
            for p in cluster_pts
        ]
        merged = unary_union(cells).intersection(poly)
        if merged.is_empty:
            continue
        merged = merged.simplify(min(step_x, step_y) * 0.4, preserve_topology=True)
        geojson_geom = mapping(merged)

        ndvi_vals = ndvi[mask]
        ndmi_vals = ndmi[mask]
        savi_vals = savi[mask]
        ndre_vals = ndre[mask]

        pixel_count = int(mask.sum())
        area_ha = round(pixel_count * pixel_area_m2 / 10_000.0, 2)

        zone_ndvi = float(ndvi_vals.mean())
        zone_ndmi = float(ndmi_vals.mean())
        zone_index_value = float(index_values[mask].mean())
        brecha_pct, priority = _compute_brecha_priority(zone_index_value, field_mean_index)

        ParcelZone.objects.create(
            zonification=zonification,
            cluster_id=int(cluster_idx),
            label=label_name,
            category=category,
            pixel_count=pixel_count,
            area_ha=area_ha,
            ndvi_mean=_r(zone_ndvi),
            ndvi_std=_r(ndvi_vals.std()),
            ndvi_min=_r(ndvi_vals.min()),
            ndvi_max=_r(ndvi_vals.max()),
            ndmi_mean=_r(zone_ndmi),
            ndmi_std=_r(ndmi_vals.std()),
            savi_mean=_r(savi_vals.mean()),
            savi_std=_r(savi_vals.std()),
            ndre_mean=_r(ndre_vals.mean()),
            ndre_std=_r(ndre_vals.std()),
            geometry_geojson=geojson_geom,
            brecha_pct=brecha_pct,
            priority=priority,
            drainage_direction=drainage_direction,
            recomendacion=_build_recommendation(
                category, index_base, zone_index_value, zone_ndvi, zone_ndmi,
                brecha_pct=brecha_pct, priority=priority,
                drainage_direction=drainage_direction,
                field_mean_index=field_mean_index,
            ),
        )

    zonification.total_pixels = int(len(coords))
    zonification.pixel_resolution_m = round((step_x * deg_to_m_x + step_y * deg_to_m_y) / 2.0, 2)
    zonification.status = 'ready'
    if not zonification.notes:
        zonification.notes = (
            'Zonificación con índices Sentinel-2 reales (Planetary Computer).'
        )
    zonification.save(update_fields=[
        'total_pixels', 'pixel_resolution_m', 'status', 'notes', 'scene_date',
        'updated_at',
    ])
    return {
        'ok': True,
        'zonification_id': zonification.id,
        'k_zones': k,
        'total_pixels': int(len(coords)),
        'zones': zonification.zones.count(),
    }


def _simulate_pixel_indices(coords: np.ndarray, poly: Polygon, parcel_id: int,
                            zonif_id: int, index_base: str):
    """Genera vectores NDVI/NDMI/SAVI/NDRE coherentes con un gradiente espacial."""
    rng = np.random.default_rng(int(parcel_id) * 7919 + int(zonif_id) * 31 + 17)
    cx, cy = poly.centroid.x, poly.centroid.y
    minx, miny, maxx, maxy = poly.bounds
    span = max(maxx - minx, maxy - miny) or 1.0
    centered = coords - np.array([cx, cy])

    direction = rng.uniform(0, 2 * np.pi)
    dvec1 = np.array([np.cos(direction), np.sin(direction)])
    dvec2 = np.array([-np.sin(direction), np.cos(direction)])
    g1 = centered @ dvec1 / span
    g2 = centered @ dvec2 / span

    base_map = {'ndvi': 0.62, 'ndmi': 0.38, 'savi': 0.55, 'ndre': 0.42}
    base = base_map.get(index_base, 0.62)

    n = len(coords)
    ndvi = np.clip(base + 0.30 * g1 + 0.10 * np.sin(3 * g2)
                   + rng.normal(0, 0.04, n), 0.05, 0.95)
    ndmi = np.clip(0.55 * ndvi + 0.10 * g2 + rng.normal(0, 0.03, n), 0.05, 0.85)
    savi = np.clip(0.88 * ndvi + rng.normal(0, 0.03, n), 0.05, 0.95)
    ndre = np.clip(0.62 * ndvi + rng.normal(0, 0.03, n), 0.05, 0.80)
    return ndvi, ndmi, savi, ndre


def _r(value) -> float:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return 0.0


def _compute_brecha_priority(zone_value: float, field_mean: float):
    """Devuelve (brecha_pct, priority) comparando la zona con el promedio del lote."""
    if not field_mean or zone_value is None:
        return None, 'baja'
    brecha_pct = round((zone_value - field_mean) / field_mean * 100, 1)
    if brecha_pct <= -25:
        priority = 'critica'
    elif brecha_pct <= -15:
        priority = 'alta'
    elif brecha_pct <= -8:
        priority = 'media'
    else:
        priority = 'baja'
    return brecha_pct, priority


def _build_recommendation(category: str, index_base: str, index_value: float,
                          ndvi_mean: float, ndmi_mean: float,
                          brecha_pct=None, priority='baja',
                          drainage_direction=None, field_mean_index=None) -> str:
    """Sugerencia clara y NO prescriptiva, atada a los índices reales.

    Principios:
    - Las categorías son relativas (rank dentro del lote), por eso el texto usa
      frases coherentes con esa posición ("la zona con menos vigor", "con más
      humedad") y nunca contradice la etiqueta.
    - No prescribe dosis absolutas; sugiere revisar/verificar en campo.
    - Siempre cierra recordando confirmar con una inspección en campo.
    """
    parts = []

    if index_base == 'ndmi':
        label = HUMIDITY_LABELS.get(category, 'Humedad media')
        if category in ('low', 'mid_low'):
            rel = 'es la zona con menos humedad del lote'
            action = 'Sugerencia: revisar el riego en esta zona, puede estar recibiendo menos agua que el resto del lote.'
        elif category == 'mid':
            rel = 'está en un punto intermedio de humedad del lote'
            action = 'Sugerencia: mantener el riego actual y monitorear la evolución.'
        else:
            rel = 'es la zona con más humedad del lote'
            if index_value is not None and index_value > 0.4:
                action = 'Sugerencia: revisar si hay encharcamiento o exceso de agua en esta zona.'
            else:
                action = 'Sugerencia: pese a ser la zona con más humedad, el nivel sigue siendo bajo; conviene mantener el riego y monitorear.'
        parts.append(f'{label}: {rel}.')
        parts.append(action)
        if field_mean_index is not None and field_mean_index < 0.2:
            parts.append('Nota: todo el lote muestra humedad de hoja baja en general; conviene revisar el plan de riego completo.')
        elif field_mean_index is not None and field_mean_index > 0.55:
            parts.append('Nota: todo el lote muestra humedad alta; vigila posibles excesos de agua.')
    else:
        label = VIGOR_LABELS.get(category, 'Vigor medio')
        if category in ('low', 'mid_low'):
            rel = 'es la zona con menos vigor del lote'
            action = 'Sugerencia: revisar en campo la germinación, posibles plagas o compactación del suelo; si todo se ve bien, evalúa reforzar la fertilización nitrogenada en esta zona.'
        elif category == 'mid':
            rel = 'está en un punto intermedio de vigor del lote'
            action = 'Sugerencia: mantener el manejo actual y monitorear la evolución en las próximas semanas.'
        else:
            rel = 'es la zona con más vigor del lote'
            action = 'Sugerencia: verificar si hay exceso de nitrógeno; si es así, conviene reducir la dosis en esta zona para evitar que el cultivo se doble (acame) y madure desparejo.'
        parts.append(f'{label}: {rel}.')
        parts.append(action)
        if ndmi_mean is not None and ndmi_mean < 0.2:
            parts.append('Además, la humedad de la hoja está baja; conviene revisar el riego en esta zona.')
        elif ndmi_mean is not None and ndmi_mean > 0.5:
            if drainage_direction:
                parts.append(f'Además, hay mucha humedad en la hoja; revisa el drenaje (el terreno tiende a drenar hacia el {drainage_direction}).')
            else:
                parts.append('Además, hay mucha humedad en la hoja; revisa el drenaje para evitar encharcamientos.')

    parts.append('Recomendación orientativa: confírmala con una inspección en campo.')
    return ' '.join(parts)
