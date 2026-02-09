"""
Webhooks endpoints para pasarelas de pago.

Endpoints:
- /api/webhooks/mercadopago/
- /api/webhooks/paddle/

SEGURIDAD:
- Rate limiting para prevenir DDoS
- Validación de firma obligatoria en producción
- Logging completo de eventos
- Idempotencia con external_event_id
"""

from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from django.core.cache import cache
from .gateways import PaymentGatewayFactory
import logging
import hashlib

logger = logging.getLogger(__name__)


class WebhookRateThrottle(AnonRateThrottle):
    """
    Rate limiting específico para webhooks.
    Permite 100 requests por minuto por IP.
    """
    rate = '100/min'
    
    def get_cache_key(self, request, view):
        # Usar IP + endpoint como cache key
        ident = self.get_ident(request)
        return f"webhook_throttle_{ident}"


def _get_request_fingerprint(request):
    """
    Genera un fingerprint único del request para detección de duplicados.
    """
    body = request.body.decode('utf-8', errors='ignore') if request.body else ''
    return hashlib.sha256(body.encode()).hexdigest()[:32]


def _is_duplicate_webhook(fingerprint, ttl=300):
    """
    Verifica si un webhook ya fue procesado recientemente.
    TTL de 5 minutos por defecto.
    """
    cache_key = f"webhook_processed_{fingerprint}"
    if cache.get(cache_key):
        return True
    cache.set(cache_key, True, ttl)
    return False


@api_view(['POST'])
@permission_classes([AllowAny])  # Webhooks no usan autenticación normal
@throttle_classes([WebhookRateThrottle])
def mercadopago_webhook(request):
    """
    Webhook endpoint para MercadoPago.
    
    POST /billing/webhooks/mercadopago/
    
    MercadoPago envía notificaciones cuando:
    - Se procesa un pago
    - Cambia el estado de una suscripción
    - Falla un pago
    
    SEGURIDAD:
    - Rate limiting: 100/min por IP
    - Validación de firma HMAC-SHA256
    - Deduplicación de eventos
    """
    # Log de entrada
    logger.info(f"Webhook MercadoPago recibido de IP: {request.META.get('REMOTE_ADDR')}")
    
    # Verificar duplicados
    fingerprint = _get_request_fingerprint(request)
    if _is_duplicate_webhook(fingerprint):
        logger.info(f"Webhook MercadoPago duplicado ignorado: {fingerprint[:16]}")
        return Response({'status': 'ok', 'message': 'Already processed'}, status=200)
    
    try:
        gateway = PaymentGatewayFactory.create('mercadopago')
        result = gateway.handle_webhook(request)
        
        # Si la firma es inválida, rechazar
        if result.get('status') == 'invalid_signature':
            logger.warning(f"Webhook MercadoPago con firma inválida desde IP: {request.META.get('REMOTE_ADDR')}")
            return Response({
                'status': 'error',
                'error': 'Invalid signature'
            }, status=401)
        
        logger.info(f"Webhook MercadoPago procesado exitosamente: {result}")
        return Response(result, status=200)
    
    except Exception as e:
        logger.exception(f"Error procesando webhook MercadoPago: {str(e)}")
        # Retornar 200 para evitar reintentos excesivos de MercadoPago
        # El error se registra en logs para investigación
        return Response({
            'status': 'error',
            'error': 'Internal error - logged for investigation'
        }, status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([WebhookRateThrottle])
def paddle_webhook(request):
    """
    Webhook endpoint para Paddle.
    
    POST /billing/webhooks/paddle/
    
    Paddle envía notificaciones cuando:
    - Se crea una suscripción
    - Se actualiza una suscripción
    - Se cancela una suscripción
    - Se procesa un pago (éxito o fallo)
    
    SEGURIDAD:
    - Rate limiting: 100/min por IP
    - Validación de firma (HMAC o RSA según versión)
    - Deduplicación de eventos
    """
    # Log de entrada
    logger.info(f"Webhook Paddle recibido de IP: {request.META.get('REMOTE_ADDR')}")
    
    # Verificar duplicados
    fingerprint = _get_request_fingerprint(request)
    if _is_duplicate_webhook(fingerprint):
        logger.info(f"Webhook Paddle duplicado ignorado: {fingerprint[:16]}")
        return Response({'status': 'ok', 'message': 'Already processed'}, status=200)
    
    try:
        gateway = PaymentGatewayFactory.create('paddle')
        result = gateway.handle_webhook(request)
        
        # Si la firma es inválida, rechazar
        if result.get('status') == 'error' and 'signature' in str(result.get('error', '')).lower():
            logger.warning(f"Webhook Paddle con firma inválida desde IP: {request.META.get('REMOTE_ADDR')}")
            return Response({
                'status': 'error',
                'error': 'Invalid signature'
            }, status=401)
        
        logger.info(f"Webhook Paddle procesado exitosamente: {result}")
        return Response(result, status=200)
    
    except Exception as e:
        logger.exception(f"Error procesando webhook Paddle: {str(e)}")
        # Retornar 200 para evitar reintentos excesivos de Paddle
        return Response({
            'status': 'error',
            'error': 'Internal error - logged for investigation'
        }, status=200)
