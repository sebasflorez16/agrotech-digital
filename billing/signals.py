"""
Django signals para el app de billing.

NOTA: La creación de suscripciones ahora se maneja principalmente
via TenantService (billing/tenant_service.py). Esta señal solo actúa
como fallback para tenants creados directamente desde admin o shell.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from base_agrotech.models import Client
from .models import Subscription, Plan, BillingEvent
from django.utils import timezone
from datetime import timedelta


@receiver(post_save, sender=Client)
def create_free_subscription_for_new_tenant(sender, instance, created, **kwargs):
    """
    Cuando se crea un nuevo tenant manualmente (admin/shell),
    asigna plan FREE si no tiene suscripción.
    
    Si el tenant se creó via TenantService, ya tendrá suscripción
    y este signal no hace nada.
    """
    if created:
        # Verificar si ya tiene suscripción (creada por TenantService)
        if Subscription.objects.filter(tenant=instance).exists():
            return
        
        # Skip para tenant público
        if instance.schema_name == 'public':
            return
        
        try:
            # Obtener el plan FREE
            free_plan = Plan.objects.get(tier='free', is_active=True)
            
            # Plan FREE = embudo permanente (no trial con expiración).
            # Los planes pagos otorgan trial de 14 días al suscribirse vía checkout.
            now = timezone.now()
            subscription = Subscription.objects.create(
                tenant=instance,
                plan=free_plan,
                payment_gateway='manual',  # FREE no requiere pago
                status='active',  # Nunca expira — evita bloquear el embudo
                current_period_start=now,
                current_period_end=now + timedelta(days=365),  # Rolling anual
                trial_end=None,
                auto_renew=False  # FREE no se renueva automáticamente
            )
            
            # Registrar evento
            BillingEvent.objects.create(
                tenant=instance,
                subscription=subscription,
                event_type='trial.started',
                event_data={
                    'plan': free_plan.tier,
                    'created_via': 'signal_fallback',
                    'note': 'Plan FREE permanente — embudo de conversión',
                }
            )
            
        except Plan.DoesNotExist:
            # Si no existe plan FREE, log error pero no fallar
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Plan FREE no encontrado. No se pudo crear suscripción para tenant {instance.schema_name}")
