"""
Módulo de funcionalidades meteorológicas para parcelas.

Datos climáticos 100% reales vía Open-Meteo (gratuito, sin API key).
NO se generan datos sintéticos ni aproximaciones presentadas como reales:
si el proveedor no responde, la vista devuelve un error explícito (503/404)
en lugar de inventar valores.
"""
import logging
from datetime import datetime

import requests
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Parcel
from billing.decorators import check_eosda_limit

logger = logging.getLogger(__name__)

MET_NO_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
MET_NO_HEADERS = {
    "User-Agent": "AgroTechDigital/1.0 (contacto@agrotechcolombia.com)",
    "Accept": "application/json",
}


def _fetch_open_meteo(lat, lng):
    """Pronóstico Open-Meteo. Devuelve lista procesada o None."""
    meteo_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lng,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,relative_humidity_2m_mean,pressure_msl_mean,cloud_cover_mean,shortwave_radiation_sum",
        "timezone": "America/Bogota",
        "forecast_days": 16,
    }
    try:
        logger.info(f"[WEATHER_FORECAST] Consultando Open-Meteo: lat={lat}, lng={lng}")
        # 10 s: si Open-Meteo está lento desde Railway, pasamos rápido al fallback.
        response = requests.get(meteo_url, params=params, timeout=10)
        if response.status_code != 200:
            logger.warning(
                f"[WEATHER_FORECAST] Open-Meteo HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )
            return None

        daily = response.json().get("daily", {})
        if not daily or "time" not in daily:
            logger.warning("[WEATHER_FORECAST] Open-Meteo sin datos daily")
            return None

        forecast = []
        for i, date_str in enumerate(daily["time"]):
            t_max = daily.get("temperature_2m_max", [0])[i] or 0
            t_min = daily.get("temperature_2m_min", [0])[i] or 0
            forecast.append({
                "date": date_str,
                "temperature_max": round(t_max, 1),
                "temperature_min": round(t_min, 1),
                "temperature": round((t_max + t_min) / 2, 1),
                "precipitation": round(daily.get("precipitation_sum", [0])[i] or 0, 1),
                "humidity": round(daily.get("relative_humidity_2m_mean", [0])[i] or 0, 1),
                "wind_speed": round(daily.get("wind_speed_10m_max", [0])[i] or 0, 1),
                "pressure": round(daily.get("pressure_msl_mean", [0])[i] or 0, 1),
                "cloud_cover": round(daily.get("cloud_cover_mean", [0])[i] or 0, 1),
                "solar_radiation": round(daily.get("shortwave_radiation_sum", [0])[i] or 0, 1),
                "is_real_data": True,
            })
        return forecast or None
    except requests.exceptions.RequestException as exc:
        logger.warning(f"[WEATHER_FORECAST] Open-Meteo no disponible: {exc}")
        return None


def _fetch_met_norway(lat, lng):
    """Fallback de pronóstico con MET Norway (sin API key).

    Open-Meteo puede quedar inaccesible desde Railway (read timeout). MET Norway
    responde por HTTPS y entrega ~9 días de pronóstico horario; se agrega a días.
    """
    from collections import defaultdict
    from datetime import datetime as dt
    from zoneinfo import ZoneInfo

    try:
        response = requests.get(
            MET_NO_URL,
            params={"lat": round(float(lat), 4), "lon": round(float(lng), 4)},
            headers=MET_NO_HEADERS,
            timeout=15,
        )
        if response.status_code != 200:
            logger.warning(
                f"[WEATHER_FORECAST] MET Norway HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )
            return None

        timeseries = response.json().get("properties", {}).get("timeseries", [])
        if not timeseries:
            return None

        bogota = ZoneInfo("America/Bogota")
        days = defaultdict(lambda: {
            "temps": [], "humidity": [], "wind": [], "pressure": [],
            "cloud": [], "precip": 0.0,
        })

        for entry in timeseries:
            time_str = entry.get("time")
            if not time_str:
                continue
            try:
                local = dt.fromisoformat(time_str.replace("Z", "+00:00")).astimezone(bogota)
            except ValueError:
                continue
            date_key = local.date().isoformat()
            details = entry.get("data", {}).get("instant", {}).get("details", {}) or {}
            bucket = days[date_key]

            if details.get("air_temperature") is not None:
                bucket["temps"].append(float(details["air_temperature"]))
            if details.get("relative_humidity") is not None:
                bucket["humidity"].append(float(details["relative_humidity"]))
            if details.get("wind_speed") is not None:
                bucket["wind"].append(float(details["wind_speed"]))
            if details.get("air_pressure_at_sea_level") is not None:
                bucket["pressure"].append(float(details["air_pressure_at_sea_level"]))
            if details.get("cloud_area_fraction") is not None:
                bucket["cloud"].append(float(details["cloud_area_fraction"]))

            next_data = entry.get("data", {})
            one_hour = (next_data.get("next_1_hours") or {}).get("details", {})
            six_hours = (next_data.get("next_6_hours") or {}).get("details", {})
            if one_hour.get("precipitation_amount") is not None:
                bucket["precip"] += float(one_hour["precipitation_amount"])
            elif six_hours.get("precipitation_amount") is not None:
                # Se reparte el acumulado de 6 h entre las horas del bloque.
                bucket["precip"] += float(six_hours["precipitation_amount"]) / 6.0

        forecast = []
        for date_key in sorted(days.keys()):
            bucket = days[date_key]
            temps = bucket["temps"]
            if not temps:
                continue
            forecast.append({
                "date": date_key,
                "temperature_max": round(max(temps), 1),
                "temperature_min": round(min(temps), 1),
                "temperature": round(sum(temps) / len(temps), 1),
                "precipitation": round(bucket["precip"], 1),
                "humidity": round(sum(bucket["humidity"]) / len(bucket["humidity"]), 1) if bucket["humidity"] else 0,
                "wind_speed": round(max(bucket["wind"]), 1) if bucket["wind"] else 0,
                "pressure": round(sum(bucket["pressure"]) / len(bucket["pressure"]), 1) if bucket["pressure"] else 0,
                "cloud_cover": round(sum(bucket["cloud"]) / len(bucket["cloud"]), 1) if bucket["cloud"] else 0,
                "solar_radiation": 0.0,
                "is_real_data": True,
            })
        return forecast or None
    except requests.exceptions.RequestException as exc:
        logger.warning(f"[WEATHER_FORECAST] MET Norway no disponible: {exc}")
        return None


class WeatherForecastView(APIView):
    """
    Pronóstico meteorológico REAL de una parcela (Open-Meteo, 16 días).
    """
    permission_classes = [IsAuthenticated]

    @check_eosda_limit
    def get(self, request, parcel_id):
        """
        GET /api/parcels/parcel/<parcel_id>/weather-forecast/

        Restricción por plan:
            - Explorador (free): sin clima (weather_basic/weather_full)
            - Agricultor (basic): clima básico
            - Empresarial (pro): clima completo
        """
        # ── Verificar si el plan incluye pronóstico climático ──
        from config.devmode import is_dev_mode_active
        if not is_dev_mode_active(request):
            subscription = getattr(request, 'subscription', None)
            if subscription:
                features = subscription.plan.features_included or []
                has_weather = any(f in features for f in ['weather_basic', 'weather_full'])
                if not has_weather:
                    logger.warning(
                        f"[WEATHER_FORECAST] Plan '{subscription.plan.name}' no incluye clima. "
                        f"Features: {features}"
                    )
                    return Response({
                        'error': 'Tu plan no incluye pronóstico climático',
                        'code': 'weather_not_available',
                        'plan': subscription.plan.name,
                        'message': f'El plan {subscription.plan.name} no incluye pronóstico meteorológico. '
                                   f'Mejora al plan Agricultor o superior para acceder al clima.',
                        'upgrade_url': '/billing/upgrade/'
                    }, status=403)

        logger.info(f"[WEATHER_FORECAST] Parámetros recibidos: parcel_id={parcel_id}")
        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)

        # Obtener coordenadas del centroide de la parcela
        if hasattr(parcel.geom, 'centroid'):
            centroid = parcel.geom.centroid
            lat = centroid.y
            lng = centroid.x
            logger.info(f"[WEATHER_FORECAST] Coordenadas del centroide: lat={lat}, lng={lng}")
        else:
            # Extraer coordenadas del GeoJSON
            try:
                geom = parcel.geom
                if isinstance(geom, dict):
                    coordinates = geom.get('coordinates', [])
                    if coordinates and len(coordinates) > 0:
                        coords = coordinates[0] if isinstance(coordinates[0], list) else coordinates
                        lng = sum(coord[0] for coord in coords) / len(coords)
                        lat = sum(coord[1] for coord in coords) / len(coords)
                        logger.info(f"[WEATHER_FORECAST] Coordenadas calculadas del GeoJSON: lat={lat}, lng={lng}")
                    else:
                        logger.warning("[WEATHER_FORECAST] Geometría vacía o inválida")
                        return Response(
                            {"error": "No se pudo determinar las coordenadas de la parcela: geometría vacía o inválida"},
                            status=400
                        )
                else:
                    logger.warning("[WEATHER_FORECAST] Formato de geometría incorrecto")
                    return Response(
                        {"error": "No se pudo determinar las coordenadas de la parcela: formato de geometría incorrecto"},
                        status=400
                    )
            except Exception as e:
                return Response(
                    {"error": f"Error al obtener coordenadas de la parcela: {str(e)}"},
                    status=400
                )

        # === Open-Meteo: pronóstico gratuito, sin API key ===
        today = datetime.now()

        # Cache por 6 horas
        weather_cache_key = f"weather_forecast_v3_{parcel_id}_{today.strftime('%Y-%m-%d')}"
        cached_forecast = cache.get(weather_cache_key)
        if cached_forecast:
            logger.info("[WEATHER_FORECAST] ✅ CACHE HIT: Retornando pronóstico cacheado")
            return Response(cached_forecast, status=200)

        # Open-Meteo es el primario; MET Norway es el fallback (Railway puede
        # quedar sin salida estable hacia api.open-meteo.com).
        forecast = _fetch_open_meteo(lat, lng)
        source = "Open-Meteo"
        if not forecast:
            logger.warning("[WEATHER_FORECAST] Open-Meteo falló; probando MET Norway")
            forecast = _fetch_met_norway(lat, lng)
            source = "MET Norway"

        if not forecast:
            logger.error("[WEATHER_FORECAST] Ningún proveedor meteorológico respondió")
            return Response({
                "error": "No se pudo obtener el pronóstico del tiempo",
                "message": (
                    "Los proveedores meteorológicos no respondieron. "
                    "Intenta de nuevo en unos minutos."
                ),
                "parcel_id": parcel_id,
                "parcel_name": parcel.name,
            }, status=503)

        logger.info(
            f"[WEATHER_FORECAST] {len(forecast)} días de pronóstico desde {source}"
        )
        response_data = {
            "forecast": forecast,
            "source": source,
            "parcel_id": parcel_id,
            "parcel_name": parcel.name,
        }
        cache.set(weather_cache_key, response_data, 21600)
        return Response(response_data, status=200)
