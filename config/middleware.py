"""
Middleware personalizado para AgroTech Digital.

Incluye:
- HealthCheckMiddleware: intercepta /health/ antes de django-tenants
- SmartTenantMiddleware: reemplaza TenantMainMiddleware con resolución
  inteligente de tenant: por header, JWT o hostname.
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
    Extiende TenantMainMiddleware para:
    1. Forzar schema 'public' en rutas de billing/auth/tokens.
    2. Resolver tenant desde header X-Tenant-Domain si está presente.
    3. Resolver tenant desde JWT (Authorization: Bearer) si el hostname resuelve a public.
    4. Fallback a resolución estándar por hostname.
    
    Esto permite que el frontend SPA (Netlify) envíe requests a través
    de localhost sin necesidad de subdominios, usando el JWT para
    resolver automáticamente el tenant del usuario.
    """

    # Prefijos de URL que SIEMPRE deben correr contra el schema public
    PUBLIC_PATH_PREFIXES = [
        '/api/auth/',
        '/api/token/',
    ]
    
    # Hostnames que deben usar ROOT_URLCONF completo en desarrollo
    DEV_HOSTNAMES = ['localhost', '127.0.0.1']

    def process_request(self, request):
        # Detectar si estamos en desarrollo local
        hostname = request.get_host().split(':')[0].lower()
        is_dev = hostname in self.DEV_HOSTNAMES
        
        # ¿Es una ruta pública (auth/tokens)?
        is_public_path = any(
            request.path.startswith(prefix)
            for prefix in self.PUBLIC_PATH_PREFIXES
        )

        if is_public_path:
            self._set_public_tenant(request)
            return

        # Intentar resolver tenant desde header X-Tenant-Domain
        tenant_domain = request.META.get('HTTP_X_TENANT_DOMAIN', '').strip()
        if tenant_domain:
            try:
                from base_agrotech.models import Domain
                domain_obj = Domain.objects.select_related('tenant').get(
                    domain=tenant_domain
                )
                request.tenant = domain_obj.tenant
                connection.set_tenant(domain_obj.tenant)
                logger.debug(
                    f"SmartTenantMiddleware: X-Tenant-Domain={tenant_domain} "
                    f"→ schema {domain_obj.tenant.schema_name}"
                )
                return
            except Exception:
                pass

        # Resolución estándar por hostname
        super().process_request(request)

        # Si el hostname resolvió a 'public' y hay JWT,
        # intentar resolver el tenant real desde el token del usuario
        if (
            hasattr(request, 'tenant')
            and request.tenant.schema_name == get_public_schema_name()
            and not is_public_path
        ):
            tenant_from_jwt = self._resolve_tenant_from_jwt(request)
            if tenant_from_jwt:
                request.tenant = tenant_from_jwt
                connection.set_tenant(tenant_from_jwt)
                # NO cambiar request.urlconf — usar ROOT_URLCONF (config.urls)
                # que tiene TODAS las rutas incluyendo billing, parcels, etc.
                if hasattr(request, 'urlconf'):
                    del request.urlconf
                logger.debug(
                    f"SmartTenantMiddleware: JWT → schema {tenant_from_jwt.schema_name}"
                )
            elif is_dev:
                # En desarrollo local sin JWT válido, usar ROOT_URLCONF
                # para poder acceder a todas las rutas de la API
                if hasattr(request, 'urlconf'):
                    del request.urlconf
                logger.debug(
                    f"SmartTenantMiddleware: Dev mode sin JWT → schema public (ROOT_URLCONF)"
                )

    def _set_public_tenant(self, request, use_full_urlconf=False):
        """
        Fuerza el schema public para rutas de auth/tokens.
        
        Args:
            use_full_urlconf: Si True, usa ROOT_URLCONF con todas las rutas
                             (útil para desarrollo local sin JWT)
        """
        try:
            from base_agrotech.models import Client
            public_tenant = Client.objects.get(
                schema_name=get_public_schema_name()
            )
            request.tenant = public_tenant
            connection.set_tenant(public_tenant)
            
            # En desarrollo local, usar ROOT_URLCONF completo
            # para poder acceder a todas las rutas (parcels, etc.)
            if use_full_urlconf:
                if hasattr(request, 'urlconf'):
                    del request.urlconf
                logger.debug(
                    f"SmartTenantMiddleware: {request.path} → schema public (ROOT_URLCONF)"
                )
            elif hasattr(settings, 'PUBLIC_SCHEMA_URLCONF'):
                request.urlconf = settings.PUBLIC_SCHEMA_URLCONF
                logger.debug(
                    f"SmartTenantMiddleware: {request.path} → schema public (PUBLIC_URLCONF)"
                )
        except Exception as exc:
            logger.warning(
                f"SmartTenantMiddleware: no pudo forzar public: {exc}"
            )
            super().process_request(request)

    def _resolve_tenant_from_jwt(self, request):
        """
        Decodifica el JWT del header Authorization y busca el tenant
        del usuario en la BD. Retorna el Client o None.
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None
        
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from django.contrib.auth import get_user_model
            
            token_str = auth_header.split(' ')[1]
            token = AccessToken(token_str)
            user_id = token.get('user_id')
            
            if not user_id:
                return None
            
            User = get_user_model()
            user = User.objects.select_related('tenant').get(id=user_id)
            
            if user.tenant and user.tenant.schema_name != get_public_schema_name():
                return user.tenant
        except Exception as exc:
            logger.debug(f"SmartTenantMiddleware: JWT resolve failed: {exc}")
        
        return None
