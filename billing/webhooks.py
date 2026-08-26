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


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([WebhookRateThrottle])
def wompi_webhook(request):
    """Webhook de Wompi (payment_links)."""
    try:
        gateway = PaymentGatewayFactory.create("wompi")
        result = gateway.handle_webhook(request)

        if not result.get("success"):
            logger.warning(f"[WOMPI WEBHOOK] Firma invalida: {result.get('error')}")
            return Response({"status": "error", "error": "invalid_signature"}, status=401)

        action = result.get("action", "")
        reference = result.get("reference", "")

        if action == "payment_approved":
            logger.info(f"[WOMPI WEBHOOK] Pago aprobado: ref={reference}")
            _process_wompi_payment(result, reference)

        return Response({"status": "ok", "action": action}, status=200)

    except Exception as e:
        logger.exception(f"[WOMPI WEBHOOK] Error: {e}")
        return Response({"status": "processed", "error": str(e)}, status=200)


def _process_wompi_payment(payment_data, reference):
    """Activa/crea la suscripción (primer pago) o la renueva (pago recurrente)."""
    import re
    from billing.models import Subscription
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()

    # ── RENOVACIÓN: referencia renew_{tenant_id}_{uuid} ──
    renew_match = re.search(r"renew_(\d+)_", reference)
    if renew_match:
        tenant_id = int(renew_match.group(1))
        try:
            from base_agrotech.models import Client
            tenant = Client.objects.filter(id=tenant_id).first()
            if not tenant:
                logger.warning(f"[WOMPI] Tenant no encontrado (renovación) tenant_id={tenant_id}")
                return
            sub = Subscription.objects.filter(tenant=tenant).first()
            if sub:
                base = sub.current_period_end if (sub.current_period_end and sub.current_period_end > now) else now
                sub.status = "active"
                sub.current_period_start = now
                sub.current_period_end = base + timedelta(days=30)
                sub.payment_gateway = "wompi"
                sub.save(update_fields=[
                    "status", "current_period_start", "current_period_end",
                    "payment_gateway", "updated_at",
                ])
                logger.info(f"[WOMPI] Suscripción renovada: tenant_id={tenant.id} hasta {sub.current_period_end.date()}")
        except Exception as e:
            logger.error(f"[WOMPI] Error renovando suscripción: {e}")
        return

    # ── PRIMER PAGO: referencia sub_{tenant_id}_{plan_tier}_{uuid} ──
    match = re.search(r"sub_(\d+)_([a-z]+)_", reference)
    if not match:
        logger.warning(f"[WOMPI] No se puede extraer tenant_id/plan de referencia: {reference}")
        return

    tenant_id = int(match.group(1))
    plan_tier = match.group(2)
    try:
        from base_agrotech.models import Client
        tenant = Client.objects.filter(id=tenant_id).first()
        if not tenant:
            logger.warning(f"[WOMPI] Tenant no encontrado para tenant_id={tenant_id}")
            return

        sub = Subscription.objects.filter(tenant=tenant).first()
        if sub:
            if sub.status in ("trialing", "canceled"):
                sub.status = "active"
                sub.current_period_start = now
                sub.current_period_end = now + timedelta(days=30)
                sub.payment_gateway = "wompi"
                sub.save()
        else:
            from billing.models import Plan
            plan = Plan.objects.filter(tier=plan_tier, is_active=True).first() or Plan.objects.filter(is_active=True).exclude(tier="free").first()
            Subscription.objects.create(
                tenant=tenant, plan=plan, payment_gateway="wompi",
                status="active", current_period_start=now,
                current_period_end=now + timedelta(days=30),
            )

        logger.info(f"[WOMPI] Suscripcion activada: tenant_id={tenant.id}")
    except Exception as e:
        logger.error(f"[WOMPI] Error activando suscripcion: {e}")
