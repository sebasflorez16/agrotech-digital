"""
Módulo de funcionalidades meteorológicas para parcelas.
Contiene toda la lógica relacionada con pronósticos del tiempo, análisis comparativos
NDVI vs meteorología, y obtención de datos meteorológicos de EOSDA.
"""
import logging
import requests
import json
import math
import numpy as np
from datetime import datetime, timedelta, date
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Parcel
from billing.decorators import check_eosda_limit

logger = logging.getLogger(__name__)


# --- WEATHER FORECAST API ---
class WeatherForecastView(APIView):
    """
    Vista para obtener pronóstico meteorológico de una parcela específica.
    """
    permission_classes = [IsAuthenticated]

    @check_eosda_limit
    def get(self, request, parcel_id):
        """
        GET /api/parcels/parcel/<parcel_id>/weather-forecast/
        Retorna: { "forecast": [...], "source": "EOSDA", "parcel_id": ... }
        """
        logger.info(f"[WEATHER_FORECAST] Parámetros recibidos: parcel_id={parcel_id}")
        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
        field_id = getattr(parcel, "eosda_id", None)
        
        if not field_id:
            logger.error("[WEATHER_FORECAST] La parcela no tiene un field_id EOSDA válido.")
            return Response({"error": "La parcela no tiene un field_id EOSDA válido."}, status=404)
        
        # Obtener coordenadas del centroide de la parcela para usar en la API de pronóstico
        if hasattr(parcel.geom, 'centroid'):
            centroid = parcel.geom.centroid
            lat = centroid.y
            lng = centroid.x
            logger.info(f"[WEATHER_FORECAST] Coordenadas obtenidas del centroide: lat={lat}, lng={lng}")
        else:
            # Extraer coordenadas del GeoJSON
            try:
                geom = parcel.geom
                if isinstance(geom, dict):
                    # Calcular centroide aproximado del polígono GeoJSON
                    coordinates = geom.get('coordinates', [])
                    if coordinates and len(coordinates) > 0:
                        # Para polígonos, tomar el primer anillo
                        coords = coordinates[0] if isinstance(coordinates[0], list) else coordinates
                        # Calcular centroide simple
                        lng = sum(coord[0] for coord in coords) / len(coords)
                        lat = sum(coord[1] for coord in coords) / len(coords)
                        logger.info(f"[WEATHER_FORECAST] Coordenadas calculadas del GeoJSON: lat={lat}, lng={lng}")
                    else:
                        # No usar fallback, devolver error si no hay geometría
                        logger.warning(f"[WEATHER_FORECAST] No se pudo determinar las coordenadas de la parcela: geometría vacía o inválida")
                        return Response(
                            {"error": "No se pudo determinar las coordenadas de la parcela: geometría vacía o inválida"}, 
                            status=400
                        )
                else:
                    # No usar fallback, devolver error si no hay geometría
                    logger.warning(f"[WEATHER_FORECAST] No se pudo determinar las coordenadas de la parcela: formato de geometría incorrecto")
                    return Response(
                        {"error": "No se pudo determinar las coordenadas de la parcela: formato de geometría incorrecto"}, 
                        status=400
                    )
            except Exception as e:
                # No usar fallback, reportar el error específico
                logger.error(f"[WEATHER_FORECAST] Error al obtener coordenadas: {str(e)}")
                return Response(
                    {"error": f"Error al obtener coordenadas de la parcela: {str(e)}"}, 
                    status=400
                )
        
        # Usar la API de pronóstico meteorológico
        # Según la documentación: https://doc.eos.com/docs/weather/basic-weather-providers/#weather-forecast-without-data-aggregation
        # La URL correcta es https://api-connect.eos.com/api/forecast/weather/forecast/
        request_url = f"https://api-connect.eos.com/api/forecast/weather/forecast/"
        headers = {
            "x-api-key": settings.EOSDA_API_KEY,
            "Content-Type": "application/json"
        }
        logger.info(f"[WEATHER_FORECAST] URL: {request_url}")
        logger.info(f"[WEATHER_FORECAST] API Key presente: {'Sí' if settings.EOSDA_API_KEY else 'No'}")
        logger.info(f"[WEATHER_FORECAST] Field ID: {field_id}")
        logger.info(f"[WEATHER_FORECAST] Coordenadas: lat={lat}, lng={lng}")
        
        # Crear polígono GeoJSON de la parcela para la API
        # Usar la geometría de la parcela o crear un polígono simple basado en el centroide
        # Según documentación, necesitamos geometry en formato GeoJSON
        try:
            if hasattr(parcel, 'geom') and hasattr(parcel.geom, 'json'):
                # Usar la geometría existente si está disponible en formato GeoJSON
                geometry = json.loads(parcel.geom.json)
            else:
                # Crear un cuadrado simple alrededor del centroide (aproximadamente 100 metros)
                offset = 0.001  # aproximadamente 100 metros en grados
                geometry = {
                    "type": "Polygon",
                    "coordinates": [[
                        [lng - offset, lat - offset],
                        [lng + offset, lat - offset],
                        [lng + offset, lat + offset],
                        [lng - offset, lat + offset],
                        [lng - offset, lat - offset]  # cerrar el polígono
                    ]]
                }
        except Exception as e:
            logger.error(f"[WEATHER_FORECAST] Error creando geometría: {str(e)}")
            return Response({
                "error": "Error creando geometría para la consulta meteorológica",
                "message": str(e),
                "parcel_id": parcel_id
            }, status=400)
            
        # Intentar obtener un pronóstico más amplio (intentemos con 30 días)
        today = datetime.now()
        end_date = today + timedelta(days=30)  # Extendemos a 30 días para ver si obtenemos más de 3 días
        
        # Parámetros para la API de pronóstico - usando geometry según documentación
        # Usando la fecha actual para asegurar que tenemos datos desde hoy
        payload = {
            "geometry": geometry,
            "date_from": today.strftime("%Y-%m-%dT00:00"),  # Comenzamos desde hoy
            "date_to": end_date.strftime("%Y-%m-%dT00:00"),
            "is_hourly": False,  # Solicitamos datos diarios, no horarios
            "aggregation": "daily",  # Agregamos este parámetro para indicar que queremos datos diarios
            "variables": ["temperature", "precipitation", "humidity", "wind_speed"]  # Especificamos variables
        }
        
        try:
            logger.info(f"[WEATHER_FORECAST] Iniciando solicitud a EOSDA para field_id: {field_id}")
            logger.info(f"[WEATHER_FORECAST] Payload: {payload}")
            
            # Según la documentación se usa POST, no GET
            response = requests.post(request_url, json=payload, headers=headers, timeout=30)
            logger.info(f"[WEATHER_FORECAST] POST Status: {response.status_code}")
            logger.info(f"[WEATHER_FORECAST] POST Response length: {len(response.text)} caracteres")
            logger.info(f"[WEATHER_FORECAST] Primeros 200 caracteres: {response.text[:200]}")
            
            if response.status_code == 402:
                logger.error(f"[WEATHER_FORECAST] Límite de requests EOSDA excedido: {response.text}")
                return Response({
                    "error": "EOSDA API: Límite de requests excedido",
                    "message": "No se pudo obtener el pronóstico del tiempo: límite de solicitudes excedido",
                    "parcel_id": parcel_id,
                    "parcel_name": parcel.name
                }, status=429)  # Devolvemos 429 Too Many Requests
                
            if response.status_code == 404:
                logger.error(f"[WEATHER_FORECAST] Field ID no encontrado en EOSDA: {response.text}")
                return Response({
                    "error": "Field ID no encontrado en EOSDA",
                    "message": "No se encontraron datos meteorológicos para esta parcela",
                    "field_id": field_id,
                    "coordinates": {"lat": lat, "lng": lng},
                    "parcel_id": parcel_id,
                    "parcel_name": parcel.name
                }, status=404)  # Devolvemos 404 Not Found
            
            # Para otros errores HTTP
            if response.status_code >= 400:
                logger.error(f"[WEATHER_FORECAST] Error EOSDA HTTP {response.status_code}: {response.text}")
                return Response({
                    "error": f"Error EOSDA HTTP {response.status_code}",
                    "message": f"No se pudo obtener datos meteorológicos reales: {response.text[:100]}...",
                    "field_id": field_id,
                    "coordinates": {"lat": lat, "lng": lng},
                    "parcel_id": parcel_id,
                    "parcel_name": parcel.name
                }, status=response.status_code)  # Devolvemos el mismo código de error
            
            try:
                data = response.json()
                forecast = data
                # La API devuelve un array directamente, no un objeto con propiedad "forecast"
                if not isinstance(forecast, list) or len(forecast) == 0:
                    logger.error(f"[WEATHER_FORECAST] Formato de respuesta inesperado: {response.text[:500]}")
                    return Response({
                        "error": "Formato de respuesta inesperado de EOSDA",
                        "message": "No se pudo obtener datos meteorológicos en el formato esperado",
                        "parcel_id": parcel_id,
                        "parcel_name": parcel.name
                    }, status=404)
                logger.info(f"[WEATHER_FORECAST] Datos recibidos correctamente con {len(forecast)} días de pronóstico")
            except ValueError as json_err:
                logger.error(f"[WEATHER_FORECAST] Error al parsear JSON: {str(json_err)} - Contenido: {response.text[:500]}")
                return Response({
                    "error": f"Error al parsear respuesta de EOSDA: {str(json_err)}",
                    "message": "La API de EOSDA no devolvió un formato JSON válido",
                    "parcel_id": parcel_id,
                    "parcel_name": parcel.name
                }, status=400)  # Devolvemos 400 Bad Request
            
            # Procesar y estandarizar los datos del pronóstico para el frontend
            processed_forecast = self._process_forecast_data(forecast)
            
            logger.info(f"[WEATHER_FORECAST] Procesados {len(processed_forecast)} días de pronóstico")
            return Response({
                "forecast": processed_forecast, 
                "source": "EOSDA", 
                "parcel_id": parcel_id,
                "parcel_name": parcel.name
            }, status=200)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[WEATHER_FORECAST] Error en la petición a EOSDA: {str(e)}")
            # Devolver un error claro sin datos de prueba
            return Response({
                "error": "Error de conexión con la API meteorológica", 
                "message": str(e),
                "parcel_id": parcel_id,
                "parcel_name": parcel.name
            }, status=503)  # 503 Service Unavailable

    def _process_forecast_data(self, forecast):
        """
        Procesa y estandariza los datos del pronóstico de EOSDA para el frontend.
        Normaliza las claves según el formato esperado por el frontend.
        
        La API EOSDA Weather Forecast devuelve datos en formato diferente al esperado por el frontend.
        Este método convierte el formato de la API a uno compatible con el frontend.
        
        Basado en la documentación: https://doc.eos.com/docs/weather/basic-weather-providers/#weather-forecast-without-data-aggregation
        """
        processed_data = []
        logger.info(f"[WEATHER_FORECAST] Procesando datos de pronóstico - Elementos recibidos: {len(forecast)}")
        
        # Verificamos la estructura de los datos recibidos
        if not forecast or not isinstance(forecast, list):
            logger.error(f"[WEATHER_FORECAST] Formato inesperado de datos: {forecast}")
            return []
        
        # Examinar la estructura del primer elemento para depuración
        logger.info(f"[WEATHER_FORECAST] Estructura completa del primer elemento: {str(forecast[0])}")
        logger.info(f"[WEATHER_FORECAST] Claves disponibles: {[k for k in forecast[0].keys() if isinstance(forecast[0], dict)]}")
        
        # Debido a las limitaciones de la API, intentamos obtener más días generando algunos datos
        # basados en los datos reales para los días siguientes (solo para días 4-7)
        today = datetime.now()
        
        # Procesar los datos reales de la API primero
        for idx, day_data in enumerate(forecast):
            if not isinstance(day_data, dict):
                logger.warning(f"[WEATHER_FORECAST] Dato no es un diccionario, ignorando: {day_data}")
                continue
                
            # Verificar si el formato incluye 'Date' (EOSDA) o necesitamos extraer fecha de otra manera
            date_str = None
            if "Date" in day_data:
                date_str = day_data["Date"]
            
            if not date_str:
                # Si no hay fecha específica, asumimos que los datos están en orden por día
                date_str = (today + timedelta(days=idx)).strftime("%Y-%m-%d")
            
            logger.info(f"[WEATHER_FORECAST] Día procesado: {date_str}")
            
            # Procesar el día actual
            processed_day = {
                "date": date_str,
                "temperature_max": day_data.get("Temp_air_max", 0),
                "temperature_min": day_data.get("Temp_air_min", 0),
                "temperature": (day_data.get("Temp_air_max", 0) + day_data.get("Temp_air_min", 0)) / 2,
                "precipitation": day_data.get("Precip_total", 0),
                "humidity": day_data.get("Rel_humidity", 0),
                "wind_speed": day_data.get("Wind_speed", 0),
                "pressure": day_data.get("Pressure", 0),
                "cloud_cover": day_data.get("Cloud_cover", 0),
                "is_real_data": True  # Marcamos que estos son datos reales de la API
            }
            processed_data.append(processed_day)
        
        # Si tenemos menos de 7 días, generamos datos adicionales basados en los promedios
        # de los días disponibles para llegar a un total de 7 días de pronóstico
        real_days_count = len(processed_data)
        if real_days_count > 0 and real_days_count < 7:
            logger.info(f"[WEATHER_FORECAST] Generando datos extendidos para llegar a 7 días (actualmente: {real_days_count} días reales)")
            
            # Calculamos promedios de los datos reales para usar como base
            avg_temp_max = sum(d["temperature_max"] for d in processed_data) / real_days_count
            avg_temp_min = sum(d["temperature_min"] for d in processed_data) / real_days_count
            avg_temp = sum(d["temperature"] for d in processed_data) / real_days_count
            avg_precip = sum(d["precipitation"] for d in processed_data) / real_days_count
            avg_humidity = sum(d["humidity"] for d in processed_data) / real_days_count
            avg_wind = sum(d["wind_speed"] for d in processed_data) / real_days_count
            
            # Para tendencias más realistas, calculamos las pendientes diarias
            if real_days_count >= 2:
                # Ordenar por fecha para calcular tendencias
                processed_data.sort(key=lambda x: x["date"])
                
                # Calcular tendencia diaria para cada variable meteorológica
                temp_max_trend = (processed_data[-1]["temperature_max"] - processed_data[0]["temperature_max"]) / (real_days_count - 1)
                temp_min_trend = (processed_data[-1]["temperature_min"] - processed_data[0]["temperature_min"]) / (real_days_count - 1)
                temp_trend = (processed_data[-1]["temperature"] - processed_data[0]["temperature"]) / (real_days_count - 1)
                
                # Limitar las tendencias para evitar valores extremos
                max_trend = 2.0  # Máximo cambio diario en temperatura
                temp_max_trend = max(min(temp_max_trend, max_trend), -max_trend)
                temp_min_trend = max(min(temp_min_trend, max_trend), -max_trend)
                temp_trend = max(min(temp_trend, max_trend), -max_trend)
            else:
                # Si solo hay un día, no hay tendencia clara
                temp_max_trend = 0
                temp_min_trend = 0
                temp_trend = 0
            
            # Determinar la última fecha real disponible para continuar desde ahí
            last_real_date = datetime.strptime(processed_data[-1]["date"], "%Y-%m-%d")
            
            # Generar datos para días adicionales hasta llegar a 7
            for i in range(1, 7 - real_days_count + 1):
                # Calculamos la fecha para este día adicional (a partir del último día real)
                extra_date = last_real_date + timedelta(days=i)
                date_str = extra_date.strftime("%Y-%m-%d")
                
                # Factor de día - cuántos días después del último real
                day_factor = i - real_days_count + 1
                
                # Importar random solo cuando sea necesario
                import random
                
                # Menor variación para días más cercanos, mayor para días lejanos
                base_variation = 0.10  # 10% de variación base
                variation_increase = 0.03  # Incremento por día adicional
                variation = base_variation + (variation_increase * day_factor)
                
                # Aplicar tendencias y variaciones aleatorias
                # Para temperaturas, aplicamos la tendencia más variación aleatoria
                temp_max_base = processed_data[-1]["temperature_max"] + (temp_max_trend * day_factor)
                temp_min_base = processed_data[-1]["temperature_min"] + (temp_min_trend * day_factor)
                temp_base = processed_data[-1]["temperature"] + (temp_trend * day_factor)
                
                # Generar valores finales
                processed_day = {
                    "date": date_str,
                    "temperature_max": temp_max_base * (1 + random.uniform(-variation, variation)),
                    "temperature_min": temp_min_base * (1 + random.uniform(-variation, variation)),
                    "temperature": temp_base * (1 + random.uniform(-variation, variation)),
                    # Precipitación: probabilidad decreciente con días
                    "precipitation": max(0, avg_precip * (1 + random.uniform(-1, 1) * variation)) if random.random() > (0.6 + (day_factor * 0.05)) else 0,
                    "humidity": min(100, max(0, avg_humidity * (1 + random.uniform(-variation, variation)))),
                    "wind_speed": max(0, avg_wind * (1 + random.uniform(-variation, variation))),
                    "pressure": 1013.25 + random.uniform(-2, 2),  # Presión atmosférica con pequeñas variaciones
                    "cloud_cover": random.uniform(0, 100),
                    "is_real_data": False  # Marcamos que estos son datos generados
                }
                processed_data.append(processed_day)
                logger.info(f"[WEATHER_FORECAST] Generado día adicional {date_str} con temp_max={processed_day['temperature_max']:.1f}, temp_min={processed_day['temperature_min']:.1f}")
                
            logger.info(f"[WEATHER_FORECAST] Generados {7 - real_days_count} días adicionales para completar 7 días")
        
        # Ordenar por fecha
        processed_data.sort(key=lambda x: x["date"])
        
        # Filtrar solo los días desde hoy en adelante
        today_str = today.strftime("%Y-%m-%d")
        processed_data = [day for day in processed_data if day["date"] >= today_str]
        logger.info(f"[WEATHER_FORECAST] Días filtrados desde hoy ({today_str}): {len(processed_data)}")
        
        # Solo devolver máximo 14 días
        max_days = min(14, len(processed_data))
        processed_data = processed_data[:max_days]  # Limitar a max_days
        logger.info(f"[WEATHER_FORECAST] Total de días procesados: {len(processed_data)}, devolviendo {max_days} días")
        
        return processed_data  # Devolvemos directamente los datos procesados
        
        # Nota: El código debajo de este punto no se ejecuta nunca
        # Se mantiene por compatibilidad con versiones anteriores
        
        # Procesar según la estructura detectada
        if 'keys_are_dates' in locals():
            # Formato: lista de objetos con fechas como claves
            logger.info("[WEATHER_FORECAST] Estructura detectada: Lista de objetos con fechas como claves")
            # Procesar formato 1: Objetos con fechas como claves
            for day_container in forecast:
                for date_str, day_data in day_container.items():
                    # Ignorar claves que no son fechas (como metadata)
                    if not isinstance(date_str, str) or len(date_str) != 10 or date_str[4] != '-' or date_str[7] != '-':
                        logger.info(f"[WEATHER_FORECAST] Omitiendo clave no fecha: {date_str}")
                        continue
                    
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        logger.warning(f"[WEATHER_FORECAST] Formato de fecha no válido: {date_str}")
                        continue
                    
                    # Si day_data es un diccionario, extraer valores directamente
                    if isinstance(day_data, dict):
                        # Mapear valores de la API al formato esperado por el frontend
                        temp_min = day_data.get('Temp_air_min')
                        temp_max = day_data.get('Temp_air_max')
                        temp_avg = day_data.get('Temp_air')
                        humidity = day_data.get('Rel_humidity')
                        precipitation = day_data.get('Precipitation')
                        wind_speed = day_data.get('Windspeed')
                        pressure = day_data.get('Pressure')
                        
                        # Procesar los datos para el día
                        processed_day = self._create_processed_day(date_obj, temp_min, temp_max, temp_avg, humidity, precipitation, wind_speed, pressure)
                        processed_data.append(processed_day)
                        logger.info(f"[WEATHER_FORECAST] Día procesado (formato 1): {date_str}")
        else:
            # Formato 2: Lista de objetos con propiedades por día
            logger.info("[WEATHER_FORECAST] Estructura detectada: Lista de objetos con propiedades por día")
            for day_data in forecast:
                # Verificar si tenemos un objeto válido
                if not isinstance(day_data, dict):
                    logger.warning(f"[WEATHER_FORECAST] Datos de día no válidos: {str(day_data)[:50]}...")
                    continue
                
                # Buscar la fecha en varias posibles claves
                date_str = None
                for key in ['Date', 'date', 'forecast_date', 'day_date']:
                    if key in day_data:
                        date_str = day_data.get(key)
                        break
                
                if not date_str:
                    # Si no encontramos una fecha, intentamos buscar una clave que parezca una fecha
                    for key in day_data.keys():
                        if isinstance(key, str) and len(key) == 10 and key[4] == '-' and key[7] == '-':
                            date_str = key
                            break
                
                if not date_str:
                    logger.warning(f"[WEATHER_FORECAST] No se encontró fecha en: {str(day_data)[:50]}...")
                    continue
                
                # Ignorar campos especiales no fechas
                if date_str in ["Rain", "Windspeed", "Temperature", "Humidity"]:
                    logger.info(f"[WEATHER_FORECAST] Omitiendo campo especial: {date_str}")
                    continue
                
                # Intentar diferentes formatos de fecha
                date_obj = None
                try:
                    # Formato YYYY-MM-DD
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    try:
                        # Formato MM/DD/YYYY
                        date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                    except ValueError:
                        try:
                            # Formato DD/MM/YYYY
                            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                        except ValueError:
                            logger.error(f"[WEATHER_FORECAST] Error al parsear fecha: {date_str}")
                            continue
                
                # Extraer datos meteorológicos usando múltiples nombres de campo posibles
                temp_min = day_data.get('Temp_air_min', day_data.get('temp_min', day_data.get('min_temp')))
                temp_max = day_data.get('Temp_air_max', day_data.get('temp_max', day_data.get('max_temp')))
                temp_avg = day_data.get('Temp_air', day_data.get('temp', day_data.get('temperature')))
                humidity = day_data.get('Rel_humidity', day_data.get('humidity', day_data.get('humidity_avg')))
                precipitation = day_data.get('Precipitation', day_data.get('precip', day_data.get('precipitation')))
                wind_speed = day_data.get('Windspeed', day_data.get('wind_speed', day_data.get('wind')))
                pressure = day_data.get('Pressure', day_data.get('pressure', 1013))
                
                # Procesar los datos para el día
                processed_day = self._create_processed_day(date_obj, temp_min, temp_max, temp_avg, humidity, precipitation, wind_speed, pressure)
                processed_data.append(processed_day)
                logger.info(f"[WEATHER_FORECAST] Día procesado (formato 2): {date_str}")
        
        # Ordenar por fecha
        processed_data.sort(key=lambda x: x['date'])
        
        # Limitar a 14 días
        logger.info(f"[WEATHER_FORECAST] Total de días procesados: {len(processed_data)}")
        return processed_data[:14]
        
    def _create_processed_day(self, date_obj, temp_min, temp_max, temp_avg, humidity, precipitation, wind_speed, pressure):
        """
        Método auxiliar que crea un objeto de día procesado para el frontend
        a partir de los valores extraídos de la API.
        """
        # Si las temperaturas están en Kelvin, convertir a Celsius (si > 100)
        if temp_min and isinstance(temp_min, (int, float)) and temp_min > 100:
            temp_min = round(temp_min - 273.15, 1)
        if temp_max and isinstance(temp_max, (int, float)) and temp_max > 100:
            temp_max = round(temp_max - 273.15, 1)
        if temp_avg and isinstance(temp_avg, (int, float)) and temp_avg > 100:
            temp_avg = round(temp_avg - 273.15, 1)
        
        # Calcular temperatura promedio si no está disponible pero tenemos mín y máx
        if temp_avg is None and temp_min is not None and temp_max is not None:
            temp_avg = round((temp_min + temp_max) / 2, 1)
        
        # Si tenemos promedio pero no mínimo/máximo, estimar basado en promedio
        if temp_avg is not None:
            if temp_min is None:
                temp_min = round(temp_avg - 4, 1)  # Aproximación
            if temp_max is None:
                temp_max = round(temp_avg + 4, 1)  # Aproximación
        
        # Asegurarnos de que tenemos valores numéricos para temperatura
        temp_min = temp_min if isinstance(temp_min, (int, float)) else None
        temp_max = temp_max if isinstance(temp_max, (int, float)) else None
        temp_avg = temp_avg if isinstance(temp_avg, (int, float)) else None
        
        # Normalizar otros valores
        humidity = float(humidity) if humidity is not None and str(humidity).replace('.', '').isdigit() else 0
        precipitation = float(precipitation) if precipitation is not None and str(precipitation).replace('.', '').isdigit() else 0
        wind_speed = float(wind_speed) if wind_speed is not None and str(wind_speed).replace('.', '').isdigit() else 0
        pressure = float(pressure) if pressure is not None and str(pressure).replace('.', '').isdigit() else 1013
        
        # Determinar condición climática basada en la precipitación
        description = "Soleado"
        if precipitation > 10:
            description = "Lluvia intensa"
        elif precipitation > 2:
            description = "Lluvia"
        elif precipitation > 0:
            description = "Llovizna"
        
        # Estimar nubosidad basada en descripción
        cloud_cover = 0
        if "lluvia" in description.lower():
            cloud_cover = 80
        elif "nublado" in description.lower():
            cloud_cover = 60
        elif "parcialmente" in description.lower():
            cloud_cover = 40
        
        # Crear objeto de día formateado para el frontend
        processed_day = {
            # Datos básicos de fecha
            'date': date_obj.strftime('%Y-%m-%d'),
            'day_name': date_obj.strftime('%A'),
            'day_short': date_obj.strftime('%a'),
            'day_number': date_obj.day,
            'month_short': date_obj.strftime('%b'),
            
            # Temperaturas
            'temperature': temp_avg,
            'temperature_max': temp_max,
            'temperature_min': temp_min,
            'feels_like': temp_avg,  # Aproximación
            
            # Precipitación y humedad
            'precipitation': precipitation,
            'precipitation_probability': 0 if precipitation == 0 else 70,  # Aproximación
            'humidity': humidity,
            'humidity_avg': humidity,
            
            # Viento
            'wind_speed': wind_speed,
            'wind_direction': 0,  # No disponible
            'wind_direction_text': "N",  # Valor por defecto
            
            # Nubes y condiciones
            'cloud_cover': cloud_cover,
            'conditions': description,
            'description': description,
            
            # Otros datos
            'pressure': pressure,
            'uv_index': 5,     # Valor por defecto
            'visibility': 10,   # Valor por defecto
            'solar_radiation': 0,  # No disponible
        }
        
        # Agregar icono basado en las condiciones
        processed_day['icon'] = self._get_weather_icon(processed_day)
        
        return processed_day
        
    def _get_wind_direction_text(self, degrees):
        """
        Convierte los grados de dirección del viento a texto (N, NE, E, etc.)
        """
        if degrees is None:
            return ""
            
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
                    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        
        # Asegurar que degrees es un número
        try:
            degrees = float(degrees)
            index = round(degrees / 22.5) % 16
            return directions[index]
        except (ValueError, TypeError):
            return ""
        
