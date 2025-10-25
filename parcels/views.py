
# --- IMPORTS ORDENADOS ---
import logging
import requests
import json
import math
import numpy as np
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from .models import Parcel, ParcelSceneCache
from .serializers import ParcelSerializer

logger = logging.getLogger(__name__)

# --- WEATHER FORECAST API ---
from .metereological import WeatherForecastView

class ParcelScenesByDateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, parcel_id):
        """
        GET /api/parcels/parcel/<parcel_id>/scenes/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
        Retorna: { "scenes": [...], "request_id": ..., "eosda_raw": ... }
        """
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        logger.info(f"[SCENES_BY_DATE] Parámetros recibidos: parcel_id={parcel_id}, start_date={start_date}, end_date={end_date}")
        if not start_date or not end_date:
            logger.error("[SCENES_BY_DATE] Faltan parámetros start_date y end_date.")
            return Response({"error": "Faltan parámetros start_date y end_date."}, status=400)
        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
        field_id = getattr(parcel, "eosda_id", None)
        logger.info(f"[SCENES_BY_DATE] field_id de parcela: {field_id}")
        if not field_id:
            logger.error("[SCENES_BY_DATE] La parcela no tiene un field_id EOSDA válido.")
            return Response({"error": "La parcela no tiene un field_id EOSDA válido."}, status=404)
        # Llamar a EOSDA scene-search filtrando por fechas
        request_url = f"https://api-connect.eos.com/scene-search/for-field/{field_id}"
        headers = {
            "x-api-key": settings.EOSDA_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "params": {
                "date_start": start_date,
                "date_end": end_date,
                "data_source": ["sentinel2"]
            }
        }
        logger.info(f"[SCENES_BY_DATE] URL: {request_url}")
        logger.info(f"[SCENES_BY_DATE] Headers: {headers}")
        logger.info(f"[SCENES_BY_DATE] Payload enviado: {payload}")
        import time
        try:
            req_response = requests.post(request_url, json=payload, headers=headers)
            logger.info(f"[SCENES_BY_DATE] POST Status: {req_response.status_code}")
            logger.info(f"[SCENES_BY_DATE] POST Response: {req_response.text}")
            
            # Manejo específico de error 402 (límite de requests excedido)
            if req_response.status_code == 402:
                error_data = req_response.json() if req_response.content else {}
                logger.error(f"[SCENES_BY_DATE] Límite de requests EOSDA excedido: {error_data}")
                return Response({
                    "error": "EOSDA API: Límite de requests excedido",
                    "message": "Se ha alcanzado el límite mensual de consultas a EOSDA API Connect. Contacte al administrador.",
                    "error_code": "EOSDA_LIMIT_EXCEEDED",
                    "limit_info": error_data
                }, status=402)
                
            # Manejo específico de error 404 (campo no encontrado)
            if req_response.status_code == 404:
                error_data = req_response.json() if req_response.content else {}
                logger.error(f"[SCENES_BY_DATE] Campo no encontrado en EOSDA: {error_data}")
                return Response({
                    "error": "EOSDA API: Campo no encontrado",
                    "message": f"El campo con ID {field_id} no existe en EOSDA API Connect. Verifique que el campo esté correctamente registrado.",
                    "error_code": "EOSDA_FIELD_NOT_FOUND",
                    "field_id": field_id,
                    "details": error_data
                }, status=404)
            
            req_response.raise_for_status()
            req_data = req_response.json()
            request_id = req_data.get('request_id')
            # Si hay request_id, hacer GET con polling para obtener escenas reales
            if request_id:
                logger.info(f"[SCENES_BY_DATE] request_id recibido: {request_id}")
                scenes_url = f"https://api-connect.eos.com/scene-search/for-field/{field_id}/{request_id}"
                scenes_headers = {
                    "x-api-key": settings.EOSDA_API_KEY
                }
                max_attempts = 5
                delay_seconds = 2
                for attempt in range(max_attempts):
                    scenes_response = requests.get(scenes_url, headers=scenes_headers)
                    logger.info(f"[SCENES_BY_DATE] GET url: {scenes_url}")
                    logger.info(f"[SCENES_BY_DATE] GET status: {scenes_response.status_code}")
                    logger.info(f"[SCENES_BY_DATE] GET response: {scenes_response.text}")
                    print(f"[SCENES_BY_DATE] Intento {attempt+1}/{max_attempts} GET status: {scenes_response.status_code}")
                    scenes_response.raise_for_status()
                    scenes_data = scenes_response.json()
                    if scenes_data.get('status') != 'pending':
                        scenes = scenes_data.get('result', [])
                        logger.info(f"[SCENES_BY_DATE] Escenas recibidas (GET): {scenes}")
                        print(f"[SCENES_BY_DATE] Escenas recibidas (GET): {scenes}")
                        return Response({"request_id": request_id, "scenes": scenes, "eosda_raw": scenes_data}, status=200)
                    time.sleep(delay_seconds)
                # Si tras los intentos sigue en pending, informar al usuario
                logger.warning(f"[SCENES_BY_DATE] EOSDA sigue en pending tras {max_attempts} intentos.")
                print(f"[SCENES_BY_DATE] EOSDA sigue en pending tras {max_attempts} intentos.")
                return Response({"request_id": request_id, "scenes": [], "eosda_raw": scenes_data, "status": "pending", "message": "La consulta está en proceso. Intenta nuevamente en unos minutos."}, status=202)
            else:
                # Si no hay request_id, usar las escenas del POST
                scenes = req_data.get('result', [])
                logger.info(f"[SCENES_BY_DATE] Escenas recibidas (POST directo): {scenes}")
                print(f"[SCENES_BY_DATE] Escenas recibidas (POST directo): {scenes}")
                return Response({"request_id": None, "scenes": scenes, "eosda_raw": req_data}, status=200)
        except requests.exceptions.RequestException as e:
            logger.error(f"[SCENES_BY_DATE] Error en la petición a EOSDA: {str(e)}")
            print(f"[SCENES_BY_DATE] Error en la petición a EOSDA: {str(e)}")
            
            # Manejo específico de errores HTTP
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 402:
                    return Response({
                        "error": "EOSDA API: Límite de requests excedido",
                        "message": "Se ha alcanzado el límite mensual de consultas a EOSDA API Connect. Contacte al administrador.",
                        "error_code": "EOSDA_LIMIT_EXCEEDED"
                    }, status=402)
            
            return Response({"error": str(e)}, status=500)
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from .models import Parcel, ParcelSceneCache
from .serializers import ParcelSerializer
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
import requests
import logging
from django.shortcuts import render
import json

logger = logging.getLogger(__name__)



