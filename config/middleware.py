"""
Middleware personalizado para AgroTech Digital.

Incluye:
- HealthCheckMiddleware: intercepta /health/ antes de django-tenants
- SmartTenantMiddleware: reemplaza TenantMainMiddleware para forzar
  schema public en rutas de billing/auth/tokens.
"""
from django.http import HttpResponse
from django.conf import settings
from django.db import connection
from django_tenants.middleware.main import TenantMainMiddleware
from django_tenants.utils import get_public_schema_name
import logging

logger = logging.getLogger(__name__)


class HealthCheckMiddleware:
    """
    Middleware que responde a /health/ ANTES de que django-tenants procese la petición.
    Esto permite que Railway haga healthcheck sin necesitar un tenant válido.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in ['/health/', '/health']:
            return HttpResponse("ok", content_type="text/plain", status=200)
        return self.get_response(request)


class SmartTenantMiddleware(TenantMainMiddleware):
    """
    Extiende TenantMainMiddleware para forzar schema 'public' en rutas
    que deben funcionar sin un tenant específico (billing API, auth, tokens).

    Para cualquier otra ruta, hace la resolución normal por hostname.
    """

    # Prefijos de URL que SIEMPRE deben correr contra el schema public
    PUBLIC_PATH_PREFIXES = [
        '/billing/',
        '/api/auth/',
        '/api/token/',
    ]

    def process_request(self, request):
        # ¿Es una ruta pública?
        is_public_path = any(
            request.path.startswith(prefix)
            for prefix in self.PUBLIC_PATH_PREFIXES
        )

        if is_public_path:
            try:
                from base_agrotech.models import Client
                public_tenant = Client.objects.get(
                    schema_name=get_public_schema_name()
                )
                request.tenant = public_tenant
                connection.set_tenant(public_tenant)

                # Usar PUBLIC_SCHEMA_URLCONF si está definido
                if hasattr(settings, 'PUBLIC_SCHEMA_URLCONF'):
                    request.urlconf = settings.PUBLIC_SCHEMA_URLCONF

                logger.debug(
                    f"SmartTenantMiddleware: {request.path} → schema public"
                )
                return  # Listo, no hace falta resolver por hostname
            except Exception as exc:
                logger.warning(
                    f"SmartTenantMiddleware: no pudo forzar public para "
                    f"{request.path}: {exc}. Fallback a resolución normal."
                )

        # Para todas las demás rutas → resolución estándar por hostname
        super().process_request(request)
