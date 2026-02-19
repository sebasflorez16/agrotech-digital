from django.urls import path
from . import views
from .analytics_views import EOSDAAnalyticsAPIView
from .simple_analytics import SimpleAnalyticsView
from django.http import JsonResponse
from .metereological import WeatherForecastView

# ELIMINADO: app_name = "parcels" - causaba conflicto con el router DRF
# El router DRF en parcels.routers no usa app_name, por lo que este tampoco debe usarlo

# Vista simple para debug
def test_analytics_endpoint(request):
    return JsonResponse({
        "message": "Endpoint funciona!",
        "path": request.path,
        "method": request.method,
        "params": dict(request.GET)
    })

from .proxy import eosda_wmts_proxy

urlpatterns = [
## Eliminado: vista dashboard que no existe
    path('eosda-wmts-tile/', eosda_wmts_proxy, name='eosda_wmts_proxy'),
    # Endpoints alineados con el nuevo flujo EOSDA
    path('eosda-scenes/', views.EosdaScenesView.as_view(), name='eosda_scenes'),
    path('eosda-image/', views.EosdaImageView.as_view(), name='eosda_image'),
    path('eosda-image-result/', views.EosdaImageResultView.as_view(), name='eosda_image_result'),
    path('eosda-scene-analytics/', views.EosdaSceneAnalyticsView.as_view(), name='eosda_scene_analytics'),
    path('eosda-bulk-analytics/', views.EosdaBulkAnalyticsView.as_view(), name='eosda_bulk_analytics'),
    # Nuevo: Advanced Statistics API (mt_stats)
    path('eosda-advanced-statistics/', views.EosdaAdvancedStatisticsView.as_view(), name='eosda_advanced_statistics'),
    path('eosda-statistics-task/<str:task_id>/', views.EosdaStatisticsTaskStatusView.as_view(), name='eosda_statistics_task_status'),
    # 🧪 DEBUG: Endpoints de prueba
    path('eosda-analytics-test/', test_analytics_endpoint, name='eosda_analytics_test'),
    path('eosda-analytics-simple/', SimpleAnalyticsView.as_view(), name='eosda_analytics_simple'),
    # Nuevo: Analytics API científico independiente
    path('eosda-analytics/', EOSDAAnalyticsAPIView.as_view(), name='eosda_analytics'),
    # Endpoint para escenas satelitales filtradas por parcela y rango de fechas
    path('parcel/<int:parcel_id>/scenes/', views.ParcelScenesByDateView.as_view(), name='parcel_scenes_by_date'),
    # Endpoint para datos históricos de índices (gráfico histórico)
    path('parcel/<int:parcel_id>/historical-indices/', views.ParcelHistoricalIndicesView.as_view(), name='parcel_historical_indices'),
    # Nuevo endpoint para análisis comparativo NDVI + Meteorología
    path('parcel/<int:parcel_id>/ndvi-weather-comparison/', views.ParcelNdviWeatherComparisonView.as_view(), name='parcel_ndvi_weather_comparison'),
    # Endpoint para pronóstico del tiempo de 14 días - ambas rutas disponibles
    path('parcel/<int:parcel_id>/weather-forecast/', WeatherForecastView.as_view(), name='weather_forecast'),
    # Ruta alternativa (preferida por el frontend) para asegurar acceso
    path('weather-forecast/<int:parcel_id>/', WeatherForecastView.as_view(), name='weather_forecast_alt'),
    # Ruta directa extra para evitar posibles conflictos con el router
    path('get-weather-forecast/<int:parcel_id>/', WeatherForecastView.as_view(), name='weather_forecast_direct'),

    # Geocoding Proxy (evita CORS y bloqueos de Nominatim)
    path('geocode/', views.geocode_proxy, name='geocode_proxy'),
]]