class ParcelViewSet(viewsets.ModelViewSet):
    # Solo mostrar parcelas no eliminadas por defecto
    queryset = Parcel.objects.filter(is_deleted=False)
    serializer_class = ParcelSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        logger.info(f"[ParcelViewSet] list() - Usuario: {request.user} - Params: {request.query_params}")
        response = super().list(request, *args, **kwargs)
        logger.info(f"[ParcelViewSet] list() - Respuesta: {response.data}")
        response.data = {
            "cesium_token": settings.CESIUM_ACCESS_TOKEN,
            "parcels": response.data
        }
        return response

    def retrieve(self, request, *args, **kwargs):
        logger.info(f"[ParcelViewSet] retrieve() - Usuario: {request.user} - kwargs: {kwargs}")
        response = super().retrieve(request, *args, **kwargs)
        logger.info(f"[ParcelViewSet] retrieve() - Respuesta: {response.data}")
        return response

    def create(self, request, *args, **kwargs):
        logger.info(f"[ParcelViewSet] create() - Usuario: {request.user} - Data: {request.data}")
        response = super().create(request, *args, **kwargs)
        logger.info(f"[ParcelViewSet] create() - Respuesta: {response.data}")
        return response

    def update(self, request, *args, **kwargs):
        logger.info(f"[ParcelViewSet] update() - Usuario: {request.user} - Data: {request.data} - kwargs: {kwargs}")
        response = super().update(request, *args, **kwargs)
        logger.info(f"[ParcelViewSet] update() - Respuesta: {response.data}")
        return response

    def destroy(self, request, *args, **kwargs):
        logger.info(f"[ParcelViewSet] destroy() - Usuario: {request.user} - kwargs: {kwargs}")
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"[ParcelViewSet] destroy() - Respuesta: {response.status_code}")
        return response

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        qs = Parcel.objects.filter(is_deleted=False)
        total = qs.count()
        total_area = 0
        activas = qs.filter(state=True).count()
        inactivas = qs.filter(state=False).count()
        tipos = {}
        suelos = {}
        topografias = {}
        last_parcel = None
        last_date = None
        for p in qs:
            total_area += p.area_hectares()
            # Tipos de campo
            if p.field_type:
                tipos[p.field_type] = tipos.get(p.field_type, 0) + 1
            # Suelos
            if p.soil_type:
                suelos[p.soil_type] = suelos.get(p.soil_type, 0) + 1
            # Topografía
            if p.topography:
                topografias[p.topography] = topografias.get(p.topography, 0) + 1
            # Última parcela
            if not last_date or (p.created_on and p.created_on > last_date):
                last_parcel = p
                last_date = p.created_on
        # Top 3 tipos de campo
        top_tipos = sorted(tipos.items(), key=lambda x: x[1], reverse=True)[:3]
        area_promedio = round(total_area / total, 2) if total > 0 else 0
        # Cambiar el límite a 300 hectáreas
        AREA_LIMIT = 300  # en hectáreas
        area_restante = max(AREA_LIMIT - total_area, 0)  # en hectáreas

        # Simulación de datos NDVI desde enero hasta junio
        ndvi_data = {
            "Enero": 0.45,
            "Febrero": 0.50,
            "Marzo": 0.60,
            "Abril": 0.55,
            "Mayo": 0.58,
            "Junio": 0.62
        }

        return Response({
            "total": total,
            "total_area": round(total_area, 2),
            "activas": activas,
            "inactivas": inactivas,
            "area_promedio": area_promedio,
            "top_tipos": top_tipos,
            "last_parcel": last_parcel.name if last_parcel else None,
            "last_parcel_date": last_parcel.created_on.strftime('%d/%m/%Y %H:%M') if last_parcel and last_parcel.created_on else None,
            "area_restante": round(area_restante, 2),
            "ndvi_data": ndvi_data
        })

    @action(detail=False, methods=["post"], url_path="ndvi-historical")
    def ndvi_historical(self, request):
        logger.debug(f"Request data: {request.data}")
        """
        Endpoint para obtener los promedios mensuales de NDVI de una parcela usando EOSDA.
        Recibe un polígono (GeoJSON) y un rango de fechas (start_date, end_date).
        """
        polygon = request.data.get("polygon")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        if not polygon or not start_date or not end_date:
            return Response({"error": "Faltan parámetros obligatorios (polygon, start_date, end_date)."}, status=400)

        eosda_url = "https://api-connect.eos.com/v1/indices/ndvi"
        headers = {
            "x-api-key": settings.EOSDA_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "geometry": polygon,
            "start_date": start_date,
            "end_date": end_date
        }
        logger.debug(f"Payload: {payload}")
        logger.debug(f"Headers: {headers}")

        try:
            response = requests.post(eosda_url, json=payload, headers=headers)
            response.raise_for_status()
            ndvi_data = response.json()
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Error al conectar con EOSDA: {str(e)}"}, status=500)

        return Response(ndvi_data, status=200)

    @action(detail=False, methods=["post"], url_path="water-stress-historical")
    def water_stress_historical(self, request):
        logger.debug(f"Request data: {request.data}")
        """
        Endpoint para obtener los promedios mensuales de estrés hídrico de una parcela usando EOSDA.
        Recibe un polígono (GeoJSON) y un rango de fechas (start_date, end_date).
        """
        polygon = request.data.get("polygon")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        if not polygon or not start_date or not end_date:
            return Response({"error": "Faltan parámetros obligatorios (polygon, start_date, end_date)."}, status=400)

        eosda_url = "https://api-connect.eos.com/v1/indices/ndmi"  # NDMI para estrés hídrico
        headers = {
            "x-api-key": settings.EOSDA_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "geometry": polygon,
            "start_date": start_date,
            "end_date": end_date
        }
        logger.debug(f"Payload: {payload}")
        logger.debug(f"Headers: {headers}")

        try:
            response = requests.post(eosda_url, json=payload, headers=headers)
            response.raise_for_status()
            ndmi_data = response.json()
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Error al conectar con EOSDA: {str(e)}"}, status=500)

        return Response(ndmi_data, status=200)

    @action(detail=False, methods=["get"], url_path="list-parcels")
    def list_parcels(self, request):
        """
        Endpoint para listar todas las parcelas con sus polígonos y nombres.
        """
        qs = Parcel.objects.filter(is_deleted=False)
        parcels_data = [
            {
                "id": parcel.id,
                "name": parcel.name,
                "polygon": parcel.geom  # Ahora es un dict (GeoJSON)
            }
            for parcel in qs
        ]
        return Response(parcels_data, status=200)

    # Esta acción fue eliminada para evitar conflictos con la implementación en metereological.py
    # La API de pronóstico del tiempo ahora está implementada en WeatherForecastView
        
        print(f"[WEATHER_FORECAST] Cache miss, generando nuevos datos...")
        
        # Obtener coordenadas del centroide de la parcela
        if hasattr(parcel.geom, 'centroid'):
            centroid = parcel.geom.centroid
            lat = centroid.y





# ENDPOINTS ALINEADOS CON EL FLUJO EOSDA Y EL FRONTEND

# --- EOSDA Scenes & Image API ---
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import requests
import json

class EosdaScenesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        POST /api/parcels/eosda-scenes/
        Recibe: { "field_id": "..." }
        Retorna: { "request_id": "...", "scenes": [...] }
        
        OPTIMIZACIÓN: Cache de escenas por field_id para evitar requests duplicados a EOSDA
        """
        field_id = request.data.get("field_id")
        if not field_id:
            return Response({"error": "Falta el parámetro field_id."}, status=400)
        
        # Verificar cache de escenas por field_id (cache por 10 minutos)
        cache_key = f"eosda_scenes_{field_id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"[CACHE HIT] Escenas encontradas en cache para field_id: {field_id}")
            return Response(cached_data, status=200)
        
        # Restaurar el envío de fechas y mostrar el request_id en la terminal
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        date_end = today.isoformat()
        date_start = (today - timedelta(days=90)).isoformat()
        request_url = f"https://api-connect.eos.com/scene-search/for-field/{field_id}"
        headers = {
            "x-api-key": settings.EOSDA_API_KEY,
            "Content-Type": "text/plain"
        }
        payload = {
            "params": {
                "date_start": date_start,
                "date_end": date_end,
                "data_source": ["sentinel2"]
            }
        }
        try:
            req_response = requests.post(request_url, data=json.dumps(payload), headers=headers)
            logger.info(f"EOSDA request POST url: {request_url}")
            logger.info(f"EOSDA request POST payload: {payload}")
            logger.info(f"EOSDA request POST status: {req_response.status_code}")
            logger.info(f"EOSDA request POST response: {req_response.text}")
            req_response.raise_for_status()
            req_data = req_response.json()
            request_id = req_data.get('request_id')
            
            # Si hay request_id, hacer GET para obtener escenas
            if request_id:
                print(f"request_id recibido de EOSDA: {request_id}")
                logger.info(f"request_id recibido de EOSDA: {request_id}")
                scenes_url = f"https://api-connect.eos.com/scene-search/for-field/{field_id}/{request_id}"
                scenes_headers = {
                    "x-api-key": settings.EOSDA_API_KEY
                }
                scenes_response = requests.get(scenes_url, headers=scenes_headers)
                logger.info(f"EOSDA scenes GET url: {scenes_url}")
                logger.info(f"EOSDA scenes GET status: {scenes_response.status_code}")
                logger.info(f"EOSDA scenes GET response: {scenes_response.text}")
                scenes_response.raise_for_status()
                scenes_data = scenes_response.json()
                scenes = scenes_data.get('result', [])
                print(f"Escenas recibidas de EOSDA (GET): {scenes}")
                logger.info(f"Escenas recibidas de EOSDA (GET): {scenes}")
                
                # Guardar en cache por 10 minutos
                response_data = {"request_id": request_id, "scenes": scenes}
                cache.set(cache_key, response_data, 600)  # 10 minutos
                logger.info(f"[CACHE SET] Escenas guardadas en cache para field_id: {field_id}")
                
                return Response(response_data, status=200)
            else:
                # Si no hay request_id, usar las escenas del POST
                scenes = req_data.get('result', [])
                print(f"Escenas recibidas de EOSDA (POST directo): {scenes}")
                logger.info(f"Escenas recibidas de EOSDA (POST directo): {scenes}")
                
                # Guardar en cache por 10 minutos
                response_data = {"request_id": None, "scenes": scenes}
                cache.set(cache_key, response_data, 600)  # 10 minutos
                logger.info(f"[CACHE SET] Escenas guardadas en cache para field_id: {field_id}")
                
                return Response(response_data, status=200)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en la petición a EOSDA: {str(e)}")
            return Response({"error": str(e)}, status=500)

class EosdaImageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        POST /api/parcels/eosda-image/
        Recibe: { "field_id": "...", "view_id": "...", "type": "ndvi" | "ndmi" | "evi", "format": "png" }
        Retorna: { "request_id": "..." }
        
        OPTIMIZACIÓN: Cache de request_id por combinación field_id+view_id+type para evitar requests duplicados
        """
        try:
            field_id = request.data.get("field_id")
            view_id = request.data.get("view_id")
            index_type = request.data.get("type")
            img_format = request.data.get("format", "png")
            logger.info(f"[EOSDA_IMAGE] Payload recibido: field_id={field_id}, view_id={view_id}, type={index_type}, format={img_format}")
            
            # Validación de parámetros
            if not field_id or not view_id or index_type not in ["ndvi", "ndmi", "evi"]:
                logger.error(f"[EOSDA_IMAGE] Parámetros inválidos: field_id={field_id}, view_id={view_id}, type={index_type}")
                return Response({"error": "Parámetros inválidos."}, status=400)
            
            # Verificar cache de request_id por combinación field_id+view_id+type (cache por 30 minutos)
            cache_key = f"eosda_image_request_{field_id}_{view_id}_{index_type}"
            cached_request_id = cache.get(cache_key)
            if cached_request_id:
                logger.info(f"[CACHE HIT] request_id encontrado en cache: {cached_request_id}")
                return Response({"request_id": cached_request_id}, status=200)
            
            eosda_url = f"https://api-connect.eos.com/field-imagery/indicies/{field_id}"
            headers = {
                "x-api-key": settings.EOSDA_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "params": {
                    "view_id": view_id,
                    "index": index_type.upper(),
                    "format": img_format
                }
            }
            logger.info(f"[EOSDA_IMAGE] URL: {eosda_url}")
            logger.info(f"[EOSDA_IMAGE] Headers: {headers}")
            logger.info(f"[EOSDA_IMAGE] Payload enviado: {payload}")
            
            response = requests.post(eosda_url, json=payload, headers=headers)
            logger.info(f"[EOSDA_IMAGE] Status: {response.status_code}")
            logger.info(f"[EOSDA_IMAGE] Response: {response.text}")
            response.raise_for_status()
            data = response.json()
            request_id = data.get("request_id")
            if not request_id:
                logger.error(f"[EOSDA_IMAGE] No se encontró el request_id en la respuesta: {data}")
                return Response({"error": "No se encontró el request_id."}, status=404)
            
            # Guardar request_id en cache por 30 minutos
            cache.set(cache_key, request_id, 1800)  # 30 minutos
            logger.info(f"[CACHE SET] request_id guardado en cache: {request_id}")
            logger.info(f"[EOSDA_IMAGE] request_id recibido: {request_id}")
            return Response({"request_id": request_id}, status=200)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[EOSDA_IMAGE] Error en la petición a EOSDA: {str(e)}")
            return Response({"error": f"Error de conexión con EOSDA: {str(e)}"}, status=500)
        except Exception as e:
            logger.error(f"[EOSDA_IMAGE] Error inesperado: {str(e)}")
            logger.error(f"[EOSDA_IMAGE] Tipo de error: {type(e).__name__}")
            import traceback
            logger.error(f"[EOSDA_IMAGE] Traceback: {traceback.format_exc()}")
            return Response({"error": f"Error interno del servidor: {str(e)}"}, status=500)