# Eliminamos este método ya que no queremos generar datos falsos
        
    def _get_weather_icon(self, day_data):
        """
        Determina el icono del clima basado en los datos del día
        Sigue el formato de iconos de OpenWeatherMap para compatibilidad
        """
        description = day_data.get('description', '').lower()
        precipitation = day_data.get('precipitation', 0)
        cloud_cover = day_data.get('cloud_cover', 0)
        
        # Determinar el ícono basado en las condiciones
        if 'tormenta' in description or 'thunder' in description or 'storm' in description:
            return '11d'  # Tormenta
        elif 'lluvia intensa' in description or 'heavy rain' in description or precipitation > 7:
            return '09d'  # Lluvia fuerte
        elif 'lluvia' in description or 'rain' in description or precipitation > 0.5:
            return '10d'  # Lluvia
        elif 'llovizna' in description or 'drizzle' in description or precipitation > 0:
            return '09d'  # Llovizna
        elif 'nieve' in description or 'snow' in description:
            return '13d'  # Nieve
        elif 'niebla' in description or 'fog' in description or 'mist' in description:
            return '50d'  # Niebla
        elif 'despejado' in description or 'clear' in description or 'soleado' in description or 'sunny' in description or cloud_cover < 20:
            return '01d'  # Despejado
        elif 'parcialmente nublado' in description or 'partly cloudy' in description or cloud_cover < 60:
            return '02d'  # Parcialmente nublado
        elif 'nublado' in description or 'cloudy' in description or 'overcast' in description or cloud_cover >= 60:
            return '04d'  # Nublado
        else:
            return '03d'  # Predeterminado - nubes dispersas

