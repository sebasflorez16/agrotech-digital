import json
import tempfile
import zipfile
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from parcels.importers import ParcelImportError, parse_geospatial_file

pytestmark = [pytest.mark.unit]

POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [-74.10, 4.60], [-74.05, 4.60], [-74.05, 4.65],
        [-74.10, 4.65], [-74.10, 4.60],
    ]],
}


def upload(name, data):
    return SimpleUploadedFile(name, data, content_type="application/octet-stream")


def test_geojson_feature_collection():
    payload = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {}, "geometry": POLYGON}],
    }
    result = parse_geospatial_file(upload("lote.geojson", json.dumps(payload).encode()))
    assert result["count"] == 1
    assert result["polygons"][0]["type"] == "Polygon"
    assert result["total_hectares"] > 0
    assert result["source_crs"] == "EPSG:4326"


def test_geojson_raw_geometry_and_multiple_features():
    second = {
        "type": "Polygon",
        "coordinates": [[
            [-74.00, 4.60], [-73.95, 4.60], [-73.95, 4.65],
            [-74.00, 4.65], [-74.00, 4.60],
        ]],
    }
    payload = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {}, "geometry": POLYGON},
            {"type": "Feature", "properties": {}, "geometry": second},
        ],
    }
    result = parse_geospatial_file(upload("dos.geojson", json.dumps(payload).encode()))
    assert result["count"] == 2


def test_multipolygon_is_split_into_polygons():
    multi = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[-74.10, 4.60], [-74.08, 4.60], [-74.08, 4.62], [-74.10, 4.62], [-74.10, 4.60]]],
            [[[-74.05, 4.60], [-74.03, 4.60], [-74.03, 4.62], [-74.05, 4.62], [-74.05, 4.60]]],
        ],
    }
    result = parse_geospatial_file(upload("multi.geojson", json.dumps(multi).encode()))
    assert result["count"] == 2
    assert all(p["type"] == "Polygon" for p in result["polygons"])


def test_kml_polygon():
    kml = """<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark>
    <Polygon><outerBoundaryIs><LinearRing><coordinates>
    -74.1,4.6,0 -74.0,4.6,0 -74.0,4.7,0 -74.1,4.7,0 -74.1,4.6,0
    </coordinates></LinearRing></outerBoundaryIs></Polygon>
    </Placemark></Document></kml>"""
    result = parse_geospatial_file(upload("lote.kml", kml.encode()))
    assert result["count"] == 1
    assert result["total_hectares"] > 0


def test_kmz_polygon():
    kml = """<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark>
    <Polygon><outerBoundaryIs><LinearRing><coordinates>
    -74.1,4.6,0 -74.0,4.6,0 -74.0,4.7,0 -74.1,4.7,0 -74.1,4.6,0
    </coordinates></LinearRing></outerBoundaryIs></Polygon>
    </Placemark></Document></kml>"""
    with tempfile.TemporaryDirectory() as tmp:
        archive_path = Path(tmp) / "lote.kmz"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("doc.kml", kml)
        result = parse_geospatial_file(upload("lote.kmz", archive_path.read_bytes()))
    assert result["count"] == 1


def test_shapefile_zip():
    pyogrio = pytest.importorskip("pyogrio")
    import geopandas as gpd
    from shapely.geometry import Polygon

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        gdf = gpd.GeoDataFrame(
            {"name": ["Lote"]},
            geometry=[Polygon([(-74.10, 4.60), (-74.05, 4.60), (-74.05, 4.65), (-74.10, 4.65)])],
            crs="EPSG:4326",
        )
        shapefile = tmp_path / "lote.shp"
        gdf.to_file(shapefile, driver="ESRI Shapefile")
        zip_path = tmp_path / "lote.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            for file in tmp_path.glob("lote.*"):
                archive.write(file, file.name)
        result = parse_geospatial_file(upload("lote.zip", zip_path.read_bytes()))
    assert result["count"] == 1
    assert result["source_crs"]


def test_gpx_without_polygons_is_rejected():
    gpx = """<?xml version="1.0"?><gpx version="1.1" creator="test"
    xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>
    <trkpt lat="4.6" lon="-74.1"/><trkpt lat="4.61" lon="-74.09"/>
    </trkseg></trk></gpx>"""
    with pytest.raises(ParcelImportError):
        parse_geospatial_file(upload("ruta.gpx", gpx.encode()))


def test_unsupported_extension_is_rejected():
    with pytest.raises(ParcelImportError):
        parse_geospatial_file(upload("lote.txt", b"hola"))
