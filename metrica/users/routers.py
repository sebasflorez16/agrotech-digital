from rest_framework.routers import DefaultRouter
from .views import UserProfileUtil

router = DefaultRouter()
router.register(r'profile-utils', UserProfileUtil, basename="profile-util")

urlpatterns = router.urls