import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def eosda_search(request):
    """
    Endpoint para buscar escenas satelitales en EOSDA (API de búsqueda).
    Recibe parámetros de búsqueda (fechas, polígono, nubes, etc.) y retorna metadatos de escenas.
    """
    # Probar con otro dataset_id alternativo (por ejemplo, S2L1C)
    dataset_id = getattr(settings, 'EOSDA_DATASET_ID', 'S2L2A')
    # Intenta con S2L1C si S2L2A falla
    alt_dataset_id = 'S2L1C' if dataset_id == 'S2L2A' else 'S2L2A'
    api_key = settings.EOSDA_API_KEY
    eosda_search_url = f"https://api-connect.eos.com/api/lms/search/v2/{dataset_id}?api_key={api_key}"
    alt_search_url = f"https://api-connect.eos.com/api/lms/search/v2/{alt_dataset_id}?api_key={api_key}"
    try:
        # El frontend debe enviar el body como JSON con los parámetros de búsqueda
        payload = request.data
        logger.info(f"EOSDA search payload: {payload}")
        resp = requests.post(eosda_search_url, json=payload, timeout=15)
        if resp.status_code == 200:
            return JsonResponse(resp.json(), safe=False)
        else:
            # Si el primer intento falla, prueba con el dataset alternativo
            logger.warning(f"Intentando con dataset alternativo: {alt_dataset_id}")
            resp_alt = requests.post(alt_search_url, json=payload, timeout=15)
            if resp_alt.status_code == 200:
                logger.info(f"EOSDA search OK con dataset alternativo: {alt_dataset_id}")
                return JsonResponse(resp_alt.json(), safe=False)
            else:
                try:
                    error_json = resp_alt.json()
                except Exception:
                    error_json = resp_alt.text
                logger.error(f"Error EOSDA search {resp_alt.status_code} (alt): {error_json}")
                return JsonResponse({"error": f"Error EOSDA search (alt): {error_json}"}, status=502)
    except Exception as e:
        logger.error(f"Error de conexión con EOSDA search: {str(e)}")
        return JsonResponse({"error": f"Error de conexión con EOSDA search: {str(e)}"}, status=502)

# NOTA: Agrega 'EOSDA_DATASET_ID' a tu settings/base.py y .env
# Ejemplo de uso desde el frontend:
# fetch('/parcels/eosda-search/', { method: 'POST', headers: {...}, body: JSON.stringify({search: {...}}) })
# El resultado contiene las escenas/metadatos para luego elegir la fecha/sceneID y visualizar los tiles WMTS.
