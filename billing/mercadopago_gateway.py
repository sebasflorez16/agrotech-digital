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
from .gateways import PaymentGateway, PaymentGatewayFactory
from .models import Subscription, Invoice, BillingEvent, Payment
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
        
        MercadoPago envía header x-signature para validar autenticidad.
        """
        # TODO: Implementar validación de firma
        # Por ahora retornamos True, pero en producción DEBE validarse
        
        # signature = request.META.get('HTTP_X_SIGNATURE')
        # request_id = request.META.get('HTTP_X_REQUEST_ID')
        
        # if not signature or not request_id:
        #     return False
        
        # # Validar según documentación de MercadoPago
        # # https://www.mercadopago.com.co/developers/es/docs/your-integrations/notifications/webhooks
        
        return True
    
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
        """
        preapproval_id = data.get('data', {}).get('id')
        
        if not preapproval_id:
            return {'status': 'error', 'error': 'No subscription ID'}
        
        # Consultar detalles de la suscripción
        sub_info = self.sdk.preapproval().get(preapproval_id)
        
        if sub_info['status'] != 200:
            return {'status': 'error', 'error': 'Subscription not found'}
        
        subscription_data = sub_info['response']
        
        # Actualizar suscripción en BD
        try:
            subscription = Subscription.objects.get(
                external_subscription_id=preapproval_id,
                payment_gateway='mercadopago'
            )
            
            mp_status = subscription_data.get('status')
            
            # Mapear estados de MercadoPago a nuestros estados
            status_mapping = {
                'authorized': 'active',
                'paused': 'paused',
                'cancelled': 'canceled',
            }
            
            new_status = status_mapping.get(mp_status, subscription.status)
            
            if new_status != subscription.status:
                subscription.status = new_status
                subscription.save()
                
                logger.info(f"Suscripción {subscription.id} actualizada a estado {new_status}")
        
        except Subscription.DoesNotExist:
            logger.warning(f"Suscripción MercadoPago {preapproval_id} no encontrada en BD")
        
        return {'status': 'ok'}
    
    def _process_successful_payment(self, payment_data):
        """
        Procesar pago exitoso.
        """
        external_reference = payment_data.get('external_reference')
        
        try:
            # Buscar factura asociada
            invoice = Invoice.objects.get(invoice_number=external_reference)
            
            # Marcar como pagada
            invoice.mark_as_paid(
                payment_method='mercadopago',
                payment_id=payment_data['id']
            )
            
            # Activar/renovar suscripción si aplica
            if invoice.subscription:
                subscription = invoice.subscription
                
                if subscription.status == 'trialing':
                    subscription.status = 'active'
                
                # Extender período
                subscription.current_period_start = timezone.now()
                subscription.current_period_end = timezone.now() + timedelta(days=30)
                subscription.save()
                
                logger.info(f"Suscripción {subscription.id} renovada tras pago exitoso")
        
        except Invoice.DoesNotExist:
            logger.warning(f"Factura con referencia {external_reference} no encontrada")
    
    def _process_failed_payment(self, payment_data):
        """
        Procesar pago fallido.
        """
        external_reference = payment_data.get('external_reference')
        
        try:
            invoice = Invoice.objects.get(invoice_number=external_reference)
            subscription = invoice.subscription
            
            if subscription:
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
                    }
                )
                
                logger.warning(f"Pago fallido para suscripción {subscription.id}")
        
        except Invoice.DoesNotExist:
            logger.warning(f"Factura con referencia {external_reference} no encontrada")


# Registrar gateway en el factory
PaymentGatewayFactory.register_gateway('mercadopago', MercadoPagoGateway)