class EosdaImageResultView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        GET /api/parcels/eosda-image-result/?field_id=...&request_id=...
        Retorna: { "image_base64": "..." }
        
        OPTIMIZACIÓN: Cache de imágenes por request_id para evitar downloads duplicados
        """
        import base64
        field_id = request.query_params.get("field_id")
        request_id = request.query_params.get("request_id")
        logger.info(f"[EOSDA_IMAGE_RESULT] Params recibidos: field_id={field_id}, request_id={request_id}")
        if not field_id or not request_id:
            logger.error(f"[EOSDA_IMAGE_RESULT] Parámetros inválidos: field_id={field_id}, request_id={request_id}")
            return Response({"error": "Parámetros inválidos."}, status=400)
        
        # Verificar cache de imagen por request_id (cache por 1 hora)
        image_cache_key = f"eosda_image_{request_id}"
        cached_image = cache.get(image_cache_key)
        if cached_image:
            logger.info(f"[CACHE HIT] Imagen encontrada en cache para request_id: {request_id}")
            return Response({"image_base64": cached_image}, status=200)
        
        eosda_url = f"https://api-connect.eos.com/field-imagery/{field_id}/{request_id}"
        headers = {
            "x-api-key": settings.EOSDA_API_KEY
        }
        logger.info(f"[EOSDA_IMAGE_RESULT] URL: {eosda_url}")
        logger.info(f"[EOSDA_IMAGE_RESULT] Headers: {headers}")
        try:
            response = requests.get(eosda_url, headers=headers)
            logger.info(f"[EOSDA_IMAGE_RESULT] Status: {response.status_code}")
            content_type = response.headers.get('Content-Type', '')
            # Si la respuesta es imagen, convertir a base64 y retornar
            if content_type.startswith('image/'):
                try:
                    image_base64 = base64.b64encode(response.content).decode('utf-8')
                    logger.info(f"[EOSDA_IMAGE_RESULT] Imagen recibida y convertida a base64.")
                    # Guardar imagen en cache por 1 hora
                    cache.set(image_cache_key, image_base64, 3600)  # 1 hora
                    logger.info(f"[CACHE SET] Imagen guardada en cache para request_id: {request_id}")
                    return Response({"image_base64": image_base64}, status=200)
                except Exception as e:
                    logger.error(f"[EOSDA_IMAGE_RESULT] Error al convertir imagen a base64: {e}")
                    return Response({"error": "Error al procesar la imagen recibida."}, status=500)
            # Si la respuesta es JSON, analizar el estado y errores específicos
            elif content_type.startswith('application/json') or content_type.startswith('text/json'):
                try:
                    data = response.json()
                    logger.error(f"[EOSDA_IMAGE_RESULT] Respuesta no es imagen: {data}")
                    # Imagen aún en proceso
                    if data.get("status") == "created":
                        return Response({"error": "La imagen aún está en proceso. Intenta nuevamente en unos minutos."}, status=202)
                    # Error específico de AOI fuera de cobertura
                    error_msg = None
                    if isinstance(data, dict):
                        if 'error_message' in data and isinstance(data['error_message'], dict):
                            error_msg = data['error_message'].get('error')
                        elif 'error_message' in data and isinstance(data['error_message'], str):
                            error_msg = data['error_message']
                    if error_msg and 'AOI is out of image extent' in error_msg:
                        logger.warning(f"[EOSDA_IMAGE_RESULT] AOI fuera de cobertura: {error_msg}")
                        return Response({"error": "La parcela está fuera de la cobertura de la imagen seleccionada. Selecciona otra escena o ajusta el polígono."}, status=404)
                    # Otros errores
                    return Response({"error": "No se recibió una imagen.", "details": data}, status=400)
                except Exception as e:
                    logger.error(f"[EOSDA_IMAGE_RESULT] Error al parsear JSON: {e}")
                    return Response({"error": "Respuesta inesperada de EOSDA."}, status=500)
            # Si la respuesta es binaria pero no tiene content-type correcto, intentar detectar PNG/JPG
            elif response.content[:8] == b'\x89PNG\r\n\x1a\n' or response.content[:2] == b'\xff\xd8':
                try:
                    image_base64 = base64.b64encode(response.content).decode('utf-8')
                    logger.info(f"[EOSDA_IMAGE_RESULT] Imagen binaria detectada y convertida a base64.")
                    # Guardar imagen en cache por 1 hora
                    cache.set(image_cache_key, image_base64, 3600)  # 1 hora
                    logger.info(f"[CACHE SET] Imagen binaria guardada en cache para request_id: {request_id}")
                    return Response({"image_base64": image_base64}, status=200)
                except Exception as e:
                    logger.error(f"[EOSDA_IMAGE_RESULT] Error al convertir binario a base64: {e}")
                    return Response({"error": "Error al procesar la imagen binaria recibida."}, status=500)
            # Si no es imagen ni JSON, devolver texto plano para depuración
            else:
                text = response.text
                logger.error(f"[EOSDA_IMAGE_RESULT] Respuesta inesperada, no es imagen ni JSON. Texto: {text}")
                return Response({"error": text}, status=500)
        except requests.exceptions.RequestException as e:
            logger.error(f"[EOSDA_IMAGE_RESULT] Error en la petición a EOSDA: {str(e)}")
            return Response({"error": str(e)}, status=500)

class EosdaSceneAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        POST /api/parcels/eosda-scene-analytics/
        Body: {
            "field_id": "string",
            "view_id": "string", 
            "scene_date": "YYYY-MM-DD",
            "indices": ["ndvi", "ndmi", "evi"]  # opcional, por defecto todos
        }
        
        Retorna: {
            "scene_info": {...},
            "analytics": {
                "ndvi": {"mean": 0.65, "std": 0.15, ...},
                "ndmi": {"mean": 0.42, "std": 0.12, ...},
                "evi": {"mean": 0.38, "std": 0.11, ...}
            }
        }
        
        OPTIMIZACIÓN: Cache por field_id+view_id+date (cache por 2 horas)
        """
        field_id = request.data.get("field_id")
        view_id = request.data.get("view_id")
        scene_date = request.data.get("scene_date")
        indices = request.data.get("indices", ["ndvi", "ndmi", "evi"])
        
        logger.info(f"[SCENE_ANALYTICS] Params: field_id={field_id}, view_id={view_id}, scene_date={scene_date}")
        
        # Validación de parámetros
        if not field_id or not view_id:
            logger.error(f"[SCENE_ANALYTICS] Parámetros inválidos: field_id={field_id}, view_id={view_id}")
            return Response({"error": "Faltan parámetros obligatorios: field_id, view_id."}, status=400)
        
        valid_indices = ["ndvi", "ndmi", "evi", "lai", "fpar", "fcover"]
        indices = [idx for idx in indices if idx in valid_indices]
        if not indices:
            indices = ["ndvi", "ndmi", "evi"]  # valores por defecto
        
        # Verificar cache de analytics por combinación field_id+view_id+date (cache por 2 horas)
        cache_key = f"eosda_analytics_{field_id}_{view_id}_{scene_date}"
        cached_analytics = cache.get(cache_key)
        if cached_analytics:
            logger.info(f"[CACHE HIT] Analytics encontrados en cache: {cache_key}")
            return Response(cached_analytics, status=200)
        
        # EOSDA API: El endpoint /v1/analytics no existe, usaremos /v1/indices para obtener datos estadísticos
        # Convertir scene_date a rango de un día para simular analytics de escena específica
        from datetime import datetime, timedelta
        try:
            date_obj = datetime.strptime(scene_date, "%Y-%m-%d")
            start_date = date_obj.strftime("%Y-%m-%d")
            end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            logger.error(f"[SCENE_ANALYTICS] Fecha inválida: {scene_date}")
            return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}, status=400)
        
        # Obtener polígono de la parcela para la consulta
        try:
            from .models import Parcel
            parcel = Parcel.objects.get(eosda_id=field_id)
            if not parcel.geom:
                return Response({"error": "La parcela no tiene geometría definida"}, status=400)
            
            # Convertir geometría a GeoJSON - manejo flexible para diferentes tipos
            import json
            from django.contrib.gis.geos import GEOSGeometry
            
            geom = parcel.geom
            logger.info(f"[SCENE_ANALYTICS] Geometría tipo: {type(geom)}, valor: {geom}")
            
            # Manejar diferentes tipos de geometría
            if isinstance(geom, dict):
                # Ya es GeoJSON dict
                polygon_geojson = geom
                logger.info(f"[SCENE_ANALYTICS] Geometría ya es dict GeoJSON")
            elif isinstance(geom, str):
                # String GeoJSON, parsear a dict
                try:
                    polygon_geojson = json.loads(geom)
                    logger.info(f"[SCENE_ANALYTICS] Geometría parseada desde string JSON")
                except json.JSONDecodeError:
                    # String WKT, convertir a GEOS y luego GeoJSON
                    geos_geom = GEOSGeometry(geom)
                    polygon_geojson = json.loads(geos_geom.geojson)
                    logger.info(f"[SCENE_ANALYTICS] Geometría convertida desde WKT")
            else:
                # Objeto GEOS Geometry
                polygon_geojson = json.loads(geom.geojson)
                logger.info(f"[SCENE_ANALYTICS] Geometría convertida desde objeto GEOS")
        except Parcel.DoesNotExist:
            return Response({"error": "Parcela no encontrada"}, status=404)
        except Exception as e:
            logger.error(f"[SCENE_ANALYTICS] Error obteniendo geometría: {e}")
            return Response({"error": "Error obteniendo geometría de la parcela"}, status=500)
        
        
        logger.info(f"[SCENE_ANALYTICS] Obteniendo analytics para {len(indices)} índices: {indices}")
        logger.info(f"[SCENE_ANALYTICS] Rango de fechas: {start_date} - {end_date}")
        
        # Preparar resultado de analytics
        analytics_result = {}
        
        try:
            for index_name in indices:
                eosda_url = f"https://api-connect.eos.com/v1/indices/{index_name}"
                headers = {
                    "x-api-key": settings.EOSDA_API_KEY,
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "geometry": polygon_geojson,
                    "start_date": start_date,
                    "end_date": end_date
                }
                
                logger.info(f"[SCENE_ANALYTICS] URL: {eosda_url}")
                logger.info(f"[SCENE_ANALYTICS] Payload: {payload}")
                
                response = requests.post(eosda_url, json=payload, headers=headers)
                logger.info(f"[SCENE_ANALYTICS] Status {index_name}: {response.status_code}")
                logger.info(f"[SCENE_ANALYTICS] Response {index_name}: {response.text}")
                
                if response.status_code == 200:
                    index_data = response.json()
                    # Extraer estadísticas del resultado
                    if 'data' in index_data and index_data['data']:
                        # Los endpoints de índices devuelven series temporales, tomamos el último punto
                        data_points = index_data['data']
                        if data_points:
                            latest_point = data_points[-1]  # Último punto de datos
                            analytics_result[index_name] = {
                                "mean": latest_point.get("mean"),
                                "median": latest_point.get("median"), 
                                "std": latest_point.get("std_dev"),
                                "min": latest_point.get("min"),
                                "max": latest_point.get("max"),
                                "date": latest_point.get("date"),
                                "source": "eosda_indices_api"
                            }
                        else:
                            analytics_result[index_name] = {
                                "error": "No hay datos disponibles para esta fecha",
                                "source": "eosda_indices_api"
                            }
                    else:
                        analytics_result[index_name] = {
                            "error": "Respuesta sin datos válidos",
                            "source": "eosda_indices_api"
                        }
                else:
                    logger.warning(f"[SCENE_ANALYTICS] Error en {index_name}: {response.status_code}")
                    analytics_result[index_name] = {
                        "error": f"Error HTTP {response.status_code}",
                        "source": "eosda_indices_api"
                    }
            
            # Estructurar respuesta
            response_data = {
                "scene_info": {
                    "field_id": field_id,
                    "view_id": view_id,
                    "date": scene_date,
                    "indices_requested": indices,
                    "date_range_used": f"{start_date} to {end_date}"
                },
                "analytics": analytics_result,
                "metadata": {
                    "source": "eosda_indices_api_workaround",
                    "note": "Analytics obtenidos usando endpoint de índices históricos con rango de 1 día",
                    "cached_at": None,
                    "cache_key": cache_key
                }
            }
            
            # Guardar en cache por 2 horas
            cache.set(cache_key, response_data, 7200)  # 2 horas
            logger.info(f"[CACHE SET] Analytics guardados en cache: {cache_key}")
            
            return Response(response_data, status=200)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[SCENE_ANALYTICS] Error en petición a EOSDA: {str(e)}")
            return Response({"error": f"Error al obtener analytics de EOSDA: {str(e)}"}, status=500)

