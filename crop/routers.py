from rest_framework import routers
from .views import (
    CropTypeViewSet, CropVarietyViewSet, CropViewSet, CropStageViewSet,
    CropProgressPhotoViewSet, CropInputViewSet, LaborInputViewSet, CropEventViewSet,
    CropCatalogViewSet, CropCycleViewSet
)

app_name = "crop"

router = routers.DefaultRouter()

router.register(r'types', CropTypeViewSet)
router.register(r'varieties', CropVarietyViewSet, basename='cropvariety')
router.register(r'crops', CropViewSet)
router.register(r'stages', CropStageViewSet)
router.register(r'progress-photos', CropProgressPhotoViewSet)
router.register(r'inputs', CropInputViewSet)
router.register(r'labor-inputs', LaborInputViewSet)
router.register(r'events', CropEventViewSet)

# Catálogo de cultivos y ciclos de cultivo (Fase 3 - Sistema de ciclos)
router.register(r'catalog', CropCatalogViewSet)
router.register(r'cycles', CropCycleViewSet, basename='cropcycle')

urlpatterns = router.urls
