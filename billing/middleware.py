"""
Middleware para verificación de límites de suscripción.

Verifica que el tenant tenga una suscripción activa antes de permitir acceso.
"""

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django_tenants.utils import get_tenant_model, get_tenant
from .models import Subscription
import logging

logger = logging.getLogger(__name__)


class SubscriptionLimitMiddleware(MiddlewareMixin):
    """
    Middleware para verificar límites de suscripción por tenant.
    
    Verifica:
    - Suscripción activa
    - Trial no expirado
    - Estado de suscripción válido
    """
    
    # URLs que NO requieren suscripción activa
    EXCLUDED_PATHS = [
        '/health/',
        '/admin/',
        '/api/auth/login/',
        '/api/auth/register/',
        '/api/auth/password-reset/',
        '/billing/webhook/',
        '/billing/subscribe/',
        '/billing/plans/',
        '/static/',
        '/media/',
        '__debug__',
    ]
    
    def process_request(self, request):
        """Verificar suscripción antes de procesar request."""
        
        # Skip para URLs excluidas
        path = request.path
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return None
        
        try:
            tenant = get_tenant(request)
        except Exception:
            # No es un request con tenant
            return None
        
        # Skip para tenant público
        if tenant.schema_name == 'public':
            return None
        
        # Verificar suscripción
        try:
            subscription = tenant.subscription
        except Subscription.DoesNotExist:
            return JsonResponse({
                'error': 'No hay suscripción activa',
                'code': 'no_subscription',
                'message': 'Este tenant no tiene una suscripción configurada.',
                'action': 'Contacta al administrador o suscríbete a un plan.',
                'upgrade_url': '/billing/subscribe/'
            }, status=402)  # 402 Payment Required
        
        # Verificar estado de suscripción
        if not subscription.is_active_or_trialing():
            status_messages = {
                'canceled': 'La suscripción ha sido cancelada.',
                'expired': 'La suscripción ha expirado.',
                'past_due': 'Hay un pago pendiente. Por favor actualiza tu método de pago.',
                'paused': 'La suscripción está pausada.'
            }
            
            message = status_messages.get(
                subscription.status,
                f'Suscripción en estado: {subscription.status}'
            )
            
            return JsonResponse({
                'error': 'Suscripción inactiva',
                'code': 'subscription_inactive',
                'status': subscription.status,
                'message': message,
                'renew_url': f'/billing/renew/{subscription.uuid}/'
            }, status=402)
        
        # Verificar trial expirado
        if subscription.is_trial_expired():
            return JsonResponse({
                'error': 'Período de prueba finalizado',
                'code': 'trial_expired',
                'message': 'Tu período de prueba de 14 días ha finalizado.',
                'trial_end': subscription.trial_end.isoformat(),
                'upgrade_url': '/billing/upgrade/'
            }, status=402)
        
        # Adjuntar suscripción al request para uso posterior
        request.subscription = subscription
        
        return None