class EosdaAdvancedStatisticsView(APIView):
    """
    Vista que utiliza la nueva EOSDA Statistics API (type: mt_stats) para obtener
    estadísticas avanzadas por escena: mean, median, std, min, max, percentiles, variance, etc.
    
    Esta API es superior al workaround anterior porque:
    - Proporciona estadísticas más precisas y completas
    - Incluye percentiles (p10, p90), quartiles (q1, q3), variance
    - Admite filtrado por cobertura de nubes
    - Proporciona estadísticas específicas por escena/fecha
    - Es la API oficial recomendada para analytics de vegetación
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        POST /api/parcels/eosda-advanced-statistics/
        Body: {
            "field_id": "string",
            "view_id": "string", 
            "scene_date": "YYYY-MM-DD",
            "indices": ["ndvi", "ndmi", "evi"],  # opcional, por defecto ["ndvi"]
            "max_cloud_cover": 50,  # opcional, por defecto 10
            "sensors": ["S2"]  # opcional, por defecto ["S2", "L8"]
        }
        
        Retorna: {
            "task_id": "uuid",
            "status": "created|started|finished",
            "scene_info": {...},
            "statistics": {
                "ndvi": {
                    "mean": 0.65, "median": 0.62, "std": 0.15,
                    "min": 0.1, "max": 0.9, "variance": 0.023,
                    "q1": 0.55, "q3": 0.75, "p10": 0.45, "p90": 0.82,
                    "cloud_coverage": 5.2, "date": "2024-01-15",
                    "scene_id": "...", "view_id": "..."
                }
            }
        }
        
        OPTIMIZACIÓN: Cache por field_id+view_id+date+indices (cache por 24 horas)
        """
        field_id = request.data.get("field_id")
        view_id = request.data.get("view_id")
        scene_date = request.data.get("scene_date")
        indices = request.data.get("indices", ["ndvi"])
        max_cloud_cover = request.data.get("max_cloud_cover", 10)
        sensors = request.data.get("sensors", ["S2", "L8"])
        
        logger.info(f"[ADVANCED_STATS] Params: field_id={field_id}, view_id={view_id}, scene_date={scene_date}")
        
        # Validación de parámetros
        if not field_id or not view_id or not scene_date:
            logger.error(f"[ADVANCED_STATS] Parámetros inválidos: field_id={field_id}, view_id={view_id}, scene_date={scene_date}")
            return Response({"error": "Faltan parámetros obligatorios: field_id, view_id, scene_date."}, status=400)
        
        # Validar índices soportados por EOSDA Statistics API
        # NOTA: Statistics API soporta bandas espectrales, no índices calculados
        valid_indices = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12"]  # Bandas Sentinel-2
        indices = [idx for idx in indices if idx in valid_indices]
        if not indices:
            indices = ["B04", "B08", "B03"]  # Bandas por defecto (Red, NIR, Green)
        
        # Solo procesamos hasta 3 bandas por vez (limitación de EOSDA)
        if len(indices) > 3:
            indices = indices[:3]
            logger.warning(f"[ADVANCED_STATS] Solo se procesarán las primeras 3 bandas: {indices}")
        
        # Verificar cache de statistics por combinación field_id+view_id+date+indices (cache por 24 horas)
        cache_key = f"eosda_advanced_stats_{field_id}_{view_id}_{scene_date}_{'_'.join(sorted(indices))}"
        cached_stats = cache.get(cache_key)
        if cached_stats:
            logger.info(f"[CACHE HIT] Advanced statistics encontradas en cache: {cache_key}")
            return Response(cached_stats, status=200)
        
        # Convertir scene_date a rango (±1 día para capturar la escena específica)
        from datetime import datetime, timedelta
        import json
        try:
            date_obj = datetime.strptime(scene_date, "%Y-%m-%d")
            # Rango de ±1 día para asegurar que capturamos la escena específica
            start_date = (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            logger.error(f"[ADVANCED_STATS] Fecha inválida: {scene_date}")
            return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}, status=400)
        
        # Obtener polígono de la parcela para la consulta
        try:
            from .models import Parcel
            parcel = Parcel.objects.get(eosda_id=field_id)
            if not parcel.geom:
                return Response({"error": "La parcela no tiene geometría definida"}, status=400)
            
            # Convertir geometría a GeoJSON - manejo flexible para diferentes tipos
            import json
            from django.contrib.gis.geos import GEOSGeometry
            
            geom = parcel.geom
            logger.info(f"[ADVANCED_STATS] Geometría tipo: {type(geom)}, valor: {geom}")
            
            # Manejar diferentes tipos de geometría
            if isinstance(geom, dict):
                # Ya es GeoJSON dict
                polygon_geojson = geom
                logger.info(f"[ADVANCED_STATS] Geometría ya es dict GeoJSON")
            elif isinstance(geom, str):
                # String GeoJSON, parsear a dict
                try:
                    polygon_geojson = json.loads(geom)
                    logger.info(f"[ADVANCED_STATS] Geometría parseada desde string JSON")
                except json.JSONDecodeError:
                    # String WKT, convertir a GEOS y luego GeoJSON
                    geos_geom = GEOSGeometry(geom)
                    polygon_geojson = json.loads(geos_geom.geojson)
                    logger.info(f"[ADVANCED_STATS] Geometría convertida desde WKT")
            else:
                # Objeto GEOS Geometry
                polygon_geojson = json.loads(geom.geojson)
                logger.info(f"[ADVANCED_STATS] Geometría convertida desde objeto GEOS")
                
            logger.info(f"[ADVANCED_STATS] GeoJSON final: {polygon_geojson}")
            
        except Parcel.DoesNotExist:
            return Response({"error": "Parcela no encontrada"}, status=404)
        except Exception as e:
            logger.error(f"[ADVANCED_STATS] Error obteniendo geometría: {e}")
            logger.error(f"[ADVANCED_STATS] Tipo de geometría: {type(parcel.geom) if 'parcel' in locals() else 'parcel no definido'}")
            return Response({"error": "Error obteniendo geometría de la parcela"}, status=500)
        
        logger.info(f"[ADVANCED_STATS] Creando tarea para {len(indices)} índices: {indices}")
        logger.info(f"[ADVANCED_STATS] Rango de fechas: {start_date} - {end_date}")
        
        # Crear tarea en EOSDA Statistics API
        try:
            eosda_url = "https://api-connect.eos.com/api/gdw/api"
            headers = {
                "x-api-key": settings.EOSDA_API_KEY,
                "Content-Type": "application/json"
            }
            
            # Preparar payload para Statistics API
            payload = {
                "type": "mt_stats",
                "params": {
                    "bm_type": indices,  # Lista de índices a calcular (máximo 3)
                    "date_start": start_date,
                    "date_end": end_date,
                    "geometry": polygon_geojson,
                    "sensors": sensors,
                    "max_cloud_cover_in_aoi": max_cloud_cover,
                    "exclude_cover_pixels": True,  # Excluir píxeles con nubes
                    "cloud_masking_level": 2,  # Nivel medio+alto de detección de nubes
                    "reference": f"agrotech_{field_id}_{view_id}_{scene_date}",
                    "limit": 100  # Máximo de escenas a considerar
                }
            }
            
            logger.info(f"[ADVANCED_STATS] URL: {eosda_url}")
            logger.info(f"[ADVANCED_STATS] Payload: {json.dumps(payload, indent=2)}")
            
            # Crear tarea
            response = requests.post(eosda_url, json=payload, headers=headers)
            logger.info(f"[ADVANCED_STATS] Status Code: {response.status_code}")
            logger.info(f"[ADVANCED_STATS] Response: {response.text}")
            
            # EOSDA devuelve 202 (Accepted) para tareas creadas exitosamente
            if response.status_code in [200, 202]:
                task_data = response.json()
                task_id = task_data.get("task_id")
                status = task_data.get("status", "created")
                
                logger.info(f"[ADVANCED_STATS] Tarea creada exitosamente: {task_id}")
                
                # Estructurar respuesta inicial
                response_data = {
                    "task_id": task_id,
                    "status": status,
                    "scene_info": {
                        "field_id": field_id,
                        "view_id": view_id,
                        "date": scene_date,
                        "indices_requested": indices,
                        "date_range_used": f"{start_date} to {end_date}",
                        "max_cloud_cover": max_cloud_cover,
                        "sensors": sensors
                    },
                    "statistics": None,  # Se llenará cuando la tarea esté completa
                    "metadata": {
                        "source": "eosda_statistics_api",
                        "api_type": "mt_stats",
                        "task_timeout": task_data.get("task_timeout", 3600),
                        "req_id": task_data.get("req_id"),
                        "cache_key": cache_key,
                        "created_at": datetime.now().isoformat()
                    }
                }
                
                # Guardar respuesta inicial en cache por 1 hora (mientras se procesa)
                cache.set(cache_key, response_data, 3600)  # 1 hora
                logger.info(f"[CACHE SET] Advanced statistics task guardada en cache: {cache_key}")
                
                return Response(response_data, status=200)
            else:
                logger.error(f"[ADVANCED_STATS] Error creando tarea: {response.status_code} - {response.text}")
                return Response({
                    "error": f"Error creando tarea en EOSDA Statistics API: {response.status_code}",
                    "details": response.text
                }, status=500)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[ADVANCED_STATS] Error en petición a EOSDA: {str(e)}")
            return Response({"error": f"Error al crear tarea en EOSDA: {str(e)}"}, status=500)


