"""
Módulo de elevación/topografía para parcelas.
Consulta datos de elevación gratuitos desde Open-Meteo Elevation API
y genera mapas de calor de elevación relativa sobre la parcela.

API usada: https://open-meteo.com/en/docs/elevation-api
- 100% gratuita, sin API key
- Resolución: ~30m (Copernicus DEM / SRTM)
- Los datos de elevación son estáticos (la topografía no cambia)

El resultado se cachea permanentemente por parcela ya que la topografía no varía.
"""
import logging
import requests
import json
import math
import io
import base64
import time
import numpy as np
from PIL import Image
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Parcel

logger = logging.getLogger(__name__)

# Timeout para la API de Open-Meteo (segundos)
OPEN_METEO_TIMEOUT = 15

# Resolución de la grilla en grados (~30m en el ecuador)
# 1 grado de latitud ≈ 111,320m → 30m ≈ 0.000270°
GRID_RESOLUTION_DEG = 0.000270

# Máximo de puntos POR BATCH a Open-Meteo (evitar URLs muy largas)
MAX_POINTS_PER_BATCH = 100

# Máximo total de puntos de grilla (se hacen múltiples requests si es necesario)
# Con interpolación scipy, 500 puntos raw generan una imagen 800x800 de alta calidad
MAX_TOTAL_GRID_POINTS = 500

# Tiempo de cache: 30 días (la topografía no cambia)
CACHE_TIMEOUT = 60 * 60 * 24 * 30


def _get_parcel_centroid_and_bounds(geom):
    """
    Extrae centroide y bounding box del GeoJSON de la parcela.
    Retorna: (lat, lng, min_lon, min_lat, max_lon, max_lat)
    """
    if not geom or not isinstance(geom, dict):
        return None

    coordinates = geom.get('coordinates', [])
    if not coordinates or len(coordinates) == 0:
        return None

    # Para polígonos, tomar el primer anillo
    coords = coordinates[0] if isinstance(coordinates[0], list) else coordinates

    if not coords or len(coords) < 3:
        return None

    # Excluir el punto de cierre si el primer y último punto coinciden
    if len(coords) > 1 and coords[0] == coords[-1]:
        ring = coords[:-1]
    else:
        ring = coords

    lons = [c[0] for c in ring]
    lats = [c[1] for c in ring]

    centroid_lng = sum(lons) / len(lons)
    centroid_lat = sum(lats) / len(lats)
    min_lon = min(lons)
    max_lon = max(lons)
    min_lat = min(lats)
    max_lat = max(lats)

    return centroid_lat, centroid_lng, min_lon, min_lat, max_lon, max_lat