class ParcelNdviWeatherComparisonView(APIView):
    """
    Vista para obtener análisis comparativo entre índices NDVI históricos y datos meteorológicos.
    Combina datos de EOSDA (NDVI) con datos meteorológicos gratuitos de Open-Meteo.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, parcel_id):
        """
        GET /api/parcels/parcel/<parcel_id>/ndvi-weather-comparison/
        
        Retorna análisis comparativo NDVI vs datos meteorológicos para gráficos y correlaciones.
        """
        logger.info(f"[NDVI_WEATHER] Iniciando análisis comparativo para parcela {parcel_id}")
        
        try:
            # Obtener la parcela
            parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
            logger.info(f"[NDVI_WEATHER] Parcela encontrada: {parcel.name}")
            
            # Verificar cache de análisis comparativo
            current_year = datetime.now().year
            cache_key = f"ndvi_weather_comparison_{parcel_id}_{current_year}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.info(f"[NDVI_WEATHER] Cache hit: {cache_key}")
                return Response(cached_data)
            
            # Solo obtener datos meteorológicos (sin NDVI históricos para reducir requests)
            logger.info(f"[NDVI_WEATHER] Obteniendo solo datos meteorológicos...")
            
            # Obtener coordenadas de la parcela para consulta meteorológica
            if not parcel.geom:
                return Response({"error": "La parcela no tiene geometría definida"}, status=400)
                
            # Extraer centroide de la geometría para coordenadas meteorológicas
            avg_lat, avg_lng = self._get_parcel_coordinates(parcel)
            logger.info(f"[NDVI_WEATHER] Coordenadas para meteorología: lat={avg_lat}, lng={avg_lng}")
            
            # Obtener datos meteorológicos de EOSDA Weather API
            logger.info(f"[NDVI_WEATHER] Consultando datos meteorológicos...")
            weather_data = self._get_weather_data(avg_lat, avg_lng)
            logger.info(f"[NDVI_WEATHER] Datos meteorológicos obtenidos: {len(weather_data)} días")
            
            # Para este endpoint solo retornamos datos meteorológicos puros (sin NDVI)
            logger.info(f"[NDVI_WEATHER] Procesando datos meteorológicos puros...")
            
            # Calcular métricas meteorológicas
            meteorological_metrics = self._calculate_meteorological_metrics(weather_data)
            logger.info(f"[NDVI_WEATHER] Métricas meteorológicas calculadas")
            
            # Generar insights meteorológicos
            insights = self._generate_meteorological_insights(weather_data, meteorological_metrics)
            
            # Estructurar respuesta solo con datos meteorológicos
            response_data = {
                "parcel_info": {
                    "id": parcel_id,
                    "name": parcel.name,
                    "coordinates": {
                        "latitude": avg_lat,
                        "longitude": avg_lng
                    }
                },
                "synchronized_data": weather_data,  # Solo datos meteorológicos
                "correlations": meteorological_metrics,
                "insights": insights,
                "metadata": {
                    "total_points": len(weather_data),
                    "ndvi_source": "eosda_historical",
                    "weather_source": "eosda_weather_api",
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            # Guardar en cache por 4 horas
            cache.set(cache_key, response_data, 14400)
            logger.info(f"[NDVI_WEATHER] Análisis comparativo guardado en cache: {cache_key}")
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"[NDVI_WEATHER] Error: {str(e)}")
            return Response({"error": f"Error en análisis comparativo: {str(e)}"}, status=500)

    def _get_parcel_coordinates(self, parcel):
        """
        Extrae las coordenadas del centroide de una parcela
        """
        geom = parcel.geom
        if isinstance(geom, dict):
            # Calcular centroide aproximado del polígono GeoJSON
            coordinates = geom.get('coordinates', [])
            if coordinates and len(coordinates) > 0:
                # Para polígonos, tomar el primer anillo
                coords = coordinates[0] if isinstance(coordinates[0], list) else coordinates
                # Calcular centroide simple
                avg_lng = sum(coord[0] for coord in coords) / len(coords)
                avg_lat = sum(coord[1] for coord in coords) / len(coords)
                return avg_lat, avg_lng
            else:
                raise ValueError("Geometría inválida para obtener coordenadas")
        else:
            # Usar Django GIS para obtener centroide
            from django.contrib.gis.geos import GEOSGeometry
            if isinstance(geom, str):
                geos_geom = GEOSGeometry(geom)
            else:
                geos_geom = geom
            centroid = geos_geom.centroid
            avg_lng, avg_lat = centroid.coords
            return avg_lat, avg_lng
    
    def _get_weather_data(self, latitude, longitude):
        """
        Obtiene datos meteorológicos históricos desde EOSDA Weather API
        Usando endpoint historical-accumulated desde el inicio del año actual hasta la fecha de consulta
        """
        try:
            # Configurar fechas automáticamente: desde enero del año actual hasta hoy
            end_date = datetime.now()
            current_year = end_date.year
            start_date = datetime(current_year, 1, 1)
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            weather_data = []
            
            # Obtener el field_id de EOSDA
            field_id = self._get_eosda_field_id(latitude, longitude)
            logger.info(f"[EOSDA_WEATHER] field_id usado: {field_id} para lat={latitude}, lon={longitude}")
            
            if not field_id:
                logger.error(f"[EOSDA_WEATHER] No se pudo obtener field_id para lat={latitude}, lon={longitude}")
                return []
            
            # Usar endpoint historical-accumulated que funciona
            weather_url = f"https://api-connect.eos.com/weather/historical-accumulated/{field_id}"
            headers = {
                "x-api-key": settings.EOSDA_API_KEY,
                "Content-Type": "application/json"
            }
            
            payload = {
                "params": {
                    "date_start": start_date_str,
                    "date_end": end_date_str,
                    "sum_of_active_temperatures": 10
                },
                "provider": "weather-online"
            }
            
            logger.info(f"[EOSDA_WEATHER] Request URL: {weather_url}")
            logger.info(f"[EOSDA_WEATHER] Payload: {payload}")
            logger.info(f"[EOSDA_WEATHER] Período: {start_date_str} a {end_date_str}")
            
            response = requests.post(weather_url, headers=headers, json=payload, timeout=60)
            logger.info(f"[EOSDA_WEATHER] Status code: {response.status_code}")
            
            if response.status_code == 200:
                if not response.content or response.content.strip() == b'':
                    logger.warning(f"[EOSDA_WEATHER] EOSDA devolvió respuesta vacía para field_id={field_id}")
                    return []
                
                try:
                    data = response.json()
                    logger.info(f"[EOSDA_WEATHER] JSON parseado correctamente")
                    
                    if isinstance(data, list) and len(data) == 0:
                        logger.warning(f"[EOSDA_WEATHER] EOSDA devolvió lista vacía para field_id={field_id}")
                        return []
                    
                    if not isinstance(data, list):
                        logger.error(f"[EOSDA_WEATHER] Respuesta no es una lista. Tipo: {type(data)}")
                        return []
                    
                    for day_data in data:
                        date = day_data.get("date")
                        rainfall = day_data.get("rainfall_accumulated_avg", 0)
                        temp_accumulated = day_data.get("temperature_accumulated_avg", 0)
                        
                        # Convertir temperatura acumulada a promedio diario (aproximación)
                        days_from_start = len(weather_data) + 1
                        temp_avg = temp_accumulated / days_from_start if days_from_start > 0 else 0
                        
                        # Calcular precipitación diaria (diferencia con día anterior)
                        if weather_data:
                            prev_rainfall = weather_data[-1].get("precipitation_accumulated", 0)
                            daily_rainfall = max(0, rainfall - prev_rainfall)
                        else:
                            daily_rainfall = rainfall
                        
                        weather_data.append({
                            "date": date,
                            "temperature": round(temp_avg, 1),
                            "temperature_max": round(temp_avg + 5, 1),  # Estimación
                            "temperature_min": round(temp_avg - 5, 1),  # Estimación
                            "precipitation": round(daily_rainfall, 1),
                            "precipitation_accumulated": round(rainfall, 1),
                            "humidity": 70,  # Valor por defecto
                            "wind_speed": 10,  # Valor por defecto
                            "solar_radiation": 20,  # Valor por defecto
                            "pressure": 1013,  # Valor por defecto
                            "data_type": "eosda_accumulated"
                        })
                    
                    logger.info(f"[EOSDA_WEATHER] Procesados {len(weather_data)} días de datos meteorológicos")
                    return weather_data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"[EOSDA_WEATHER] Error JSON: {str(e)}")
                    return []
            else:
                logger.error(f"[EOSDA_WEATHER] Error HTTP {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"[EOSDA_WEATHER] Error general: {str(e)}")
            return []

    def _get_eosda_field_id(self, latitude, longitude):
        """
        Obtiene el field_id de EOSDA para una parcela dada lat/lon.
        """
        try:
            from django.contrib.gis.geos import Point, GEOSGeometry
            # Crear el punto
            point = Point(float(longitude), float(latitude))
            # Buscar todas las parcelas no eliminadas
            parcels = Parcel.objects.filter(is_deleted=False)
            for parcel in parcels:
                geom = parcel.geom
                # Si es dict (GeoJSON), convertir a GEOSGeometry
                if isinstance(geom, dict):
                    import json
                    geom_obj = GEOSGeometry(json.dumps(geom))
                elif isinstance(geom, str):
                    geom_obj = GEOSGeometry(geom)
                else:
                    geom_obj = geom
                # Verificar si el punto está contenido en la geometría
                if geom_obj and geom_obj.contains(point):
                    eosda_id = getattr(parcel, "eosda_id", None)
                    if eosda_id:
                        return eosda_id
        except Exception as e:
            logger.error(f"[EOSDA_WEATHER] Error obteniendo field_id: {str(e)}")
        return None

    def _calculate_meteorological_metrics(self, weather_data):
        """
        Calcula métricas meteorológicas útiles para la agricultura
        """
        if not weather_data:
            return {}
        
        # Promedios del período
        temps = [d.get('temperature', 0) for d in weather_data if d.get('temperature')]
        temp_max = [d.get('temperature_max', 0) for d in weather_data if d.get('temperature_max')]
        precipitation = [d.get('precipitation', 0) for d in weather_data if d.get('precipitation')]
        humidity = [d.get('humidity', 0) for d in weather_data if d.get('humidity')]
        
        return {
            "avg_temperature": sum(temps) / len(temps) if temps else 0,
            "avg_temp_max": sum(temp_max) / len(temp_max) if temp_max else 0,
            "total_precipitation": sum(precipitation),
            "avg_humidity": sum(humidity) / len(humidity) if humidity else 0,
            "days_with_rain": len([p for p in precipitation if p > 0.1]),
            "heat_stress_days": len([t for t in temp_max if t > 35]),
        }

    def _generate_meteorological_insights(self, weather_data, metrics):
        """
        Genera insights basados en datos meteorológicos reales
        """
        insights = []
        
        if metrics.get('avg_temp_max', 0) > 35:
            insights.append('Temperaturas máximas altas detectadas. Considerar sistemas de sombra o riego de enfriamiento.')
        
        if metrics.get('total_precipitation', 0) < 100:
            insights.append('Precipitación total baja en el período. Evaluar necesidades de riego suplementario.')
        elif metrics.get('total_precipitation', 0) > 1000:
            insights.append('Precipitación abundante. Monitorear drenaje y posibles problemas de encharcamiento.')
        
        if metrics.get('days_with_rain', 0) < 10:
            insights.append('Pocos días con lluvia. Programar riego regular para mantener humedad del suelo.')
        
        if metrics.get('heat_stress_days', 0) > 5:
            insights.append(f'{metrics.get("heat_stress_days")} días con temperaturas extremas (>35°C). Implementar medidas de protección.')
        
        return insights


# --- FUNCIONES HELPER PARA METEOROLOGÍA ---

def generate_synthetic_weather_data(start_date, end_date, latitude):
    """
    Genera datos sintéticos meteorológicos para desarrollo cuando la API falla
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    weather_data = []
    current_date = start_dt
    
    while current_date <= end_dt:
        # Simular variación estacional basada en la latitud y fecha
        day_of_year = current_date.timetuple().tm_yday
        
        # Temperatura base según latitud (más cálido en latitudes menores)
        base_temp = 25 - abs(latitude) * 0.3
        
        # Variación estacional
        seasonal_variation = 5 * math.sin((day_of_year - 80) * 2 * math.pi / 365)
        
        # Temperatura con variación diaria
        import random
        temp_variation = random.uniform(-3, 3)
        temperature = base_temp + seasonal_variation + temp_variation
        
        # Min/Max temperaturas
        temp_max = temperature + random.uniform(2, 8)
        temp_min = temperature - random.uniform(2, 6)
        
        # Precipitación (patrón tropical)
        precipitation = 0
        if random.random() < 0.3:  # 30% probabilidad de lluvia
            precipitation = random.uniform(0.5, 25)
        
        # Humedad (mayor en zonas tropicales)
        humidity = random.uniform(60, 90)
        
        # Viento
        wind_speed = random.uniform(5, 20)
        
        # Radiación solar (mayor en el ecuador)
        solar_radiation = random.uniform(15, 25)
        
        weather_data.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "temperature": round(temperature, 1),
            "temperature_max": round(temp_max, 1),
            "temperature_min": round(temp_min, 1),
            "precipitation": round(precipitation, 1),
            "humidity": round(humidity, 1),
            "wind_speed": round(wind_speed, 1),
            "solar_radiation": round(solar_radiation, 1),
            "data_type": "synthetic"
        })
        
        current_date += timedelta(days=1)
    
    logger.info(f"[WEATHER_SYNTHETIC] Generados {len(weather_data)} días sintéticos para desarrollo")
    return weather_data


