"""
Middleware personalizado para AgroTech Digital
"""
from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)


class HealthCheckMiddleware:
    """
    Middleware que responde a /health/ ANTES de que django-tenants procese la petición.
    Esto permite que Railway haga healthcheck sin necesitar un tenant válido.
    
    NO afecta el resto de la aplicación - todo sigue funcionando con subdominios normalmente.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Interceptar solo /health/ y /health
        if request.path in ['/health/', '/health']:
            logger.info(f"✅ HEALTHCHECK interceptado desde {request.get_host()}")
            return HttpResponse("ok", content_type="text/plain", status=200)
        
        # Para cualquier otra ruta, continuar normalmente
        return self.get_response(request)