def _point_in_polygon(x, y, polygon_coords):
    """
    Ray casting algorithm para verificar si un punto está dentro del polígono.
    polygon_coords: lista de [lon, lat]
    """
    n = len(polygon_coords)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon_coords[i][0], polygon_coords[i][1]
        xj, yj = polygon_coords[j][0], polygon_coords[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _generate_grid_points(geom, resolution=GRID_RESOLUTION_DEG):
    """
    Genera una grilla de puntos dentro del polígono de la parcela.
    Retorna: lista de (lat, lon) y dimensiones de la grilla (rows, cols)
    """
    result = _get_parcel_centroid_and_bounds(geom)
    if not result:
        return [], 0, 0, None

    _, _, min_lon, min_lat, max_lon, max_lat = result
    coords = geom['coordinates'][0]

    # Calcular cuántos puntos caben en cada dirección
    lon_range = max_lon - min_lon
    lat_range = max_lat - min_lat

    # Mínimo 5x5, máximo limitado por MAX_TOTAL_GRID_POINTS
    cols = max(5, int(lon_range / resolution) + 1)
    rows = max(5, int(lat_range / resolution) + 1)

    # Limitar el total de puntos
    total = rows * cols
    if total > MAX_TOTAL_GRID_POINTS:
        # Reducir resolución proporcionalmente
        scale = math.sqrt(MAX_TOTAL_GRID_POINTS / total)
        cols = max(5, int(cols * scale))
        rows = max(5, int(rows * scale))

    # Generar grilla
    points = []
    lon_step = lon_range / (cols - 1) if cols > 1 else 0
    lat_step = lat_range / (rows - 1) if rows > 1 else 0

    grid_mask = np.zeros((rows, cols), dtype=bool)

    for r in range(rows):
        for c in range(cols):
            lon = min_lon + c * lon_step
            lat = min_lat + r * lat_step

            if _point_in_polygon(lon, lat, coords):
                points.append((lat, lon))
                grid_mask[r, c] = True

    bounds = [min_lon, min_lat, max_lon, max_lat]
    return points, rows, cols, grid_mask, bounds


def _fetch_elevation_data(points):
    """
    Consulta la API de Open-Meteo para obtener la elevación de cada punto.
    Soporta batching: divide los puntos en lotes de MAX_POINTS_PER_BATCH.
    API: https://api.open-meteo.com/v1/elevation?latitude=...&longitude=...
    Retorna: lista de elevaciones (float) en el mismo orden que points.
    """
    if not points:
        return []

    all_elevations = []
    total_batches = math.ceil(len(points) / MAX_POINTS_PER_BATCH)

    logger.info(f"[ELEVATION] Consultando Open-Meteo con {len(points)} puntos en {total_batches} batch(es)...")

    for batch_idx in range(total_batches):
        start = batch_idx * MAX_POINTS_PER_BATCH
        end = min(start + MAX_POINTS_PER_BATCH, len(points))
        batch = points[start:end]

        lats = [str(round(p[0], 6)) for p in batch]
        lons = [str(round(p[1], 6)) for p in batch]

        url = "https://api.open-meteo.com/v1/elevation"
        params = {
            "latitude": ",".join(lats),
            "longitude": ",".join(lons),
        }

        # Retry con backoff para manejar rate limiting (429)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, params=params, timeout=OPEN_METEO_TIMEOUT)
                if resp.status_code == 429 and attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)  # 2s, 4s
                    logger.warning(f"[ELEVATION] Rate limited en batch {batch_idx + 1}, esperando {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()

                elevations = data.get("elevation", [])
                if not isinstance(elevations, list):
                    elevations = [elevations]

                all_elevations.extend(elevations)
                logger.info(f"[ELEVATION] Batch {batch_idx + 1}/{total_batches}: {len(elevations)} elevaciones recibidas")
                break  # Éxito, salir del retry loop

            except requests.exceptions.Timeout:
                logger.error(f"[ELEVATION] Timeout en batch {batch_idx + 1}/{total_batches}")
                raise
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1 and '429' in str(e):
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"[ELEVATION] Rate limited, retry {attempt + 1}, esperando {wait}s...")
                    time.sleep(wait)
                    continue
                logger.error(f"[ELEVATION] Error en batch {batch_idx + 1}/{total_batches}: {e}")
                raise
            except (KeyError, ValueError, json.JSONDecodeError) as e:
                logger.error(f"[ELEVATION] Error al parsear respuesta batch {batch_idx + 1}: {e}")
                raise

        # Delay entre batches para evitar rate limiting
        if batch_idx < total_batches - 1:
            time.sleep(1.0)

    logger.info(f"[ELEVATION] Total: {len(all_elevations)} elevaciones. "
                 f"Min: {min(all_elevations):.1f}m, Max: {max(all_elevations):.1f}m")
    return all_elevations