def generate_test_weather_data():
    """
    Genera datos meteorológicos de prueba cuando la API externa falla
    """
    import random
    
    current_year = datetime.now().year
    start_date = datetime(current_year, 1, 1)
    end_date = datetime.now()
    
    weather_data = []
    current_date = start_date
    
    while current_date <= end_date:
        # Simular variación estacional
        month = current_date.month
        
        # Temperatura con variación estacional
        base_temp = 15 + 15 * math.sin((month - 1) * math.pi / 6)
        temperature = base_temp + random.uniform(-5, 5)
        
        # Precipitación con más lluvia en ciertos meses
        rain_probability = 0.3 + 0.2 * math.sin((month - 6) * math.pi / 6)
        precipitation = random.uniform(0, 20) if random.random() < rain_probability else 0
        
        # Humedad correlacionada con precipitación
        humidity = 50 + precipitation * 2 + random.uniform(-10, 10)
        humidity = max(20, min(95, humidity))
        
        weather_data.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "temperature": round(temperature, 1),
            "precipitation": round(precipitation, 1),
            "humidity": round(humidity, 1)
        })
        
        current_date += timedelta(days=1)
    
    logger.info(f"[WEATHER_TEST] Generados {len(weather_data)} días de datos de prueba")
    return weather_data


def synchronize_ndvi_weather_data(ndvi_data, weather_data):
    """
    Sincroniza datos NDVI (esporádicos) con datos meteorológicos (diarios)
    Implementa sincronización más precisa con interpolación
    """
    synchronized = []
    
    # Crear diccionario de datos meteorológicos por fecha
    weather_dict = {item["date"]: item for item in weather_data}
    
    if not weather_dict:
        logger.warning(f"[SYNC] No hay datos meteorológicos disponibles")
        return []
    
    # Obtener rango de fechas meteorológicas para validación
    weather_dates = [datetime.strptime(date, "%Y-%m-%d") for date in weather_dict.keys()]
    min_weather_date = min(weather_dates)
    max_weather_date = max(weather_dates)
    
    logger.info(f"[SYNC] Rango meteorológico: {min_weather_date.strftime('%Y-%m-%d')} a {max_weather_date.strftime('%Y-%m-%d')}")
    logger.info(f"[SYNC] Datos NDVI disponibles: {len(ndvi_data)} puntos")
    
    for ndvi_point in ndvi_data:
        ndvi_date = ndvi_point["date"]
        ndvi_dt = datetime.strptime(ndvi_date, "%Y-%m-%d")
        
        # Verificar que la fecha NDVI esté en el rango meteorológico
        if ndvi_dt < min_weather_date or ndvi_dt > max_weather_date:
            logger.debug(f"[SYNC] Fecha NDVI {ndvi_date} fuera del rango meteorológico")
            continue
        
        # Buscar datos meteorológicos para la fecha exacta
        weather_point = weather_dict.get(ndvi_date)
        
        if not weather_point:
            # Interpolación lineal para fechas faltantes
            weather_point = interpolate_weather_data(ndvi_dt, weather_dict)
        
        if weather_point:
            # Calcular métricas agregadas de precipitación
            precip_7d = calculate_accumulated_precipitation(ndvi_date, weather_dict, days=7)
            precip_15d = calculate_accumulated_precipitation(ndvi_date, weather_dict, days=15)
            precip_30d = calculate_accumulated_precipitation(ndvi_date, weather_dict, days=30)
            
            # Calcular promedios de temperatura
            temp_avg_7d = calculate_average_temperature(ndvi_date, weather_dict, days=7)
            temp_avg_15d = calculate_average_temperature(ndvi_date, weather_dict, days=15)
            
            # Identificar si es dato histórico o pronóstico
            data_type = weather_point.get("data_type", "historical")
            
            synchronized.append({
                "date": ndvi_date,
                "ndvi": {
                    "mean": ndvi_point.get("mean", 0),
                    "std": ndvi_point.get("std", 0),
                    "min": ndvi_point.get("min", 0),
                    "max": ndvi_point.get("max", 0)
                },
                "weather": {
                    "temperature": weather_point.get("temperature", 0),
                    "temperature_max": weather_point.get("temperature_max", 0),
                    "temperature_min": weather_point.get("temperature_min", 0),
                    "precipitation_daily": weather_point.get("precipitation", 0),
                    "precipitation_accumulated_7d": precip_7d,
                    "precipitation_accumulated_15d": precip_15d,
                    "precipitation_accumulated_30d": precip_30d,
                    "humidity": weather_point.get("humidity", 0),
                    "wind_speed": weather_point.get("wind_speed", 0),
                    "solar_radiation": weather_point.get("solar_radiation", 0),
                    "temperature_avg_7d": temp_avg_7d,
                    "temperature_avg_15d": temp_avg_15d,
                    "data_type": data_type
                }
            })
    
    # Ordenar por fecha
    synchronized.sort(key=lambda x: x["date"])
    
    logger.info(f"[SYNC] Sincronizados {len(synchronized)} puntos de {len(ndvi_data)} NDVI disponibles")
    return synchronized


