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
        """
        field_id = request.data.get("field_id")
        if not field_id:
            return Response({"error": "Falta el parámetro field_id."}, status=400)
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
                return Response({"request_id": request_id, "scenes": scenes}, status=200)
            else:
                # Si no hay request_id, usar las escenas del POST
                scenes = req_data.get('result', [])
                print(f"Escenas recibidas de EOSDA (POST directo): {scenes}")
                logger.info(f"Escenas recibidas de EOSDA (POST directo): {scenes}")
                return Response({"request_id": None, "scenes": scenes}, status=200)
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
        """
        import base64
        field_id = request.query_params.get("field_id")
        request_id = request.query_params.get("request_id")
        logger.info(f"[EOSDA_IMAGE_RESULT] Params recibidos: field_id={field_id}, request_id={request_id}")
        if not field_id or not request_id:
            logger.error(f"[EOSDA_IMAGE_RESULT] Parámetros inválidos: field_id={field_id}, request_id={request_id}")
            return Response({"error": "Parámetros inválidos."}, status=400)
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
                    return Response({"image_base64": image_base64}, status=200)
                except Exception as e:
                    logger.error(f"[EOSDA_IMAGE_RESULT] Error al convertir imagen a base64: {e}")
                    return Response({"error": "Error al procesar la imagen recibida."}, status=500)
            # Si la respuesta es JSON, analizar el estado
            elif content_type.startswith('application/json') or content_type.startswith('text/json'):
                try:
                    data = response.json()
                    logger.error(f"[EOSDA_IMAGE_RESULT] Respuesta no es imagen: {data}")
                    if data.get("status") == "created":
                        return Response({"error": "La imagen aún está en proceso. Intenta nuevamente en unos minutos."}, status=202)
                    return Response({"error": "No se recibió una imagen.", "details": data}, status=400)
                except Exception as e:
                    logger.error(f"[EOSDA_IMAGE_RESULT] Error al parsear JSON: {e}")
                    return Response({"error": "Respuesta inesperada de EOSDA."}, status=500)
            # Si la respuesta es binaria pero no tiene content-type correcto, intentar detectar PNG/JPG
            elif response.content[:8] == b'\x89PNG\r\n\x1a\n' or response.content[:2] == b'\xff\xd8':
                try:
                    image_base64 = base64.b64encode(response.content).decode('utf-8')
                    logger.info(f"[EOSDA_IMAGE_RESULT] Imagen binaria detectada y convertida a base64.")
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
