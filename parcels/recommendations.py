"""
Motor de recomendaciones agronómicas con datos REALES.

Combina:
- índices Sentinel-2 (NDVI/NDMI/SAVI/NDRE) del lote,
- cultivo y etapa fenológica (si hay ciclo activo),
- zonas de manejo (última sectorización),
- clima (Open-Meteo: lluvia últimos 7 días / próximos 7 días y Tmax),
- fecha.

No inventa datos ni precios de mercado. Si falta un dato, se omite.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import requests
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

INDEX_KEYS = ("ndvi", "ndmi", "savi", "ndre")
INDEX_LABEL = {"ndvi": "NDVI", "ndmi": "NDMI", "savi": "SAVI", "ndre": "NDRE"}

PRIORITY_LABEL = {
    "alta": "Alta", "high": "Alta",
    "media": "Media", "medium": "Media",
    "baja": "Baja", "low": "Baja",
}


def _priority_rank(p):
    return {"alta": 0, "high": 0, "media": 1, "medium": 1, "baja": 2, "low": 2}.get(
        (p or "").lower(), 3
    )


# ─────────────────────────────────────────────────────────────
#  Clima (Open-Meteo, sin API key)
# ─────────────────────────────────────────────────────────────

def _parcel_center(geom):
    """Devuelve (lat, lng) del centro del lote a partir de su GeoJSON."""
    try:
        from .sentinel1 import _geometry_bbox_lonlat
        bbox = _geometry_bbox_lonlat(geom)
        if not bbox:
            return None
        min_lng, min_lat, max_lng, max_lat = bbox
        return ((min_lat + max_lat) / 2.0, (min_lng + max_lng) / 2.0)
    except Exception:
        return None


def _sum_daily(payload, field):
    daily = (payload or {}).get("daily") or {}
    values = [v for v in (daily.get(field) or []) if isinstance(v, (int, float))]
    return sum(values) if values else None


def _avg_daily(payload, field):
    daily = (payload or {}).get("daily") or {}
    values = [v for v in (daily.get(field) or []) if isinstance(v, (int, float))]
    return round(sum(values) / len(values), 1) if values else None


def _weather_context(geom):
    """Lluvia últimos/próximos 7 días y Tmax promedio (Open-Meteo). Cache 6 h."""
    center = _parcel_center(geom)
    if not center:
        return None
    lat, lng = center
    key = f"rec:wx:{lat:.4f}:{lng:.4f}:{date.today().isoformat()}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    today = date.today()
    forecast = None
    archive = None

    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lng,
                "daily": "precipitation_sum,temperature_2m_max",
                "forecast_days": 7, "timezone": "America/Bogota",
            },
            timeout=10,
        )
        if r.status_code == 200:
            forecast = r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Open-Meteo forecast falló: %s", exc)

    try:
        r = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": lat, "longitude": lng,
                "start_date": (today - timedelta(days=7)).isoformat(),
                "end_date": (today - timedelta(days=1)).isoformat(),
                "daily": "precipitation_sum,temperature_2m_max",
                "timezone": "America/Bogota",
            },
            timeout=10,
        )
        if r.status_code == 200:
            archive = r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Open-Meteo archive falló: %s", exc)

    rain_next = _sum_daily(forecast, "precipitation_sum")
    rain_last = _sum_daily(archive, "precipitation_sum")
    tmax_avg = _avg_daily(forecast, "temperature_2m_max")

    if rain_next is None and rain_last is None and tmax_avg is None:
        return None

    ctx = {
        "rain_last_7d_mm": round(rain_last, 1) if rain_last is not None else None,
        "rain_next_7d_mm": round(rain_next, 1) if rain_next is not None else None,
        "tmax_avg_c": tmax_avg,
        "dry_forecast": (rain_next is not None and rain_next < 10),
        "wet_forecast": (rain_next is not None and rain_next > 40),
        "heat": (tmax_avg is not None and tmax_avg >= 30),
        "source": "Open-Meteo",
    }
    cache.set(key, ctx, 6 * 3600)
    return ctx


# ─────────────────────────────────────────────────────────────
#  Índices
# ─────────────────────────────────────────────────────────────

def _generic_index_status(key, value):
    if key == "ndvi":
        if value < 0.30:
            return "warning", "Vigor bajo para el cultivo."
        if value < 0.60:
            return "normal", "Vigor medio."
        return "optimal", "Buen vigor."
    if key == "ndmi":
        if value < 0.10:
            return "warning", "Humedad de hoja baja (posible estrés hídrico)."
        if value < 0.30:
            return "normal", "Humedad media."
        return "optimal", "Buena humedad."
    if key == "savi":
        if value < 0.25:
            return "warning", "Cobertura baja."
        if value < 0.50:
            return "normal", "Cobertura media."
        return "optimal", "Buena cobertura."
    if key == "ndre":
        if value < 0.20:
            return "warning", "Clorofila/nitrógeno bajo."
        return "normal", "Clorofila en rango."
    return "unknown", ""


def _index_entries(stats, crop_cycle):
    entries = []
    for key in INDEX_KEYS:
        s = (stats or {}).get(key)
        if not s or s.get("mean") is None:
            continue
        value = float(s["mean"])
        status, message = _generic_index_status(key, value)
        optimal = rng = deviation = None
        if crop_cycle and key in ("ndvi", "ndmi", "savi"):
            try:
                interp = crop_cycle.get_index_interpretation(key, value)
                if interp and interp.get("status") != "unknown":
                    status = interp.get("status")
                    message = interp.get("message") or message
                    idx = interp.get("index") or {}
                    optimal = idx.get("optimal")
                    rng = idx.get("range")
                    deviation = idx.get("deviation_percent")
            except Exception:
                pass
        entries.append({
            "key": key,
            "label": INDEX_LABEL[key],
            "value": round(value, 3),
            "status": status,
            "message": message,
            "optimal": optimal,
            "range": rng,
            "deviation_percent": deviation,
        })
    return entries


# ─────────────────────────────────────────────────────────────
#  Zonas
# ─────────────────────────────────────────────────────────────

def _zone_entry(zone, parcel_ndvi, parcel_ndmi, weather):
    ndvi = zone.get("ndvi_mean")
    ndmi = zone.get("ndmi_mean")
    ndre = zone.get("ndre_mean")
    brecha = zone.get("brecha_pct")
    prio = (zone.get("priority") or "media").lower()

    finding = []
    action = []
    timing = "1 semana"

    if ndvi is not None:
        extra = f" ({brecha:+.0f}% vs promedio)" if isinstance(brecha, (int, float)) else ""
        finding.append(f"NDVI {ndvi:.2f}{extra}")
    if ndmi is not None:
        finding.append(f"humedad {ndmi:.2f}")

    wet = bool((weather or {}).get("wet_forecast"))

    if ndmi is not None and ndmi < 0.10:
        action.append("Revisar riego y humedad del suelo en esta zona.")
        timing = "24-48 h"
        prio = "alta"
    elif ndmi is not None and ndmi > 0.40 and wet:
        action.append("Revisar drenaje; evitar riego por exceso de humedad.")
        timing = "48-72 h"

    # La brecha_pct ya está calculada contra el promedio del lote en la MISMA
    # escena de la sectorización. No comparamos con el NDVI de otra fecha.
    if isinstance(brecha, (int, float)):
        low_vs_parcel = brecha <= -10
        if brecha <= -30:
            prio = "alta"
        elif brecha <= -20 and _priority_rank(prio) > 1:
            prio = "media"
    else:
        low_vs_parcel = (
            parcel_ndvi is not None and ndvi is not None and ndvi < parcel_ndvi - 0.05
        )

    if low_vs_parcel:
        action.append("Inspeccionar en campo (plagas, compactación, germinación).")
        if ndre is not None and ndre < 0.20:
            action.append("Evaluar nitrógeno con análisis foliar antes de fertilizar.")
        if timing == "1 semana":
            timing = "48-72 h"

    if not action:
        action.append("Mantener el manejo actual y monitorear la evolución.")
        timing = "2 semanas"

    return {
        "label": zone.get("label") or "Zona",
        "area_ha": round(float(zone.get("area_ha") or 0), 2),
        "ndvi_mean": round(ndvi, 3) if ndvi is not None else None,
        "ndmi_mean": round(ndmi, 3) if ndmi is not None else None,
        "brecha_pct": round(brecha, 1) if isinstance(brecha, (int, float)) else None,
        "priority": prio,
        "finding": " · ".join(finding) if finding else "Sin datos de índice.",
        "action": " ".join(action),
        "timing": timing,
    }


# ─────────────────────────────────────────────────────────────
#  Construcción del reporte (sin I/O)
# ─────────────────────────────────────────────────────────────

def build_recommendations(parcel_name, stats, scene=None, crop_cycle=None,
                          zones=None, weather=None, zones_scene_date=None):
    indices = _index_entries(stats, crop_cycle)
    parcel_ndvi = next((i["value"] for i in indices if i["key"] == "ndvi"), None)
    parcel_ndmi = next((i["value"] for i in indices if i["key"] == "ndmi"), None)

    zone_entries = [
        _zone_entry(z, parcel_ndvi, parcel_ndmi, weather) for z in (zones or [])
    ]
    zone_entries.sort(key=lambda z: _priority_rank(z["priority"]))

    dry = bool((weather or {}).get("dry_forecast"))
    wet = bool((weather or {}).get("wet_forecast"))
    heat = bool((weather or {}).get("heat"))

    actions = []

    if parcel_ndmi is not None and parcel_ndmi < 0.10:
        actions.append({
            "priority": "alta",
            "title": "Revisar riego del lote",
            "detail": "El NDMI promedio es bajo (poca agua en la hoja)."
                      + (" Se esperan pocas lluvias en 7 días." if dry else ""),
            "timing": "24-48 h",
            "zone": "Todo el lote",
        })

    if dry:
        actions.append({
            "priority": "media",
            "title": "Ventana seca",
            "detail": f"Lluvia prevista baja ({(weather or {}).get('rain_next_7d_mm')} mm/7d). "
                      "Prioriza riego y evita fertilizar si el suelo está seco.",
            "timing": "Esta semana",
            "zone": "Lote",
        })

    if wet:
        actions.append({
            "priority": "media",
            "title": "Revisar drenaje",
            "detail": f"Se esperan lluvias altas ({(weather or {}).get('rain_next_7d_mm')} mm/7d). "
                      "Evita riego y revisa encharcamientos.",
            "timing": "48-72 h",
            "zone": "Lote",
        })

    if heat:
        actions.append({
            "priority": "media",
            "title": "Estrés térmico",
            "detail": f"Tmax promedio {(weather or {}).get('tmax_avg_c')} °C. "
                      "Riega en horas frescas y vigila el estrés.",
            "timing": "Esta semana",
            "zone": "Lote",
        })

    if parcel_ndvi is not None and parcel_ndvi < 0.30:
        actions.append({
            "priority": "alta",
            "title": "Bajo vigor general",
            "detail": "NDVI promedio bajo. Revisa nutrición, plagas y compactación; "
                      "considera análisis foliar.",
            "timing": "48-72 h",
            "zone": "Todo el lote",
        })

    for z in zone_entries:
        if _priority_rank(z["priority"]) == 0:
            actions.append({
                "priority": "alta",
                "title": f"Zona {z['label']}",
                "detail": f"{z['finding']}. {z['action']}",
                "timing": z["timing"],
                "zone": z["label"],
            })

    if not actions:
        actions.append({
            "priority": "baja",
            "title": "Mantener el plan",
            "detail": "Sin alertas relevantes; continúa el manejo y vuelve a monitorear en 1-2 semanas.",
            "timing": "2 semanas",
            "zone": "Lote",
        })

    actions.sort(key=lambda a: _priority_rank(a["priority"]))
    seen = set()
    actions = [a for a in actions if not (a["title"] in seen or seen.add(a["title"]))]

    crop = None
    if crop_cycle:
        try:
            stage = crop_cycle.current_stage
            crop = {
                "name": crop_cycle.crop_catalog.name if crop_cycle.crop_catalog else None,
                "stage": stage.name if stage else None,
                "days_since_planting": crop_cycle.days_since_planting,
                "progress_percent": crop_cycle.progress_percent,
            }
        except Exception:
            crop = None

    summary_parts = []
    if crop:
        summary_parts.append(
            f"{crop['name']} en etapa {crop['stage']} (día {crop['days_since_planting']})."
        )
    else:
        summary_parts.append("Sin ciclo de cultivo asignado; recomendaciones generales.")
    if indices:
        summary_parts.append(
            "Índices: " + ", ".join(f"{i['label']} {i['value']:.2f}" for i in indices) + "."
        )
    if zone_entries:
        risk = zone_entries[0]
        summary_parts.append(
            f"Zona prioritaria: {risk['label']} ({risk['area_ha']:.2f} ha)."
        )
        if zones_scene_date:
            summary_parts.append(f"Sectorización del {zones_scene_date}.")
    if scene and scene.get("date"):
        summary_parts.append(f"Escena Sentinel-2 del {scene['date']}.")
    if weather and weather.get("rain_next_7d_mm") is not None:
        summary_parts.append(f"Lluvia prevista 7 d: {weather['rain_next_7d_mm']} mm.")

    return {
        "parcel_name": parcel_name,
        "generated_at": timezone.now().isoformat(),
        "scene": scene or {},
        "crop": crop,
        "weather": weather,
        "indices": indices,
        "zones": zone_entries,
        "zones_scene_date": zones_scene_date,
        "summary": " ".join(summary_parts),
        "actions": actions,
        "disclaimer": (
            "Recomendaciones de apoyo basadas en datos satelitales y climáticos reales. "
            "No sustituyen un diagnóstico agronómico; confirma en campo antes de aplicar."
        ),
    }


# ─────────────────────────────────────────────────────────────
#  Wrapper con I/O (S2, zonas, clima)
# ─────────────────────────────────────────────────────────────

def build_parcel_report(parcel, stats=None, scene=None):
    """Construye el reporte completo para una parcela (usa datos reales)."""
    if not stats:
        try:
            from .sentinel2 import _find_scene_and_arrays, get_index_analysis
            scene_obj, arrays = _find_scene_and_arrays(
                parcel.geom, str(date.today()), mask_clouds=True
            )
            if scene_obj and arrays:
                stats = get_index_analysis(
                    parcel.geom, str(date.today()), arrays=arrays
                )
                scene = scene_obj
        except Exception as exc:  # noqa: BLE001
            logger.warning("S2 para recomendaciones falló: %s", exc)

    crop_cycle = None
    try:
        crop_cycle = (
            parcel.crop_cycles.filter(status="active")
            .order_by("-planting_date").first()
        )
    except Exception:
        crop_cycle = None

    zones = []
    zone_scene_date = None
    try:
        from .models import ParcelZonification
        zon = (
            ParcelZonification.objects.filter(parcel=parcel, status="ready")
            .order_by("-created_at").first()
        )
        if zon:
            zone_scene_date = zon.scene_date.isoformat() if zon.scene_date else None
            for z in zon.zones.all().order_by("cluster_id"):
                zones.append({
                    "label": z.label,
                    "area_ha": z.area_ha,
                    "ndvi_mean": z.ndvi_mean,
                    "ndmi_mean": z.ndmi_mean,
                    "savi_mean": z.savi_mean,
                    "ndre_mean": z.ndre_mean,
                    "brecha_pct": z.brecha_pct,
                    "priority": z.priority,
                })
    except Exception as exc:  # noqa: BLE001
        logger.warning("Zonas para recomendaciones fallaron: %s", exc)

    weather = _weather_context(parcel.geom) if parcel.geom else None

    return build_recommendations(
        parcel.name, stats, scene=scene, crop_cycle=crop_cycle,
        zones=zones, weather=weather, zones_scene_date=zone_scene_date,
    )
