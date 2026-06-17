"""
Pipeline de zonificación de manejo (precision farming).

Implementación pragmática que funciona sin descargar el raster Sentinel-2:
genera una grilla densa de puntos dentro del polígono de la parcela, asigna
valores sintéticos coherentes (gradiente espacial + ruido controlado por seed
del parcel.id) a los índices NDVI/NDMI/SAVI/NDRE, ejecuta K-means y vectoriza
los clusters como polígonos GeoJSON.

Cuando exista el pipeline real con EOSDA/Sentinel-2, reemplazar
`_simulate_pixel_indices` por la lectura del raster recortado.
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

CATEGORY_LABEL = {
    'low': 'Bajo vigor',
    'mid_low': 'Vigor medio-bajo',
    'mid': 'Vigor medio',
    'mid_high': 'Vigor medio-alto',
    'high': 'Alto vigor',
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
    ndvi, ndmi, savi, ndre = _simulate_pixel_indices(
        coords, poly, parcel.id or 0, zonification.id or 0, zonification.index_base
    )

    features = np.column_stack([ndvi, ndmi, savi, ndre])

    k = max(2, min(int(zonification.k_zones or 5), 5))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(features)
    centers = km.cluster_centers_

    # Ordenar clusters por NDVI medio para asignar categorías
    order = np.argsort(centers[:, 0])
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
        label_name = CATEGORY_LABEL[category]

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

        ParcelZone.objects.create(
            zonification=zonification,
            cluster_id=int(cluster_idx),
            label=label_name,
            category=category,
            pixel_count=pixel_count,
            area_ha=area_ha,
            ndvi_mean=_r(ndvi_vals.mean()),
            ndvi_std=_r(ndvi_vals.std()),
            ndvi_min=_r(ndvi_vals.min()),
            ndvi_max=_r(ndvi_vals.max()),
            ndmi_mean=_r(ndmi_vals.mean()),
            ndmi_std=_r(ndmi_vals.std()),
            savi_mean=_r(savi_vals.mean()),
            savi_std=_r(savi_vals.std()),
            ndre_mean=_r(ndre_vals.mean()),
            ndre_std=_r(ndre_vals.std()),
            geometry_geojson=geojson_geom,
            recomendacion=_build_recommendation(
                category, float(ndvi_vals.mean()), float(ndmi_vals.mean()),
                zonification.index_base,
            ),
        )

    zonification.total_pixels = int(len(coords))
    zonification.pixel_resolution_m = round((step_x * deg_to_m_x + step_y * deg_to_m_y) / 2.0, 2)
    zonification.status = 'ready'
    if not zonification.notes:
        zonification.notes = (
            'Generado con motor heurístico (gradiente espacial sintético). '
            'Reemplazar por raster Sentinel-2 real cuando esté disponible.'
        )
    zonification.save(update_fields=[
        'total_pixels', 'pixel_resolution_m', 'status', 'notes', 'updated_at',
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


def _build_recommendation(category: str, ndvi_mean: float, ndmi_mean: float,
                          index_base: str) -> str:
    parts = []
    if category in ('low', 'mid_low'):
        parts.append(
            'Zona de bajo vigor: revisar emergencia, presencia de plagas/enfermedades, '
            'compactación o deficiencia hídrica.'
        )
        if ndmi_mean < 0.28:
            parts.append('NDMI bajo: posible estrés hídrico, priorizar riego y monitoreo de humedad.')
        parts.append('Acción sugerida: muestreo de suelo dirigido y refertilización nitrogenada localizada.')
    elif category == 'mid':
        parts.append('Zona de vigor medio: mantener manejo estándar.')
        parts.append('Considerar fertilización foliar de complemento y monitoreo de plagas.')
    else:  # mid_high / high
        parts.append('Zona de alto vigor: reducir dosis de N para evitar exceso vegetativo y encamamiento.')
        if ndmi_mean > 0.55:
            parts.append('Alta retención de humedad: ajustar lámina de riego para evitar exceso.')
        parts.append('Acción sugerida: validar densidad de plantas y ventilación del cultivo.')
    parts.append(
        f'Base: {index_base.upper()} promedio ≈ {ndvi_mean:.2f}.'
    )
    return ' '.join(parts)
