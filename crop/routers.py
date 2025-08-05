from rest_framework import routers
from .views import (
    CropTypeViewSet, CropViewSet, CropStageViewSet,
    CropProgressPhotoViewSet, CropInputViewSet, LaborInputViewSet, CropEventViewSet
)

app_name = "crop"

router = routers.DefaultRouter()

router.register(r'types', CropTypeViewSet)
router.register(r'crops', CropViewSet)
router.register(r'stages', CropStageViewSet)
router.register(r'progress-photos', CropProgressPhotoViewSet)
router.register(r'inputs', CropInputViewSet)
router.register(r'labor-inputs', LaborInputViewSet)
router.register(r'events', CropEventViewSet)

urlpatterns = router.urls