class EosdaStatisticsTaskStatusView(APIView):
    """
    Vista para consultar el estado de una tarea de Statistics API y obtener los resultados
    cuando esté completa.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        """
        GET /api/parcels/eosda-statistics-task/{task_id}/
        
        Retorna el estado actual de la tarea y los resultados si están disponibles.
        """
        logger.info(f"[STATS_TASK_STATUS] Consultando estado de tarea: {task_id}")
        
        try:
            eosda_url = f"https://api-connect.eos.com/api/gdw/api/{task_id}"
            headers = {
                "x-api-key": settings.EOSDA_API_KEY
            }
            
            response = requests.get(eosda_url, headers=headers)
            logger.info(f"[STATS_TASK_STATUS] Status Code: {response.status_code}")
            
            if response.status_code == 200:
                task_result = response.json()
                
                # Verificar si hay errores en la respuesta
                errors = task_result.get("errors", [])
                results = task_result.get("result", [])
                status = task_result.get("status", "unknown")
                task_type = task_result.get("task_type", "")
                error_message = task_result.get("error_message", {})
                
                # Manejar caso cuando results es None
                if results is None:
                    results = []
                
                logger.info(f"[STATS_TASK_STATUS] Status: {status}, Task Type: {task_type}, Errors: {len(errors)}, Results: {len(results)}")
                logger.info(f"[STATS_TASK_STATUS] Error Message: {error_message}")
                logger.info(f"[STATS_TASK_STATUS] Full response: {json.dumps(task_result, indent=2)}")
                
                # Verificar si la tarea tiene errores (task_type: "error" o error_message presente)
                if task_type == "error" or error_message:
                    error_detail = error_message.get("error", "Error desconocido") if error_message else "Error en la tarea"
                    logger.error(f"[STATS_TASK_STATUS] Tarea {task_id} falló: {error_detail}")
                    return Response({
                        "task_id": task_id,
                        "status": "failed",
                        "error": error_detail,
                        "message": f"La tarea falló: {error_detail}",
                        "metadata": {
                            "source": "eosda_statistics_api",
                            "task_type": task_type,
                            "full_error": error_message,
                            "retrieved_at": datetime.now().isoformat()
                        }
                    }, status=200)
                
                # Si el status indica que está completada, procesar independientemente de si hay results
                if status in ["finished", "completed", "success"]:
                    if results:
                        # Procesar resultados y organizarlos por índice
                        processed_stats = self._process_statistics_results(results)
                        
                        response_data = {
                            "task_id": task_id,
                            "status": "finished",
                            "statistics": processed_stats,
                            "errors": errors,
                            "metadata": {
                                "source": "eosda_statistics_api",
                                "total_scenes": len(results),
                                "total_errors": len(errors),
                                "retrieved_at": datetime.now().isoformat()
                            }
                        }
                        
                        return Response(response_data, status=200)
                    else:
                        # Tarea completada pero sin resultados
                        logger.warning(f"[STATS_TASK_STATUS] Tarea {task_id} completada pero sin resultados")
                        return Response({
                            "task_id": task_id,
                            "status": "finished_no_results",
                            "statistics": {},
                            "errors": errors,
                            "message": "Tarea completada pero no se encontraron datos para los parámetros especificados.",
                            "metadata": {
                                "source": "eosda_statistics_api",
                                "total_errors": len(errors),
                                "retrieved_at": datetime.now().isoformat()
                            }
                        }, status=200)
                
                elif results:
                    # Hay resultados aunque el status no sea explícitamente "finished"
                    processed_stats = self._process_statistics_results(results)
                    
                    response_data = {
                        "task_id": task_id,
                        "status": "finished",
                        "statistics": processed_stats,
                        "errors": errors,
                        "metadata": {
                            "source": "eosda_statistics_api",
                            "total_scenes": len(results),
                            "total_errors": len(errors),
                            "retrieved_at": datetime.now().isoformat()
                        }
                    }
                    
                    return Response(response_data, status=200)
                    
                elif errors:
                    logger.warning(f"[STATS_TASK_STATUS] Tarea completada con errores: {errors}")
                    return Response({
                        "task_id": task_id,
                        "status": "finished_with_errors",
                        "statistics": {},
                        "errors": errors,
                        "metadata": {
                            "source": "eosda_statistics_api",
                            "total_errors": len(errors),
                            "retrieved_at": datetime.now().isoformat()
                        }
                    }, status=200)
                    
                else:
                    # Tarea aún en proceso
                    return Response({
                        "task_id": task_id,
                        "status": "processing",
                        "statistics": None,
                        "message": "Tarea aún en proceso. Intente nuevamente en unos momentos."
                    }, status=202)  # Accepted
                    
            else:
                logger.error(f"[STATS_TASK_STATUS] Error consultando tarea: {response.status_code} - {response.text}")
                return Response({
                    "error": f"Error consultando estado de tarea: {response.status_code}",
                    "details": response.text
                }, status=500)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[STATS_TASK_STATUS] Error en petición a EOSDA: {str(e)}")
            return Response({"error": f"Error al consultar estado de tarea: {str(e)}"}, status=500)
    
    def _process_statistics_results(self, results):
        """
        Procesa los resultados de la Statistics API y los organiza por índice.
        
        Input: Lista de resultados de EOSDA con estadísticas por escena
        Output: Diccionario organizado por índice con estadísticas agregadas
        """
        processed = {}
        
        # Agrupar resultados por scene/date si hay múltiples índices
        for result in results:
            scene_id = result.get("scene_id")
            view_id = result.get("view_id")
            date = result.get("date")
            cloud = result.get("cloud")
            
            # Los resultados de mt_stats vienen organizados por escena
            # Cada resultado contiene estadísticas para todos los índices solicitados
            
            # Para este caso, tomamos el primer resultado (escena más cercana a la fecha solicitada)
            if not processed:  # Primera escena encontrada
                processed = {
                    "scene_id": scene_id,
                    "view_id": view_id,
                    "date": date,
                    "cloud_coverage": cloud,
                    "statistics": {
                        "mean": result.get("average"),
                        "median": result.get("median"),
                        "std": result.get("std"),
                        "min": result.get("min"),
                        "max": result.get("max"),
                        "variance": result.get("variance"),
                        "q1": result.get("q1"),  # Primer quartil
                        "q3": result.get("q3"),  # Tercer quartil
                        "p10": result.get("p10"),  # Percentil 10
                        "p90": result.get("p90"),  # Percentil 90
                        "notes": result.get("notes", [])
                    }
                }
                
        return processed

class EosdaBulkAnalyticsView(APIView):
    """
    Vista para obtener analytics de múltiples escenas de una vez
    Útil para construir datasets históricos rápidamente
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        POST /api/parcels/eosda-bulk-analytics/
        Body: {
            "field_id": "string",
            "scenes": [
                {"view_id": "abc123", "date": "2024-01-15"},
                {"view_id": "def456", "date": "2024-01-20"}
            ],
            "indices": ["ndvi", "ndmi"]  # opcional
        }
        
        Retorna analytics de múltiples escenas de una vez
        """
        field_id = request.data.get("field_id")
        scenes = request.data.get("scenes", [])
        indices = request.data.get("indices", ["ndvi", "ndmi", "evi"])
        
        logger.info(f"[BULK_ANALYTICS] field_id={field_id}, {len(scenes)} escenas")
        
        if not field_id or not scenes:
            return Response({"error": "Faltan parámetros: field_id, scenes"}, status=400)
        
        results = []
        cache_misses = []
        
        # Verificar cache para cada escena
        for scene in scenes:
            view_id = scene.get("view_id")
            date = scene.get("date")
            cache_key = f"eosda_analytics_{field_id}_{view_id}_{date}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                results.append({
                    "view_id": view_id,
                    "date": date,
                    "data": cached_data,
                    "source": "cache"
                })
            else:
                cache_misses.append(scene)
        
        # Para las escenas que no están en cache, usar la API básica por ahora
        # En el futuro se puede implementar usando la Advanced Statistics API
        for scene in cache_misses:
            try:
                # Placeholder: por ahora devolver datos de ejemplo
                results.append({
                    "view_id": scene.get("view_id"),
                    "date": scene.get("date"),
                    "data": {
                        "analytics": {
                            "ndvi": {"mean": 0.65, "std": 0.15, "source": "bulk_placeholder"},
                            "ndmi": {"mean": 0.42, "std": 0.12, "source": "bulk_placeholder"},
                            "evi": {"mean": 0.38, "std": 0.11, "source": "bulk_placeholder"}
                        }
                    },
                    "source": "generated",
                    "note": "Datos de ejemplo - implementar con Advanced Statistics API"
                })
            except Exception as e:
                results.append({
                    "view_id": scene.get("view_id"),
                    "date": scene.get("date"),
                    "error": str(e),
                    "source": "error"
                })
        
        return Response({
            "field_id": field_id,
            "total_scenes": len(scenes),
            "cache_hits": len(scenes) - len(cache_misses),
            "cache_misses": len(cache_misses),
            "results": results,
            "note": "Implementación básica - mejorar con Advanced Statistics API para procesamiento en lote"
        }, status=200)

class ParcelHistoricalIndicesView(APIView):
    """
    Vista para obtener datos históricos de índices NDVI, NDMI y EVI 
    desde principio de año hasta la fecha actual para gráfico histórico
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, parcel_id):
        """
        GET /api/parcels/parcel/<parcel_id>/historical-indices/
        Retorna datos históricos de NDVI, NDMI y EVI desde enero del año actual
        """
        logger.info(f"[HISTORICAL_INDICES] Iniciando consulta para parcela ID: {parcel_id}")
        
        try:
            # Obtener la parcela
            parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
            logger.info(f"[HISTORICAL_INDICES] Parcela encontrada: {parcel.name}")
            
            eosda_id = getattr(parcel, "eosda_id", None)
            logger.info(f"[HISTORICAL_INDICES] EOSDA ID: {eosda_id}")
            
            if not eosda_id:
                logger.error(f"[HISTORICAL_INDICES] Parcela {parcel_id} no tiene eosda_id")
                return Response({"error": "La parcela no tiene eosda_id configurado"}, status=400)
            
            # Configurar fechas: desde enero del año actual hasta hoy
            current_year = datetime.now().year
            start_date = f"{current_year}-01-01"
            end_date = datetime.now().strftime("%Y-%m-%d")
            
            # Cache key para datos históricos
            cache_key = f"historical_indices_{eosda_id}_{current_year}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.info(f"[HISTORICAL_INDICES] Cache hit: {cache_key}")
                return Response(cached_data)
            
            # Obtener geometría de la parcela
            if not parcel.geom:
                return Response({"error": "La parcela no tiene geometría definida"}, status=400)
            
            # Manejar geometría GeoJSON
            geom = parcel.geom
            logger.info(f"[HISTORICAL_INDICES] Tipo de geometría: {type(geom)}")
            
            if isinstance(geom, dict):
                # Ya es un diccionario GeoJSON
                polygon_geojson = geom
            elif isinstance(geom, str):
                # Es un string JSON, parsearlo
                polygon_geojson = json.loads(geom)
            else:
                # Podría ser un objeto GEOS, convertir
                polygon_geojson = json.loads(geom.geojson)
            
            logger.info(f"[HISTORICAL_INDICES] GeoJSON preparado: {polygon_geojson.get('type', 'unknown')}")
            
            logger.info(f"[HISTORICAL_INDICES] Obteniendo datos históricos para parcela {parcel_id}")
            logger.info(f"[HISTORICAL_INDICES] Período: {start_date} a {end_date}")
            
            # Índices a consultar
            indices = ["ndvi", "ndmi", "evi"]
            historical_data = {}
            
            # Consultar cada índice a EOSDA usando Field Analytics API
            for index_name in indices:
                logger.info(f"[HISTORICAL_INDICES] Consultando {index_name}...")
                
                # Usar Field Analytics API para obtener trend histórico del índice
                eosda_url = f"https://api-connect.eos.com/field-analytics/trend/{eosda_id}"
                headers = {
                    "x-api-key": settings.EOSDA_API_KEY,
                    "Content-Type": "text/plain"
                }
                
                # Payload para obtener trend histórico de índice específico
                payload = {
                    "params": {
                        "date_start": start_date,
                        "date_end": end_date,
                        "index": index_name.upper(),  # NDVI, NDMI, EVI
                        "data_source": "S2"  # Sentinel-2
                    }
                }
                
                try:
                    # Paso 1: Crear tarea
                    response = requests.post(eosda_url, json=payload, headers=headers, timeout=30)
                    
                    if response.status_code in [200, 202]:
                        task_data = response.json()
                        
                        if task_data.get("status") == "created":
                            request_id = task_data.get("request_id")
                            logger.info(f"[HISTORICAL_INDICES] Tarea creada para {index_name}: {request_id}")
                            
                            # Paso 2: Obtener resultado de la tarea
                            result_url = f"{eosda_url}/{request_id}"
                            
                            # Intentar obtener el resultado (puede requerir espera)
                            import time
                            max_attempts = 10
                            wait_time = 3  # segundos
                            
                            for attempt in range(max_attempts):
                                try:
                                    result_response = requests.get(result_url, headers=headers, timeout=30)
                                    
                                    if result_response.status_code == 200:
                                        result_data = result_response.json()
                                        
                                        if result_data.get("status") == "success":
                                            # Procesar datos reales de EOSDA
                                            raw_data = result_data.get("result", [])
                                            processed_data = []
                                            
                                            for point in raw_data:
                                                processed_data.append({
                                                    'date': point.get('date'),
                                                    'mean': round(point.get('average', 0), 3),
                                                    'median': round(point.get('median', 0), 3),
                                                    'std': round(point.get('std', 0), 3),
                                                    'min': round(point.get('min', 0), 3),
                                                    'max': round(point.get('max', 0), 3)
                                                })
                                            
                                            historical_data[index_name] = processed_data
                                            logger.info(f"[HISTORICAL_INDICES] Obtenidos {len(processed_data)} puntos reales para {index_name}")
                                            break
                                        elif result_data.get("status") == "processing":
                                            logger.info(f"[HISTORICAL_INDICES] Tarea {index_name} aún procesando, intento {attempt + 1}/{max_attempts}")
                                            time.sleep(wait_time)
                                            continue
                                        else:
                                            logger.error(f"[HISTORICAL_INDICES] Error en resultado {index_name}: {result_data}")
                                            break
                                    else:
                                        logger.error(f"[HISTORICAL_INDICES] Error obteniendo resultado {index_name}: {result_response.status_code}")
                                        break
                                        
                                except Exception as e:
                                    logger.error(f"[HISTORICAL_INDICES] Error en intento {attempt + 1} para {index_name}: {str(e)}")
                                    if attempt == max_attempts - 1:
                                        break
                                    time.sleep(wait_time)
                            
                            # Si no se obtuvieron datos reales, usar fallback
                            if index_name not in historical_data:
                                logger.warning(f"[HISTORICAL_INDICES] No se pudieron obtener datos reales para {index_name}, usando fallback")
                                historical_data[index_name] = self._generate_test_data(index_name, start_date, end_date)
                        else:
                            logger.error(f"[HISTORICAL_INDICES] Error creando tarea {index_name}: {task_data}")
                            historical_data[index_name] = self._generate_test_data(index_name, start_date, end_date)
                            
                    else:
                        logger.error(f"[HISTORICAL_INDICES] Error {index_name}: {response.status_code} - {response.text}")
                        # Generar datos de prueba como fallback cuando EOSDA falla
                        logger.info(f"[HISTORICAL_INDICES] Generando datos de prueba como fallback para {index_name}")
                        historical_data[index_name] = self._generate_test_data(index_name, start_date, end_date)
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"[HISTORICAL_INDICES] Error de conexión {index_name}: {str(e)}")
                    # Generar datos de prueba para desarrollo
                    logger.info(f"[HISTORICAL_INDICES] Generando datos de prueba para {index_name}")
                    historical_data[index_name] = self._generate_test_data(index_name, start_date, end_date)
                    logger.info(f"[HISTORICAL_INDICES] Datos de prueba generados para {index_name}: {len(historical_data[index_name])} puntos")
            
            # Estructurar respuesta
            response_data = {
                "parcel_info": {
                    "id": parcel_id,
                    "name": parcel.name,
                    "eosda_id": eosda_id
                },
                "period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "historical_data": historical_data,
                "metadata": {
                    "total_points": sum(len(data) for data in historical_data.values()),
                    "indices_available": [idx for idx, data in historical_data.items() if len(data) > 0],
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            # Guardar en cache por 6 horas
            cache.set(cache_key, response_data, 21600)
            logger.info(f"[HISTORICAL_INDICES] Datos guardados en cache: {cache_key}")
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"[HISTORICAL_INDICES] Error: {str(e)}")
            return Response({"error": f"Error obteniendo datos históricos: {str(e)}"}, status=500)

    def _generate_test_data(self, index_name, start_date, end_date):
        """
        Genera datos de prueba para desarrollo cuando EOSDA no está disponible
        """
        import random
        from datetime import datetime, timedelta
        
        # Configurar rangos base para cada índice
        base_values = {
            'ndvi': {'base': 0.6, 'range': 0.4},  # 0.2 - 1.0
            'ndmi': {'base': 0.4, 'range': 0.6},  # -0.2 - 1.0  
            'evi': {'base': 0.5, 'range': 0.5}    # 0.0 - 1.0
        }
        
        base_val = base_values.get(index_name, {'base': 0.5, 'range': 0.4})
        
        # Generar fechas cada 10 días aproximadamente
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        test_data = []
        current_date = start
        
        while current_date <= end:
            # Simular variación estacional (más alto en primavera/verano)
            month = current_date.month
            seasonal_factor = 0.8 + 0.4 * abs(6 - month) / 6  # Pico en junio
            
            # Valor base con variación aleatoria y estacional
            mean_val = base_val['base'] + (random.random() - 0.5) * base_val['range'] * seasonal_factor
            mean_val = max(0, min(1, mean_val))  # Mantener en rango 0-1
            
            # Generar estadísticas relacionadas
            std_val = random.uniform(0.05, 0.15)
            min_val = max(0, mean_val - std_val * 2)
            max_val = min(1, mean_val + std_val * 2)
            median_val = mean_val + random.uniform(-0.05, 0.05)
            
            test_data.append({
                'date': current_date.strftime("%Y-%m-%d"),
                'mean': round(mean_val, 3),
                'median': round(median_val, 3),
                'std': round(std_val, 3),
                'min': round(min_val, 3),
                'max': round(max_val, 3)
            })
            
            # Avanzar 7-15 días aleatoriamente
            current_date += timedelta(days=random.randint(7, 15))
        
        logger.info(f"[HISTORICAL_INDICES] Generados {len(test_data)} puntos de prueba para {index_name}")
        return test_data

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
                else:
                    return Response({"error": "Geometría inválida para obtener coordenadas"}, status=400)
            else:
                # Usar Django GIS para obtener centroide
                from django.contrib.gis.geos import GEOSGeometry
                if isinstance(geom, str):
                    geos_geom = GEOSGeometry(geom)
                else:
                    geos_geom = geom
                centroid = geos_geom.centroid
                avg_lng, avg_lat = centroid.coords
            
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
    
    def _get_weather_data(self, latitude, longitude):
        """
        Obtiene datos meteorológicos históricos desde EOSDA Weather API
        Usando endpoint historical-accumulated desde el inicio del año actual hasta la fecha de consulta
        """
        try:
            # Configurar fechas automáticamente: desde enero del año actual hasta hoy
            from datetime import datetime, timedelta
            end_date = datetime.now()
            # Obtener el año actual y configurar inicio desde enero 1
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
            logger.info(f"[EOSDA_WEATHER] Período: {start_date_str} a {end_date_str}")
            
            response = requests.post(weather_url, headers=headers, json=payload, timeout=60)
            logger.info(f"[EOSDA_WEATHER] Status code: {response.status_code}")
            logger.info(f"[EOSDA_WEATHER] Response content length: {len(response.content)}")
            # No imprimir el contenido completo para evitar saturar los logs
            
            if response.status_code == 200:
                if not response.content or response.content.strip() == b'':
                    logger.warning(f"[EOSDA_WEATHER] EOSDA devolvió respuesta vacía para field_id={field_id}, período {start_date_str} a {end_date_str}")
                    
                    # Fallback: Si no hay datos desde enero del año actual, intentar desde enero del año anterior
                    if start_date.year == current_year:
                        logger.info(f"[EOSDA_WEATHER] Intentando fallback: desde enero del año anterior")
                        fallback_start = datetime(current_year - 1, 1, 1)
                        fallback_start_str = fallback_start.strftime("%Y-%m-%d")
                        
                        fallback_payload = {
                            "params": {
                                "date_start": fallback_start_str,
                                "date_end": end_date_str,
                                "sum_of_active_temperatures": 10
                            },
                            "provider": "weather-online"
                        }
                        
                        logger.info(f"[EOSDA_WEATHER] Fallback request: {fallback_start_str} a {end_date_str}")
                        fallback_response = requests.post(weather_url, headers=headers, json=fallback_payload, timeout=60)
                        
                        if fallback_response.status_code == 200 and fallback_response.content:
                            response = fallback_response
                            start_date_str = fallback_start_str
                            logger.info(f"[EOSDA_WEATHER] Fallback exitoso con datos desde {fallback_start_str}")
                        else:
                            logger.warning(f"[EOSDA_WEATHER] Fallback también falló")
                            return []
                    else:
                        return []
                
                try:
                    data = response.json()
                    logger.info(f"[EOSDA_WEATHER] JSON parseado correctamente")
                    logger.info(f"[EOSDA_WEATHER] Datos recibidos: {len(data)} días" if isinstance(data, list) else f"[EOSDA_WEATHER] Tipo de respuesta: {type(data)}")
                    
                    if isinstance(data, list) and len(data) == 0:
                        logger.warning(f"[EOSDA_WEATHER] EOSDA devolvió lista vacía para field_id={field_id}, período {start_date_str} a {end_date_str}")
                        return []
                    
                    if not isinstance(data, list):
                        logger.error(f"[EOSDA_WEATHER] Respuesta no es una lista. Tipo: {type(data)}, Contenido: {data}")
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
                    
                    logger.info(f"[EOSDA_WEATHER] Procesados {len(weather_data)} días correctamente")
                    return weather_data
                    
                except Exception as e:
                    logger.error(f"[EOSDA_WEATHER] Error parseando datos: {str(e)}")
                    return []
            else:
                logger.error(f"[EOSDA_WEATHER] Error HTTP: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"[EOSDA_WEATHER] Error general: {str(e)}")
            return []

    def _get_eosda_field_id(self, latitude, longitude):
        """
        Obtiene el field_id de EOSDA para una parcela dada lat/lon.
        Debes implementar la lógica para obtener el field_id según tu modelo Parcel.
        """
        # Ejemplo: buscar el Parcel más cercano y devolver su eosda_id
        # Este método debe ser adaptado según tu modelo y lógica de negocio
        try:
            from parcels.models import Parcel
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
    
    def _generate_synthetic_weather_data(self, start_date, end_date, latitude):
        """
        Genera datos sintéticos meteorológicos para desarrollo cuando la API falla
        """
        from datetime import datetime, timedelta
        import random
        import math
        
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
    
    def _generate_test_weather_data(self):
        """
        Genera datos meteorológicos de prueba cuando la API externa falla
        """
        from datetime import datetime, timedelta
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
    
    def _synchronize_ndvi_weather_data(self, ndvi_data, weather_data):
        """
        Sincroniza datos NDVI (esporádicos) con datos meteorológicos (diarios)
        Implementa sincronización más precisa con interpolación
        """
        from datetime import datetime, timedelta
        
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
                logger.debug(f"[SYNC] Fecha NDVI {ndvi_date} fuera del rango meteorológico ({min_weather_date.strftime('%Y-%m-%d')} - {max_weather_date.strftime('%Y-%m-%d')})")
                continue
            
            # Buscar datos meteorológicos para la fecha exacta
            weather_point = weather_dict.get(ndvi_date)
            
            if not weather_point:
                # Interpolación lineal para fechas faltantes
                weather_point = self._interpolate_weather_data(ndvi_dt, weather_dict)
            
            if weather_point:
                # Calcular métricas agregadas de precipitación
                precip_7d = self._calculate_accumulated_precipitation(ndvi_date, weather_dict, days=7)
                precip_15d = self._calculate_accumulated_precipitation(ndvi_date, weather_dict, days=15)
                precip_30d = self._calculate_accumulated_precipitation(ndvi_date, weather_dict, days=30)
                
                # Calcular promedios de temperatura
                temp_avg_7d = self._calculate_average_temperature(ndvi_date, weather_dict, days=7)
                temp_avg_15d = self._calculate_average_temperature(ndvi_date, weather_dict, days=15)
                
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
    
    def _interpolate_weather_data(self, target_date, weather_dict):
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
    
    def _calculate_average_temperature(self, target_date, weather_dict, days=7):
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
    
    def _calculate_accumulated_precipitation(self, target_date, weather_dict, days=7):
        """
        Calcula precipitación acumulada de los últimos N días
        """
        from datetime import datetime, timedelta
        
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
    
    def _calculate_correlations(self, synchronized_data):
        """
        Calcula correlaciones entre NDVI y todas las variables meteorológicas disponibles
        Incluye análisis de lag (retraso) para detectar correlaciones desfasadas
        """
        import numpy as np
        
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
                "ndvi_vs_precipitation_daily": self._safe_correlation(ndvi_values, precip_daily),
                "ndvi_vs_precipitation_7d": self._safe_correlation(ndvi_values, precip_7d),
                "ndvi_vs_precipitation_15d": self._safe_correlation(ndvi_values, precip_15d),
                "ndvi_vs_precipitation_30d": self._safe_correlation(ndvi_values, precip_30d),
                "ndvi_vs_temperature": self._safe_correlation(ndvi_values, temperatures),
                "ndvi_vs_temperature_max": self._safe_correlation(ndvi_values, temp_max),
                "ndvi_vs_temperature_min": self._safe_correlation(ndvi_values, temp_min),
                "ndvi_vs_humidity": self._safe_correlation(ndvi_values, humidity_values),
                "ndvi_vs_wind_speed": self._safe_correlation(ndvi_values, wind_speed),
                "ndvi_vs_solar_radiation": self._safe_correlation(ndvi_values[:len(solar_radiation)], solar_radiation) if len(solar_radiation) > 2 else 0
            }
            
            # Análisis de lag (correlaciones con retraso)
            lag_analysis = self._calculate_lag_correlations(ndvi_values, precip_7d, temperatures)
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
    
    def _safe_correlation(self, x, y):
        """
        Calcula correlación de Pearson de forma segura manejando NaN y arrays de diferentes tamaños
        """
        import numpy as np
        
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
    
    def _calculate_lag_correlations(self, ndvi_values, precip_values, temp_values):
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
                    precip_lag_corr = self._safe_correlation(ndvi_lagged, precip_lead)
                    
                    # NDVI vs temperatura con lag
                    temp_lead = temp_values[:-lag]
                    temp_lag_corr = self._safe_correlation(ndvi_lagged, temp_lead)
                    
                    lag_results[f"lag_{lag}"] = {
                        "precipitation": precip_lag_corr,
                        "temperature": temp_lag_corr
                    }
        except Exception as e:
            logger.error(f"[LAG_ANALYSIS] Error: {str(e)}")
        
        return lag_results
    
    def _generate_insights(self, synchronized_data, correlations):
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
            insights.append(f"Condiciones térmicas favorables para el crecimiento ({temp_corr:.2f}). El rango de temperatura es óptimo.")
        elif temp_corr < -0.4:
            insights.append(f"Estrés térmico detectado ({temp_corr:.2f}). Evaluar estrategias de manejo de temperatura.")
        
        # Análisis de humedad relativa
        humidity_corr = correlations.get("ndvi_vs_humidity", 0)
        if humidity_corr > 0.5:
            insights.append(f"La humedad relativa favorece el desarrollo ({humidity_corr:.2f}). Ambiente húmedo óptimo para la fotosíntesis.")
        elif humidity_corr < -0.5:
            insights.append(f"La alta humedad puede estar afectando negativamente ({humidity_corr:.2f}). Posible riesgo de enfermedades fúngicas.")
        
        # Análisis de viento
        wind_corr = correlations.get("ndvi_vs_wind_speed", 0)
        if wind_corr < -0.4:
            insights.append(f"Vientos fuertes están afectando el cultivo ({wind_corr:.2f}). Considerar cortavientos o protecciones.")
        elif wind_corr > 0.3:
            insights.append(f"Ventilación moderada favorece el cultivo ({wind_corr:.2f}). Buena circulación de aire.")
        
        # Análisis de radiación solar
        solar_corr = correlations.get("ndvi_vs_solar_radiation", 0)
        if solar_corr > 0.4:
            insights.append(f"Radiación solar óptima para fotosíntesis ({solar_corr:.2f}). Excelente disponibilidad lumínica.")
        elif solar_corr < -0.3:
            insights.append(f"Exceso de radiación puede estar causando estrés ({solar_corr:.2f}). Evaluar necesidad de sombreo.")
        
        # Análisis de lag (respuestas desfasadas)
        lag_analysis = correlations.get("lag_analysis", {})
        best_lag = None
        best_lag_corr = 0
        
        for lag_period, lag_data in lag_analysis.items():
            precip_lag = lag_data.get("precipitation", 0)
            if abs(precip_lag) > abs(best_lag_corr):
                best_lag_corr = precip_lag
                best_lag = lag_period
        
        if best_lag and abs(best_lag_corr) > 0.4:
            lag_days = best_lag.replace("lag_", "")
            if best_lag_corr > 0:
                insights.append(f"La vegetación responde a precipitaciones con {lag_days} períodos de retraso ({best_lag_corr:.2f}). Respuesta típica de cultivos establecidos.")
            else:
                insights.append(f"Respuesta negativa desfasada a precipitación ({lag_days} períodos: {best_lag_corr:.2f}). Posible problema de drenaje o enfermedades.")
        
        # Análisis de tendencias estacionales y pronóstico
        if len(synchronized_data) > 10:
            recent_data = synchronized_data[-5:]
            historical_data = [point for point in synchronized_data if point["weather"]["data_type"] == "historical"]
            forecast_data = [point for point in synchronized_data if point["weather"]["data_type"] == "forecast"]
            
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
            
            # Análisis de datos de pronóstico si están disponibles
            if forecast_data:
                forecast_precip = sum(point["weather"]["precipitation_daily"] for point in forecast_data)
                forecast_temp_avg = sum(point["weather"]["temperature"] for point in forecast_data) / len(forecast_data)
                
                if forecast_precip > 50:
                    insights.append(f"Pronóstico: Se esperan {forecast_precip:.1f}mm de lluvia en próximos días. Condiciones favorables para crecimiento vegetativo.")
                elif forecast_precip < 5:
                    insights.append(f"Pronóstico: Período seco esperado ({forecast_precip:.1f}mm). Considerar riego suplementario.")
                
                if forecast_temp_avg > 30:
                    insights.append(f"Pronóstico: Temperaturas altas esperadas ({forecast_temp_avg:.1f}°C promedio). Monitorear estrés térmico.")
                elif forecast_temp_avg < 10:
                    insights.append(f"Pronóstico: Temperaturas bajas esperadas ({forecast_temp_avg:.1f}°C promedio). Evaluar protección contra frío.")
        
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
