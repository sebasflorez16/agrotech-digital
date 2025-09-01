from rest_framework import routers
from . import views
from django.urls import path


app_name = "parcels"

router = routers.DefaultRouter()
router.register(r'parcel', views.ParcelViewSet, basename='parcel')

# Obtener las rutas generadas por el router
generated_urls = router.urls

# Definir nuestras URLs personalizadas
urlpatterns = generated_urls