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
from django.conf import settings
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


def _is_duplicate_webhook(fingerprint):
    """Verifica si un webhook ya fue procesado recientemente.

    No marca el evento: se marca SOLO después de procesarlo correctamente.
    Antes se marcaba antes de procesar y un fallo transitorio perdía el evento.
    """
    try:
        return bool(cache.get(f"webhook_processed_{fingerprint}"))
    except Exception:
        return False


def _mark_webhook_processed(fingerprint, ttl=300):
    """Marca un webhook como procesado (idempotencia best-effort)."""
    try:
        cache.set(f"webhook_processed_{fingerprint}", True, ttl)
    except Exception:
        pass


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
        _mark_webhook_processed(fingerprint)
        return Response(result, status=200)
    
    except Exception as e:
        logger.exception(f"Error procesando webhook MercadoPago: {str(e)}")
        # 5xx para que MercadoPago reintente el evento.
        return Response({
            'status': 'error',
            'error': 'Internal error - logged for investigation'
        }, status=500)


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

    # Paddle está deshabilitado: su webhook histórico no verificaba firma de
    # forma robusta y podía activar planes. No procesar eventos sin contrato.
    if not getattr(settings, 'PADDLE_ENABLED', False):
        logger.warning("[PADDLE] Webhook rechazado: PADDLE_ENABLED=False")
        return Response({'status': 'error', 'error': 'paddle_disabled'}, status=503)
    
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
        _mark_webhook_processed(fingerprint)
        return Response(result, status=200)
    
    except Exception as e:
        logger.exception(f"Error procesando webhook Paddle: {str(e)}")
        # 5xx para que Paddle reintente el evento.
        return Response({
            'status': 'error',
            'error': 'Internal error - logged for investigation'
        }, status=500)


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
        # Devolver 5xx para que Wompi reintente. Antes se devolvía 200 y el
        # evento se perdía si la base de datos fallaba de forma transitoria.
        return Response({"status": "error", "error": "internal_error"}, status=500)


def _create_wompi_invoice(tenant, sub, payment_data, reference):
    """Crea (idempotente) la factura pagada de un pago aprobado de Wompi."""
    from decimal import Decimal
    from django.utils import timezone
    from billing.models import Invoice

    try:
        if Invoice.objects.filter(tenant=tenant, metadata__reference=reference).exists():
            return
        amount_cents = int((payment_data or {}).get("amount_cents") or 0)
        amount = (Decimal(amount_cents) / Decimal("100")).quantize(Decimal("0.01"))
        # El precio mostrado al cliente incluye IVA. La factura debe desglosar
        # base + impuesto sin inflar el total (antes se sumaba 19% dos veces).
        subtotal = (amount / Decimal("1.19")).quantize(Decimal("0.01"))
        tax_amount = (amount - subtotal).quantize(Decimal("0.01"))
        now = timezone.now()
        plan_name = sub.plan.name if (sub and sub.plan_id) else "AgroTech Digital"
        tx_id = (payment_data or {}).get('transaction_id') or reference
        Invoice.objects.create(
            invoice_number=f"WOMPI-{tx_id}"[:50],
            tenant=tenant,
            subscription=sub,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total=amount,
            currency="COP",
            status="paid",
            invoice_date=now.date(),
            due_date=now.date(),
            paid_at=now,
            line_items=[{"description": f"Plan {plan_name}", "quantity": 1, "amount": float(subtotal)}],
            metadata={
                "gateway": "wompi",
                "reference": reference,
                "transaction_id": (payment_data or {}).get("transaction_id"),
            },
        )
        logger.info(f"[WOMPI] Factura creada para {tenant.name} ref={reference}")
    except Exception as e:
        logger.error(f"[WOMPI] No se pudo crear factura para {reference}: {e}")


