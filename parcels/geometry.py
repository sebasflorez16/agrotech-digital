"""
Utilidades de geometría para parcelas.

Única fuente de verdad para el cálculo de área en hectáreas.
Se usa en: modelo (Parcel.area_hectares), ViewSet (límites), facturación y reportes.

La fórmula es la MISMA que usa el frontend (`polygonAreaHectares` en
`metrica/static/js/parcels/parcel.js`): área esférica de Shoelace adaptada a la
Tierra (spherical excess) con radio ecuatorial. De esta forma el valor mostrado
en la UI y el usado por el backend para límites/facturación son idénticos.
"""

import math

# Radio ecuatorial de la Tierra en metros (coincide con el frontend).
EARTH_RADIUS_M = 6378137.0


def calculate_area_hectares(geom):
    """
    Calcula el área en hectáreas de un polígono GeoJSON.

    Acepta:
      - {'type': 'Polygon', 'coordinates': [[ [lon, lat], ... ]]}
      - {'type': 'MultiPolygon', ...} (suma todos los polígonos)

    Devuelve 0.0 si el GeoJSON es inválido o no está presente.
    """
    if not geom or not isinstance(geom, dict):
        return 0.0

    geom_type = geom.get('type')
    coordinates = geom.get('coordinates')
    if not coordinates:
        return 0.0

    if geom_type == 'Polygon':
        return _polygon_area_hectares(coordinates)
    if geom_type == 'MultiPolygon':
        return sum(_polygon_area_hectares(poly) for poly in coordinates)

    # Fallback: 'coordinates' es directamente un anillo.
    if coordinates and isinstance(coordinates[0], (list, tuple)):
        first = coordinates[0]
        if isinstance(first, (list, tuple)) and (isinstance(first[0], (int, float))):
            return _polygon_area_hectares([coordinates])
    return 0.0


def _polygon_area_hectares(polygon_coords):
    """Área de un Polygon (lista de anillos); usa el anillo exterior."""
    if not polygon_coords or not polygon_coords[0]:
        return 0.0
    ring = polygon_coords[0]
    if len(ring) < 3:
        return 0.0

    area = 0.0
    n = len(ring)
    for i in range(n):
        lon1, lat1 = float(ring[i][0]), float(ring[i][1])
        lon2, lat2 = float(ring[(i + 1) % n][0]), float(ring[(i + 1) % n][1])
        area += (math.radians(lon2) - math.radians(lon1)) * (
            2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2))
        )

    area_m2 = area * EARTH_RADIUS_M * EARTH_RADIUS_M / 2.0
    return abs(area_m2) / 10000.0
