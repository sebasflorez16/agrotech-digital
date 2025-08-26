"""
Vista para Analytics API de EOSDA - Datos 100% reales.
Propósito: Obtener datos científicos NDVI/NDMI reales de EOSDA con cache inteligente.
"""

import logging
import requests
import json
import hashlib
from django.conf import settings
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EOSDAAnalyticsAPIView(APIView):
    """
    Vista para obtener analytics científicos REALES de EOSDA.
    
    Endpoint: /api/parcels/eosda-analytics/
    Parámetros: 
        - view_id (requerido): ID de la vista EOSDA 
        - scene_date (opcional): Fecha de la escena para contexto
    
    Retorna: Datos científicos 100% reales de EOSDA con interpretación agronómica
    """
    permission_classes = [AllowAny]  # Temporal para debugging
    
    def get(self, request):
        """GET method para compatibilidad"""
        return self._handle_analytics_request(request, request.GET)
    
    def post(self, request):
        """POST method - método principal"""
        return self._handle_analytics_request(request, request.data)
    
    def _handle_analytics_request(self, request, data):
        """
        Obtiene analytics científicos REALES de EOSDA Statistics API.
        
        Args:
            request: Request HTTP
            data: Datos del request (GET params o POST body)
            
        Returns:
            Response: Datos científicos reales con interpretación agronómica
        """
        try:
            # ✅ CONFIRMAR QUE LA VISTA SÍ SE ESTÁ EJECUTANDO
            logger.info(f"[EOSDA_ANALYTICS_REAL] ✅ ✅ ✅ VISTA EJECUTÁNDOSE ✅ ✅ ✅")
            logger.info(f"[EOSDA_ANALYTICS_REAL] ✅ Path: {request.path}")
            logger.info(f"[EOSDA_ANALYTICS_REAL] ✅ Method: {request.method}")
            logger.info(f"[EOSDA_ANALYTICS_REAL] ✅ Data: {data}")
            
            view_id = data.get('view_id')
            scene_date = data.get('scene_date', '')
            parcel_id = request.GET.get('parcel_id')  # ← NUEVO: Aceptar parcel_id directamente
            
            if not view_id:
                logger.warning("[EOSDA_ANALYTICS_REAL] view_id faltante en request")
                response = Response({'error': 'view_id es requerido'}, status=400)
                logger.info(f"[EOSDA_ANALYTICS_REAL] ✅ RETORNANDO 400: {response.data}")
                return response
            
            # 🎯 NUEVO: Si tenemos parcel_id, usar esa parcela específica
            if parcel_id:
                logger.info(f"[EOSDA_ANALYTICS_REAL] 🎯 Usando parcela específica ID: {parcel_id}")
                parcel_data = self._get_parcel_by_id(parcel_id)
            else:
                logger.info(f"[EOSDA_ANALYTICS_REAL] 🔍 Buscando parcela por view_id: {view_id}")
                parcel_data = self._get_real_parcel_from_view_id(view_id)
            
            if not parcel_data:
                logger.error(f"[EOSDA_ANALYTICS_REAL] ❌ No se encontró parcela")
                return Response({
                    "error": "No se encontró parcela válida",
                    "details": "Parcela no existe o no tiene geometría válida",
                    "parcel_id": parcel_id,
                    "view_id": view_id
                }, status=404)
                
            logger.info(f"[EOSDA_ANALYTICS_REAL] Iniciando análisis REAL para view_id: {view_id}")
            logger.info(f"[EOSDA_ANALYTICS_REAL] Parcela: {parcel_data['name']} (field_id: {parcel_data['field_id']})")
            
            # Cache key único para evitar requests duplicados (cache por 2 horas)
            cache_key = f"eosda_real_analytics_{hashlib.md5(view_id.encode()).hexdigest()[:8]}_{scene_date}_{parcel_data.get('parcel_id', '')}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.info(f"[EOSDA_ANALYTICS_REAL] Cache hit: {cache_key}")
                response = Response(cached_data, status=200)
                logger.info(f"[EOSDA_ANALYTICS_REAL] ✅ RETORNANDO 200 (CACHE)")
                return response
            
            # Configurar fechas para EOSDA Statistics API - FECHA EXACTA DE ESCENA
            if scene_date:
                try:
                    date_obj = datetime.strptime(scene_date, "%Y-%m-%d")
                    # Usar SOLO la fecha exacta de la escena seleccionada
                    start_date = date_obj.strftime("%Y-%m-%d")
                    end_date = date_obj.strftime("%Y-%m-%d")  # Mismo día
                    
                    logger.info(f"[EOSDA_ANALYTICS_REAL] 🎯 Analizando ESCENA ESPECÍFICA: {scene_date}")
                    logger.info(f"[EOSDA_ANALYTICS_REAL] 🎯 Si hay imagen, DEBE haber datos para esta fecha exacta")
                except ValueError:
                    logger.error(f"[EOSDA_ANALYTICS_REAL] ❌ Fecha inválida: {scene_date}")
                    return Response({"error": f"Formato de fecha inválido: {scene_date}. Use YYYY-MM-DD"}, status=400)
            else:
                logger.error(f"[EOSDA_ANALYTICS_REAL] ❌ scene_date es REQUERIDO para análisis de escena específica")
                return Response({"error": "scene_date es requerido para análisis de escena específica"}, status=400)
            
            logger.info(f"[EOSDA_ANALYTICS_REAL] 📅 Fecha exacta: {start_date} (escena seleccionada por usuario)")
            
            # Obtener datos REALES de EOSDA Statistics API usando datos de la parcela
            real_analytics = self._get_real_eosda_statistics_for_parcel(parcel_data, start_date, end_date)
            
            # EOSDA hace timeout para escena específica - Error más específico
            if not real_analytics:
                logger.error(f"[EOSDA_ANALYTICS_REAL] ❌ NO se obtuvieron datos para ESCENA ESPECÍFICA")
                logger.error(f"[EOSDA_ANALYTICS_REAL] ❌ Escena: {view_id} - Fecha: {scene_date}")
                logger.error(f"[EOSDA_ANALYTICS_REAL] ❌ Parcela: {parcel_data.get('name', 'Unknown')}")
                
                return Response({
                    "error": "No se obtuvieron datos para la escena específica",
                    "details": f"EOSDA no pudo procesar la escena {view_id} del {scene_date}",
                    "view_id": view_id,
                    "scene_date": scene_date,
                    "parcel_name": parcel_data.get('name', 'Unknown'),
                    "field_id": parcel_data.get('field_id', 'Unknown'),
                    "possible_reasons": [
                        "La escena está siendo procesada por EOSDA (reintente en 1-2 minutos)",
                        "La escena no tiene datos de índices vegetales disponibles",
                        "La geometría de la parcela no intersecta con la escena",
                        "Problema temporal con EOSDA Statistics API"
                    ],
                    "troubleshooting": {
                        "step1": "Verificar que la escena seleccionada tenga baja nubosidad",
                        "step2": "Reintente en 1-2 minutos",
                        "step3": "Seleccione otra escena de fecha cercana",
                        "step4": "Contacte soporte si persiste el problema"
                    }
                }, status=503)
            
            # Interpretar datos reales con contexto agronómico
            interpreted_data = self._interpret_real_analytics(real_analytics, scene_date, view_id)
            
            # Guardar en cache por 2 horas para optimizar requests
            cache.set(cache_key, interpreted_data, 7200)
            logger.info(f"[EOSDA_ANALYTICS_REAL] Datos reales guardados en cache: {cache_key}")
            
            logger.info(f"[EOSDA_ANALYTICS_REAL] Analytics científicos REALES obtenidos exitosamente")
            return Response(interpreted_data, status=200)
                
        except Exception as e:
            logger.error(f"[EOSDA_ANALYTICS_REAL] Error inesperado: {str(e)}")
            import traceback
            logger.error(f"[EOSDA_ANALYTICS_REAL] Traceback: {traceback.format_exc()}")
            return Response({'error': f'Error interno: {str(e)}'}, status=500)
    
    def _get_real_eosda_statistics(self, view_id, start_date, end_date):
        """
        Obtiene estadísticas REALES de EOSDA Statistics API usando field_id y geometría reales.
        
        Args:
            view_id: ID de la vista EOSDA
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)
            
        Returns:
            dict: Datos reales de EOSDA o None si falla
        """
        try:
            # PASO 1: Obtener parcela real desde view_id
            parcel_data = self._get_real_parcel_from_view_id(view_id)
            
            if not parcel_data:
                logger.error(f"[EOSDA_REAL] ❌ No se encontró parcela real para view_id: {view_id}")
                return None
            
            field_id = parcel_data['field_id']
            geometry = parcel_data['geometry']
            parcel_name = parcel_data['name']
            
            logger.info(f"[EOSDA_REAL] ✅ Parcela encontrada: {parcel_name}")
            logger.info(f"[EOSDA_REAL] ✅ field_id REAL: {field_id}")
            logger.info(f"[EOSDA_REAL] ✅ Geometría REAL: {geometry}")
            
            # PASO 2: Llamar a EOSDA Statistics API con datos reales
            eosda_url = "https://api-connect.eos.com/api/gdw/api"
            headers = {
                "x-api-key": settings.EOSDA_API_KEY,
                "Content-Type": "application/json"
            }
            
            # Payload para obtener estadísticas de múltiples índices REALES
            payload = {
                "type": "mt_stats",
                "params": {
                    "bm_type": ["NDVI"],  # Solo NDVI para respuesta más rápida
                    "date_start": start_date,
                    "date_end": end_date,
                    "geometry": geometry,  # ← GEOMETRÍA REAL DE LA PARCELA
                    "sensors": ["S2"],  # Sentinel-2
                    "max_cloud_cover_in_aoi": 50,  # Aumentar tolerancia a nubes para más datos
                    "exclude_cover_pixels": False,  # Incluir pixeles cubiertos para más datos
                    "reference": f"agrotech_fast_{field_id}_{start_date}",
                    "limit": 3  # Reducir límite para respuesta más rápida
                }
            }
            
            logger.info(f"[EOSDA_REAL] 🚀 URL: {eosda_url}")
            logger.info(f"[EOSDA_REAL] 🚀 Payload REAL: {json.dumps(payload, indent=2)}")
            
            # PASO 3: Crear tarea en EOSDA Statistics API
            response = requests.post(eosda_url, json=payload, headers=headers, timeout=30)
            logger.info(f"[EOSDA_REAL] 📡 Create task status: {response.status_code}")
            logger.info(f"[EOSDA_REAL] 📡 Create task response: {response.text}")
            
            if response.status_code in [200, 202]:
                task_data = response.json()
                task_id = task_data.get("task_id")
                
                if task_id:
                    logger.info(f"[EOSDA_REAL] ✅ Task created: {task_id}")
                    
                    # PASO 4: Polling para obtener resultados reales (reducido a 5 intentos)
                    import time
                    for attempt in range(5):  # Reducido de 10 a 5 intentos
                        time.sleep(2)  # Reducido de 4 a 2 segundos
                        
                        result_url = f"https://api-connect.eos.com/api/gdw/api/{task_id}"
                        result_response = requests.get(result_url, headers=headers, timeout=15)  # Reducido timeout
                        
                        logger.info(f"[EOSDA_REAL] 🔄 Attempt {attempt + 1}/5 - Status: {result_response.status_code}")
                        
                        if result_response.status_code == 200:
                            result_data = result_response.json()
                            
                            if result_data.get("result"):
                                logger.info(f"[EOSDA_REAL] 🎉 Resultados REALES obtenidos después de {attempt + 1} intentos!")
                                logger.info(f"[EOSDA_REAL] 📊 Datos recibidos: {json.dumps(result_data.get('result', [])[:2], indent=2)}")
                                return self._process_eosda_results(result_data.get("result", []))
                            elif result_data.get("status") in ["finished", "completed"]:
                                logger.warning(f"[EOSDA_REAL] ⚠️ Task completado pero sin resultados")
                                return None
                        
                        logger.info(f"[EOSDA_REAL] ⏳ Attempt {attempt + 1}/5 - task aún procesando...")
                    
                    logger.error(f"[EOSDA_REAL] ❌ Task {task_id} timeout después de 5 intentos (10 segundos)")
                    return None
                else:
                    logger.error(f"[EOSDA_REAL] ❌ No task_id en respuesta: {task_data}")
                    return None
            else:
                logger.error(f"[EOSDA_REAL] ❌ Error creando task: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[EOSDA_REAL] ❌ Error de conexión: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"[EOSDA_REAL] ❌ Error inesperado: {str(e)}")
            import traceback
            logger.error(f"[EOSDA_REAL] 📋 Traceback: {traceback.format_exc()}")
            return None
    
    def _get_real_parcel_from_view_id(self, view_id):
        """
        Obtiene datos reales de la parcela desde la base de datos usando view_id.
        
        Args:
            view_id: ID de vista EOSDA (ej: "S2/18/N/ZK/2025/8/19/0")
            
        Returns:
            dict: Datos de la parcela real o None si no se encuentra
        """
        try:
            from .models import Parcel
            
            logger.info(f"[REAL_PARCEL] 🔍 Buscando parcela para view_id: {view_id}")
            
            # TODO: Necesitamos mapear el view_id a la parcela que el usuario seleccionó
            # Por ahora, como no sabemos qué parcela seleccionó el usuario desde view_id,
            # vamos a usar una lógica temporal hasta implementar el mapeo correcto
            
            # TEMPORAL: Buscar parcela que tenga eosda_id y geometría válida
            parcel = Parcel.objects.filter(
                eosda_id__isnull=False,
                is_deleted=False,
                geom__isnull=False
            ).first()
            
            if parcel:
                logger.info(f"[REAL_PARCEL] ✅ Parcela encontrada: {parcel.name} (ID: {parcel.id})")
                logger.info(f"[REAL_PARCEL] ✅ eosda_id: {parcel.eosda_id}")
                
                # Convertir geometría Django a GeoJSON - SOLO GEOMETRÍA REAL
                import json
                from django.contrib.gis.geos import GEOSGeometry
                
                try:
                    # Verificar el tipo de geometría que tenemos
                    logger.info(f"[REAL_PARCEL] 🔍 Tipo de geometría: {type(parcel.geom)}")
                    logger.info(f"[REAL_PARCEL] 🔍 Valor geometría: {str(parcel.geom)[:100]}...")
                    
                    if isinstance(parcel.geom, dict):
                        # Ya es un diccionario GeoJSON
                        geometry_geojson = parcel.geom
                        logger.info(f"[REAL_PARCEL] ✅ Geometría ya es dict/JSON")
                    elif hasattr(parcel.geom, 'geojson'):
                        # Es un objeto GeoDjango con método geojson
                        geometry_geojson = json.loads(parcel.geom.geojson)
                        logger.info(f"[REAL_PARCEL] ✅ Geometría desde geojson()")
                    elif hasattr(parcel.geom, 'coords'):
                        # Objeto GeoDjango con coordenadas
                        coords = list(parcel.geom.coords[0])
                        geometry_geojson = {
                            "type": "Polygon",
                            "coordinates": [coords]
                        }
                        logger.info(f"[REAL_PARCEL] ✅ Geometría desde coords")
                    elif hasattr(parcel.geom, 'json'):
                        # Objeto GeoDjango con método json
                        geometry_geojson = json.loads(parcel.geom.json)
                        logger.info(f"[REAL_PARCEL] ✅ Geometría desde json()")
                    else:
                        # Intentar convertir a string y luego a JSON
                        geom_str = str(parcel.geom)
                        geometry_geojson = json.loads(geom_str)
                        logger.info(f"[REAL_PARCEL] ✅ Geometría desde string")
                        
                    # Validar que tenemos coordenadas
                    if 'coordinates' in geometry_geojson and geometry_geojson['coordinates']:
                        coords_preview = geometry_geojson['coordinates'][0][:3]
                        logger.info(f"[REAL_PARCEL] 📍 Coordenadas REALES (primeras 3): {coords_preview}")
                        
                        return {
                            'field_id': parcel.eosda_id,
                            'geometry': geometry_geojson,
                            'name': parcel.name,
                            'parcel_id': parcel.id
                        }
                    else:
                        logger.error(f"[REAL_PARCEL] ❌ Geometría sin coordenadas válidas")
                        return None
                    
                except Exception as geom_error:
                    logger.error(f"[REAL_PARCEL] ❌ ERROR obteniendo geometría real: {geom_error}")
                    logger.error(f"[REAL_PARCEL] ❌ Tipo recibido: {type(parcel.geom)}")
                    logger.error(f"[REAL_PARCEL] ❌ Valor: {str(parcel.geom)[:200]}")
                    return None
            else:
                logger.error(f"[REAL_PARCEL] ❌ No se encontró parcela con eosda_id válido")
                
                # Debug: Mostrar parcelas disponibles
                parcels_debug = Parcel.objects.filter(is_deleted=False).values('id', 'name', 'eosda_id')[:5]
                logger.info(f"[REAL_PARCEL] 📋 Parcelas disponibles: {list(parcels_debug)}")
                
                return None
                
        except Exception as e:
            logger.error(f"[REAL_PARCEL] ❌ Error obteniendo parcela: {str(e)}")
            import traceback
            logger.error(f"[REAL_PARCEL] 📋 Traceback: {traceback.format_exc()}")
            return None
    
    def _get_parcel_by_id(self, parcel_id):
        """
        Obtiene parcela específica por ID.
        
        Args:
            parcel_id: ID de la parcela
            
        Returns:
            dict: Datos de la parcela o None si no se encuentra
        """
        try:
            from .models import Parcel
            
            logger.info(f"[PARCEL_BY_ID] 🔍 Buscando parcela ID: {parcel_id}")
            
            parcel = Parcel.objects.filter(
                id=parcel_id,
                eosda_id__isnull=False,
                is_deleted=False,
                geom__isnull=False
            ).first()
            
            if not parcel:
                logger.error(f"[PARCEL_BY_ID] ❌ Parcela ID {parcel_id} no encontrada o inválida")
                return None
            
            logger.info(f"[PARCEL_BY_ID] ✅ Parcela encontrada: {parcel.name}")
            logger.info(f"[PARCEL_BY_ID] ✅ eosda_id: {parcel.eosda_id}")
            
            # Obtener geometría real
            try:
                import json
                logger.info(f"[PARCEL_BY_ID] 🔍 Tipo geometría: {type(parcel.geom)}")
                
                if isinstance(parcel.geom, dict):
                    # Ya es un diccionario GeoJSON
                    geometry_geojson = parcel.geom
                    logger.info(f"[PARCEL_BY_ID] ✅ Geometría ya es dict")
                elif hasattr(parcel.geom, 'geojson'):
                    geometry_geojson = json.loads(parcel.geom.geojson)
                    logger.info(f"[PARCEL_BY_ID] ✅ Geometría desde geojson()")
                elif hasattr(parcel.geom, 'coords'):
                    coords = list(parcel.geom.coords[0])
                    geometry_geojson = {"type": "Polygon", "coordinates": [coords]}
                    logger.info(f"[PARCEL_BY_ID] ✅ Geometría desde coords")
                elif hasattr(parcel.geom, 'json'):
                    geometry_geojson = json.loads(parcel.geom.json)
                    logger.info(f"[PARCEL_BY_ID] ✅ Geometría desde json()")
                else:
                    # Intentar como string
                    geometry_geojson = json.loads(str(parcel.geom))
                    logger.info(f"[PARCEL_BY_ID] ✅ Geometría desde string")
                
                # Validar coordenadas
                if 'coordinates' in geometry_geojson and geometry_geojson['coordinates']:
                    coords_preview = geometry_geojson['coordinates'][0][:2]
                    logger.info(f"[PARCEL_BY_ID] 📍 Coordenadas: {coords_preview}...")
                    
                    return {
                        'field_id': parcel.eosda_id,
                        'geometry': geometry_geojson,
                        'name': parcel.name,
                        'parcel_id': parcel.id
                    }
                else:
                    logger.error(f"[PARCEL_BY_ID] ❌ Sin coordenadas válidas")
                    return None
                
            except Exception as geom_error:
                logger.error(f"[PARCEL_BY_ID] ❌ Error geometría: {geom_error}")
                logger.error(f"[PARCEL_BY_ID] ❌ Tipo: {type(parcel.geom)}")
                return None
                
        except Exception as e:
            logger.error(f"[PARCEL_BY_ID] ❌ Error: {str(e)}")
            return None
    
    def _get_real_eosda_statistics_for_parcel(self, parcel_data, start_date, end_date):
        """
        Obtiene estadísticas REALES de EOSDA usando datos específicos de parcela.
        
        Args:
            parcel_data: Datos de la parcela con field_id y geometry
            start_date: Fecha inicio
            end_date: Fecha fin
            
        Returns:
            dict: Datos de EOSDA o None si falla
        """
        try:
            field_id = parcel_data['field_id']
            geometry = parcel_data['geometry']
            parcel_name = parcel_data['name']
            
            logger.info(f"[EOSDA_PARCEL] ✅ Procesando parcela: {parcel_name}")
            logger.info(f"[EOSDA_PARCEL] ✅ field_id: {field_id}")
            
            # Llamar al método original pero con datos específicos
            return self._get_real_eosda_statistics_with_data(field_id, geometry, start_date, end_date)
            
        except Exception as e:
            logger.error(f"[EOSDA_PARCEL] ❌ Error: {str(e)}")
            return None
    
    def _get_real_eosda_statistics_with_data(self, field_id, geometry, start_date, end_date):
        """
        Llama a EOSDA Statistics API con datos específicos.
        """
        try:
            import requests
            from django.conf import settings
            
            # URL de EOSDA Statistics API
            eosda_url = "https://api-connect.eos.com/api/gdw/api"
            headers = {
                "x-api-key": settings.EOSDA_API_KEY,
                "Content-Type": "application/json"
            }
            
            # Payload optimizado para ESCENA ESPECÍFICA - TODOS LOS ÍNDICES
            payload = {
                "type": "mt_stats",
                "params": {
                    "bm_type": ["NDVI", "NDMI", "EVI"],  # Todos los índices en una sola llamada
                    "date_start": start_date,  # Fecha exacta
                    "date_end": end_date,      # Misma fecha
                    "geometry": geometry,      # Geometría real de la parcela
                    "sensors": ["S2"],         # Sentinel-2 (coincide con la escena)
                    "max_cloud_cover_in_aoi": 90,  # Muy tolerante (escena ya filtrada)
                    "exclude_cover_pixels": False,  # Incluir todos los pixeles
                    "reference": f"agrotech_scene_{field_id}_{start_date}",
                    "limit": 3  # 3 resultados esperados (uno por cada índice)
                }
            }
            
            logger.info(f"[EOSDA_API] 🎯 Solicitando datos para ESCENA ESPECÍFICA: {start_date}")
            logger.info(f"[EOSDA_API] 🎯 Parcela: field_id {field_id}")
            logger.info(f"[EOSDA_API] 🎯 Índices solicitados: NDVI, NDMI, EVI")
            logger.info(f"[EOSDA_API] 🎯 Si existe imagen, DEBE existir análisis para esta fecha")
            
            # Crear tarea
            response = requests.post(eosda_url, json=payload, headers=headers, timeout=30)
            logger.info(f"[EOSDA_API] 📡 Task status: {response.status_code}")
            logger.info(f"[EOSDA_API] 📡 Response: {response.text}")
            
            if response.status_code in [200, 202]:
                task_data = response.json()
                task_id = task_data.get("task_id")
                
                if task_id:
                    logger.info(f"[EOSDA_API] ✅ Task created: {task_id}")
                    
                    # Polling mejorado (8 intentos, 3 segundos cada uno = 24 segundos total)
                    import time
                    for attempt in range(8):  # Aumentado de 5 a 8
                        time.sleep(3)  # Aumentado de 2 a 3 segundos
                        
                        result_url = f"https://api-connect.eos.com/api/gdw/api/{task_id}"
                        result_response = requests.get(result_url, headers=headers, timeout=20)  # Timeout más alto
                        
                        logger.info(f"[EOSDA_API] 🔄 Attempt {attempt + 1}/8 - Status: {result_response.status_code}")
                        
                        if result_response.status_code == 200:
                            result_data = result_response.json()
                            
                            # DEBUGGING: Mostrar toda la respuesta para entender qué pasa
                            logger.info(f"[EOSDA_API] 🔬 RESPUESTA COMPLETA Attempt {attempt + 1}: {result_data}")
                            
                            # Verificar si hay error en el task
                            if result_data.get("task_type") == "error":
                                error_msg = result_data.get("error_message", {})
                                logger.error(f"[EOSDA_API] ❌ EOSDA ERROR: {error_msg}")
                                return None
                            
                            # Verificar diferentes posibles estructuras de respuesta
                            if result_data.get("result"):
                                logger.info(f"[EOSDA_API] 🎉 Datos REALES obtenidos después de {attempt + 1} intentos!")
                                logger.info(f"[EOSDA_API] 📊 Resultados: {len(result_data.get('result', []))} registros")
                                return self._process_eosda_results(result_data.get("result", []))
                            elif result_data.get("status") in ["finished", "completed"]:
                                logger.warning(f"[EOSDA_API] ⚠️ Task completado pero sin resultados en intento {attempt + 1}")
                                logger.warning(f"[EOSDA_API] 📋 Status: {result_data.get('status')}")
                                # Si está "finished" pero sin result, es que no hay datos para esa fecha
                                if result_data.get("status") == "finished":
                                    logger.error(f"[EOSDA_API] ❌ Task FINISHED pero SIN RESULTADOS - probablemente no hay imagen para esa fecha")
                                    return None
                            elif result_data.get("status") == "failed":
                                logger.error(f"[EOSDA_API] ❌ Task FAILED: {result_data.get('error', 'Unknown error')}")
                                return None
                        
                        logger.info(f"[EOSDA_API] ⏳ Attempt {attempt + 1}/8 - task aún procesando...")
                    
                    logger.error(f"[EOSDA_API] ❌ Timeout después de 8 intentos (24 segundos)")
                    return None
                else:
                    logger.error(f"[EOSDA_API] ❌ No task_id en respuesta: {task_data}")
                    return None
            else:
                logger.error(f"[EOSDA_API] ❌ Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"[EOSDA_API] ❌ Error: {str(e)}")
            import traceback
            logger.error(f"[EOSDA_API] 📋 Traceback: {traceback.format_exc()}")
            return None
    
    def _extract_field_id_from_view_id(self, view_id):
        """
        Extrae field_id del view_id si tiene formato conocido.
        
        Args:
            view_id: ID de vista EOSDA (ej: "S2/18/N/ZK/2025/8/19/0")
            
        Returns:
            str: field_id extraído o None
        """
        try:
            # Los view_id de EOSDA suelen tener formato como "S2/18/N/ZK/2025/8/19/0"
            # Para testing, generar un field_id basado en el view_id
            if "/" in view_id:
                # Usar hash del view_id para generar field_id consistente
                import hashlib
                view_hash = hashlib.md5(view_id.encode()).hexdigest()[:8]
                field_id = f"field_{view_hash}"
                logger.info(f"[EOSDA_REAL] Field ID generado desde view_id: {field_id}")
                return field_id
            else:
                return view_id  # Asumir que es directamente un field_id
                
        except Exception as e:
            logger.error(f"[EOSDA_REAL] Error extrayendo field_id: {str(e)}")
            return None
    
    def _process_eosda_results(self, eosda_results):
        """
        Procesa los resultados REALES de EOSDA Statistics API (mt_stats).
        
        Args:
            eosda_results: Lista de datos de EOSDA API con estructura mt_stats
            
        Returns:
            dict: Datos procesados para el frontend
        """
        if not eosda_results:
            logger.warning("[EOSDA_PROCESS] ⚠️ No hay resultados para procesar")
            return None
        
        logger.info(f"[EOSDA_PROCESS] 🔄 Procesando {len(eosda_results)} registros REALES de mt_stats")
        
        try:
            # Estructura correcta para mt_stats
            processed_data = {
                'dates': [],
                'ndvi_values': [],
                'ndmi_values': [],
                'evi_values': [],
                'metadata': {
                    'total_records': len(eosda_results),
                    'data_source': 'EOSDA_REAL',
                    'sensors': [],
                    'cloud_cover': []
                }
            }
            
            for record in eosda_results:
                # Estructura mt_stats: 
                # {
                #   "scene_id": "S2A_tile_20250819_18NYK_0",
                #   "view_id": "S2/18/N/YK/2025/8/19/0",
                #   "date": "2025-08-19",
                #   "cloud": 77.31,
                #   "indexes": {
                #     "NDVI": {"average": 0.354, "median": 0.352, ...}
                #   }
                # }
                
                date_str = record.get('date', '')
                cloud_cover = record.get('cloud', 0)
                indexes = record.get('indexes', {})
                scene_id = record.get('scene_id', '')
                
                if not date_str:
                    logger.warning(f"[EOSDA_PROCESS] ⚠️ Registro sin fecha: {record}")
                    continue
                
                # Extraer sensor del scene_id (ej: "S2A_tile_20250819_18NYK_0" -> "S2A")
                sensor = scene_id.split('_')[0] if scene_id else 'Unknown'
                
                # Procesar índices disponibles con estadísticas completas
                ndvi_data = indexes.get('NDVI', {})
                ndmi_data = indexes.get('NDMI', {})
                evi_data = indexes.get('EVI', {})
                
                # Extraer estadísticas completas para cada índice
                ndvi_stats = None
                if ndvi_data:
                    ndvi_stats = {
                        'average': ndvi_data.get('average'),
                        'min': ndvi_data.get('min'),
                        'max': ndvi_data.get('max'),
                        'median': ndvi_data.get('median'),
                        'std': ndvi_data.get('std'),
                        'variance': ndvi_data.get('variance'),
                        'q1': ndvi_data.get('q1'),
                        'q3': ndvi_data.get('q3'),
                        'p10': ndvi_data.get('p10'),
                        'p90': ndvi_data.get('p90')
                    }
                    
                ndmi_stats = None
                if ndmi_data:
                    ndmi_stats = {
                        'average': ndmi_data.get('average'),
                        'min': ndmi_data.get('min'),
                        'max': ndmi_data.get('max'),
                        'median': ndmi_data.get('median'),
                        'std': ndmi_data.get('std'),
                        'variance': ndmi_data.get('variance'),
                        'q1': ndmi_data.get('q1'),
                        'q3': ndmi_data.get('q3'),
                        'p10': ndmi_data.get('p10'),
                        'p90': ndmi_data.get('p90')
                    }
                    
                evi_stats = None
                if evi_data:
                    evi_stats = {
                        'average': evi_data.get('average'),
                        'min': evi_data.get('min'),
                        'max': evi_data.get('max'),
                        'median': evi_data.get('median'),
                        'std': evi_data.get('std'),
                        'variance': evi_data.get('variance'),
                        'q1': evi_data.get('q1'),
                        'q3': evi_data.get('q3'),
                        'p10': evi_data.get('p10'),
                        'p90': evi_data.get('p90')
                    }
                
                # Agregar a las listas (usando average como valor principal para compatibilidad)
                processed_data['dates'].append(date_str)
                processed_data['ndvi_values'].append(ndvi_stats['average'] if ndvi_stats else None)
                processed_data['ndmi_values'].append(ndmi_stats['average'] if ndmi_stats else None)
                processed_data['evi_values'].append(evi_stats['average'] if evi_stats else None)
                
                # NUEVO: Agregar estadísticas completas
                if 'ndvi_statistics' not in processed_data:
                    processed_data['ndvi_statistics'] = []
                    processed_data['ndmi_statistics'] = []
                    processed_data['evi_statistics'] = []
                    
                processed_data['ndvi_statistics'].append(ndvi_stats)
                processed_data['ndmi_statistics'].append(ndmi_stats)
                processed_data['evi_statistics'].append(evi_stats)
                
                # Metadatos
                if sensor and sensor not in processed_data['metadata']['sensors']:
                    processed_data['metadata']['sensors'].append(sensor)
                
                processed_data['metadata']['cloud_cover'].append(cloud_cover)
                
                # Log con las variables correctas
                ndvi_avg = ndvi_stats['average'] if ndvi_stats else None
                logger.info(f"[EOSDA_PROCESS] ✅ Procesado: {date_str} - NDVI: {ndvi_avg:.3f} - Cloud: {cloud_cover:.1f}%" if ndvi_avg else f"[EOSDA_PROCESS] ✅ Procesado: {date_str} - Sin NDVI - Cloud: {cloud_cover:.1f}%")
            
            # Estadísticas de metadatos
            if processed_data['metadata']['cloud_cover']:
                processed_data['metadata']['avg_cloud_cover'] = sum(processed_data['metadata']['cloud_cover']) / len(processed_data['metadata']['cloud_cover'])
            else:
                processed_data['metadata']['avg_cloud_cover'] = 0
            
            logger.info(f"[EOSDA_PROCESS] ✅ Procesamiento exitoso:")
            logger.info(f"[EOSDA_PROCESS] 📅 Fechas: {len(processed_data['dates'])}")
            logger.info(f"[EOSDA_PROCESS] 🌱 NDVI: {sum(1 for v in processed_data['ndvi_values'] if v is not None)} valores")
            logger.info(f"[EOSDA_PROCESS] 💧 NDMI: {sum(1 for v in processed_data['ndmi_values'] if v is not None)} valores")
            logger.info(f"[EOSDA_PROCESS] 🌿 EVI: {sum(1 for v in processed_data['evi_values'] if v is not None)} valores")
            logger.info(f"[EOSDA_PROCESS] 🛰️ Sensores: {processed_data['metadata']['sensors']}")
            logger.info(f"[EOSDA_PROCESS] ☁️ Nubosidad promedio: {processed_data['metadata']['avg_cloud_cover']:.1f}%")
            
            return processed_data
            
        except Exception as e:
            logger.error(f"[EOSDA_PROCESS] ❌ Error procesando resultados: {str(e)}")
            import traceback
            logger.error(f"[EOSDA_PROCESS] 📋 Traceback: {traceback.format_exc()}")
            return None
            logger.error(f"[EOSDA_PROCESS] 📋 Traceback: {traceback.format_exc()}")
            return None
    
    def _generate_minimal_fallback_data(self, view_id, scene_date):
        """
        Genera datos mínimos consistentes cuando EOSDA no responde.
        Usa hash del view_id para garantizar consistencia.
        
        Args:
            view_id: ID de vista
            scene_date: Fecha de escena
            
        Returns:
            dict: Datos mínimos consistentes
        """
        try:
            # Usar hash para generar datos consistentes (no aleatorios)
            import hashlib
            seed_string = f"{view_id}_{scene_date}"
            seed_hash = hashlib.md5(seed_string.encode()).hexdigest()
            
            # Convertir hash a números para datos consistentes
            hash_int = int(seed_hash[:8], 16)
            
            # Generar NDVI consistente entre 0.2-0.8
            ndvi_base = 0.2 + ((hash_int % 1000) / 1000.0) * 0.6
            
            # Generar NDMI consistente entre -0.2-0.4
            ndmi_base = -0.2 + ((hash_int % 600) / 1000.0) * 0.6
            
            logger.info(f"[EOSDA_REAL] Generando datos consistentes para view_id: {view_id}")
            logger.info(f"[EOSDA_REAL] NDVI consistente: {ndvi_base:.3f}, NDMI: {ndmi_base:.3f}")
            
            return {
                'ndvi': {
                    'mean': round(ndvi_base, 3),
                    'median': round(ndvi_base + 0.01, 3),
                    'std': round(0.05 + ((hash_int % 100) / 1000.0) * 0.1, 3),
                    'min': round(max(0, ndvi_base - 0.1), 3),
                    'max': round(min(1, ndvi_base + 0.1), 3),
                    'count': 15000 + (hash_int % 10000),
                    'source': 'fallback_consistent'
                },
                'ndmi': {
                    'mean': round(ndmi_base, 3),
                    'median': round(ndmi_base + 0.005, 3),
                    'std': round(0.03 + ((hash_int % 50) / 1000.0) * 0.05, 3),
                    'min': round(max(-1, ndmi_base - 0.08), 3),
                    'max': round(min(1, ndmi_base + 0.08), 3),
                    'count': 15000 + (hash_int % 10000),
                    'source': 'fallback_consistent'
                }
            }
            
        except Exception as e:
            logger.error(f"[EOSDA_REAL] Error generando fallback: {str(e)}")
            # Fallback del fallback
            return {
                'ndvi': {'mean': 0.4, 'median': 0.4, 'std': 0.1, 'min': 0.2, 'max': 0.6, 'count': 10000},
                'ndmi': {'mean': 0.1, 'median': 0.1, 'std': 0.05, 'min': 0.0, 'max': 0.2, 'count': 10000}
            }
    
    def _interpret_real_analytics(self, analytics_data, scene_date, view_id):
        """
        Interpreta los datos científicos REALES y añade contexto agronómico.
        
        Args:
            analytics_data: Datos REALES de EOSDA con estructura processed
            scene_date: Fecha de la escena
            view_id: ID de la vista
            
        Returns:
            dict: Datos interpretados con contexto agronómico
        """
        try:
            interpretation = {
                'raw_data': analytics_data,
                'interpretation': {},
                'alerts': [],
                'recommendations': [],
                'scientific_data': {  # NUEVO: Datos científicos visibles
                    'satellite_indices': {},
                    'analysis_summary': '',
                    'data_quality': {}
                },
                'metadata': {
                    'view_id': view_id,
                    'scene_date': scene_date,
                    'analysis_type': 'real_eosda_data',
                    'confidence': 'high',
                    'data_source': 'eosda_statistics_api',
                    'processed_at': self._get_current_datetime()
                }
            }
            
            # Extraer valores de la estructura processed
            ndvi_values = analytics_data.get('ndvi_values', [])
            ndmi_values = analytics_data.get('ndmi_values', [])
            evi_values = analytics_data.get('evi_values', [])
            dates = analytics_data.get('dates', [])
            metadata = analytics_data.get('metadata', {})
            
            # NUEVO: Extraer estadísticas completas
            ndvi_statistics = analytics_data.get('ndvi_statistics', [])
            ndmi_statistics = analytics_data.get('ndmi_statistics', [])
            evi_statistics = analytics_data.get('evi_statistics', [])
            
            # Preparar datos científicos para mostrar en interfaz
            scientific_summary = []
            
            # Interpretar NDVI con estadísticas completas
            if ndvi_values and len(ndvi_values) > 0 and ndvi_values[0] is not None:
                ndvi_value = ndvi_values[0]
                ndvi_stats = ndvi_statistics[0] if ndvi_statistics and ndvi_statistics[0] else None
                ndvi_interpretation = self._interpret_ndvi_value(ndvi_value)
                
                interpretation['interpretation']['ndvi'] = {
                    'value': ndvi_value,
                    'statistics': ndvi_stats,
                    'interpretation': ndvi_interpretation,
                    'date': dates[0] if dates else scene_date
                }
                
                interpretation['scientific_data']['satellite_indices']['ndvi'] = {
                    'name': 'NDVI - Salud Vegetal',
                    'description': 'Mide qué tan verde y vigoroso está su cultivo',
                    'value': round(ndvi_value, 3),
                    'percentage': round(ndvi_value * 100, 1),
                    'status': ndvi_interpretation['status'],
                    'explanation': ndvi_interpretation['description'],
                    'color': ndvi_interpretation['color'],
                    'ranges': {
                        'excelente': '0.7 - 1.0',
                        'bueno': '0.3 - 0.7',
                        'problema': '< 0.3'
                    },
                    'statistics': {
                        'promedio': {
                            'value': round(ndvi_stats['average'], 3) if ndvi_stats else round(ndvi_value, 3),
                            'description': 'Condición general del campo'
                        },
                        'minimo': {
                            'value': round(ndvi_stats['min'], 3) if ndvi_stats and ndvi_stats['min'] else 'N/D',
                            'description': 'Zona más problemática'
                        },
                        'maximo': {
                            'value': round(ndvi_stats['max'], 3) if ndvi_stats and ndvi_stats['max'] else 'N/D',
                            'description': 'Zona en mejor estado'
                        },
                        'desviacion': {
                            'value': round(ndvi_stats['std'], 3) if ndvi_stats and ndvi_stats['std'] else 'N/D',
                            'description': 'Uniformidad del cultivo',
                            'interpretation': 'Campo uniforme' if ndvi_stats and ndvi_stats['std'] and ndvi_stats['std'] < 0.1 else 'Campo variable' if ndvi_stats and ndvi_stats['std'] else 'N/D'
                        }
                    }
                }
                scientific_summary.append(f"NDVI: {ndvi_value:.3f} ({ndvi_interpretation['status']})")
                logger.info(f"[ANALYTICS_INTERPRETATION] NDVI REAL interpretado: {ndvi_value:.3f} - {ndvi_interpretation['status']}")
                
            # Interpretar NDMI con estadísticas completas
            if ndmi_values and len(ndmi_values) > 0 and ndmi_values[0] is not None:
                ndmi_value = ndmi_values[0]
                ndmi_stats = ndmi_statistics[0] if ndmi_statistics and ndmi_statistics[0] else None
                ndmi_interpretation = self._interpret_ndmi_value(ndmi_value)
                
                interpretation['interpretation']['ndmi'] = {
                    'value': ndmi_value,
                    'statistics': ndmi_stats,
                    'interpretation': ndmi_interpretation,
                    'date': dates[0] if dates else scene_date
                }
                
                interpretation['scientific_data']['satellite_indices']['ndmi'] = {
                    'name': 'NDMI - Contenido de Agua',
                    'description': 'Detecta si las plantas tienen suficiente humedad',
                    'value': round(ndmi_value, 3),
                    'percentage': round((ndmi_value + 1) * 50, 1),
                    'status': ndmi_interpretation['status'],
                    'explanation': ndmi_interpretation['description'],
                    'color': ndmi_interpretation['color'],
                    'ranges': {
                        'optimo': '0.4 - 1.0',
                        'moderado': '0.0 - 0.4',
                        'estres': '< 0.0'
                    },
                    'statistics': {
                        'promedio': {
                            'value': round(ndmi_stats['average'], 3) if ndmi_stats else round(ndmi_value, 3),
                            'description': 'Nivel general de humedad'
                        },
                        'minimo': {
                            'value': round(ndmi_stats['min'], 3) if ndmi_stats and ndmi_stats['min'] else 'N/D',
                            'description': 'Zona más seca'
                        },
                        'maximo': {
                            'value': round(ndmi_stats['max'], 3) if ndmi_stats and ndmi_stats['max'] else 'N/D',
                            'description': 'Zona más húmeda'
                        },
                        'desviacion': {
                            'value': round(ndmi_stats['std'], 3) if ndmi_stats and ndmi_stats['std'] else 'N/D',
                            'description': 'Uniformidad del riego',
                            'interpretation': 'Riego uniforme' if ndmi_stats and ndmi_stats['std'] and ndmi_stats['std'] < 0.1 else 'Riego variable' if ndmi_stats and ndmi_stats['std'] else 'N/D'
                        }
                    }
                }
                scientific_summary.append(f"NDMI: {ndmi_value:.3f} ({ndmi_interpretation['status']})")
                logger.info(f"[ANALYTICS_INTERPRETATION] NDMI REAL interpretado: {ndmi_value:.3f} - {ndmi_interpretation['status']}")
                
            # Interpretar EVI con estadísticas completas
            if evi_values and len(evi_values) > 0 and evi_values[0] is not None:
                evi_value = evi_values[0]
                evi_stats = evi_statistics[0] if evi_statistics and evi_statistics[0] else None
                evi_interpretation = self._interpret_evi_value(evi_value)
                
                interpretation['interpretation']['evi'] = {
                    'value': evi_value,
                    'statistics': evi_stats,
                    'interpretation': evi_interpretation,
                    'date': dates[0] if dates else scene_date
                }
                
                interpretation['scientific_data']['satellite_indices']['evi'] = {
                    'name': 'EVI - Precisión Mejorada',
                    'description': 'Análisis más preciso para cultivos densos',
                    'value': round(evi_value, 3),
                    'percentage': round(evi_value * 100, 1),
                    'status': evi_interpretation['status'],
                    'explanation': evi_interpretation['description'],
                    'color': evi_interpretation['color'],
                    'ranges': {
                        'excelente': '0.5 - 1.0',
                        'bueno': '0.2 - 0.5',
                        'bajo': '< 0.2'
                    },
                    'statistics': {
                        'promedio': {
                            'value': round(evi_stats['average'], 3) if evi_stats else round(evi_value, 3),
                            'description': 'Vigor general del cultivo'
                        },
                        'minimo': {
                            'value': round(evi_stats['min'], 3) if evi_stats and evi_stats['min'] else 'N/D',
                            'description': 'Zona menos vigorosa'
                        },
                        'maximo': {
                            'value': round(evi_stats['max'], 3) if evi_stats and evi_stats['max'] else 'N/D',
                            'description': 'Zona más vigorosa'
                        },
                        'desviacion': {
                            'value': round(evi_stats['std'], 3) if evi_stats and evi_stats['std'] else 'N/D',
                            'description': 'Uniformidad del vigor',
                            'interpretation': 'Crecimiento uniforme' if evi_stats and evi_stats['std'] and evi_stats['std'] < 0.1 else 'Crecimiento variable' if evi_stats and evi_stats['std'] else 'N/D'
                        }
                    }
                }
                scientific_summary.append(f"EVI: {evi_value:.3f} ({evi_interpretation['status']})")
                logger.info(f"[ANALYTICS_INTERPRETATION] EVI REAL interpretado: {evi_value:.3f} - {evi_interpretation['status']}")
            
            # Crear resumen científico
            interpretation['scientific_data']['analysis_summary'] = " | ".join(scientific_summary)
            interpretation['scientific_data']['data_quality'] = {
                'sensor': metadata.get('sensors', ['Unknown'])[0] if metadata.get('sensors') else 'Unknown',
                'cloud_cover': round(metadata.get('avg_cloud_cover', 0), 1),
                'acquisition_date': dates[0] if dates else scene_date,
                'data_source': 'EOSDA Satellite Analytics',
                'confidence': 'Alta' if metadata.get('avg_cloud_cover', 100) < 50 else 'Media'
            }
                
            # Generar alertas automáticas basadas en datos REALES
            interpretation['alerts'] = self._generate_real_alerts_from_values(ndvi_values, ndmi_values, evi_values)
            
            # Generar recomendaciones agronómicas basadas en datos REALES
            interpretation['recommendations'] = self._generate_real_recommendations_from_values(ndvi_values, ndmi_values, evi_values, scene_date)
            
            logger.info(f"[ANALYTICS_INTERPRETATION] Interpretación REAL completada - Alertas: {len(interpretation['alerts'])}, Recomendaciones: {len(interpretation['recommendations'])}")
            
            return interpretation
            
        except Exception as e:
            logger.error(f"[ANALYTICS_INTERPRETATION] Error en interpretación REAL: {str(e)}")
            # Retornar datos brutos si falla la interpretación
            return {
                'raw_data': analytics_data,
                'interpretation': {},
                'alerts': [{'type': 'warning', 'title': 'Error en Interpretación', 'message': 'Mostrando datos brutos REALES'}],
                'recommendations': [],
                'metadata': {'view_id': view_id, 'scene_date': scene_date, 'error': str(e), 'data_source': 'eosda_real_with_error'}
            }
    
    def _interpret_ndvi_value(self, ndvi_value):
        """Interpreta un valor NDVI individual"""
        if ndvi_value >= 0.8:
            return {
                'status': 'Excelente',
                'category': 'alta_vegetacion',
                'description': 'Vegetación muy densa y saludable',
                'color': '#2E7D32'
            }
        elif ndvi_value >= 0.6:
            return {
                'status': 'Bueno',
                'category': 'vegetacion_buena',
                'description': 'Vegetación densa y saludable',
                'color': '#388E3C'
            }
        elif ndvi_value >= 0.4:
            return {
                'status': 'Moderado',
                'category': 'vegetacion_moderada',
                'description': 'Vegetación moderada, monitorear desarrollo',
                'color': '#FFA000'
            }
        elif ndvi_value >= 0.2:
            return {
                'status': 'Bajo',
                'category': 'vegetacion_baja',
                'description': 'Vegetación escasa o estresada',
                'color': '#F57C00'
            }
        else:
            return {
                'status': 'Crítico',
                'category': 'sin_vegetacion',
                'description': 'Suelo desnudo o vegetación muy escasa',
                'color': '#D32F2F'
            }
    
    def _interpret_ndmi_value(self, ndmi_value):
        """Interpreta un valor NDMI individual (humedad)"""
        if ndmi_value >= 0.4:
            return {
                'status': 'Óptimo',
                'category': 'humedad_alta',
                'description': 'Excelente contenido de humedad en vegetación',
                'color': '#1976D2'
            }
        elif ndmi_value >= 0.2:
            return {
                'status': 'Bueno',
                'category': 'humedad_buena',
                'description': 'Buen contenido de humedad',
                'color': '#0288D1'
            }
        elif ndmi_value >= 0.0:
            return {
                'status': 'Moderado',
                'category': 'humedad_moderada',
                'description': 'Humedad moderada, considerar riego',
                'color': '#FFA000'
            }
        else:
            return {
                'status': 'Bajo',
                'category': 'humedad_baja',
                'description': 'Bajo contenido de humedad, riego necesario',
                'color': '#F57C00'
            }
    
    def _interpret_evi_value(self, evi_value):
        """Interpreta un valor EVI individual (índice de vegetación mejorado)"""
        if evi_value >= 0.6:
            return {
                'status': 'Excelente',
                'category': 'evi_alto',
                'description': 'Vegetación muy vigorosa',
                'color': '#2E7D32'
            }
        elif evi_value >= 0.4:
            return {
                'status': 'Bueno',
                'category': 'evi_bueno',
                'description': 'Vegetación vigorosa',
                'color': '#388E3C'
            }
        elif evi_value >= 0.2:
            return {
                'status': 'Moderado',
                'category': 'evi_moderado',
                'description': 'Vigor moderado de vegetación',
                'color': '#FFA000'
            }
        else:
            return {
                'status': 'Bajo',
                'category': 'evi_bajo',
                'description': 'Bajo vigor de vegetación',
                'color': '#F57C00'
            }
    
    def _generate_real_alerts_from_values(self, ndvi_values, ndmi_values, evi_values):
        """Genera alertas basadas en valores reales"""
        alerts = []
        
        # Verificar NDVI
        if ndvi_values and ndvi_values[0] is not None:
            ndvi = ndvi_values[0]
            if ndvi < 0.3:
                alerts.append({
                    'type': 'warning',
                    'priority': 'high',
                    'title': 'NDVI Bajo Detectado',
                    'message': f'NDVI de {ndvi:.3f} indica vegetación escasa o estresada',
                    'recommended_action': 'Revisar nutrición y riego del cultivo'
                })
        
        # Verificar NDMI (humedad)
        if ndmi_values and ndmi_values[0] is not None:
            ndmi = ndmi_values[0]
            if ndmi < 0.1:
                alerts.append({
                    'type': 'critical',
                    'priority': 'high',
                    'title': 'Estrés Hídrico Detectado',
                    'message': f'NDMI de {ndmi:.3f} indica bajo contenido de humedad',
                    'recommended_action': 'Implementar riego urgente'
                })
        
        return alerts
    
    def _generate_real_recommendations_from_values(self, ndvi_values, ndmi_values, evi_values, scene_date):
        """Genera recomendaciones agronómicas basadas en valores reales"""
        recommendations = []
        
        # Análisis combinado de índices con datos específicos
        if ndvi_values and ndvi_values[0] is not None:
            ndvi = ndvi_values[0]
            ndmi = ndmi_values[0] if ndmi_values and ndmi_values[0] is not None else None
            evi = evi_values[0] if evi_values and evi_values[0] is not None else None
            
            # Recomendación basada en NDVI y contexto temporal
            if ndvi < 0.4:
                # Crear descripción detallada con datos científicos
                detailed_description = f'NDVI de {ndvi:.3f} sugiere necesidad de mejora nutricional'
                if ndmi is not None:
                    detailed_description += f'. NDMI de {ndmi:.3f} indica nivel de humedad {"bajo" if ndmi < 0.1 else "moderado"}'
                if evi is not None:
                    detailed_description += f'. EVI de {evi:.3f} muestra vigor {"bueno" if evi > 0.4 else "moderado"} de vegetación'
                
                recommendations.append({
                    'priority': 'high',
                    'category': 'nutricion',
                    'title': 'Optimizar Nutrición del Cultivo',
                    'description': detailed_description,
                    'scientific_data': {
                        'ndvi': {
                            'value': round(ndvi, 3),
                            'status': 'Bajo' if ndvi < 0.3 else 'Moderado',
                            'target': '> 0.6 (Óptimo)'
                        },
                        'ndmi': {
                            'value': round(ndmi, 3) if ndmi is not None else 'N/D',
                            'status': 'Bajo' if ndmi and ndmi < 0.1 else 'Moderado' if ndmi else 'N/D',
                            'target': '> 0.2 (Bueno)'
                        } if ndmi is not None else None,
                        'evi': {
                            'value': round(evi, 3) if evi is not None else 'N/D',
                            'status': 'Bueno' if evi and evi > 0.4 else 'Moderado' if evi else 'N/D',
                            'target': '> 0.6 (Excelente)'
                        } if evi is not None else None
                    },
                    'actions': [
                        'Aplicar fertilizante nitrogenado',
                        'Verificar pH del suelo',
                        'Considerar análisis foliar'
                    ],
                    'timeline': 'Próximos 7-14 días',
                    'expected_impact': 'Mejora de vigor vegetativo en 2-3 semanas',
                    'monitoring': f'Monitorear NDVI objetivo: > 0.6 para cultivos óptimos'
                })
            elif ndvi >= 0.6:
                recommendations.append({
                    'priority': 'low',
                    'category': 'mantenimiento',
                    'title': 'Mantener Prácticas Actuales',
                    'description': f'NDVI de {ndvi:.3f} indica vegetación saludable',
                    'scientific_data': {
                        'ndvi': {
                            'value': round(ndvi, 3),
                            'status': 'Excelente',
                            'target': 'Alcanzado'
                        }
                    },
                    'actions': [
                        'Continuar plan nutricional actual',
                        'Monitorear para mantener niveles'
                    ],
                    'timeline': 'Seguimiento mensual',
                    'expected_impact': 'Mantenimiento de productividad',
                    'monitoring': f'Mantener NDVI > 0.6 para productividad óptima'
                })
        
        # Recomendación específica por estrés hídrico
        if ndmi_values and ndmi_values[0] is not None and ndmi_values[0] < 0.0:
            recommendations.append({
                'priority': 'high',
                'category': 'riego',
                'title': 'Implementar Riego Urgente',
                'description': f'NDMI de {ndmi_values[0]:.3f} indica estrés hídrico severo',
                'scientific_data': {
                    'ndmi': {
                        'value': round(ndmi_values[0], 3),
                        'status': 'Crítico',
                        'target': '> 0.2 (Bueno)'
                    }
                },
                'actions': [
                    'Activar sistema de riego inmediatamente',
                    'Revisar programación de riego',
                    'Monitorear humedad del suelo'
                ],
                'timeline': 'Inmediato (24-48 horas)',
                'expected_impact': 'Recuperación de estrés hídrico en 3-5 días',
                'monitoring': 'Monitorear NDMI objetivo: > 0.2 para buena hidratación'
            })
        
        # Añadir recomendación de monitoreo si no hay suficientes índices
        if not any([ndmi_values and ndmi_values[0] is not None, evi_values and evi_values[0] is not None]):
            recommendations.append({
                'priority': 'medium',
                'category': 'monitoreo',
                'title': 'Ampliar Análisis de Índices',
                'description': 'Se recomienda obtener índices NDMI y EVI para análisis completo',
                'scientific_data': {
                    'available': ['NDVI'],
                    'missing': ['NDMI', 'EVI'],
                    'completeness': '33%'
                },
                'actions': [
                    'Solicitar análisis NDMI (humedad)',
                    'Solicitar análisis EVI (vigor)',
                    'Establecer monitoreo regular'
                ],
                'timeline': 'Próxima semana',
                'expected_impact': 'Diagnóstico más preciso del cultivo',
                'monitoring': 'Análisis tri-dimensional: NDVI + NDMI + EVI'
            })
        
        return recommendations
    
    def _interpret_ndvi_real(self, ndvi_data):
        """
        Interpreta datos NDVI REALES con clasificación agronómica científica.
        
        Args:
            ndvi_data: Diccionario con estadísticas NDVI reales de EOSDA
            
        Returns:
            dict: Interpretación agronómica del NDVI real
        """
        mean = ndvi_data.get('mean', 0)
        std = ndvi_data.get('std', 0)
        min_val = ndvi_data.get('min', 0)
        max_val = ndvi_data.get('max', 0)
        count = ndvi_data.get('count', 0)
        
        # Clasificación científica NDVI basada en estándares agronómicos internacionales
        if mean >= 0.8:
            health_status = "🟢 Vegetación excelente"
            description = "Cultivo en condiciones óptimas de crecimiento con máxima actividad fotosintética"
            priority = "low"
            emoji = "🌱✨"
        elif mean >= 0.7:
            health_status = "🟢 Vegetación muy saludable"
            description = "Cultivo con excelente desarrollo vegetativo y buena actividad fotosintética"
            priority = "low"
            emoji = "🌿"
        elif mean >= 0.6:
            health_status = "🟢 Vegetación saludable"  
            description = "Cultivo en buen estado de desarrollo vegetativo"
            priority = "low"
            emoji = "🌾"
        elif mean >= 0.4:
            health_status = "🟡 Vegetación moderada"
            description = "Cultivo en desarrollo normal, monitorear evolución"
            priority = "medium"
            emoji = "⚠️"
        elif mean >= 0.2:
            health_status = "🟠 Vegetación escasa"
            description = "Posible estrés en el cultivo, requiere atención"
            priority = "medium"
            emoji = "🔶"
        elif mean >= 0.1:
            health_status = "🔴 Vegetación muy pobre"
            description = "Estrés severo en el cultivo"
            priority = "high"
            emoji = "🚨"
        else:
            health_status = "🔴 Vegetación crítica"
            description = "Requiere intervención inmediata"
            priority = "critical"
            emoji = "🆘"
            
        # Evaluar uniformidad del cultivo basado en desviación estándar real
        if std <= 0.05:
            uniformity = "🟢 Extremadamente uniforme"
            uniformity_desc = "Excelente homogeneidad en todo el cultivo"
        elif std <= 0.1:
            uniformity = "🟢 Muy uniforme"
            uniformity_desc = "Excelente uniformidad en el cultivo"
        elif std <= 0.15:
            uniformity = "🟡 Moderadamente uniforme"
            uniformity_desc = "Variabilidad normal en el campo"
        elif std <= 0.2:
            uniformity = "🟠 Desigual"
            uniformity_desc = "Variabilidad notable - revisar manejo"
        else:
            uniformity = "🔴 Muy desigual"
            uniformity_desc = "Alta variabilidad - revisar riego y fertilización urgentemente"
            
        # Rango de valores reales
        value_range = max_val - min_val
        
        # Análisis de distribución basado en datos reales
        if count > 20000:
            coverage = "🟢 Cobertura excelente"
        elif count > 10000:
            coverage = "🟡 Cobertura buena"
        else:
            coverage = "🟠 Cobertura limitada"
        
        return {
            'health_status': health_status,
            'description': description,
            'uniformity': uniformity,
            'uniformity_description': uniformity_desc,
            'priority': priority,
            'emoji': emoji,
            'coverage': coverage,
            'metrics': {
                'mean_value': round(mean, 3),
                'variability': round(std, 3),
                'min_value': round(min_val, 3),
                'max_value': round(max_val, 3),
                'range': round(value_range, 3),
                'pixel_count': count,
                'coefficient_variation': round((std / mean * 100) if mean > 0 else 0, 1)
            }
        }
    
    def _interpret_ndmi_real(self, ndmi_data):
        """
        Interpreta datos NDMI REALES (índice de humedad).
        
        Args:
            ndmi_data: Diccionario con estadísticas NDMI reales de EOSDA
            
        Returns:
            dict: Interpretación agronómica del NDMI real
        """
        mean = ndmi_data.get('mean', 0)
        std = ndmi_data.get('std', 0)
        min_val = ndmi_data.get('min', 0)
        max_val = ndmi_data.get('max', 0)
        count = ndmi_data.get('count', 0)
        
        # Clasificación científica NDMI (Normalized Difference Moisture Index) real
        if mean >= 0.6:
            moisture_status = "💧 Extremadamente húmedo"
            description = "Excelente contenido de humedad en la vegetación - posible exceso"
            priority = "low"
            emoji = "💙"
        elif mean >= 0.4:
            moisture_status = "💧 Muy húmedo"
            description = "Excelente nivel de humedad en el cultivo"
            priority = "low"
            emoji = "💧"
        elif mean >= 0.2:
            moisture_status = "🟢 Húmedo"
            description = "Buen nivel de humedad en el cultivo"
            priority = "low"
            emoji = "🌊"
        elif mean >= 0.0:
            moisture_status = "🟡 Normal a seco"
            description = "Humedad moderada - monitorear tendencias"
            priority = "medium"
            emoji = "⚠️"
        elif mean >= -0.2:
            moisture_status = "🟠 Seco"
            description = "Posible estrés hídrico - considerar riego"
            priority = "medium"
            emoji = "🔶"
        elif mean >= -0.4:
            moisture_status = "🔴 Muy seco"
            description = "Estrés hídrico moderado a severo"
            priority = "high"
            emoji = "🚨"
        else:
            moisture_status = "🔴 Extremadamente seco"
            description = "Estrés hídrico crítico - riego urgente"
            priority = "critical"
            emoji = "🆘"
        
        # Evaluar variabilidad de humedad
        if std <= 0.05:
            moisture_uniformity = "🟢 Humedad muy uniforme"
        elif std <= 0.1:
            moisture_uniformity = "🟡 Humedad moderadamente uniforme"
        else:
            moisture_uniformity = "🔴 Humedad muy variable"
            
        return {
            'moisture_status': moisture_status,
            'description': description,
            'priority': priority,
            'emoji': emoji,
            'uniformity': moisture_uniformity,
            'metrics': {
                'mean_value': round(mean, 3),
                'variability': round(std, 3),
                'min_value': round(min_val, 3),
                'max_value': round(max_val, 3),
                'range': round(max_val - min_val, 3),
                'pixel_count': count
            }
        }
    
    def _interpret_evi_real(self, evi_data):
        """
        Interpreta datos EVI REALES (Enhanced Vegetation Index).
        
        Args:
            evi_data: Diccionario con estadísticas EVI reales de EOSDA
            
        Returns:
            dict: Interpretación agronómica del EVI real
        """
        mean = evi_data.get('mean', 0)
        
        if mean >= 0.5:
            status = "🟢 EVI Excelente"
            description = "Vegetación muy densa y saludable con óptima estructura"
            emoji = "🌱"
        elif mean >= 0.3:
            status = "🟡 EVI Bueno"
            description = "Vegetación moderadamente densa"
            emoji = "🌿"
        else:
            status = "🔴 EVI Bajo"
            description = "Vegetación escasa o estresada"
            emoji = "⚠️"
            
        return {
            'status': status,
            'description': description,
            'emoji': emoji,
            'mean_value': round(mean, 3)
        }
    
    def _generate_real_alerts(self, analytics_data):
        """
        Genera alertas automáticas basadas en umbrales científicos y datos REALES.
        
        Args:
            analytics_data: Datos de analytics REALES de EOSDA
            
        Returns:
            list: Lista de alertas con tipo, título, mensaje y acción
        """
        alerts = []
        
        # Alertas NDVI críticas basadas en datos reales
        if 'ndvi' in analytics_data:
            ndvi_mean = analytics_data['ndvi'].get('mean', 0)
            ndvi_std = analytics_data['ndvi'].get('std', 0)
            ndvi_count = analytics_data['ndvi'].get('count', 0)
            
            if ndvi_mean < 0.15:
                alerts.append({
                    'type': 'critical',
                    'title': '🆘 NDVI Crítico Detectado',
                    'message': f'NDVI promedio de {ndvi_mean:.3f} indica estrés vegetal severo',
                    'action': 'Revisar inmediatamente: nutrición, riego, plagas y enfermedades',
                    'priority': 'urgent',
                    'data_source': 'eosda_real'
                })
            elif ndvi_mean < 0.3:
                alerts.append({
                    'type': 'warning',
                    'title': '🚨 NDVI Bajo Detectado',
                    'message': f'NDVI promedio de {ndvi_mean:.3f} sugiere estrés en el cultivo',
                    'action': 'Evaluar condiciones de nutrición y riego en las próximas 48 horas',
                    'priority': 'high',
                    'data_source': 'eosda_real'
                })
                
            # Alerta por alta variabilidad real
            if ndvi_std > 0.25:
                alerts.append({
                    'type': 'info',
                    'title': '📊 Alta Variabilidad Detectada',
                    'message': f'Desviación estándar de {ndvi_std:.3f} indica cultivo muy desigual',
                    'action': 'Revisar uniformidad de riego, fertilización y condiciones del suelo',
                    'priority': 'medium',
                    'data_source': 'eosda_real'
                })
            
            # Alerta por cobertura limitada
            if ndvi_count < 5000:
                alerts.append({
                    'type': 'info',
                    'title': '📡 Cobertura de Datos Limitada',
                    'message': f'Solo {ndvi_count} píxeles analizados - resultado puede ser limitado',
                    'action': 'Verificar cobertura de nubes y considerar nueva captura',
                    'priority': 'low',
                    'data_source': 'eosda_real'
                })
        
        # Alertas NDMI críticas (estrés hídrico) basadas en datos reales
        if 'ndmi' in analytics_data:
            ndmi_mean = analytics_data['ndmi'].get('mean', 0)
            
            if ndmi_mean < -0.3:
                alerts.append({
                    'type': 'critical',
                    'title': '💧 Estrés Hídrico Crítico',
                    'message': f'NDMI promedio de {ndmi_mean:.3f} indica estrés hídrico severo',
                    'action': 'Implementar riego de emergencia inmediatamente',
                    'priority': 'urgent',
                    'data_source': 'eosda_real'
                })
            elif ndmi_mean < 0.0:
                alerts.append({
                    'type': 'warning',
                    'title': '🟠 Estrés Hídrico Detectado',
                    'message': f'NDMI promedio de {ndmi_mean:.3f} sugiere déficit hídrico',
                    'action': 'Evaluar necesidades de riego y programar aplicación',
                    'priority': 'high',
                    'data_source': 'eosda_real'
                })
                
        return alerts
    
    def _generate_real_recommendations(self, analytics_data, scene_date):
        """
        Genera recomendaciones agronómicas automáticas basadas en análisis científico REAL.
        
        Args:
            analytics_data: Datos de analytics REALES de EOSDA
            scene_date: Fecha de la escena para contexto temporal
            
        Returns:
            list: Lista de recomendaciones con prioridad, categoría y acciones
        """
        recommendations = []
        
        # Obtener valores principales reales
        ndvi_mean = analytics_data.get('ndvi', {}).get('mean', 0)
        ndmi_mean = analytics_data.get('ndmi', {}).get('mean', 0)
        ndvi_std = analytics_data.get('ndvi', {}).get('std', 0)
        ndvi_count = analytics_data.get('ndvi', {}).get('count', 0)
        
        # Análisis combinado NDVI + NDMI para recomendaciones integrales basadas en datos reales
        
        # Caso 1: Estrés hídrico severo con vegetación comprometida (datos reales)
        if ndvi_mean < 0.3 and ndmi_mean < 0.0:
            recommendations.append({
                'priority': 'urgent',
                'category': 'emergencia_hidrica',
                'title': '🆘 Intervención de Emergencia Requerida',
                'description': 'Los datos satelitales reales muestran estrés severo combinado',
                'actions': [
                    'Aplicar riego de emergencia inmediatamente',
                    'Evaluar sistema radicular por muestreo',
                    'Análisis foliar urgente para deficiencias nutricionales',
                    'Monitorear recuperación con nueva imagen en 5-7 días'
                ],
                'timeframe': '24-48 horas',
                'data_confidence': 'alta_eosda'
            })
        
        # Caso 2: Vegetación buena pero con déficit hídrico (datos reales)
        elif ndvi_mean > 0.6 and ndmi_mean < 0.2:
            recommendations.append({
                'priority': 'high',
                'category': 'riego_preventivo',
                'title': '💧 Riego Preventivo Urgente',
                'description': 'Cultivo saludable pero con estrés hídrico incipiente detectado por satélite',
                'actions': [
                    'Implementar riego programado en 24-48 horas',
                    'Monitorear humedad del suelo con sondas',
                    'Evaluar eficiencia del sistema de riego',
                    'Ajustar frecuencia según datos meteorológicos'
                ],
                'timeframe': '24-48 horas',
                'data_confidence': 'alta_eosda'
            })
        
        # Caso 3: Vegetación excelente (datos reales)
        elif ndvi_mean > 0.7 and ndmi_mean > 0.3:
            recommendations.append({
                'priority': 'low',
                'category': 'mantenimiento_optimo',
                'title': '🌱 Mantener Excelentes Condiciones',
                'description': 'Análisis satelital confirma cultivo en condiciones óptimas',
                'actions': [
                    'Continuar programa actual de fertilización',
                    'Mantener cronograma de riego establecido',
                    'Monitoreo preventivo de plagas cada 15 días',
                    'Programar próxima evaluación satelital en 2 semanas'
                ],
                'timeframe': '2 semanas',
                'data_confidence': 'alta_eosda'
            })
        
        # Caso 4: Alta variabilidad requiere uniformización (datos reales)
        if ndvi_std > 0.2:
            recommendations.append({
                'priority': 'medium',
                'category': 'uniformidad_campo',
                'title': '📊 Mejorar Uniformidad del Cultivo',
                'description': f'Datos satelitales muestran variabilidad alta (σ={ndvi_std:.3f})',
                'actions': [
                    'Mapear zonas de variabilidad con GPS',
                    'Calibrar sistema de riego por sectores identificados',
                    'Aplicación variable de fertilizantes según zonas',
                    'Análisis de suelo por sectores problemáticos'
                ],
                'timeframe': '1-2 semanas',
                'data_confidence': 'alta_eosda'
            })
        
        # Caso 5: Condiciones moderadas - optimización basada en datos reales
        elif 0.3 <= ndvi_mean <= 0.6:
            recommendations.append({
                'priority': 'medium',
                'category': 'optimizacion_rendimiento',
                'title': '📈 Oportunidad de Optimización',
                'description': 'Datos satelitales muestran potencial de mejora en desarrollo vegetativo',
                'actions': [
                    'Evaluar programa nutricional con análisis de suelo',
                    'Optimizar frecuencia de riego según datos NDMI',
                    'Monitorear condiciones climáticas próximos 7 días',
                    'Considerar aplicación de bioestimulantes foliares'
                ],
                'timeframe': '1 semana',
                'data_confidence': 'alta_eosda'
            })
        
        # Recomendación especial para cobertura limitada
        if ndvi_count < 5000:
            recommendations.append({
                'priority': 'low',
                'category': 'monitoreo',
                'title': '📡 Mejorar Cobertura de Monitoreo',
                'description': 'Datos limitados por cobertura de nubes o área pequeña',
                'actions': [
                    'Solicitar nueva imagen satelital en días despejados',
                    'Complementar con monitoreo de campo',
                    'Verificar configuración del área de interés'
                ],
                'timeframe': '1 semana',
                'data_confidence': 'media_limitada'
            })
            
        return recommendations
    
    def _get_current_datetime(self):
        """
        Obtiene la fecha y hora actual en formato ISO.
        
        Returns:
            str: Fecha y hora actual
        """
        return datetime.now().isoformat()
        """
        Interpreta los datos científicos y añade contexto agronómico.
        
        Args:
            analytics_data: Datos brutos de EOSDA
            scene_date: Fecha de la escena
            view_id: ID de la vista
            
        Returns:
            dict: Datos interpretados con contexto agronómico
        """
        try:
            interpretation = {
                'raw_data': analytics_data,
                'interpretation': {},
                'alerts': [],
                'recommendations': [],
                'metadata': {
                    'view_id': view_id,
                    'scene_date': scene_date,
                    'analysis_type': 'scientific_eosda',
                    'confidence': 'high',
                    'processed_at': self._get_current_datetime()
                }
            }
            
            # Interpretar NDVI si está disponible
            if 'ndvi' in analytics_data:
                ndvi_data = analytics_data['ndvi']
                interpretation['interpretation']['ndvi'] = self._interpret_ndvi(ndvi_data)
                logger.info(f"[ANALYTICS_INTERPRETATION] NDVI interpretado: mean={ndvi_data.get('mean', 'N/A')}")
                
            # Interpretar NDMI si está disponible
            if 'ndmi' in analytics_data:
                ndmi_data = analytics_data['ndmi']
                interpretation['interpretation']['ndmi'] = self._interpret_ndmi(ndmi_data)
                logger.info(f"[ANALYTICS_INTERPRETATION] NDMI interpretado: mean={ndmi_data.get('mean', 'N/A')}")
                
            # Interpretar EVI si está disponible
            if 'evi' in analytics_data:
                evi_data = analytics_data['evi']
                interpretation['interpretation']['evi'] = self._interpret_evi(evi_data)
                
            # Generar alertas automáticas basadas en datos científicos
            interpretation['alerts'] = self._generate_alerts(analytics_data)
            
            # Generar recomendaciones agronómicas
            interpretation['recommendations'] = self._generate_recommendations(analytics_data, scene_date)
            
            logger.info(f"[ANALYTICS_INTERPRETATION] Interpretación completada - Alertas: {len(interpretation['alerts'])}, Recomendaciones: {len(interpretation['recommendations'])}")
            
            return interpretation
            
        except Exception as e:
            logger.error(f"[ANALYTICS_INTERPRETATION] Error en interpretación: {str(e)}")
            # Retornar datos brutos si falla la interpretación
            return {
                'raw_data': analytics_data,
                'interpretation': {},
                'alerts': [{'type': 'warning', 'title': 'Error en Interpretación', 'message': 'Mostrando datos brutos'}],
                'recommendations': [],
                'metadata': {'view_id': view_id, 'scene_date': scene_date, 'error': str(e)}
            }
    
    def _interpret_ndvi(self, ndvi_data):
        """
        Interpreta datos NDVI científicos con clasificación agronómica.
        
        Args:
            ndvi_data: Diccionario con estadísticas NDVI
            
        Returns:
            dict: Interpretación agronómica del NDVI
        """
        mean = ndvi_data.get('mean', 0)
        std = ndvi_data.get('std', 0)
        min_val = ndvi_data.get('min', 0)
        max_val = ndvi_data.get('max', 0)
        
        # Clasificación científica NDVI basada en estándares agronómicos
        if mean >= 0.8:
            health_status = "🟢 Vegetación excelente"
            description = "Cultivo en condiciones óptimas de crecimiento"
            priority = "low"
        elif mean >= 0.6:
            health_status = "🟢 Vegetación saludable"  
            description = "Cultivo en buen estado de desarrollo"
            priority = "low"
        elif mean >= 0.4:
            health_status = "🟡 Vegetación moderada"
            description = "Cultivo en desarrollo normal, monitorear evolución"
            priority = "medium"
        elif mean >= 0.2:
            health_status = "🟠 Vegetación escasa"
            description = "Posible estrés en el cultivo, requiere atención"
            priority = "medium"
        elif mean >= 0.1:
            health_status = "🔴 Vegetación muy pobre"
            description = "Estrés severo en el cultivo"
            priority = "high"
        else:
            health_status = "🔴 Vegetación crítica"
            description = "Requiere intervención inmediata"
            priority = "critical"
            
        # Evaluar uniformidad del cultivo
        if std <= 0.1:
            uniformity = "🟢 Muy uniforme"
            uniformity_desc = "Excelente uniformidad en el cultivo"
        elif std <= 0.2:
            uniformity = "🟡 Moderadamente uniforme"
            uniformity_desc = "Variabilidad normal en el campo"
        else:
            uniformity = "🔴 Muy desigual"
            uniformity_desc = "Alta variabilidad - revisar riego y fertilización"
            
        # Rango de valores
        value_range = max_val - min_val
        
        return {
            'health_status': health_status,
            'description': description,
            'uniformity': uniformity,
            'uniformity_description': uniformity_desc,
            'priority': priority,
            'metrics': {
                'mean_value': round(mean, 3),
                'variability': round(std, 3),
                'min_value': round(min_val, 3),
                'max_value': round(max_val, 3),
                'range': round(value_range, 3)
            }
        }
    
    def _interpret_ndmi(self, ndmi_data):
        """
        Interpreta datos NDMI científicos (índice de humedad).
        
        Args:
            ndmi_data: Diccionario con estadísticas NDMI
            
        Returns:
            dict: Interpretación agronómica del NDMI
        """
        mean = ndmi_data.get('mean', 0)
        std = ndmi_data.get('std', 0)
        min_val = ndmi_data.get('min', 0)
        max_val = ndmi_data.get('max', 0)
        
        # Clasificación científica NDMI (Normalized Difference Moisture Index)
        if mean >= 0.6:
            moisture_status = "💧 Muy húmedo"
            description = "Excelente contenido de humedad en la vegetación"
            priority = "low"
        elif mean >= 0.4:
            moisture_status = "💙 Húmedo"
            description = "Buen nivel de humedad en el cultivo"
            priority = "low"
        elif mean >= 0.2:
            moisture_status = "🟡 Normal"
            description = "Humedad moderada - monitorear tendencias"
            priority = "medium"
        elif mean >= 0.0:
            moisture_status = "🟠 Seco"
            description = "Posible estrés hídrico - considerar riego"
            priority = "medium"
        elif mean >= -0.2:
            moisture_status = "🔴 Muy seco"
            description = "Estrés hídrico moderado a severo"
            priority = "high"
        else:
            moisture_status = "🔴 Extremadamente seco"
            description = "Estrés hídrico crítico - riego urgente"
            priority = "critical"
            
        return {
            'moisture_status': moisture_status,
            'description': description,
            'priority': priority,
            'metrics': {
                'mean_value': round(mean, 3),
                'variability': round(std, 3),
                'min_value': round(min_val, 3),
                'max_value': round(max_val, 3),
                'range': round(max_val - min_val, 3)
            }
        }
    
    def _interpret_evi(self, evi_data):
        """
        Interpreta datos EVI científicos (Enhanced Vegetation Index).
        
        Args:
            evi_data: Diccionario con estadísticas EVI
            
        Returns:
            dict: Interpretación agronómica del EVI
        """
        mean = evi_data.get('mean', 0)
        
        if mean >= 0.5:
            status = "🟢 EVI Excelente"
            description = "Vegetación muy densa y saludable"
        elif mean >= 0.3:
            status = "🟡 EVI Bueno"
            description = "Vegetación moderadamente densa"
        else:
            status = "🔴 EVI Bajo"
            description = "Vegetación escasa o estresada"
            
        return {
            'status': status,
            'description': description,
            'mean_value': round(mean, 3)
        }
    
    def _generate_alerts(self, analytics_data):
        """
        Genera alertas automáticas basadas en umbrales científicos.
        
        Args:
            analytics_data: Datos de analytics de EOSDA
            
        Returns:
            list: Lista de alertas con tipo, título, mensaje y acción
        """
        alerts = []
        
        # Alerta NDVI crítico
        if 'ndvi' in analytics_data:
            ndvi_mean = analytics_data['ndvi'].get('mean', 0)
            ndvi_std = analytics_data['ndvi'].get('std', 0)
            
            if ndvi_mean < 0.2:
                alerts.append({
                    'type': 'critical',
                    'title': 'NDVI Crítico Detectado',
                    'message': f'NDVI promedio de {ndvi_mean:.3f} indica estrés severo en el cultivo',
                    'action': 'Revisar inmediatamente: nutrición, riego, plagas y enfermedades',
                    'priority': 'urgent'
                })
            elif ndvi_mean < 0.4:
                alerts.append({
                    'type': 'warning',
                    'title': 'NDVI Bajo Detectado',
                    'message': f'NDVI promedio de {ndvi_mean:.3f} sugiere posible estrés en el cultivo',
                    'action': 'Evaluar condiciones de nutrición y riego',
                    'priority': 'high'
                })
                
            # Alerta por alta variabilidad
            if ndvi_std > 0.25:
                alerts.append({
                    'type': 'info',
                    'title': 'Alta Variabilidad en el Cultivo',
                    'message': f'Desviación estándar de {ndvi_std:.3f} indica cultivo muy desigual',
                    'action': 'Revisar uniformidad de riego, fertilización y condiciones del suelo',
                    'priority': 'medium'
                })
        
        # Alerta NDMI crítico (estrés hídrico)
        if 'ndmi' in analytics_data:
            ndmi_mean = analytics_data['ndmi'].get('mean', 0)
            
            if ndmi_mean < -0.1:
                alerts.append({
                    'type': 'critical',
                    'title': 'Estrés Hídrico Severo',
                    'message': f'NDMI promedio de {ndmi_mean:.3f} indica estrés hídrico crítico',
                    'action': 'Implementar riego de emergencia inmediatamente',
                    'priority': 'urgent'
                })
            elif ndmi_mean < 0.1:
                alerts.append({
                    'type': 'warning',
                    'title': 'Estrés Hídrico Detectado',
                    'message': f'NDMI promedio de {ndmi_mean:.3f} sugiere déficit hídrico',
                    'action': 'Evaluar necesidades de riego y programar aplicación',
                    'priority': 'high'
                })
                
        return alerts
    
    def _generate_recommendations(self, analytics_data, scene_date):
        """
        Genera recomendaciones agronómicas automáticas basadas en análisis científico.
        
        Args:
            analytics_data: Datos de analytics de EOSDA
            scene_date: Fecha de la escena para contexto temporal
            
        Returns:
            list: Lista de recomendaciones con prioridad, categoría y acciones
        """
        recommendations = []
        
        # Obtener valores principales
        ndvi_mean = analytics_data.get('ndvi', {}).get('mean', 0)
        ndmi_mean = analytics_data.get('ndmi', {}).get('mean', 0)
        ndvi_std = analytics_data.get('ndvi', {}).get('std', 0)
        
        # Análisis combinado NDVI + NDMI para recomendaciones integrales
        
        # Caso 1: Estrés hídrico con vegetación comprometida
        if ndvi_mean < 0.4 and ndmi_mean < 0.2:
            recommendations.append({
                'priority': 'urgent',
                'category': 'riego_nutricion',
                'title': 'Intervención Urgente Requerida',
                'description': 'Combinar riego inmediato con evaluación nutricional del cultivo',
                'actions': [
                    'Aplicar riego de emergencia',
                    'Evaluar sistema radicular',
                    'Análisis foliar para deficiencias nutricionales',
                    'Monitorear recuperación en 3-5 días'
                ]
            })
        
        # Caso 2: Vegetación buena pero con déficit hídrico
        elif ndvi_mean > 0.6 and ndmi_mean < 0.3:
            recommendations.append({
                'priority': 'high',
                'category': 'riego',
                'title': 'Riego Preventivo Recomendado',
                'description': 'Mantener riego para preservar la excelente condición del cultivo',
                'actions': [
                    'Implementar riego programado',
                    'Monitorear humedad del suelo',
                    'Evaluar eficiencia del sistema de riego'
                ]
            })
        
        # Caso 3: Vegetación excelente
        elif ndvi_mean > 0.7 and ndmi_mean > 0.4:
            recommendations.append({
                'priority': 'low',
                'category': 'mantenimiento',
                'title': 'Continuar Manejo Actual',
                'description': 'El cultivo está en excelentes condiciones - mantener prácticas actuales',
                'actions': [
                    'Continuar programa de fertilización',
                    'Mantener cronograma de riego',
                    'Monitoreo preventivo de plagas',
                    'Planificar próxima evaluación'
                ]
            })
        
        # Caso 4: Alta variabilidad requiere uniformización
        if ndvi_std > 0.2:
            recommendations.append({
                'priority': 'medium',
                'category': 'uniformidad',
                'title': 'Mejorar Uniformidad del Cultivo',
                'description': 'Reducir variabilidad para optimizar rendimiento',
                'actions': [
                    'Calibrar sistema de riego por zonas',
                    'Aplicación variable de fertilizantes',
                    'Análisis de suelo por sectores',
                    'Evaluar topografía y drenaje'
                ]
            })
        
        # Caso 5: Condiciones moderadas - optimización
        elif 0.4 <= ndvi_mean <= 0.6:
            recommendations.append({
                'priority': 'medium',
                'category': 'optimizacion',
                'title': 'Oportunidad de Optimización',
                'description': 'Condiciones moderadas con potencial de mejora',
                'actions': [
                    'Evaluar programa nutricional',
                    'Optimizar frecuencia de riego',
                    'Monitorear condiciones climáticas',
                    'Considerar bioestimulantes'
                ]
            })
            
        return recommendations
    
    def _get_current_datetime(self):
        """
        Obtiene la fecha y hora actual en formato ISO.
        
        Returns:
            str: Fecha y hora actual
        """
        from datetime import datetime
        return datetime.now().isoformat()
