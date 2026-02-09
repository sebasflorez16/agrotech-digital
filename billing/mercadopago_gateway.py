"""
Integración con MercadoPago para Colombia (COP).

MercadoPago maneja:
- Suscripciones recurrentes (preapproval)
- Pagos únicos
- Webhooks para notificaciones
"""

import mercadopago
import hashlib
import hmac
from typing import Dict, Any
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .gateways import PaymentGateway, PaymentGatewayFactory
from .models import Subscription, Invoice, BillingEvent
from .tenant_service import TenantService
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class MercadoPagoGateway(PaymentGateway):
    """
    Implementación de PaymentGateway para MercadoPago.
    
    Documentación: https://www.mercadopago.com.co/developers/es/docs
    """
    
    def __init__(self):
        """Inicializar SDK de MercadoPago."""
        self.access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', '')
        
        if not self.access_token:
            logger.warning("MERCADOPAGO_ACCESS_TOKEN no configurado en settings")
        
        self.sdk = mercadopago.SDK(self.access_token)
        self.currency = 'COP'
    
    def create_subscription(self, user, plan, payment_method_token=None) -> Dict[str, Any]:
        """
        Crear suscripción recurrente en MercadoPago.
        
        MercadoPago usa "preapproval" para suscripciones.
        """
        try:
            # Obtener o crear tenant
            tenant = user.tenant if hasattr(user, 'tenant') else None
            
            # Preparar datos de suscripción
            subscription_data = {
                "reason": f"{plan.name} - AgroTech Digital",
                "auto_recurring": {
                    "frequency": plan.frequency,  # 1=mensual, 12=anual
                    "frequency_type": "months",
                    "transaction_amount": float(plan.price_cop),
                    "currency_id": self.currency,
                },
                "back_url": f"{settings.SITE_URL}/billing/success/",
                "payer_email": user.email,
                "status": "pending",  # Se activará tras primer pago
            }
            
            # Si hay token de método de pago, agregarlo
            if payment_method_token:
                subscription_data["card_token_id"] = payment_method_token
            
            # Crear suscripción en MercadoPago
            result = self.sdk.preapproval().create(subscription_data)
            
            if result["status"] == 201:
                response = result['response']
                
                logger.info(f"Suscripción MercadoPago creada: {response['id']}")
                
                return {
                    'success': True,
                    'subscription_id': response['id'],
                    'init_point': response.get('init_point'),  # URL de pago
                    'sandbox_init_point': response.get('sandbox_init_point'),
                    'status': response.get('status', 'pending'),
                }
            else:
                error_message = result.get('response', {}).get('message', 'Error desconocido')
                logger.error(f"Error creando suscripción MercadoPago: {error_message}")
                
                return {
                    'success': False,
                    'error': error_message
                }
        
        except Exception as e:
            logger.exception(f"Excepción creando suscripción MercadoPago: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Cancelar suscripción en MercadoPago.
        """
        try:
            result = self.sdk.preapproval().update(subscription_id, {"status": "cancelled"})
            
            if result["status"] == 200:
                logger.info(f"Suscripción MercadoPago cancelada: {subscription_id}")
                return {'success': True}
            else:
                error_message = result.get('response', {}).get('message', 'Error desconocido')
                logger.error(f"Error cancelando suscripción MercadoPago: {error_message}")
                return {'success': False, 'error': error_message}
        
        except Exception as e:
            logger.exception(f"Excepción cancelando suscripción: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_subscription_status(self, subscription_id: str) -> Dict[str, Any]:
        """
        Obtener estado de suscripción en MercadoPago.
        """
        try:
            result = self.sdk.preapproval().get(subscription_id)
            
            if result["status"] == 200:
                response = result['response']
                
                return {
                    'success': True,
                    'status': response.get('status'),
                    'next_payment_date': response.get('next_payment_date'),
                    'last_modified': response.get('last_modified'),
                    'data': response
                }
            else:
                return {
                    'success': False,
                    'error': 'Suscripción no encontrada'
                }
        
        except Exception as e:
            logger.exception(f"Error obteniendo status de suscripción: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_payment_method_info(self, subscription_id: str) -> Dict[str, Any]:
        """
        Obtener información del método de pago.
        """
        try:
            result = self.sdk.preapproval().get(subscription_id)
            
            if result["status"] == 200:
                response = result['response']
                
                return {
                    'success': True,
                    'payment_method': response.get('payment_method_id'),
                    'last_four_digits': response.get('last_four_digits'),
                    'card_brand': response.get('card_brand'),
                }
            else:
                return {'success': False}
        
        except Exception as e:
            logger.exception(f"Error obteniendo método de pago: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def handle_webhook(self, request) -> Dict[str, Any]:
        """
        Procesar webhooks de MercadoPago.
        
        MercadoPago envía notificaciones para:
        - payment: Pagos individuales
        - subscription_preapproval: Cambios en suscripción
        """
        try:
            # Validar firma del webhook (seguridad)
            if not self._verify_webhook_signature(request):
                logger.warning("Webhook MercadoPago con firma inválida")
                return {'status': 'invalid_signature'}
            
            # Obtener datos del webhook
            data = request.data if hasattr(request, 'data') else request.POST
            webhook_type = data.get('type')
            
            logger.info(f"Webhook MercadoPago recibido: {webhook_type}")
            
            # Procesar según tipo de evento
            if webhook_type == 'payment':
                return self._handle_payment_webhook(data)
            
            elif webhook_type in ['subscription_preapproval', 'preapproval']:
                return self._handle_subscription_webhook(data)
            
            else:
                logger.info(f"Webhook type no manejado: {webhook_type}")
                return {'status': 'ok', 'message': 'Event type not handled'}
        
        except Exception as e:
            logger.exception(f"Error procesando webhook MercadoPago: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _verify_webhook_signature(self, request) -> bool:
        """
        Verificar la firma del webhook de MercadoPago.
        
        MercadoPago envía los headers:
        - x-signature: "ts=<ts>,v1=<hash>"
        - x-request-id: ID único del request
        
        Documentación:
        https://www.mercadopago.com.co/developers/es/docs/your-integrations/notifications/webhooks
        
        SEGURIDAD: En producción, RECHAZA webhooks si no hay secret configurado.
        """
        webhook_secret = getattr(settings, 'MERCADOPAGO_WEBHOOK_SECRET', '')
        is_production = not getattr(settings, 'DEBUG', True)
        
        # FAIL-SAFE: En producción sin secret, RECHAZAR
        if not webhook_secret:
            if is_production:
                logger.error(
                    "MERCADOPAGO_WEBHOOK_SECRET no configurado en producción. "
                    "Webhook RECHAZADO por seguridad. Configure la variable de entorno."
                )
                return False
            else:
                logger.warning(
                    "MERCADOPAGO_WEBHOOK_SECRET no configurado en desarrollo. "
                    "Webhook aceptado SIN verificación. Configúralo para producción."
                )
                return True
        
        signature_header = request.META.get('HTTP_X_SIGNATURE', '')
        request_id = request.META.get('HTTP_X_REQUEST_ID', '')
        
        if not signature_header or not request_id:
            logger.warning("Webhook MercadoPago sin headers x-signature o x-request-id")
            return False
        
        try:
            # Parsear "ts=<timestamp>,v1=<hash>" del header x-signature
            parts = {}
            for part in signature_header.split(','):
                key_value = part.split('=', 1)
                if len(key_value) == 2:
                    parts[key_value[0].strip()] = key_value[1].strip()
            
            ts = parts.get('ts')
            received_hash = parts.get('v1')
            
            if not ts or not received_hash:
                logger.warning("Formato de x-signature inválido")
                return False
            
            # Obtener el data.id del body
            data = request.data if hasattr(request, 'data') else {}
            data_id = data.get('data', {}).get('id', '')
            
            # Construir el manifest: "id:<data_id>;request-id:<request_id>;ts:<ts>;"
            manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
            
            # Calcular HMAC-SHA256
            expected_hash = hmac.new(
                webhook_secret.encode('utf-8'),
                manifest.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Comparación segura contra timing attacks
            is_valid = hmac.compare_digest(expected_hash, received_hash)
            
            if not is_valid:
                logger.warning(
                    f"Firma MercadoPago inválida. "
                    f"Expected: {expected_hash[:16]}... Got: {received_hash[:16]}..."
                )
            
            return is_valid
            
        except Exception as e:
            logger.exception(f"Error verificando firma MercadoPago: {str(e)}")
            return False
    
    def _handle_payment_webhook(self, data) -> Dict[str, Any]:
        """
        Manejar webhook de pago.
        """
        payment_id = data.get('data', {}).get('id')
        
        if not payment_id:
            return {'status': 'error', 'error': 'No payment ID'}
        
        # Consultar detalles del pago
        payment_info = self.sdk.payment().get(payment_id)
        
        if payment_info['status'] != 200:
            return {'status': 'error', 'error': 'Payment not found'}
        
        payment = payment_info['response']
        
        # Procesar según estado del pago
        if payment['status'] == 'approved':
            self._process_successful_payment(payment)
        
        elif payment['status'] in ['rejected', 'cancelled']:
            self._process_failed_payment(payment)
        
        return {'status': 'ok'}
    
    def _handle_subscription_webhook(self, data) -> Dict[str, Any]:
        """
        Manejar webhook de suscripción.
        
        Si la suscripción se activa (authorized) y no existe tenant → crearlo.
        Si la suscripción se cancela → desactivar tenant.
        """
        preapproval_id = data.get('data', {}).get('id')
        
        if not preapproval_id:
            return {'status': 'error', 'error': 'No subscription ID'}
        
        # Consultar detalles de la suscripción en MercadoPago
        sub_info = self.sdk.preapproval().get(preapproval_id)
        
        if sub_info['status'] != 200:
            return {'status': 'error', 'error': 'Subscription not found'}
        
        subscription_data = sub_info['response']
        mp_status = subscription_data.get('status')
        external_ref = subscription_data.get('external_reference', '')
        payer_email = subscription_data.get('payer_email', '')
        
        # Intentar actualizar suscripción existente
        try:
            subscription = Subscription.objects.get(
                external_subscription_id=preapproval_id,
                payment_gateway='mercadopago'
            )
            
            # Mapear estados de MercadoPago a nuestros estados
            status_mapping = {
                'authorized': 'active',
                'paused': 'paused',
                'cancelled': 'canceled',
            }
            
            new_status = status_mapping.get(mp_status, subscription.status)
            
            if new_status != subscription.status:
                old_status = subscription.status
                subscription.status = new_status
                subscription.save()
                
                logger.info(f"Suscripción {subscription.id} actualizada: {old_status} → {new_status}")
                
                # Si se cancela, desactivar tenant
                if new_status == 'canceled':
                    TenantService.deactivate_tenant(
                        subscription.tenant,
                        reason='mercadopago_cancelled'
                    )
        
        except Subscription.DoesNotExist:
            # No existe suscripción local — crear tenant si MercadoPago dice authorized
            if mp_status in ['authorized', 'pending']:
                logger.info(
                    f"Webhook: suscripción {preapproval_id} authorized sin tenant local. "
                    f"Creando tenant automáticamente..."
                )
                
                # Parsear external_reference para extraer plan y email
                plan_tier = 'basic'
                billing_cycle = 'monthly'
                tenant_name = ''
                
                if external_ref:
                    # Formato: plan_basic_monthly__email_user@x.com__tenant_Mi Finca
                    parts = external_ref.split('__')
                    for part in parts:
                        if part.startswith('plan_'):
                            plan_parts = part.replace('plan_', '').rsplit('_', 1)
                            if len(plan_parts) == 2:
                                plan_tier, billing_cycle = plan_parts
                        elif part.startswith('email_'):
                            payer_email = payer_email or part.replace('email_', '')
                        elif part.startswith('tenant_'):
                            tenant_name = part.replace('tenant_', '')
                
                if not tenant_name:
                    tenant_name = payer_email.split('@')[0] if payer_email else 'nuevo_tenant'
                
                result = TenantService.create_tenant_for_subscription(
                    tenant_name=tenant_name,
                    plan_tier=plan_tier,
                    billing_cycle=billing_cycle,
                    payer_email=payer_email,
                    external_subscription_id=preapproval_id,
                    payment_gateway='mercadopago',
                )
                
                if result['success']:
                    logger.info(f"✅ Tenant creado via webhook: {tenant_name}")
                else:
                    logger.error(f"❌ Error creando tenant via webhook: {result.get('error')}")
            else:
                logger.warning(f"Suscripción MercadoPago {preapproval_id} no encontrada en BD (status={mp_status})")
        
        return {'status': 'ok'}
    
    def _process_successful_payment(self, payment_data):
        """
        Procesar pago exitoso con transacción atómica.
        
        SEGURIDAD: Usa transaction.atomic para garantizar consistencia.
        Si falla cualquier operación, se revierte todo.
        """
        external_reference = payment_data.get('external_reference')
        
        try:
            with transaction.atomic():
                # Buscar factura asociada con lock
                invoice = Invoice.objects.select_for_update().get(
                    invoice_number=external_reference
                )
                
                # Marcar como pagada
                invoice.mark_as_paid(
                    payment_method='mercadopago',
                    payment_id=payment_data['id']
                )
                
                # Activar/renovar suscripción si aplica
                if invoice.subscription:
                    subscription = Subscription.objects.select_for_update().get(
                        pk=invoice.subscription.pk
                    )
                    
                    if subscription.status == 'trialing':
                        subscription.status = 'active'
                    
                    # Extender período
                    subscription.current_period_start = timezone.now()
                    subscription.current_period_end = timezone.now() + timedelta(days=30)
                    subscription.save()
                    
                    # Registrar evento de pago exitoso
                    BillingEvent.objects.create(
                        tenant=subscription.tenant,
                        subscription=subscription,
                        event_type='invoice.paid',
                        event_data={
                            'invoice_number': invoice.invoice_number,
                            'payment_id': payment_data['id'],
                            'amount': payment_data.get('transaction_amount'),
                            'gateway': 'mercadopago'
                        },
                        external_event_id=str(payment_data['id'])
                    )
                    
                    logger.info(f"Suscripción {subscription.id} renovada tras pago exitoso")
        
        except Invoice.DoesNotExist:
            logger.warning(f"Factura con referencia {external_reference} no encontrada")
    
    def _process_failed_payment(self, payment_data):
        """
        Procesar pago fallido con transacción atómica.
        
        SEGURIDAD: Usa transaction.atomic para garantizar consistencia.
        """
        external_reference = payment_data.get('external_reference')
        
        try:
            with transaction.atomic():
                invoice = Invoice.objects.select_for_update().get(
                    invoice_number=external_reference
                )
                subscription = invoice.subscription
                
                if subscription:
                    subscription = Subscription.objects.select_for_update().get(
                        pk=subscription.pk
                    )
                    
                    # Marcar como pago vencido
                    subscription.status = 'past_due'
                    subscription.save()
                    
                    # Registrar evento
                    BillingEvent.objects.create(
                        tenant=subscription.tenant,
                        subscription=subscription,
                        event_type='invoice.payment_failed',
                        event_data={
                            'invoice_number': invoice.invoice_number,
                            'payment_id': payment_data['id'],
                            'status_detail': payment_data.get('status_detail')
                        },
                        external_event_id=str(payment_data['id'])
                    )
                    
                    logger.warning(f"Pago fallido para suscripción {subscription.id}")
        
        except Invoice.DoesNotExist:
            logger.warning(f"Factura con referencia {external_reference} no encontrada")


# Registrar gateway en el factory
PaymentGatewayFactory.register_gateway('mercadopago', MercadoPagoGateway)
