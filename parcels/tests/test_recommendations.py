"""Tests del motor de recomendaciones (reglas puras, sin I/O)."""

from parcels.recommendations import build_recommendations


def _stats(ndvi=0.28, ndmi=0.05, savi=0.20, ndre=0.15):
    return {
        "ndvi": {"mean": ndvi},
        "ndmi": {"mean": ndmi},
        "savi": {"mean": savi},
        "ndre": {"mean": ndre},
    }


def test_dry_and_low_ndmi_generates_water_action():
    zones = [{
        "label": "Norte", "area_ha": 4.7, "ndvi_mean": 0.18, "ndmi_mean": 0.04,
        "ndre_mean": 0.14, "savi_mean": 0.18, "brecha_pct": -23.0,
        "priority": "alta",
    }]
    weather = {
        "rain_next_7d_mm": 5.0, "rain_last_7d_mm": 0.0, "tmax_avg_c": 31.0,
        "dry_forecast": True, "wet_forecast": False, "heat": True,
    }
    r = build_recommendations("Lote", _stats(), zones=zones, weather=weather)
    text = " ".join(a["title"].lower() + " " + a["detail"].lower() for a in r["actions"])
    assert "riego" in text
    assert r["zones"][0]["priority"] == "alta"
    assert "Norte" in r["summary"]


def test_wet_forecast_recommends_drainage():
    stats = _stats(ndvi=0.75, ndmi=0.35, savi=0.60, ndre=0.30)
    r = build_recommendations("Lote", stats, zones=[], weather={
        "rain_next_7d_mm": 50.0, "dry_forecast": False,
        "wet_forecast": True, "tmax_avg_c": 25.0, "heat": False,
    })
    assert r["actions"]
    assert any("drenaje" in a["title"].lower() for a in r["actions"])


def test_high_vigor_zone_is_not_alerted():
    """Una zona con brecha positiva NO debe marcarse como prioridad alta."""
    zones = [{
        "label": "Alto vigor", "area_ha": 2.45, "ndvi_mean": 0.46,
        "ndmi_mean": 0.30, "ndre_mean": 0.30, "savi_mean": 0.60,
        "brecha_pct": 140.4, "priority": "baja",
    }]
    r = build_recommendations(
        "Lote",
        _stats(ndvi=0.56, ndmi=0.30, savi=0.84, ndre=0.43),
        zones=zones,
        weather={"rain_next_7d_mm": 5.9, "dry_forecast": True,
                 "wet_forecast": False, "tmax_avg_c": 33.0, "heat": True},
    )
    assert r["zones"][0]["priority"] == "baja"
    assert not any("Alto vigor" in a["title"] for a in r["actions"])


def test_no_crop_cycle_does_not_crash():
    r = build_recommendations(
        "Lote", _stats(ndvi=0.50, ndmi=0.20, savi=0.40, ndre=0.25), weather=None
    )
    assert r["crop"] is None
    assert r["indices"]
    assert r["actions"]
