from rest_framework import routers
from . import views

# Crear el router para DRF
router = routers.DefaultRouter()

# Registrar el ViewSet de parcelas
# Esto genera automáticamente: /parcel/, /parcel/<pk>/, etc.
router.register(r'parcel', views.ParcelViewSet, basename='parcel')

# Exportar las URLs del router
urlpatterns = router.urls