"""
Pruebas del monitoreo radar Sentinel-1 (Planetary Computer S1 RTC, datos reales).

Se mockean las llamadas externas (STAC, SAS, rasterio) para probar la lógica de
extracción sigma0, serie temporal, detección de cambio y sectorización.

La prueba REAL de descubrimiento+lectura AOI está documentada en
docs/AUDITORIA_SEGUNDA_RONDA.md (ejecutada contra Planetary Computer).
"""
import math
import pytest
from unittest import mock

from parcels import sentinel1


POLYGON = {
    "type": "Polygon",
    "coordinates": [[[-74.0, 4.0], [-74.0, 4.01], [-73.99, 4.01], [-73.99, 4.0], [-74.0, 4.0]]],
}


# ----------------------------------------------------------------- detección

def test_detect_change_stable():
    series = [
        {"date": "2026-01-01", "available": True, "vv_db": -6.0, "vh_db": -12.0},
        {"date": "2026-02-01", "available": True, "vv_db": -6.3, "vh_db": -12.4},
    ]
    change = sentinel1.detect_radar_change(series)
    assert change["change_detected"] is False
    assert change["status"] == "stable"


def test_detect_change_requires_review_not_sick():
    series = [
        {"date": "2026-01-01", "available": True, "vv_db": -6.0, "vh_db": -12.0},
        {"date": "2026-02-01", "available": True, "vv_db": -10.0, "vh_db": -17.0},
    ]
    change = sentinel1.detect_radar_change(series)
    assert change["change_detected"] is True
    assert change["status"] == "review"
    assert "enferm" not in change["interpretation"].lower()
    assert "revis" in change["interpretation"].lower()


def test_detect_change_insufficient_data():
    series = [{"date": "2026-01-01", "available": True, "vv_db": -6.0, "vh_db": -12.0}]
    assert sentinel1.detect_radar_change(series)["change_detected"] is False


def test_dominant_orbit():
    scenes = [
        {"relative_orbit": 69},
        {"relative_orbit": 69},
        {"relative_orbit": 25},
    ]
    assert sentinel1._dominant_orbit(scenes) == 69


# ------------------------------------------------------ extracción sigma0

def test_mean_sigma0_db_linear_power():
    """_mean_sigma0_db: sigma0 ya es lineal (RTC) → dB = 10*log10(media)."""
    import numpy as np

    class FakeWindow:
        width = 5
        height = 5
        def intersection(self, other):
            return self

    fake_ds = mock.MagicMock()
    fake_ds.__enter__ = mock.MagicMock(return_value=fake_ds)
    fake_ds.__exit__ = mock.MagicMock(return_value=False)
    fake_ds.width = 100
    fake_ds.height = 100
    fake_ds.transform = object()
    fake_ds.crs = "EPSG:32618"
    # sigma0 lineal constante 0.1 → 10*log10(0.1) = -10 dB
    fake_ds.read.return_value = np.full((5, 5), 0.1, dtype="float32")

    fake_rasterio = mock.MagicMock()
    fake_rasterio.open.return_value = fake_ds
    fake_rasterio.Env.return_value = mock.MagicMock()

    with mock.patch.object(sentinel1, "rasterio", fake_rasterio), \
         mock.patch.object(sentinel1, "transform_bounds", return_value=(1, 2, 3, 4)), \
         mock.patch.object(sentinel1, "from_bounds", return_value=FakeWindow()), \
         mock.patch.object(sentinel1, "Window", return_value=FakeWindow()), \
         mock.patch.object(sentinel1, "_sign_url", return_value="https://signed"):
        result = sentinel1._mean_sigma0_db("https://x/vv.tif", (-74.0, 4.0, -73.99, 4.01))
        assert result is not None
        assert abs(result - (-10.0)) < 0.01


def test_mean_sigma0_db_returns_none_without_rasterio(monkeypatch):
    monkeypatch.setattr(sentinel1, "rasterio", None)
    assert sentinel1._mean_sigma0_db("https://x/vv.tif", (-74.0, 4.0, -73.99, 4.01)) is None


# -------------------------------------------------------------- orquestador

def test_get_radar_monitoring_no_data(monkeypatch):
    monkeypatch.setattr(sentinel1, "search_sentinel1_scenes", lambda *a, **k: [])
    result = sentinel1.get_radar_monitoring(POLYGON, days_back=30)
    assert result["available"] is False
    assert "no disponible" in result["message"].lower()


def test_get_radar_monitoring_with_data(monkeypatch):
    scenes = [
        {"id": "s1", "date": "2026-01-01", "relative_orbit": 69, "vv_href": "x", "vh_href": "y"},
        {"id": "s2", "date": "2026-02-01", "relative_orbit": 69, "vv_href": "x", "vh_href": "y"},
    ]
    vals = {"s1": {"vv_db": -6.0, "vh_db": -12.0}, "s2": {"vv_db": -10.0, "vh_db": -17.0}}

    monkeypatch.setattr(sentinel1, "search_sentinel1_scenes", lambda *a, **k: scenes)
    monkeypatch.setattr(sentinel1, "_sigma0_for_scene", lambda scene, bbox: vals.get(scene["id"]))

    result = sentinel1.get_radar_monitoring(POLYGON, days_back=60)
    assert result["available"] is True
    assert result["data_nature"] == "real"
    assert len(result["time_series"]) == 2
    assert result["change"]["change_detected"] is True