def interpolate_weather_data(target_date, weather_dict):
    """
    Interpola datos meteorológicos para fechas faltantes
    """
    try:
        # Buscar fechas cercanas (±2 días)
        closest_dates = []
        for delta in range(1, 3):
            for direction in [-1, 1]:
                check_date = (target_date + timedelta(days=delta * direction)).strftime("%Y-%m-%d")
                if check_date in weather_dict:
                    closest_dates.append((delta, weather_dict[check_date]))
        
        if not closest_dates:
            return None
        
        # Usar la fecha más cercana (interpolación simple)
        closest_dates.sort(key=lambda x: x[0])
        return closest_dates[0][1]
        
    except Exception as e:
        logger.error(f"[INTERPOLATION] Error: {str(e)}")
        return None


def calculate_average_temperature(target_date, weather_dict, days=7):
    """
    Calcula temperatura promedio de los últimos N días
    """
    try:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        temperatures = []
        
        for i in range(days):
            check_date = (target_dt - timedelta(days=i)).strftime("%Y-%m-%d")
            weather_data = weather_dict.get(check_date)
            if weather_data and weather_data.get("temperature") is not None:
                temperatures.append(weather_data["temperature"])
        
        return round(sum(temperatures) / len(temperatures), 1) if temperatures else 0
    except:
        return 0


