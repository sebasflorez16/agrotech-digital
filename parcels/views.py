from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from .models import Parcel, ParcelSceneCache
from .serializers import ParcelSerializer
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
import requests
import logging
from django.shortcuts import render

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



# Nuevo endpoint para obtener la URL WMTS NDVI/NDMI de EOSDA usando el ID EOSDA
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def eosda_wmts_urls(request):
    """
    Endpoint seguro que retorna la lista de escenas satelitales para un field EOSDA usando la nueva API Connect.
    Recibe el id EOSDA (eosda_id) y retorna la lista de escenas disponibles (view_id, fecha, etc) para Cesium.
    """
    import logging
    import requests
    import time
    logger = logging.getLogger(__name__)
    from rest_framework.parsers import JSONParser
    if request.method == 'POST':
        data = request.data if hasattr(request, 'data') else JSONParser().parse(request)
    else:
        data = request.GET
    eosda_id = data.get("eosda_id")
    date_start = data.get("date_start")
    date_end = data.get("date_end")
    if not eosda_id:
        return Response({"error": "Falta el parámetro 'eosda_id'."}, status=400)
    api_key = settings.EOSDA_API_KEY
    search_url = f"https://api-connect.eos.com/scene-search/for-field/{eosda_id}"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    # Parámetros de búsqueda: fechas y fuente sentinel2 por defecto
    params = {
        "date_start": date_start or "2024-01-01",
        "date_end": date_end or time.strftime("%Y-%m-%d"),
        "data_source": ["sentinel2"],
        "params.max_cloud_cover_in_aoi": 50
    }
    payload = {"params": params}
    try:
        # 1. Lanzar búsqueda de escenas
        resp = requests.post(search_url, json=payload, headers=headers, timeout=20)
        if resp.status_code == 403:
            logger.error(f"Permiso denegado por EOSDA (403 Forbidden): {resp.text}")
            return Response({
                "error": "Permiso denegado por EOSDA (403 Forbidden). Verifica que el campo (eosda_id) exista, pertenezca a tu cuenta y que tu API Key tenga acceso a la búsqueda de escenas. Si el problema persiste, revisa tu plan EOSDA o contacta soporte.",
                "detalle": resp.text
            }, status=403)
        if resp.status_code not in (200, 201):
            logger.error(f"Error lanzando búsqueda de escenas EOSDA: {resp.status_code} {resp.text}")
            return Response({
                "error": f"Error lanzando búsqueda de escenas EOSDA: {resp.text}",
                "codigo": resp.status_code
            }, status=502)
        search_data = resp.json()
        request_id = search_data.get("request_id")
        # Si no hay request_id pero hay escenas en 'result', devolverlas directamente (caso especial de EOSDA)
        if not request_id and search_data.get("result"):
            logger.info("EOSDA devolvió escenas directamente en 'result', sin request_id.")
            scenes = search_data.get("result", [])
            scenes_sorted = sorted(scenes, key=lambda s: s.get("date", ""), reverse=True)
            return Response({"scenes": scenes_sorted, "request_id": None}, status=200)
        logger.info(f"EOSDA request_id recibido: {request_id}")
        print(f"EOSDA request_id recibido: {request_id}")
        if not request_id:
            logger.error(f"No se recibió request_id de EOSDA: {search_data}")
            return Response({"error": "No se recibió request_id de EOSDA.", "search_data": search_data}, status=502)
        # 2. Polling para obtener resultados (máx 5 intentos)
        result_url = f"https://api-connect.eos.com/scene-search/for-field/{eosda_id}/{request_id}"
        scenes = []
        for _ in range(5):
            try:
                result_resp = requests.get(result_url, headers=headers, timeout=20)
            except Exception as e:
                logger.error(f"Error de conexión con EOSDA (polling): {str(e)}")
                return Response({"error": f"Error de conexión con EOSDA (polling): {str(e)}"}, status=502)
            if result_resp.status_code == 403:
                logger.error(f"Permiso denegado al consultar resultados de escenas EOSDA (403 Forbidden): {result_resp.text}")
                return Response({
                    "error": "Permiso denegado al consultar resultados de escenas EOSDA (403 Forbidden). Verifica tu API Key y el ownership del campo.",
                    "detalle": result_resp.text
                }, status=403)
            if result_resp.status_code == 200:
                result_data = result_resp.json()
                scenes = result_data.get("scenes", [])
                if scenes:
                    break
            time.sleep(2)
        if not scenes:
            logger.warning(f"No se encontraron escenas para el field {eosda_id} en EOSDA.")
            return Response({"scenes": [], "request_id": request_id}, status=200)
        # Ordenar por fecha descendente y devolver todas para el modal
        scenes_sorted = sorted(scenes, key=lambda s: s.get("date", ""), reverse=True)
        return Response({"scenes": scenes_sorted, "request_id": request_id}, status=200)
    except Exception as e:
        logger.error(f"Error de conexión con EOSDA: {str(e)}")
        return Response({"error": f"Error de conexión con EOSDA: {str(e)}"}, status=502)

