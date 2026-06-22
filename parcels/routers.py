from rest_framework import routers
from . import views
from .zone_views import ParcelZonificationViewSet, ParcelZoneViewSet

# Crear el router para DRF
router = routers.DefaultRouter()

# Registrar el ViewSet de parcelas
# Esto genera automáticamente: /parcel/, /parcel/<pk>/, etc.
router.register(r'parcel', views.ParcelViewSet, basename='parcel')

# Zonificación de manejo (precision farming)
router.register(r'parcel-zonifications', ParcelZonificationViewSet, basename='parcel-zonification')
router.register(r'parcel-zones', ParcelZoneViewSet, basename='parcel-zone')

# Exportar las URLs del router
urlpatterns = router.urls