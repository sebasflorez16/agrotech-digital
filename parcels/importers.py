"""Importación de lotes desde archivos geoespaciales.

Formatos soportados:
- GeoJSON / JSON
- KML / KMZ
- Shapefile comprimido (.zip)
- GPX
- GeoPackage (.gpkg)

El resultado es una lista de polígonos GeoJSON en EPSG:4326, listos para
guardarse en `Parcel.geom` (JSONField). Si el archivo trae varios lotes, se
devuelve un polígono por lote; la vista decide si crea una parcela por cada uno.
"""

from __future__ import annotations

import json
import logging
import tempfile
import zipfile
from pathlib import Path

import pyogrio
from shapely import force_2d
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, mapping, shape

from .geometry import calculate_area_hectares

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_UNCOMPRESSED_ZIP = 60 * 1024 * 1024  # 60 MB
MAX_POLYGONS = 50
ALLOWED_EXTENSIONS = {'.geojson', '.json', '.kml', '.kmz', '.zip', '.gpx', '.gpkg'}


class ParcelImportError(ValueError):
    """Error de validación de un archivo de importación."""


def parse_geospatial_file(uploaded_file):
    """Lee un archivo subido y devuelve polígonos normalizados.

    Returns:
        dict con:
          - polygons: list[dict] GeoJSON Polygon en WGS84
          - count: int
          - skipped: int (geometrías que no eran polígonos)
          - source_crs: str | None
          - total_hectares: float
    """
    name = getattr(uploaded_file, 'name', '') or ''
    extension = Path(name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ParcelImportError(
            'Formato no soportado. Usa GeoJSON, KML, KMZ, Shapefile (.zip), '
            'GPX o GeoPackage (.gpkg).'
        )

    size = getattr(uploaded_file, 'size', None)
    if size is not None and size > MAX_FILE_SIZE:
        raise ParcelImportError('El archivo supera el límite de 20 MB.')

    with tempfile.TemporaryDirectory(prefix='parcel_import_') as tmp:
        tmp_path = Path(tmp)
        file_path = tmp_path / f'input{extension}'
        with open(file_path, 'wb') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        try:
            polygons, skipped, source_crs = _parse_file(file_path, extension, tmp_path)
        except ParcelImportError:
            raise
        except Exception as exc:
            logger.warning('No se pudo interpretar el archivo %s: %s', name, exc)
            raise ParcelImportError(
                'No se pudo interpretar el archivo. Verifica que sea un polígono '
                'válido y que incluya su sistema de coordenadas (.prj en Shapefile).'
            ) from exc

    if not polygons:
        raise ParcelImportError(
            'El archivo no contiene polígonos válidos. Si es un GPX, exporta el '
            'lote como polígono o usa GeoJSON/KML.'
        )
    if len(polygons) > MAX_POLYGONS:
        raise ParcelImportError(
            f'El archivo contiene más de {MAX_POLYGONS} lotes. Divídelo o '
            'impórtalo por partes.'
        )

    total_hectares = sum(calculate_area_hectares(mapping(p)) for p in polygons)
    return {
        'polygons': [mapping(p) for p in polygons],
        'count': len(polygons),
        'skipped': skipped,
        'source_crs': source_crs,
        'total_hectares': total_hectares,
    }


def _parse_file(file_path: Path, extension: str, tmp_path: Path):
    if extension in ('.geojson', '.json'):
        return _parse_geojson(file_path)
    if extension == '.kmz':
        return _parse_kmz(file_path, tmp_path)
    if extension == '.zip':
        return _parse_shapefile_zip(file_path, tmp_path)
    return _parse_vector(file_path)


def _parse_geojson(file_path: Path):
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as source:
            data = json.load(source)
    except json.JSONDecodeError as exc:
        raise ParcelImportError('El archivo JSON no es válido.') from exc

    if data.get('type') == 'FeatureCollection':
        features = data.get('features') or []
    elif data.get('type') == 'Feature':
        features = [data]
    else:
        features = [data]

    geometries = []
    skipped = 0
    for feature in features:
        geometry = feature.get('geometry') if isinstance(feature, dict) and feature.get('type') == 'Feature' else feature
        if not geometry:
            skipped += 1
            continue
        try:
            geometries.append(shape(geometry))
        except Exception:
            skipped += 1

    polygons, skipped_more = _extract_polygons(geometries)
    _validate_wgs84(polygons)
    return polygons, skipped + skipped_more, 'EPSG:4326'


def _parse_kmz(file_path: Path, tmp_path: Path):
    kml_files = _extract_from_zip(file_path, tmp_path, suffixes=('.kml',))
    if not kml_files:
        raise ParcelImportError('El archivo KMZ no contiene un KML válido.')
    all_polygons = []
    skipped = 0
    source_crs = None
    for kml_file in kml_files:
        polygons, skipped_file, crs = _parse_vector(kml_file)
        all_polygons.extend(polygons)
        skipped += skipped_file
        source_crs = source_crs or crs
    return all_polygons, skipped, source_crs


def _parse_shapefile_zip(file_path: Path, tmp_path: Path):
    # Se extraen todos los archivos del ZIP para conservar .shx/.dbf/.prj.
    extracted = _extract_from_zip(file_path, tmp_path, suffixes=None)
    shapefiles = [path for path in extracted if path.suffix.lower() == '.shp']
    if not shapefiles:
        raise ParcelImportError(
            'El ZIP no contiene un Shapefile. Incluye .shp, .shx, .dbf y .prj.'
        )
    all_polygons = []
    skipped = 0
    source_crs = None
    for shapefile in shapefiles:
        polygons, skipped_file, crs = _parse_vector(shapefile)
        all_polygons.extend(polygons)
        skipped += skipped_file
        source_crs = source_crs or crs
    return all_polygons, skipped, source_crs


def _extract_from_zip(file_path: Path, tmp_path: Path, suffixes=None):
    """Extrae de un ZIP los archivos pedidos (o todos si suffixes=None)."""
    extracted = []
    with zipfile.ZipFile(file_path) as archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        total_size = sum(member.file_size for member in members)
        if total_size > MAX_UNCOMPRESSED_ZIP:
            raise ParcelImportError('El contenido del ZIP es demasiado grande.')

        root = tmp_path.resolve()
        for member in members:
            member_path = Path(member.filename)
            if member_path.is_absolute() or '..' in member_path.parts:
                raise ParcelImportError('El ZIP contiene rutas no permitidas.')
            target = (tmp_path / member_path).resolve()
            if not str(target).startswith(str(root)):
                raise ParcelImportError('El ZIP contiene rutas no permitidas.')
            if suffixes is None or member_path.suffix.lower() in suffixes:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, open(target, 'wb') as destination:
                    destination.write(source.read())
                extracted.append(target)
    return extracted


def _parse_vector(file_path: Path):
    layers = pyogrio.list_layers(file_path)
    polygons = []
    skipped = 0
    source_crs = None

    for layer in layers:
        layer_name = layer[0]
        try:
            data = pyogrio.read_dataframe(file_path, layer=layer_name)
        except Exception as exc:
            logger.debug('No se pudo leer la capa %s de %s: %s', layer_name, file_path, exc)
            continue
        if data is None or data.empty:
            continue

        if source_crs is None and data.crs is not None:
            source_crs = data.crs.to_string()

        if data.crs is not None:
            try:
                data = data.to_crs(4326)
            except Exception as exc:
                logger.debug('No se pudo reproyectar %s: %s', file_path, exc)
                continue

        layer_polygons, layer_skipped = _extract_polygons(list(data.geometry))
        polygons.extend(layer_polygons)
        skipped += layer_skipped

    _validate_wgs84(polygons)
    return polygons, skipped, source_crs


def _extract_polygons(geometries):
    """Convierte Polygon/MultiPolygon/GeometryCollection en una lista de Polygon."""
    polygons = []
    skipped = 0

    def add(geom):
        nonlocal skipped
        if geom is None or geom.is_empty:
            skipped += 1
            return
        geom = force_2d(geom)
        if geom.geom_type == 'Polygon':
            polygons.append(_clean_polygon(geom))
        elif geom.geom_type == 'MultiPolygon':
            for part in geom.geoms:
                add(part)
        elif geom.geom_type == 'GeometryCollection':
            for part in geom.geoms:
                add(part)
        else:
            skipped += 1

    for geometry in geometries:
        add(geometry)

    return [polygon for polygon in polygons if polygon is not None], skipped


def _clean_polygon(polygon: Polygon):
    if polygon.is_empty or polygon.area <= 0:
        return None
    if not polygon.is_valid:
        fixed = polygon.buffer(0)
        if fixed.is_empty:
            return None
        if fixed.geom_type == 'MultiPolygon':
            # buffer(0) puede devolver varias partes; nos quedamos con la mayor.
            fixed = max(fixed.geoms, key=lambda part: part.area)
        if fixed.geom_type != 'Polygon' or fixed.area <= 0:
            return None
        polygon = fixed
    return polygon


def _validate_wgs84(polygons):
    for polygon in polygons:
        min_x, min_y, max_x, max_y = polygon.bounds
        if min_x < -180 or max_x > 180 or min_y < -90 or max_y > 90:
            raise ParcelImportError(
                'Las coordenadas están fuera de rango para WGS84. Incluye el '
                'archivo .prj correcto o exporta el lote en EPSG:4326.'
            )
