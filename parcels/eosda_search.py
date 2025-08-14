from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
import requests
from django.conf import settings
import logging

logger = logging.getLogger("eosda")


def get_eosda_id(field_id):
    """
    Convierte un field_id numérico en su eosda_id.
    """
    from .models import Parcel
    if field_id and str(field_id).isdigit():
        try:
            parcel = Parcel.objects.get(id=field_id)
            if not parcel.eosda_id:
                raise ValueError("La parcela no tiene eosda_id configurado")
            return parcel.eosda_id
        except Parcel.DoesNotExist:
            raise ValueError("No existe la parcela con ese id")
    # Si el field_id no es numérico, se asume que ya es un eosda_id válido
    return field_id


@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def eosda_scenes(request):
    field_id = request.data.get("field_id")
    try:
        eosda_id = get_eosda_id(field_id)
    except ValueError as e:
        logger.error(f"Error obteniendo eosda_id: {e}")
        return JsonResponse({"error": str(e)}, status=400)

    date_start = request.data.get("date_start")
    date_end = request.data.get("date_end")
    # Si no se proveen fechas, usar rango de los últimos 7 días
    from datetime import datetime, timedelta
    if not date_start or not date_end:
        today = datetime.utcnow().date()
        date_end = str(today)
        date_start = str(today - timedelta(days=7))

    url = f"https://api-connect.eos.com/scene-search/for-field/{eosda_id}"
    headers = {"x-api-key": settings.EOSDA_API_KEY, "Content-Type": "application/json"}
    payload = {"params": {"date_start": date_start, "date_end": date_end, "data_source": ["sentinel2"]}}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        try:
            data = resp.json()
        except Exception as ex_json:
            logger.error(f"Respuesta no JSON de EOSDA: {resp.text}")
            return JsonResponse({"error": "Respuesta no JSON de EOSDA", "raw": resp.text}, status=502)
    except Exception as e:
        logger.error(f"Error de conexión con EOSDA request_id: {e}")
        return JsonResponse({"error": f"Error de conexión con EOSDA request_id: {str(e)}"}, status=502)

    logger.info(f"Respuesta EOSDA scenes: status={resp.status_code}, data={data}")
    if resp.status_code in [200, 201]:
        if "request_id" in data:
            logger.info(f"Request_id recibido: {data['request_id']}")
            return JsonResponse({"request_id": data["request_id"], "raw": data})
        if "result" in data:
            logger.info(f"Escenas recibidas: {data['result']}")
            return JsonResponse({"scenes": data["result"], "raw": data})
        logger.error(f"Respuesta inesperada de EOSDA: {data}")
        return JsonResponse({"error": "Respuesta inesperada de EOSDA", "raw": data}, status=502)
    logger.error(f"Error EOSDA: status={resp.status_code}, data={data}")
    return JsonResponse({"error": data, "status_code": resp.status_code}, status=502)


@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def eosda_ndvi_image(request):
    eosda_id = request.data.get("eosda_id") or request.data.get("field_id")
    try:
        eosda_id = get_eosda_id(eosda_id)
    except ValueError as e:
        logger.error(f"Error obteniendo eosda_id para NDVI: {e}")
        return JsonResponse({"error": str(e)}, status=400)

    view_id = request.data.get("view_id")
    if not view_id:
        logger.error("Falta parámetro view_id en la petición NDVI")
        return JsonResponse({"error": "Falta parámetro view_id"}, status=400)

    api_key = settings.EOSDA_API_KEY
    ndvi_request_id = request.data.get("ndvi_request_id")

    if ndvi_request_id:
        logger.info(f"NDVI GET directo con request_id: {ndvi_request_id}")
        return get_ndvi_image(eosda_id, ndvi_request_id, api_key)

    # POST para generar request_id de NDVI
    post_url = f"https://api-connect.eos.com/field-imagery/indicies/{eosda_id}"
    payload = {"params": {"view_id": view_id, "index": "NDVI", "format": "png"}}

    try:
        post_resp = requests.post(post_url, headers={"x-api-key": api_key}, json=payload, timeout=15)
        try:
            post_data = post_resp.json()
        except Exception as ex_json:
            logger.error(f"Respuesta no JSON de EOSDA NDVI: {post_resp.text}")
            return JsonResponse({"error": "Respuesta no JSON de EOSDA NDVI", "raw": post_resp.text}, status=502)
    except Exception as e:
        logger.error(f"Error conexión EOSDA NDVI: {e}")
        return JsonResponse({"error": f"Error conexión EOSDA NDVI: {str(e)}"}, status=502)

    logger.info(f"Respuesta EOSDA NDVI: status={post_resp.status_code}, data={post_data}")
    if post_resp.status_code not in [200, 201] or "request_id" not in post_data:
        logger.error(f"No se pudo generar request_id NDVI: {post_data}")
        return JsonResponse({"error": "No se pudo generar request_id NDVI", "raw": post_data}, status=502)

    ndvi_request_id = post_data["request_id"]
    logger.info(f"NDVI request_id generado: {ndvi_request_id}")
    return get_ndvi_image(eosda_id, ndvi_request_id, api_key)


def get_ndvi_image(eosda_id, request_id, api_key):
    get_url = f"https://api-connect.eos.com/field-imagery/{eosda_id}/{request_id}"
    try:
        get_resp = requests.get(get_url, headers={"x-api-key": api_key}, timeout=15)
        content_type = get_resp.headers.get("Content-Type", "")
    except Exception as e:
        logger.error(f"Error conexión EOSDA NDVI GET: {e}")
        return JsonResponse({"error": f"Error conexión EOSDA NDVI GET: {str(e)}"}, status=502)

    logger.info(f"Respuesta EOSDA NDVI GET: status={get_resp.status_code}, content_type={content_type}")
    if get_resp.status_code == 200:
        if "image/png" in content_type:
            from django.http import HttpResponse
            logger.info(f"NDVI imagen PNG recibida para request_id: {request_id}")
            return HttpResponse(get_resp.content, content_type="image/png")
        try:
            data = get_resp.json()
            logger.info(f"NDVI JSON recibido: {data}")
            return JsonResponse({"image_url": data.get("image_url"), "request_id": request_id, "raw": data})
        except Exception:
            logger.error(f"Respuesta no JSON NDVI GET: {get_resp.text}")
            return JsonResponse({"error": "Respuesta no JSON NDVI", "raw": get_resp.text}, status=502)

    logger.error(f"Error NDVI GET: status={get_resp.status_code}, text={get_resp.text}")
    return JsonResponse({"error": get_resp.text, "status_code": get_resp.status_code}, status=502)
