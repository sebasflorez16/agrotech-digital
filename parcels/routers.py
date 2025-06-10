from rest_framework import routers
from . import views


app_name = "parcels"

router = routers.DefaultRouter()
router.register(r'parcel', views.ParcelViewSet, basename='parcel')

urlpatterns = router.urls