def parcels_dashboard(request):
    """
    Renderiza el dashboard de parcelas y expone las URLs WMTS de Sentinel Hub (NDVI y NDMI) de forma segura.
    """
    from django.conf import settings
    context = {
        'SENTINEL_NDVI_WMTS': getattr(settings, 'SENTINEL_NDVI_WMTS', None),
        'SENTINEL_NDMI_WMTS': getattr(settings, 'SENTINEL_NDMI_WMTS', None),
    }
    return render(request, 'parcels/parcels-dashboard.html', context)

# Utilidad para obtener/cachar NDVI/NDMI de EOSDA por escena

def fetch_eosda_scene_ndvi(parcel, scene_id, index_type, date, **kwargs):
    """
    Función que consulta la API de EOSDA para obtener los datos NDVI/NDMI de una escena específica.
    Retorna un dict con metadata, image_url, raw_response, date.
    """
    import requests
    from django.conf import settings
    # Aquí deberías construir la URL y los headers según la documentación de EOSDA para renderizar la escena
    # Este ejemplo asume que tienes el endpoint y los parámetros correctos
    api_key = settings.EOSDA_API_KEY
    # Ejemplo de endpoint (ajusta según tu integración real)
    render_url = f"https://api-connect.eos.com/v1/scene/{scene_id}/render/{index_type.lower()}"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    try:
        resp = requests.get(render_url, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        # Suponiendo que la respuesta tiene 'image_url' y 'metadata'
        return {
            'metadata': data.get('metadata'),
            'image_url': data.get('image_url'),
            'raw_response': data,
            'date': date
        }
    except Exception as e:
        # Puedes loggear el error si lo deseas
        return None

# Ejemplo de uso en una vista:
# (Puedes adaptar esto a tu endpoint real de renderizado NDVI/NDMI)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def get_ndvi_scene_cached(request):
    """
    Endpoint que retorna los datos NDVI/NDMI de una escena, usando cache si existe.
    Recibe: parcel_id, scene_id, index_type, date
    """
    parcel_id = request.data.get("parcel_id")
    scene_id = request.data.get("scene_id")
    index_type = request.data.get("index_type", "NDVI")
    date = request.data.get("date")
    if not (parcel_id and scene_id and index_type and date):
        return Response({"error": "Faltan parámetros obligatorios (parcel_id, scene_id, index_type, date)."}, status=400)
    try:
        parcel = Parcel.objects.get(id=parcel_id)
    except Parcel.DoesNotExist:
        return Response({"error": "Parcela no encontrada."}, status=404)
    # Buscar en cache o pedir a EOSDA
    cache_obj, created = ParcelSceneCache.get_or_create_cache(
        parcel=parcel,
        scene_id=scene_id,
        index_type=index_type,
        date=date,
        fetch_func=fetch_eosda_scene_ndvi,

    )
    if not cache_obj:
        return Response({"error": "No se pudo obtener la escena de EOSDA."}, status=502)
    # Devuelve los datos cacheados o recién obtenidos
    return Response({
        "metadata": cache_obj.metadata,
        "image_url": cache_obj.image_url,
        "date": str(cache_obj.date),
        "index_type": cache_obj.index_type,
        "from_cache": not created,
        "raw_response": cache_obj.raw_response
    }, status=200)