def test_sectorization_attributes_change(monkeypatch):
    class FakeZone:
        def __init__(self, cid, label, geom):
            self.cluster_id = cid
            self.label = label
            self.geometry_geojson = geom

    zones = [FakeZone(3, "Sector C-04", POLYGON)]

    def fake_series(geom, date_from, date_to, max_results):
        return [
            {"date": "2026-01-01", "available": True, "vv_db": -6.0, "vh_db": -12.0},
            {"date": "2026-02-01", "available": True, "vv_db": -10.0, "vh_db": -17.0},
        ]

    monkeypatch.setattr(sentinel1, "get_radar_time_series", fake_series)
    sectors = sentinel1._attribute_change_to_sectors(zones, "2026-01-01", "2026-02-01")
    assert len(sectors) == 1
    assert sectors[0]["label"] == "Sector C-04"


def test_provider_error_returns_no_data(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("provider down")
    monkeypatch.setattr(sentinel1, "search_sentinel1_scenes", boom)
    result = sentinel1.get_radar_monitoring(POLYGON, days_back=30)
    assert result["available"] is False
    assert result["last_observation"] is None


def test_compat_wrapper_no_simulation(monkeypatch):
    monkeypatch.setattr(sentinel1, "search_sentinel1_scenes", lambda *a, **k: [])
    result = sentinel1.get_crop_status_from_radar(POLYGON, days_back=30)
    assert result["radar_status"] == "no_data"
    assert result["change_detected"] is False


# --------------------------------------------------------------- capas raster

def test_linear_to_db():
    import numpy as np
    arr = np.array([1.0, 0.1, 0.01])
    db = sentinel1._linear_to_db(arr)
    assert abs(db[0]) < 1e-9          # 10*log10(1) = 0
    assert abs(db[1] - (-10.0)) < 1e-9
    assert abs(db[2] - (-20.0)) < 1e-9


def test_compute_rvi():
    import numpy as np
    # RVI = 4*VH/(VV+VH). VV=VH=1 → 2.0? No: 4*1/(2)=2.0 → clip a 1.0
    rvi = sentinel1.compute_rvi(np.array([1.0]), np.array([1.0]))
    assert abs(rvi[0] - 1.0) < 1e-6
    # VH=0 → RVI=0
    rvi2 = sentinel1.compute_rvi(np.array([1.0]), np.array([0.0]))
    assert abs(rvi2[0]) < 1e-6


def test_grid_to_png_generates_image():
    import numpy as np
    arr = np.full((20, 20), -10.0)
    arr[0, 0] = np.nan
    png = sentinel1._grid_to_png(arr, -25, 0, "sigma0")
    assert png is not None
    assert png.startswith("iVBOR") or len(png) > 100


def test_change_grid_to_png_nan_safe():
    import numpy as np
    mag = np.full((20, 20), np.nan)
    mag[2:5, 2:5] = 4.0  # cambio
    png = sentinel1._change_grid_to_png(mag, 2.0)
    assert png is not None
    assert len(png) > 100


def test_get_radar_layers_with_mock(monkeypatch):
    import numpy as np
    scenes = [
        {"id": "s1", "date": "2026-02-01", "relative_orbit": 69, "vv_href": "x", "vh_href": "y"},
        {"id": "s2", "date": "2026-01-01", "relative_orbit": 69, "vv_href": "x", "vh_href": "y"},
    ]
    # sigma0 lineal: última escena vs anterior (diferentes → cambio)
    latest = (np.full((30, 30), 0.5), np.full((30, 30), 0.2), (-74.0, 4.0, -73.99, 4.01))
    prev = (np.full((30, 30), 0.2), np.full((30, 30), 0.1), (-74.0, 4.0, -73.99, 4.01))
    calls = {"n": 0}

    def fake_read(scene, geom, **k):
        calls["n"] += 1
        return latest if scene["id"] == "s1" else prev

    monkeypatch.setattr(sentinel1, "search_sentinel1_scenes", lambda *a, **k: scenes)
    monkeypatch.setattr(sentinel1, "read_aoi_sigma0", fake_read)

    result = sentinel1.get_radar_layers(POLYGON, "2026-01-01", "2026-02-01")
    assert result["available"] is True
    assert result["layers"]["vv"]["image_base64"] is not None
    assert result["layers"]["rvi"]["image_base64"] is not None
    assert result["change"]["change_detected"] is True
    assert result["change"]["change_heatmap"] is not None