def _send_meta_purchase(event_name, event_id, tenant, plan, payer_email, amount_cents, intent):
    """Envía Purchase/Subscribe a Meta CAPI sin romper el webhook."""
    try:
        if not (intent or {}).get('marketing_consent'):
            return
        from core.meta_capi import send_event

        send_event(
            event_name,
            event_id,
            email=payer_email or '',
            external_id=str(tenant.id),
            fbp=(intent or {}).get('fbp', ''),
            fbc=(intent or {}).get('fbc', ''),
            value=(amount_cents or 0) / 100.0,
            currency='COP',
            custom_data={
                'content_name': plan.tier if plan else '',
                'content_ids': [plan.tier] if plan else [],
                'transaction_id': event_id,
            },
        )
    except Exception as exc:
        logger.warning(f"[META CAPI] No se pudo enviar {event_name}: {exc}")


def _process_wompi_payment(payment_data, reference):
    """Activa/crea la suscripción (primer pago) o la renueva (pago recurrente).

    Reglas:
    - El ciclo (mensual/anual) sale de la referencia firmada y/o de la
      suscripción, nunca del cliente.
    - Un evento duplicado no extiende el período dos veces.
    - Un pago anual otorga 365 días (antes otorgaba 30).
    - El monto aprobado debe coincidir con el plan para activar.
    """
    import re
    from billing.models import Subscription, BillingEvent
    from django.utils import timezone
    from .payment_utils import (
        add_billing_days,
        get_checkout_intent,
        normalize_cycle,
        parse_wompi_reference,
        period_end,
        plan_amount_cents,
    )

    now = timezone.now()
    tx_id = str((payment_data or {}).get("transaction_id") or "")
    intent = get_checkout_intent(reference)
    parsed = parse_wompi_reference(reference)
    cycle = normalize_cycle(intent.get("billing_cycle") or parsed.get("cycle") or "monthly")

    # Idempotencia durable a nivel de evento (Wompi puede reintentar).
    if tx_id and BillingEvent.objects.filter(
        external_event_id=tx_id,
        event_type__in=["subscription.renewed", "subscription.created", "invoice.paid"],
    ).exists():
        logger.info(f"[WOMPI] Evento ya procesado tx={tx_id} ref={reference}; se ignora")
        return

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
                cycle = normalize_cycle(sub.billing_cycle or cycle)
                sub.status = "active"
                sub.current_period_start = now
                sub.current_period_end = add_billing_days(sub.current_period_end, cycle)
                sub.trial_end = None
                sub.auto_renew = True
                sub.payment_gateway = "wompi"
                sub.save(update_fields=[
                    "status", "current_period_start", "current_period_end",
                    "trial_end", "auto_renew", "payment_gateway", "updated_at",
                ])
                tenant.paid_until = sub.current_period_end.date()
                tenant.on_trial = False
                tenant.save(update_fields=["paid_until", "on_trial"])
                _create_wompi_invoice(tenant, sub, payment_data, reference)
                BillingEvent.objects.create(
                    tenant=tenant,
                    subscription=sub,
                    event_type="subscription.renewed",
                    event_data={
                        "gateway": "wompi",
                        "reference": reference,
                        "billing_cycle": cycle,
                        "period_end": sub.current_period_end.isoformat(),
                    },
                    external_event_id=tx_id or reference,
                )
                _send_meta_purchase(
                    event_name="Subscribe",
                    event_id=f"subscribe_{reference}_{tx_id or 'renewal'}",
                    tenant=tenant,
                    plan=sub.plan,
                    payer_email=(payment_data or {}).get("customer_email", ""),
                    amount_cents=int((payment_data or {}).get("amount_cents") or 0),
                    intent=intent,
                )
                logger.info(
                    f"[WOMPI] Suscripción renovada: tenant_id={tenant.id} "
                    f"cycle={cycle} hasta {sub.current_period_end.date()}"
                )
        except Exception as e:
            logger.error(f"[WOMPI] Error renovando suscripción: {e}")
            raise
        return

    # ── PRIMER PAGO: referencia sub_{tenant_id}_{plan_tier}_{cycle}_{uuid} ──
    if not parsed:
        logger.warning(f"[WOMPI] No se puede extraer tenant_id/plan de referencia: {reference}")
        return

    tenant_id = parsed["tenant_id"]
    plan_tier = parsed["plan_tier"]

    from base_agrotech.models import Client
    from billing.models import Plan

    try:
        tenant = Client.objects.filter(id=tenant_id).first()
        if not tenant:
            payer_email = (payment_data or {}).get("customer_email", "")
            if tenant_id == 0 and payer_email:
                # Pago de visitante anónimo: creamos la cuenta aquí, sin depender
                # de que la página de éxito llame a confirm-payment.
                from billing.tenant_service import TenantService

                plan = Plan.objects.filter(tier=plan_tier, is_active=True).first()
                if not plan:
                    logger.error(f"[WOMPI] Plan inexistente en pago anónimo: {plan_tier}")
                    return
                expected = plan_amount_cents(plan, cycle)
                received = int((payment_data or {}).get("amount_cents") or 0)
                if received != expected:
                    logger.error(
                        f"[WOMPI] Monto no coincide (anónimo): ref={reference} "
                        f"recibido={received} esperado={expected}"
                    )
                    return

                # Si el email ya tiene cuenta (p. ej. plan free), aplicar el
                # plan pagado a ese tenant. No crear una cuenta duplicada y
                # no dejar el pago sin efecto si la página de éxito no carga.
                from django.contrib.auth import get_user_model

                User = get_user_model()
                existing_user = User.objects.filter(
                    email__iexact=payer_email,
                    tenant_id__isnull=False,
                ).first()
                if existing_user:
                    existing_tenant = Client.objects.filter(id=existing_user.tenant_id).first()
                    if existing_tenant:
                        upgraded = TenantService.upgrade_subscription(
                            tenant=existing_tenant,
                            new_plan_tier=plan_tier,
                            billing_cycle=cycle,
                            external_subscription_id=reference,
                            payment_gateway="wompi",
                            payer_email=payer_email,
                        )
                        if upgraded.get("success"):
                            upgraded_sub = Subscription.objects.filter(
                                tenant=existing_tenant
                            ).first()
                            if upgraded_sub:
                                _create_wompi_invoice(
                                    existing_tenant, upgraded_sub, payment_data, reference
                                )
                                BillingEvent.objects.create(
                                    tenant=existing_tenant,
                                    subscription=upgraded_sub,
                                    event_type="subscription.created",
                                    event_data={
                                        "gateway": "wompi",
                                        "reference": reference,
                                        "billing_cycle": cycle,
                                        "plan": plan_tier,
                                        "created_via": "webhook_existing_account",
                                    },
                                    external_event_id=tx_id or reference,
                                )
                                _send_meta_purchase(
                                    event_name="Purchase",
                                    event_id=f"purchase_{reference}",
                                    tenant=existing_tenant,
                                    plan=upgraded_sub.plan,
                                    payer_email=payer_email,
                                    amount_cents=int((payment_data or {}).get("amount_cents") or 0),
                                    intent=intent,
                                )
                        else:
                            logger.error(
                                f"[WOMPI] No se pudo aplicar plan a cuenta existente "
                                f"{payer_email}: {upgraded.get('error')}"
                            )
                        return

                local = payer_email.split("@")[0]
                created = TenantService.create_tenant_for_subscription(
                    tenant_name=intent.get("tenant_name") or local,
                    plan_tier=plan_tier,
                    billing_cycle=cycle,
                    payer_email=payer_email,
                    external_subscription_id=reference,
                    payment_gateway="wompi",
                    username=intent.get("username") or local.replace(".", "_").replace("-", "_"),
                    password=intent.get("password") or None,
                )
                if created.get("success"):
                    logger.info(f"[WOMPI] Cuenta creada desde webhook (pago anónimo): {payer_email}")
                    new_sub = Subscription.objects.filter(
                        external_subscription_id=reference
                    ).first()
                    if new_sub:
                        new_tenant = getattr(new_sub, "tenant", None)
                        if new_tenant:
                            _create_wompi_invoice(new_tenant, new_sub, payment_data, reference)
                            BillingEvent.objects.create(
                                tenant=new_tenant,
                                subscription=new_sub,
                                event_type="subscription.created",
                                event_data={
                                    "gateway": "wompi",
                                    "reference": reference,
                                    "billing_cycle": cycle,
                                    "plan": plan_tier,
                                },
                                external_event_id=tx_id or reference,
                            )
                            _send_meta_purchase(
                                event_name="Purchase",
                                event_id=f"purchase_{reference}",
                                tenant=new_tenant,
                                plan=new_sub.plan,
                                payer_email=payer_email,
                                amount_cents=int((payment_data or {}).get("amount_cents") or 0),
                                intent=intent,
                            )
                else:
                    logger.error(f"[WOMPI] No se pudo crear cuenta anónima: {created.get('error')}")
                return
            logger.warning(
                f"[WOMPI] Tenant no encontrado para tenant_id={tenant_id} "
                f"(ref={reference}). Sin customer_email no se puede crear la cuenta."
            )
            return

        # El plan viene en la referencia; si no existe, usar 'basic' (NO .first(),
        # que puede devolver cualquier plan según el orden de IDs).
        plan = (
            Plan.objects.filter(tier=plan_tier, is_active=True).first()
            or Plan.objects.filter(tier="basic", is_active=True).first()
            or Plan.objects.filter(is_active=True).exclude(tier="free").first()
        )
        if not plan:
            logger.error(f"[WOMPI] No hay plan activo para activar tenant_id={tenant_id}")
            return

        expected = plan_amount_cents(plan, cycle)
        received = int((payment_data or {}).get("amount_cents") or 0)
        if received != expected:
            logger.error(
                f"[WOMPI] Monto no coincide: ref={reference} tenant={tenant_id} "
                f"recibido={received} esperado={expected} plan={plan.tier} cycle={cycle}"
            )
            return

        sub = Subscription.objects.filter(tenant=tenant).first()
        if sub:
            if sub.external_subscription_id == reference and sub.status == "active":
                logger.info(f"[WOMPI] Pago ya aplicado ref={reference}; se ignora")
                return
            # Upgrade/activación: pasa del plan free (o trial) al plan pagado.
            old_tier = sub.plan.tier if sub.plan_id else None
            sub.plan = plan
            sub.status = "active"
            sub.billing_cycle = cycle
            sub.current_period_start = now
            sub.current_period_end = period_end(now, cycle)
            sub.trial_end = None
            sub.payment_gateway = "wompi"
            sub.external_subscription_id = reference
            sub.auto_renew = True
            sub.cancel_at_period_end = False
            sub.ended_at = None
            sub.canceled_at = None
            sub.save()
            logger.info(
                f"[WOMPI] Suscripción activada/upgrade: tenant_id={tenant.id} "
                f"{old_tier} → {plan.tier} cycle={cycle}"
            )
        else:
            sub = Subscription.objects.create(
                tenant=tenant, plan=plan, payment_gateway="wompi",
                status="active", billing_cycle=cycle,
                current_period_start=now,
                current_period_end=period_end(now, cycle),
                external_subscription_id=reference, auto_renew=True,
            )
            logger.info(
                f"[WOMPI] Suscripción creada: tenant_id={tenant.id} "
                f"plan={plan.tier} cycle={cycle}"
            )

        tenant.paid_until = sub.current_period_end.date()
        tenant.on_trial = False
        tenant.save(update_fields=["paid_until", "on_trial"])
        _create_wompi_invoice(tenant, sub, payment_data, reference)
        BillingEvent.objects.create(
            tenant=tenant,
            subscription=sub,
            event_type="subscription.created",
            event_data={
                "gateway": "wompi",
                "reference": reference,
                "billing_cycle": cycle,
                "plan": plan.tier,
                "period_end": sub.current_period_end.isoformat(),
            },
            external_event_id=tx_id or reference,
        )
        _send_meta_purchase(
            event_name="Purchase",
            event_id=f"purchase_{reference}",
            tenant=tenant,
            plan=plan,
            payer_email=(payment_data or {}).get("customer_email", ""),
            amount_cents=int((payment_data or {}).get("amount_cents") or 0),
            intent=intent,
        )
    except Exception as e:
        logger.error(f"[WOMPI] Error activando suscripcion: {e}")
        raise
