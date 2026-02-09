"""
URLs públicas que NO requieren tenant.
Estas rutas funcionan sin schema de tenant para healthchecks, autenticación y registro.
"""
from django.http import HttpResponse
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def health_check(request):
    """Endpoint de salud para Railway - NO requiere tenant"""
    return HttpResponse("ok", content_type="text/plain", status=200)


urlpatterns = [
    path('health/', health_check, name='health'),
    
    # 🔹 Autenticación JWT - NO requiere tenant
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # 🔹 Auth completo (register, login, me) - NO requiere tenant
    path("api/auth/", include("authentication.urls")),
    
    # 🔹 Billing público (planes, webhooks) - NO requiere tenant
    path("billing/", include("billing.urls", namespace="billing")),
]