def _generate_elevation_heatmap(elevations, rows, cols, grid_mask, parcel_geom=None, bounds=None):
    """
    Genera una imagen PNG de mapa de calor a partir de los datos de elevación.
    Usa interpolación scipy para cobertura completa sin gaps.
    Recorta la imagen al polígono exacto de la parcela.
    Colores consistentes con la leyenda del frontend:
      - Bajo:  azul (#1E50AA → #46B4FF)
      - Medio: verde (#64F064 → #DCC840)
      - Alto:  marrón (#DCA028 → #8C6428)
    Retorna: base64 del PNG.
    """
    from PIL import ImageDraw
    from scipy.interpolate import griddata as scipy_griddata

    # Crear matriz de elevaciones con NaN para puntos fuera del polígono
    grid = np.full((rows, cols), np.nan, dtype=float)

    idx = 0
    for r in range(rows):
        for c in range(cols):
            if grid_mask[r, c]:
                if idx < len(elevations):
                    grid[r, c] = elevations[idx]
                idx += 1

    # Obtener rango de valores válidos
    valid_values = grid[~np.isnan(grid)]
    if len(valid_values) == 0:
        logger.error("[ELEVATION] No hay datos válidos de elevación")
        return None, {}

    min_elev = float(np.min(valid_values))
    max_elev = float(np.max(valid_values))
    avg_elev = float(np.mean(valid_values))
    diff_elev = max_elev - min_elev

    stats = {
        "min_elevation": round(min_elev, 1),
        "max_elevation": round(max_elev, 1),
        "avg_elevation": round(avg_elev, 1),
        "difference": round(diff_elev, 1),
        "grid_points": int(len(valid_values)),
        "grid_size": f"{rows}x{cols}",
        "resolution_m": 30
    }

    # -- Interpolación scipy para llenar toda el área sin gaps --
    # Recopilar puntos conocidos (row, col) → elevation
    known_rows = []
    known_cols = []
    known_vals = []
    for r in range(rows):
        for c in range(cols):
            if not np.isnan(grid[r, c]):
                known_rows.append(r)
                known_cols.append(c)
                known_vals.append(grid[r, c])

    known_points = np.array(list(zip(known_rows, known_cols)))
    known_values = np.array(known_vals)

    # Imagen final de alta resolución
    IMG_SIZE = 800  # píxeles de salida
    target_rows = IMG_SIZE
    target_cols = IMG_SIZE

    # Crear grilla densa para interpolación
    grid_r = np.linspace(0, rows - 1, target_rows)
    grid_c = np.linspace(0, cols - 1, target_cols)
    mesh_c, mesh_r = np.meshgrid(grid_c, grid_r)

    # Interpolar con método cúbico (suave), fallback a nearest para bordes
    try:
        interp_cubic = scipy_griddata(
            known_points, known_values,
            (mesh_r, mesh_c), method='cubic'
        )
        interp_nearest = scipy_griddata(
            known_points, known_values,
            (mesh_r, mesh_c), method='nearest'
        )
        # Rellenar NaN del cúbico con nearest
        interpolated = np.where(np.isnan(interp_cubic), interp_nearest, interp_cubic)
    except Exception as e:
        logger.warning(f"[ELEVATION] Interpolación cúbica falló, usando nearest: {e}")
        interpolated = scipy_griddata(
            known_points, known_values,
            (mesh_r, mesh_c), method='nearest'
        )

    # Normalizar valores al rango [0, 1]
    if diff_elev > 0:
        normalized = (interpolated - min_elev) / diff_elev
        normalized = np.clip(normalized, 0.0, 1.0)
    else:
        normalized = np.full_like(interpolated, 0.5)

    # -- Colormap que coincide EXACTAMENTE con la leyenda del frontend --
    # Bajo:  #1E50AA (30,80,170) → #46B4FF (70,180,255)
    # Medio: #64F064 (100,240,100) → #DCC840 (220,200,64)
    # Alto:  #DCA028 (220,160,40) → #8C6428 (140,100,40)
    ALPHA = 210

    img_array = np.zeros((target_rows, target_cols, 4), dtype=np.uint8)

    for r in range(target_rows):
        for c in range(target_cols):
            v = normalized[r, c]
            if np.isnan(v):
                img_array[r, c] = [0, 0, 0, 0]
                continue

            if v < 0.33:
                # Bajo: azul oscuro → azul claro
                t = v / 0.33
                red = int(30 + t * 40)      # 30 → 70
                green = int(80 + t * 100)    # 80 → 180
                blue = int(170 + t * 85)     # 170 → 255
            elif v < 0.66:
                # Medio: verde brillante → amarillo verdoso
                t = (v - 0.33) / 0.33
                red = int(100 + t * 120)     # 100 → 220
                green = int(240 - t * 40)    # 240 → 200
                blue = int(100 - t * 36)     # 100 → 64
            else:
                # Alto: ámbar/naranja → marrón oscuro
                t = (v - 0.66) / 0.34
                red = int(220 - t * 80)      # 220 → 140
                green = int(160 - t * 60)    # 160 → 100
                blue = int(40)               # 40 → 40

            img_array[r, c] = [red, green, blue, ALPHA]

    # Invertir filas: la grilla tiene row 0 = min_lat (sur), la imagen necesita norte arriba
    img_array = np.flipud(img_array)

    # Crear imagen PIL
    img = Image.fromarray(img_array, 'RGBA')

    # Recortar al polígono exacto de la parcela
    if parcel_geom and bounds:
        try:
            coords = parcel_geom['coordinates'][0]
            min_lon, min_lat, max_lon, max_lat = bounds
            img_w, img_h = img.size

            # Convertir coordenadas geográficas a píxeles
            poly_pixels = []
            for lon, lat in coords:
                px = (lon - min_lon) / (max_lon - min_lon) * img_w if max_lon != min_lon else img_w / 2
                py = (1.0 - (lat - min_lat) / (max_lat - min_lat)) * img_h if max_lat != min_lat else img_h / 2
                poly_pixels.append((px, py))

            # Crear máscara del polígono
            mask = Image.new('L', img.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.polygon(poly_pixels, fill=255)

            # Aplicar máscara: combinar alpha del heatmap con máscara del polígono
            orig_alpha = np.array(img)[:, :, 3]
            mask_array = np.array(mask)
            # Donde la máscara es 0 → transparente; donde es 255 → mantener alpha original
            combined_alpha = np.where(mask_array > 0, orig_alpha, 0).astype(np.uint8)

            img_np = np.array(img)
            img_np[:, :, 3] = combined_alpha
            img = Image.fromarray(img_np, 'RGBA')

            logger.info(f"[ELEVATION] Imagen recortada al polígono de la parcela")
        except Exception as e:
            logger.warning(f"[ELEVATION] No se pudo recortar al polígono: {e}")

    buffer = io.BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')

    logger.info(f"[ELEVATION] Imagen generada: {img.size[0]}x{img.size[1]}px, "
                f"elevación {min_elev:.1f}m - {max_elev:.1f}m (dif: {diff_elev:.1f}m)")

    return img_base64, stats


class ElevationView(APIView):
    """
    Vista API para obtener mapa de elevación de una parcela.

    GET /api/parcels/parcel/<parcel_id>/elevation/

    Retorna:
    {
        "image_base64": "iVBOR...",
        "bounds": [west, south, east, north],
        "stats": {
            "min_elevation": 2538.0,
            "max_elevation": 2547.0,
            "difference": 9.0,
            "avg_elevation": 2543.0,
            "grid_points": 85,
            "grid_size": "10x10",
            "resolution_m": 30
        },
        "parcel_id": 123,
        "cached": false
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, parcel_id):
        logger.info(f"[ELEVATION] Solicitud de elevación para parcela {parcel_id}")

        # Obtener la parcela
        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)

        if not parcel.geom or not isinstance(parcel.geom, dict):
            return Response(
                {"error": "La parcela no tiene geometría definida."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar cache (la topografía no cambia)
        cache_key = f"elevation_parcel_{parcel_id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"[ELEVATION] Cache HIT para parcela {parcel_id}")
            cached_data['cached'] = True
            return Response(cached_data, status=status.HTTP_200_OK)

        # Generar grilla de puntos dentro del polígono
        try:
            points, rows, cols, grid_mask, bounds = _generate_grid_points(parcel.geom)
        except Exception as e:
            logger.error(f"[ELEVATION] Error al generar grilla: {e}")
            return Response(
                {"error": f"Error al generar grilla de puntos: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not points:
            return Response(
                {"error": "No se pudieron generar puntos dentro de la parcela. Verifica la geometría."},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"[ELEVATION] Grilla generada: {rows}x{cols}, {len(points)} puntos dentro del polígono")

        # Consultar elevaciones a Open-Meteo
        try:
            elevations = _fetch_elevation_data(points)
        except requests.exceptions.Timeout:
            return Response(
                {"error": "Timeout al consultar datos de elevación. Intenta de nuevo."},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except Exception as e:
            logger.error(f"[ELEVATION] Error al obtener elevaciones: {e}")
            return Response(
                {"error": f"Error al obtener datos de elevación: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        if not elevations:
            return Response(
                {"error": "No se obtuvieron datos de elevación para esta zona."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generar imagen heatmap
        try:
            img_base64, stats = _generate_elevation_heatmap(
                elevations, rows, cols, grid_mask,
                parcel_geom=parcel.geom, bounds=bounds
            )
        except Exception as e:
            logger.error(f"[ELEVATION] Error al generar heatmap: {e}")
            return Response(
                {"error": f"Error al generar mapa de elevación: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not img_base64:
            return Response(
                {"error": "No se pudo generar la imagen de elevación."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        response_data = {
            "image_base64": img_base64,
            "bounds": bounds,  # [west, south, east, north]
            "stats": stats,
            "parcel_id": parcel_id,
            "cached": False
        }

        # Guardar en cache (30 días — la topografía no cambia)
        cache.set(cache_key, response_data, CACHE_TIMEOUT)
        logger.info(f"[ELEVATION] Datos guardados en cache para parcela {parcel_id}")

        return Response(response_data, status=status.HTTP_200_OK)
