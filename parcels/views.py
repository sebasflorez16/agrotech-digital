# Endpoint para escenas satelitales filtradas por parcela y rango de fechas
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import requests
import logging
import json
from datetime import datetime, timedelta
from django.core.cache import cache

logger = logging.getLogger(__name__)

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
        response = super().list(request, *args, **kwargs)
        response.data = {
            "cesium_token": settings.CESIUM_ACCESS_TOKEN,
            "parcels": response.data
        }
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
        try:
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
            return Response({"error": str(e)}, status=500)

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
