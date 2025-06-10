"""from django.utils.deprecation import MiddlewareMixin
from django_tenants.utils import get_tenant_model
from django.core.cache import cache
from corsheaders.conf import settings as cors_settings
from urllib.parse import urlsplit
import logging

logger = logging.getLogger(__name__)

class DynamicCORSMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Obtén el dominio sin el puerto
        raw_host = request.get_host()
        domain = urlsplit(f"//{raw_host}").hostname  # Elimina el puerto si está presente
        logger.debug(f"Procesando dominio: {domain} (original: {raw_host})")

        tenant_model = get_tenant_model()

        # Intenta buscar el dominio en caché
        cached_tenant_domain = cache.get(domain)
        if cached_tenant_domain:
            cors_settings.CORS_ALLOWED_ORIGINS = [f"http://{cached_tenant_domain}"]
            logger.info(f"CORS configurado desde caché para el dominio: {cached_tenant_domain}")
            return

        try:
            # Buscar el dominio en la base de datos
            tenant_domain = tenant_model.objects.filter(domains__domain=domain).first()

            if tenant_domain:
                primary_domain = tenant_domain.domains.first().domain
                cors_settings.CORS_ALLOWED_ORIGINS = [f"http://{primary_domain}"]
                cache.set(domain, primary_domain, timeout=3600)  # Cachea el dominio
                logger.info(f"CORS configurado para el dominio: {primary_domain}")
            else:
                # Si no se encuentra el dominio, bloquea CORS
                cors_settings.CORS_ALLOWED_ORIGINS = []
                logger.warning(f"Dominio no registrado: {domain}. Bloqueando CORS.")

        except Exception as e:
            cors_settings.CORS_ALLOWED_ORIGINS = []
            logger.error(f"Error al procesar CORS para el dominio: {domain}. Detalles: {e}")
"""