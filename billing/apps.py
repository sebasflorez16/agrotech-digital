from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'billing'
    verbose_name = 'Facturación y Suscripciones'
    
    def ready(self):
        """Importar signal handlers y registrar pasarelas de pago."""
        import billing.signals  # noqa

        # Registrar pasarelas en PaymentGatewayFactory (se auto-registran al importarse)
        import importlib
        for mod in ("billing.mercadopago_gateway", "billing.paddle_gateway", "billing.wompi_gateway"):
            try:
                importlib.import_module(mod)
            except Exception:
                logger.warning(f"No se pudo registrar la pasarela {mod}", exc_info=True)
