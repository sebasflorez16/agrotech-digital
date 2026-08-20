from rest_framework import routers
from .views import LaborViewSet, LaborPhotoViewSet, LaborPhaseViewSet, LaborInputViewSet

app_name = "labores"


router = routers.DefaultRouter()
router.register(r'labores', LaborViewSet, basename='labor')
router.register(r'labor-fotos', LaborPhotoViewSet, basename='laborphoto')
router.register(r'labor-fases', LaborPhaseViewSet, basename='laborphase')
router.register(r'labor-insumos', LaborInputViewSet, basename='laborinput')

urlpatterns = router.urls
