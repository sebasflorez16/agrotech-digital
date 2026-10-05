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
        weather_cache_key = f"weather_forecast_openmeteo_{parcel_id}_{today.strftime('%Y-%m-%d')}"
        cached_forecast = cache.get(weather_cache_key)
        if cached_forecast:
            logger.info("[WEATHER_FORECAST] ✅ CACHE HIT: Retornando pronóstico cacheado")
            return Response(cached_forecast, status=200)

        # Llamar a Open-Meteo API
        meteo_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lng,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,relative_humidity_2m_mean,pressure_msl_mean,cloud_cover_mean",
            "timezone": "America/Bogota",
            "forecast_days": 16,
        }

        try:
            logger.info(f"[WEATHER_FORECAST] Consultando Open-Meteo: lat={lat}, lng={lng}")
            response = requests.get(meteo_url, params=params, timeout=15)
            logger.info(f"[WEATHER_FORECAST] Status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"[WEATHER_FORECAST] Error Open-Meteo HTTP {response.status_code}: {response.text[:200]}")
                return Response({
                    "error": f"Error del proveedor meteorológico HTTP {response.status_code}",
                    "message": "No se pudo obtener el pronóstico del tiempo",
                    "parcel_id": parcel_id,
                    "parcel_name": parcel.name
                }, status=503)

            data = response.json()
            daily = data.get("daily", {})
            if not daily or "time" not in daily:
                logger.error(f"[WEATHER_FORECAST] Respuesta Open-Meteo sin datos daily: {data}")
                return Response({
                    "error": "Formato de respuesta inesperado",
                    "message": "No se pudo obtener datos meteorológicos",
                    "parcel_id": parcel_id,
                    "parcel_name": parcel.name
                }, status=404)

            # Procesar datos al formato del frontend (solo valores reales)
            processed_forecast = []
            days = daily["time"]
            for i, date_str in enumerate(days):
                t_max = daily.get("temperature_2m_max", [None])[i] or 0
                t_min = daily.get("temperature_2m_min", [None])[i] or 0
                processed_forecast.append({
                    "date": date_str,
                    "temperature_max": round(t_max, 1),
                    "temperature_min": round(t_min, 1),
                    "temperature": round((t_max + t_min) / 2, 1),
                    "precipitation": round(daily.get("precipitation_sum", [0])[i] or 0, 1),
                    "humidity": round(daily.get("relative_humidity_2m_mean", [0])[i] or 0, 1),
                    "wind_speed": round(daily.get("wind_speed_10m_max", [0])[i] or 0, 1),
                    "pressure": round(daily.get("pressure_msl_mean", [0])[i] or 0, 1),
                    "cloud_cover": round(daily.get("cloud_cover_mean", [0])[i] or 0, 1),
                    "is_real_data": True,
                })

            logger.info(f"[WEATHER_FORECAST] Procesados {len(processed_forecast)} días de pronóstico")

            response_data = {
                "forecast": processed_forecast,
                "source": "Open-Meteo",
                "parcel_id": parcel_id,
                "parcel_name": parcel.name,
            }
            cache.set(weather_cache_key, response_data, 21600)
            return Response(response_data, status=200)

        except requests.exceptions.RequestException as e:
            logger.error(f"[WEATHER_FORECAST] Error de conexión: {str(e)}")
            return Response({
                "error": "Error de conexión con la API meteorológica",
                "message": str(e),
                "parcel_id": parcel_id,
                "parcel_name": parcel.name
            }, status=503)