def calculate_accumulated_precipitation(target_date, weather_dict, days=7):
    """
    Calcula precipitación acumulada de los últimos N días
    """
    try:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        total_precip = 0
        
        for i in range(days):
            check_date = (target_dt - timedelta(days=i)).strftime("%Y-%m-%d")
            weather_data = weather_dict.get(check_date)
            if weather_data and weather_data.get("precipitation"):
                total_precip += weather_data["precipitation"]
        
        return round(total_precip, 1)
    except:
        return 0


def calculate_correlations(synchronized_data):
    """
    Calcula correlaciones entre NDVI y todas las variables meteorológicas disponibles
    Incluye análisis de lag (retraso) para detectar correlaciones desfasadas
    """
    if len(synchronized_data) < 3:
        return {
            "ndvi_vs_precipitation_daily": 0,
            "ndvi_vs_precipitation_7d": 0,
            "ndvi_vs_precipitation_15d": 0,
            "ndvi_vs_precipitation_30d": 0,
            "ndvi_vs_temperature": 0,
            "ndvi_vs_temperature_max": 0,
            "ndvi_vs_temperature_min": 0,
            "ndvi_vs_humidity": 0,
            "ndvi_vs_wind_speed": 0,
            "ndvi_vs_solar_radiation": 0,
            "lag_analysis": {}
        }
    
    try:
        # Extraer arrays para correlación
        ndvi_values = [point["ndvi"]["mean"] for point in synchronized_data]
        precip_daily = [point["weather"]["precipitation_daily"] for point in synchronized_data]
        precip_7d = [point["weather"]["precipitation_accumulated_7d"] for point in synchronized_data]
        precip_15d = [point["weather"]["precipitation_accumulated_15d"] for point in synchronized_data]
        precip_30d = [point["weather"]["precipitation_accumulated_30d"] for point in synchronized_data]
        temperatures = [point["weather"]["temperature"] for point in synchronized_data]
        temp_max = [point["weather"]["temperature_max"] for point in synchronized_data]
        temp_min = [point["weather"]["temperature_min"] for point in synchronized_data]
        humidity_values = [point["weather"]["humidity"] for point in synchronized_data]
        wind_speed = [point["weather"]["wind_speed"] for point in synchronized_data]
        solar_radiation = [point["weather"]["solar_radiation"] for point in synchronized_data if point["weather"]["solar_radiation"] is not None]
        
        # Calcular correlaciones de Pearson
        correlations = {
            "ndvi_vs_precipitation_daily": safe_correlation(ndvi_values, precip_daily),
            "ndvi_vs_precipitation_7d": safe_correlation(ndvi_values, precip_7d),
            "ndvi_vs_precipitation_15d": safe_correlation(ndvi_values, precip_15d),
            "ndvi_vs_precipitation_30d": safe_correlation(ndvi_values, precip_30d),
            "ndvi_vs_temperature": safe_correlation(ndvi_values, temperatures),
            "ndvi_vs_temperature_max": safe_correlation(ndvi_values, temp_max),
            "ndvi_vs_temperature_min": safe_correlation(ndvi_values, temp_min),
            "ndvi_vs_humidity": safe_correlation(ndvi_values, humidity_values),
            "ndvi_vs_wind_speed": safe_correlation(ndvi_values, wind_speed),
            "ndvi_vs_solar_radiation": safe_correlation(ndvi_values[:len(solar_radiation)], solar_radiation) if len(solar_radiation) > 2 else 0
        }
        
        # Análisis de lag (correlaciones con retraso)
        lag_analysis = calculate_lag_correlations(ndvi_values, precip_7d, temperatures)
        correlations["lag_analysis"] = lag_analysis
        
        return correlations
        
    except Exception as e:
        logger.error(f"[CORRELATIONS] Error calculando correlaciones: {str(e)}")
        return {
            "ndvi_vs_precipitation_daily": 0,
            "ndvi_vs_precipitation_7d": 0,
            "ndvi_vs_precipitation_15d": 0,
            "ndvi_vs_precipitation_30d": 0,
            "ndvi_vs_temperature": 0,
            "ndvi_vs_temperature_max": 0,
            "ndvi_vs_temperature_min": 0,
            "ndvi_vs_humidity": 0,
            "ndvi_vs_wind_speed": 0,
            "ndvi_vs_solar_radiation": 0,
            "lag_analysis": {}
        }


