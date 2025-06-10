from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from .models import Parcel
from .serializers import ParcelSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
import requests
import logging
from django.shortcuts import render

logger = logging.getLogger(__name__)

class SentinelHubClient:
    BASE_URL = "https://services.sentinel-hub.com/api/v1"

    def __init__(self, configuration_id):
        self.configuration_id = configuration_id

    def fetch_layer_data(self, layer_name, bbox, time_range):
        url = f"{self.BASE_URL}/process"
        headers = {
            "Authorization": f"Bearer {self.configuration_id}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": {
                "bounds": {"bbox": bbox},
                "data": [{"type": layer_name}],
            },
            "output": {"width": 512, "height": 512},
            "time": time_range,
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

class ParcelViewSet(viewsets.ModelViewSet):
    # Solo mostrar parcelas no eliminadas por defecto
    queryset = Parcel.objects.filter(is_deleted=False)
    serializer_class = ParcelSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data = {
            "cesium_token": settings.CESIUM_ACCESS_TOKEN,
            "weather_api_key": settings.WEATHER_API_KEY,
            "sentinel_ndvi_wmts": settings.SENTINEL_NDVI_WMTS,
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
        Endpoint para obtener los promedios mensuales de NDVI de una parcela.
        Recibe un polígono (GeoJSON) y un rango de fechas (start_date, end_date).
        """
        # Extraer datos del request
        polygon = request.data.get("polygon")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        if not polygon or not start_date or not end_date:
            return Response({"error": "Faltan parámetros obligatorios (polygon, start_date, end_date)."}, status=400)

        # Configuración de Sentinel Hub
        sentinel_url = f"https://services.sentinel-hub.com/api/v1/configurations/{settings.SENTINEL_CONFIGURATION_ID}/process"
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "input": {
                "bounds": {
                    "geometry": polygon
                },
                "data": [{
                    "type": "sentinel-2-l1c",
                    "dataFilter": {
                        "timeRange": {
                            "from": start_date,
                            "to": end_date
                        }
                    }
                }]
            },
            "output": {
                "resx": 10,
                "resy": 10,
                "responses": [{
                    "identifier": "ndvi",
                    "format": {
                        "type": "application/json"
                    }
                }]
            }
        }
        logger.debug(f"Payload: {payload}")
        logger.debug(f"Headers: {headers}")

        # Realizar la solicitud a Sentinel Hub
        try:
            response = requests.post(sentinel_url, json=payload, headers=headers)
            response.raise_for_status()
            ndvi_data = response.json()
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Error al conectar con Sentinel Hub: {str(e)}"}, status=500)

        # Procesar y devolver los datos
        return Response(ndvi_data, status=200)

    @action(detail=False, methods=["post"], url_path="water-stress-historical")
    def water_stress_historical(self, request):
        logger.debug(f"Request data: {request.data}")
        """
        Endpoint para obtener los promedios mensuales de estrés hídrico de una parcela.
        Recibe un polígono (GeoJSON) y un rango de fechas (start_date, end_date).
        """
        # Extraer datos del request
        polygon = request.data.get("polygon")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        if not polygon or not start_date or not end_date:
            return Response({"error": "Faltan parámetros obligatorios (polygon, start_date, end_date)."}, status=400)

        # Configuración de Sentinel Hub
        sentinel_url = f"https://services.sentinel-hub.com/api/v1/configurations/{settings.SENTINEL_CONFIGURATION_ID}/process"
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "input": {
                "bounds": {
                    "geometry": polygon
                },
                "data": [{
                    "type": "sentinel-2-l1c",
                    "dataFilter": {
                        "timeRange": {
                            "from": start_date,
                            "to": end_date
                        }
                    }
                }]
            },
            "output": {
                "resx": 10,
                "resy": 10,
                "responses": [{
                    "identifier": "water-stress",
                    "format": {
                        "type": "application/json"
                    }
                }]
            }
        }
        logger.debug(f"Payload: {payload}")
        logger.debug(f"Headers: {headers}")

        # Realizar la solicitud a Sentinel Hub
        try:
            response = requests.post(sentinel_url, json=payload, headers=headers)
            response.raise_for_status()
            water_stress_data = response.json()
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Error al conectar con Sentinel Hub: {str(e)}"}, status=500)

        # Procesar y devolver los datos
        return Response(water_stress_data, status=200)

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
                "polygon": parcel.geom.geojson
            }
            for parcel in qs
        ]
        return Response(parcels_data, status=200)

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
