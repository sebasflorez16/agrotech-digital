# parcels/views/eosda_proxy.py
import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def eosda_wmts_proxy(request):
    """
    Proxy seguro para servir tiles NDVI/NDMI desde EOSDA Render API.
    Documentación: https://doc.eos.com/docs/quickstart/
    
    OPTIMIZACIÓN: Cache de 24 horas por tile (las imágenes satelitales históricas no cambian).
    """
    # EOSDA Render API base
    eosda_base_url = "https://api-connect.eos.com/api/render"
    api_key = settings.EOSDA_API_KEY

    # Parámetros requeridos
    scene_id = request.GET.get("scene_id")
    layer = request.GET.get("layer", "NDVI")
    z = request.GET.get("z")
    x = request.GET.get("x")
    y = request.GET.get("y")
    time = request.GET.get("time")

    # Validación básica
    if not scene_id or not layer or not z or not x or not y:
        return JsonResponse({"error": "Faltan parámetros obligatorios."}, status=400)

    # Sanear fecha si es válida
    try:
        if time and time != "{time}":
            time = datetime.fromisoformat(time[:10]).strftime("%Y-%m-%d")
        else:
            time = None
    except:
        time = None

    # ============ CACHE DE TILES (24 horas) ============
    # Las imágenes satelitales históricas no cambian, cache seguro
    cache_key = f"wmts_{scene_id}_{layer}_{z}_{x}_{y}"
    if time:
        cache_key += f"_{time}"
    # Acortar clave si es muy larga para el backend de cache
    if len(cache_key) > 200:
        cache_key = f"wmts_{hashlib.md5(cache_key.encode()).hexdigest()}"
    
    cached_tile = cache.get(cache_key)
    if cached_tile:
        logger.debug(f"[EOSDA TILE CACHE HIT] {cache_key}")
        response = HttpResponse(cached_tile, content_type="image/png")
        response["Cache-Control"] = "public, max-age=86400"  # 24h browser cache
        return response

    # Construir URL final a EOSDA
    eosda_url = f"{eosda_base_url}/{scene_id}/{layer}/{z}/{x}/{y}?api_key={api_key}"
    if time:
        eosda_url += f"&time={time}"

    logger.info(f"[EOSDA TILE URL] → {eosda_url}")

    try:
        response = requests.get(eosda_url, timeout=10)
        if response.status_code == 200:
            # Guardar en cache por 24 horas (86400 segundos)
            cache.set(cache_key, response.content, 86400)
            logger.debug(f"[EOSDA TILE CACHE SET] {cache_key}")
            
            http_response = HttpResponse(response.content, content_type="image/png")
            http_response["Cache-Control"] = "public, max-age=86400"  # 24h browser cache
            return http_response
        else:
            logger.error(f"[EOSDA ERROR {response.status_code}] {response.text}")
            return JsonResponse({"error": f"Error EOSDA: {response.text}"}, status=502)
    except Exception as e:
        logger.exception(f"Conexión fallida con EOSDA: {e}")
        return JsonResponse({"error": f"Conexión fallida con EOSDA: {str(e)}"}, status=502)