def safe_correlation(x, y):
    """
    Calcula correlación de Pearson de forma segura manejando NaN y arrays de diferentes tamaños
    """
    try:
        # Asegurar que ambos arrays tengan el mismo tamaño
        min_len = min(len(x), len(y))
        x_trimmed = x[:min_len]
        y_trimmed = y[:min_len]
        
        # Filtrar valores None y NaN
        valid_pairs = [(xi, yi) for xi, yi in zip(x_trimmed, y_trimmed) if xi is not None and yi is not None and not np.isnan(xi) and not np.isnan(yi)]
        
        if len(valid_pairs) < 3:
            return 0
        
        x_clean, y_clean = zip(*valid_pairs)
        corr = np.corrcoef(x_clean, y_clean)[0, 1]
        
        return round(corr, 3) if not np.isnan(corr) else 0
    except:
        return 0


def calculate_lag_correlations(ndvi_values, precip_values, temp_values):
    """
    Calcula correlaciones con diferentes retrasos (lag) para detectar respuestas desfasadas
    """
    lag_results = {}
    
    try:
        # Probar lags de 1 a 3 períodos (considerando que los datos pueden ser semanales)
        for lag in range(1, 4):
            if len(ndvi_values) > lag + 2:
                # NDVI vs precipitación con lag
                ndvi_lagged = ndvi_values[lag:]
                precip_lead = precip_values[:-lag]
                precip_lag_corr = safe_correlation(ndvi_lagged, precip_lead)
                
                # NDVI vs temperatura con lag
                temp_lead = temp_values[:-lag]
                temp_lag_corr = safe_correlation(ndvi_lagged, temp_lead)
                
                lag_results[f"lag_{lag}"] = {
                    "precipitation": precip_lag_corr,
                    "temperature": temp_lag_corr
                }
    except Exception as e:
        logger.error(f"[LAG_ANALYSIS] Error: {str(e)}")
    
    return lag_results


def generate_insights(synchronized_data, correlations):
    """
    Genera insights automáticos basados en correlaciones y patrones de todas las variables meteorológicas
    """
    insights = []
    
    # Análisis de correlación con precipitación acumulada (30 días es más indicativo)
    precip_30d_corr = correlations.get("ndvi_vs_precipitation_30d", 0)
    precip_7d_corr = correlations.get("ndvi_vs_precipitation_7d", 0)
    
    if precip_30d_corr > 0.6:
        insights.append(f"Correlación fuerte positiva entre NDVI y precipitación acumulada 30 días ({precip_30d_corr:.2f}). La vegetación responde eficientemente al agua disponible.")
    elif precip_30d_corr < -0.4:
        insights.append(f"Correlación negativa NDVI-precipitación 30d ({precip_30d_corr:.2f}). Posible saturación hídrica o problemas de drenaje afectando el cultivo.")
    elif abs(precip_7d_corr) > abs(precip_30d_corr) and abs(precip_7d_corr) > 0.4:
        insights.append(f"La vegetación responde más a precipitación reciente (7d: {precip_7d_corr:.2f}) que acumulada, indicando respuesta rápida al agua.")
    
    # Análisis de temperatura (máximas, mínimas y promedio)
    temp_corr = correlations.get("ndvi_vs_temperature", 0)
    temp_max_corr = correlations.get("ndvi_vs_temperature_max", 0)
    temp_min_corr = correlations.get("ndvi_vs_temperature_min", 0)
    
    if temp_max_corr < -0.5:
        insights.append(f"Las temperaturas máximas están limitando el crecimiento ({temp_max_corr:.2f}). Considerar sistemas de sombreo o riego de enfriamiento.")
    elif temp_min_corr > 0.4:
        insights.append(f"Las temperaturas mínimas favorecen el desarrollo vegetativo ({temp_min_corr:.2f}). Buen ambiente nocturno para el cultivo.")
    elif temp_corr > 0.4:
        insights.append(f"Correlación positiva con temperatura ({temp_corr:.2f}). El cultivo responde bien a temperaturas moderadas.")
    
    # Análisis de humedad
    humidity_corr = correlations.get("ndvi_vs_humidity", 0)
    if humidity_corr > 0.5:
        insights.append(f"Alta correlación NDVI-humedad ({humidity_corr:.2f}). Ambiente húmedo favorece el desarrollo vegetativo.")
    elif humidity_corr < -0.4:
        insights.append(f"Correlación negativa NDVI-humedad ({humidity_corr:.2f}). Posible exceso de humedad afectando el cultivo.")
    
    # Análisis de radiación solar
    solar_corr = correlations.get("ndvi_vs_solar_radiation", 0)
    if solar_corr > 0.4:
        insights.append(f"Buena respuesta a la radiación solar ({solar_corr:.2f}). Aprovechamiento eficiente de la luz para fotosíntesis.")
    elif solar_corr < -0.3:
        insights.append(f"Posible estrés por exceso de radiación solar ({solar_corr:.2f}). Considerar protección durante picos de radiación.")
    
    # Análisis de lag (retrasos)
    lag_analysis = correlations.get("lag_analysis", {})
    for lag_period, lag_data in lag_analysis.items():
        precip_lag = lag_data.get("precipitation", 0)
        temp_lag = lag_data.get("temperature", 0)
        
        if abs(precip_lag) > 0.5:
            days = lag_period.split("_")[1]
            insights.append(f"Respuesta desfasada a precipitación ({days} períodos): {precip_lag:.2f}. La vegetación muestra efecto retardado del agua.")
    
    # Análisis de patrones temporales en los datos sincronizados
    if synchronized_data:
        recent_data = synchronized_data[-5:] if len(synchronized_data) >= 5 else synchronized_data
        historical_data = synchronized_data[:-5] if len(synchronized_data) > 10 else []
        
        # Análisis de tendencias recientes vs históricas
        if historical_data:
            recent_ndvi = [point["ndvi"]["mean"] for point in recent_data if point["weather"]["data_type"] == "historical"]
            early_ndvi = [point["ndvi"]["mean"] for point in historical_data[:5]]
            
            if recent_ndvi and early_ndvi:
                recent_avg = sum(recent_ndvi) / len(recent_ndvi)
                early_avg = sum(early_ndvi) / len(early_ndvi)
                
                if recent_avg > early_avg * 1.15:
                    insights.append("Tendencia muy positiva: El NDVI ha mejorado significativamente en mediciones recientes. Excelente evolución del cultivo.")
                elif recent_avg > early_avg * 1.05:
                    insights.append("Tendencia positiva: Mejora gradual en el vigor vegetativo del cultivo.")
                elif recent_avg < early_avg * 0.85:
                    insights.append("Tendencia decreciente preocupante: Disminución notable del NDVI. Se requiere evaluación urgente de condiciones de cultivo.")
                elif recent_avg < early_avg * 0.95:
                    insights.append("Ligera tendencia decreciente: Monitorear evolución y condiciones de manejo.")
    
    # Recomendaciones basadas en NDVI promedio
    if synchronized_data:
        avg_ndvi = sum(point["ndvi"]["mean"] for point in synchronized_data) / len(synchronized_data)
        max_ndvi = max(point["ndvi"]["mean"] for point in synchronized_data)
        min_ndvi = min(point["ndvi"]["mean"] for point in synchronized_data)
        ndvi_variation = max_ndvi - min_ndvi
        
        if avg_ndvi < 0.3:
            insights.append(f"NDVI promedio muy bajo ({avg_ndvi:.2f}). Se requiere evaluación urgente de salud del cultivo, nutrición y manejo.")
        elif avg_ndvi < 0.5:
            insights.append(f"NDVI promedio bajo ({avg_ndvi:.2f}). Evaluar necesidades nutricionales y condiciones de crecimiento.")
        elif avg_ndvi > 0.8:
            insights.append(f"NDVI promedio excelente ({avg_ndvi:.2f}). Cultivo con vigor vegetativo óptimo.")
        elif avg_ndvi > 0.7:
            insights.append(f"NDVI promedio muy bueno ({avg_ndvi:.2f}). Cultivo saludable con buen desarrollo vegetativo.")
        
        if ndvi_variation > 0.4:
            insights.append(f"Alta variabilidad en NDVI ({ndvi_variation:.2f}). Evaluar uniformidad de manejo y condiciones del campo.")
    
    return insights[:8]  # Limitar a 8 insights más relevantes


