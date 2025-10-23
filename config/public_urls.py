"""
URLs públicas que NO requieren tenant.
Estas rutas funcionan sin schema de tenant para healthchecks, etc.
"""
from django.http import HttpResponse
from django.urls import path


def health_check(request):
    """Endpoint de salud para Railway - NO requiere tenant"""
    return HttpResponse("ok", content_type="text/plain", status=200)


urlpatterns = [
    path('health/', health_check, name='health'),
]