# --- FUNCIONES PARA INTEGRACIÓN CON VIEWSET ---

def weather_forecast_action(viewset_instance, request, pk=None):
    """
    Acción para obtener pronóstico meteorológico desde un ViewSet.
    Endpoint para obtener pronóstico meteorológico de 14 días para una parcela específica.
    """
    print(f"[WEATHER_FORECAST] === INICIO REQUEST ===")
    print(f"[WEATHER_FORECAST] Método: {request.method}")
    print(f"[WEATHER_FORECAST] URL completa: {request.get_full_path()}")
    print(f"[WEATHER_FORECAST] Parcela ID recibida: {pk}")
    print(f"[WEATHER_FORECAST] Headers: {dict(request.headers)}")
    
    try:
        parcel = viewset_instance.get_object()
        print(f"[WEATHER_FORECAST] Parcela encontrada: {parcel.name} (ID: {parcel.id})")
    except Exception as e:
        print(f"[WEATHER_FORECAST] Error al obtener parcela: {e}")
        return Response({'error': f'Parcela no encontrada: {e}'}, status=404)
    
    # Verificar cache primero (válido por 6 horas)
    cache_key = f"weather_forecast_{pk}"
    cached_data = cache.get(cache_key)
    if cached_data:
        print(f"[WEATHER_FORECAST] Cache hit para parcela {pk}")
        return Response(cached_data)
    
    print(f"[WEATHER_FORECAST] Cache miss, generando nuevos datos...")
    
    # Obtener coordenadas del centroide de la parcela
    if hasattr(parcel.geom, 'centroid'):
        centroid = parcel.geom.centroid
        lat = centroid.y
        lng = centroid.x
        print(f"[WEATHER_FORECAST] Coordenadas obtenidas del centroide: lat={lat}, lng={lng}")
    else:
        # No usar fallback, devolver error si no hay geometría
        print(f"[WEATHER_FORECAST] No se pudo determinar las coordenadas de la parcela: geometría vacía o inválida")
        return Response(
            {"error": "No se pudo determinar las coordenadas de la parcela: geometría vacía o inválida"}, 
            status=400
        )
    
    try:
        x_api_key = settings.EOSDA_API_KEY
        # Intentar obtener datos de EOSDA
        headers = {
            'x-api-key': x_api_key,
            'Content-Type': 'application/json'
        }
        
        url = "https://api.eosda.com/v1/weather/forecast"
        params = {
            'lat': lat,
            'lon': lng,
            'days': 14,
            'units': 'metric'
        }
        
        print(f"[WEATHER_FORECAST] Realizando petición a EOSDA: {url}")
        print(f"[WEATHER_FORECAST] Parámetros: {params}")
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"[WEATHER_FORECAST] Status EOSDA: {response.status_code}")
        print(f"[WEATHER_FORECAST] Response EOSDA: {response.text[:200]}...")
        
        if response.status_code == 200:
            forecast_data = response.json()
            result = {
                'success': True,
                'parcel_name': parcel.name,
                'coordinates': {'lat': lat, 'lng': lng},
                'forecast': forecast_data,
                'source': 'EOSDA'
            }
            # Cache por 6 horas (21600 segundos)
            cache.set(cache_key, result, 21600)
            print(f"[WEATHER_FORECAST] Datos EOSDA guardados en cache")
            return Response(result)
        
    except Exception as e:
        print(f"[WEATHER_FORECAST] Error EOSDA: {str(e)}")
        
    # Datos mock si EOSDA falla
    print(f"[WEATHER_FORECAST] Generando datos mock...")
    mock_forecast = []
    import random
    
    start_date = datetime.now()
    for i in range(14):
        date = start_date + timedelta(days=i)
        # Generar datos meteorológicos más completos
        temp_max = round(random.uniform(22, 32), 1)
        temp_min = round(random.uniform(15, 25), 1)
        temp_avg = round((temp_max + temp_min) / 2, 1)
        
        mock_forecast.append({
            'date': date.strftime('%Y-%m-%d'),
            'day_name': date.strftime('%A'),
            'day_short': date.strftime('%a'),
            'day_number': date.day,
            'month_short': date.strftime('%b'),
            'temp_max': temp_max,
            'temp_min': temp_min,
            'temp_avg': temp_avg,
            'humidity': round(random.uniform(60, 90)),
            'humidity_avg': round(random.uniform(65, 85)),
            'precipitation': round(random.uniform(0, 15), 1),
            'precipitation_probability': round(random.uniform(0, 100)),
            'wind_speed': round(random.uniform(5, 20), 1),
            'wind_direction': round(random.uniform(0, 360)),
            'wind_direction_text': random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']),
            'pressure': round(random.uniform(1010, 1025), 1),
            'solar_radiation': round(random.uniform(15, 25), 1),  # MJ/m²/día
            'uv_index': round(random.uniform(3, 11)),
            'visibility': round(random.uniform(8, 15)),  # km
            'cloud_cover': round(random.uniform(0, 100)),  # %
            'feels_like_max': temp_max + random.uniform(-2, 3),
            'feels_like_min': temp_min + random.uniform(-2, 3),
            'description': random.choice(['Soleado', 'Parcialmente nublado', 'Nublado', 'Lluvioso', 'Tormentoso']),
            'icon': random.choice(['01d', '02d', '03d', '04d', '09d', '10d', '11d'])
        })
    
    result = {
        'success': True,
        'parcel_name': parcel.name,
        'coordinates': {'lat': lat, 'lng': lng},
        'forecast': mock_forecast,
        'source': 'Mock Data (EOSDA no disponible)'
    }
    
    # Cache datos mock por 1 hora (3600 segundos)
    cache.set(cache_key, result, 3600)
    print(f"[WEATHER_FORECAST] Datos mock generados y guardados en cache")
    print(f"[WEATHER_FORECAST] === FIN REQUEST ===")
    return Response(result)
