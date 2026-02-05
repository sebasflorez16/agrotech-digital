"""
Integración con Paddle para clientes internacionales (USD).

Paddle actúa como Merchant of Record:
- Maneja compliance fiscal global (VAT, sales tax, etc.)
- Facturación automática
- Suscripciones recurrentes
- Webhooks para notificaciones
"""

import requests
import hashlib
import json
from typing import Dict, Any
from urllib.parse import urlencode
from collections import OrderedDict
from django.conf import settings
from django.utils import timezone
from .gateways import PaymentGateway, PaymentGatewayFactory
from .models import Subscription, Invoice, BillingEvent
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class PaddleGateway(PaymentGateway):
    """
    Implementación de PaymentGateway para Paddle.
    
    Documentación: https://developer.paddle.com/api-reference
    """
    
    def __init__(self):
        """Inicializar cliente de Paddle."""
        self.vendor_id = getattr(settings, 'PADDLE_VENDOR_ID', '')
        self.api_key = getattr(settings, 'PADDLE_API_KEY', '')
        self.public_key = getattr(settings, 'PADDLE_PUBLIC_KEY', '')
        self.sandbox = getattr(settings, 'PADDLE_SANDBOX', False)
        
        if not self.vendor_id or not self.api_key:
            logger.warning("PADDLE_VENDOR_ID o PADDLE_API_KEY no configurados en settings")
        
        # URLs de API
        if self.sandbox:
            self.api_url = "https://sandbox-vendors.paddle.com/api/2.0"
            self.checkout_url = "https://sandbox-checkout.paddle.com/checkout/custom"
        else:
            self.api_url = "https://vendors.paddle.com/api/2.0"
            self.checkout_url = "https://checkout.paddle.com/checkout/custom"
        
        self.currency = 'USD'
    
    def create_subscription(self, user, plan, payment_method_token=None) -> Dict[str, Any]:
        """
        Crear suscripción en Paddle.
        
        Paddle usa Checkout.js, por lo que generamos una URL de checkout
        en lugar de procesar el pago directamente.
        """
        try:
            # Obtener tenant
            tenant = user.tenant if hasattr(user, 'tenant') else None
            
            # Preparar parámetros de checkout
            checkout_params = {
                'vendor': self.vendor_id,
                'product': plan.paddle_product_id,  # Debe estar configurado en Paddle dashboard
                'email': user.email,
                'passthrough': json.dumps({
                    'user_id': user.id,
                    'tenant_id': tenant.id if tenant else None,
                    'plan_tier': plan.tier
                }),
                'success_url': f"{settings.SITE_URL}/billing/success/",
                'cancel_url': f"{settings.SITE_URL}/billing/cancel/",
            }
            
            # Generar URL de checkout
            checkout_url = f"{self.checkout_url}?{urlencode(checkout_params)}"
            
            logger.info(f"Checkout URL Paddle generada para plan {plan.tier}")
            
            return {
                'success': True,
                'checkout_url': checkout_url,
                'subscription_id': None,  # Se obtendrá del webhook tras pago
                'provider': 'paddle'
            }
        
        except Exception as e:
            logger.exception(f"Error creando checkout Paddle: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Cancelar suscripción en Paddle.
        """
        try:
            payload = {
                'vendor_id': self.vendor_id,
                'vendor_auth_code': self.api_key,
                'subscription_id': subscription_id,
            }
            
            response = requests.post(
                f"{self.api_url}/subscription/users_cancel",
                data=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    logger.info(f"Suscripción Paddle cancelada: {subscription_id}")
                    return {'success': True}
                else:
                    error_msg = result.get('error', {}).get('message', 'Error desconocido')
                    logger.error(f"Error cancelando suscripción Paddle: {error_msg}")
                    return {'success': False, 'error': error_msg}
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}'
                }
        
        except Exception as e:
            logger.exception(f"Excepción cancelando suscripción Paddle: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_subscription_status(self, subscription_id: str) -> Dict[str, Any]:
        """
        Obtener información de suscripción en Paddle.
        """
        try:
            payload = {
                'vendor_id': self.vendor_id,
                'vendor_auth_code': self.api_key,
                'subscription_id': subscription_id,
            }
            
            response = requests.post(
                f"{self.api_url}/subscription/users",
                data=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success') and result.get('response'):
                    data = result['response'][0] if result['response'] else {}
                    
                    return {
                        'success': True,
                        'status': data.get('state'),
                        'next_payment': data.get('next_payment'),
                        'data': data
                    }
                else:
                    return {'success': False, 'error': 'Suscripción no encontrada'}
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}'}
        
        except Exception as e:
            logger.exception(f"Error obteniendo status Paddle: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_payment_method_info(self, subscription_id: str) -> Dict[str, Any]:
        """
        Obtener información del método de pago.
        
        Paddle no expone detalles de tarjeta por API (por seguridad).
        """
        return {
            'success': True,
            'message': 'Paddle no expone detalles de método de pago'
        }
    
    def handle_webhook(self, request) -> Dict[str, Any]:
        """
        Procesar webhooks de Paddle.
        
        Paddle envía webhooks para:
        - subscription_created
        - subscription_updated
        - subscription_cancelled
        - subscription_payment_succeeded
        - subscription_payment_failed
        - subscription_payment_refunded
        """
        try:
            # Validar firma del webhook
            if not self._verify_webhook_signature(request):
                logger.warning("Webhook Paddle con firma inválida")
                return {'status': 'error', 'error': 'Invalid signature'}
            
            # Obtener datos
            data = request.POST.dict() if hasattr(request.POST, 'dict') else dict(request.POST)
            alert_name = data.get('alert_name')
            
            logger.info(f"Webhook Paddle recibido: {alert_name}")
            
            # Procesar según tipo de alerta
            if alert_name == 'subscription_created':
                return self._handle_subscription_created(data)
            
            elif alert_name == 'subscription_updated':
                return self._handle_subscription_updated(data)
            
            elif alert_name == 'subscription_cancelled':
                return self._handle_subscription_cancelled(data)
            
            elif alert_name == 'subscription_payment_succeeded':
                return self._handle_payment_succeeded(data)
            
            elif alert_name == 'subscription_payment_failed':
                return self._handle_payment_failed(data)
            
            else:
                logger.info(f"Webhook Paddle type no manejado: {alert_name}")
                return {'status': 'ok', 'message': 'Event type not handled'}
        
        except Exception as e:
            logger.exception(f"Error procesando webhook Paddle: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _verify_webhook_signature(self, request) -> bool:
        """
        Verificar la firma del webhook de Paddle.
        
        Paddle envía firma p_signature para validación.
        """
        try:
            # Obtener datos
            data = request.POST.dict() if hasattr(request.POST, 'dict') else dict(request.POST)
            signature = data.pop('p_signature', None)
            
            if not signature:
                return False
            
            # Ordenar datos alfabéticamente
            sorted_data = OrderedDict(sorted(data.items()))
            
            # Serializar datos (formato específico de Paddle)
            serialized = self._serialize_paddle_data(sorted_data)
            
            # Verificar firma con la public key
            # TODO: Implementar verificación con RSA public key
            # Por ahora, retornamos True pero DEBE implementarse en producción
            
            return True
        
        except Exception as e:
            logger.exception(f"Error verificando firma Paddle: {str(e)}")
            return False
    
    def _serialize_paddle_data(self, data):
        """
        Serializar datos según el formato de Paddle.
        """
        parts = []
        for key, value in data.items():
            parts.append(f"{key}={value}")
        return ';'.join(parts)
    
    def _handle_subscription_created(self, data) -> Dict[str, Any]:
        """
        Manejar creación de suscripción.
        """
        try:
            # Parsear passthrough data
            passthrough = json.loads(data.get('passthrough', '{}'))
            user_id = passthrough.get('user_id')
            tenant_id = passthrough.get('tenant_id')
            
            if not user_id or not tenant_id:
                logger.warning("Webhook subscription_created sin user_id/tenant_id")
                return {'status': 'error', 'error': 'Missing user/tenant info'}
            
            # Buscar suscripción pendiente o crear nueva
            from django.contrib.auth import get_user_model
            from base_agrotech.models import Client
            
            User = get_user_model()
            user = User.objects.get(id=user_id)
            tenant = Client.objects.get(id=tenant_id)
            
            # Actualizar suscripción existente o crear
            subscription, created = Subscription.objects.get_or_create(
                tenant=tenant,
                defaults={
                    'plan_id': data.get('subscription_plan_id'),  # Mapear a Plan
                    'payment_gateway': 'paddle',
                    'external_subscription_id': data.get('subscription_id'),
                    'status': 'active',
                    'current_period_start': timezone.now(),
                    'current_period_end': timezone.now() + timedelta(days=30),
                }
            )
            
            if not created:
                subscription.external_subscription_id = data.get('subscription_id')
                subscription.payment_gateway = 'paddle'
                subscription.status = 'active'
                subscription.save()
            
            logger.info(f"Suscripción Paddle creada/actualizada: {subscription.id}")
            
            return {'status': 'ok'}
        
        except Exception as e:
            logger.exception(f"Error en subscription_created: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_subscription_updated(self, data) -> Dict[str, Any]:
        """
        Manejar actualización de suscripción.
        """
        try:
            subscription_id = data.get('subscription_id')
            
            subscription = Subscription.objects.get(
                external_subscription_id=subscription_id,
                payment_gateway='paddle'
            )
            
            # Actualizar status si cambió
            paddle_status = data.get('status')
            status_mapping = {
                'active': 'active',
                'trialing': 'trialing',
                'past_due': 'past_due',
                'paused': 'paused',
                'deleted': 'canceled',
            }
            
            new_status = status_mapping.get(paddle_status, subscription.status)
            
            if new_status != subscription.status:
                subscription.status = new_status
                subscription.save()
                
                logger.info(f"Suscripción Paddle {subscription.id} actualizada a {new_status}")
            
            return {'status': 'ok'}
        
        except Subscription.DoesNotExist:
            logger.warning(f"Suscripción Paddle {subscription_id} no encontrada")
            return {'status': 'error', 'error': 'Subscription not found'}
        except Exception as e:
            logger.exception(f"Error en subscription_updated: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_subscription_cancelled(self, data) -> Dict[str, Any]:
        """
        Manejar cancelación de suscripción.
        """
        try:
            subscription_id = data.get('subscription_id')
            
            subscription = Subscription.objects.get(
                external_subscription_id=subscription_id,
                payment_gateway='paddle'
            )
            
            subscription.status = 'canceled'
            subscription.canceled_at = timezone.now()
            subscription.ended_at = timezone.now()
            subscription.save()
            
            # Registrar evento
            BillingEvent.objects.create(
                tenant=subscription.tenant,
                subscription=subscription,
                event_type='subscription.canceled',
                event_data={
                    'cancellation_effective_date': data.get('cancellation_effective_date'),
                    'paddle_subscription_id': subscription_id
                }
            )
            
            logger.info(f"Suscripción Paddle {subscription.id} cancelada")
            
            return {'status': 'ok'}
        
        except Subscription.DoesNotExist:
            logger.warning(f"Suscripción Paddle {subscription_id} no encontrada")
            return {'status': 'ok'}  # No error para evitar reintentos
        except Exception as e:
            logger.exception(f"Error en subscription_cancelled: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_payment_succeeded(self, data) -> Dict[str, Any]:
        """
        Manejar pago exitoso.
        """
        try:
            subscription_id = data.get('subscription_id')
            
            subscription = Subscription.objects.get(
                external_subscription_id=subscription_id,
                payment_gateway='paddle'
            )
            
            # Crear factura (Paddle ya generó su propia factura)
            invoice = Invoice.objects.create(
                tenant=subscription.tenant,
                subscription=subscription,
                subtotal=float(data.get('sale_gross', 0)),
                tax_amount=float(data.get('payment_tax', 0)),
                total=float(data.get('sale_gross', 0)),
                currency='USD',
                status='paid',
                invoice_date=timezone.now().date(),
                due_date=timezone.now().date(),
                paid_at=timezone.now(),
                paddle_payment_id=data.get('order_id'),
                line_items=[{
                    'description': subscription.plan.name,
                    'quantity': 1,
                    'amount': float(data.get('sale_gross', 0))
                }]
            )
            
            # Renovar suscripción
            subscription.status = 'active'
            subscription.current_period_start = timezone.now()
            subscription.current_period_end = timezone.now() + timedelta(days=30)
            subscription.save()
            
            logger.info(f"Pago Paddle exitoso para suscripción {subscription.id}")
            
            return {'status': 'ok'}
        
        except Subscription.DoesNotExist:
            logger.warning(f"Suscripción Paddle {subscription_id} no encontrada")
            return {'status': 'ok'}
        except Exception as e:
            logger.exception(f"Error en payment_succeeded: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_payment_failed(self, data) -> Dict[str, Any]:
        """
        Manejar pago fallido.
        """
        try:
            subscription_id = data.get('subscription_id')
            
            subscription = Subscription.objects.get(
                external_subscription_id=subscription_id,
                payment_gateway='paddle'
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
                    'amount': data.get('amount'),
                    'currency': data.get('currency'),
                    'next_retry_date': data.get('next_retry_date')
                }
            )
            
            logger.warning(f"Pago Paddle fallido para suscripción {subscription.id}")
            
            return {'status': 'ok'}
        
        except Subscription.DoesNotExist:
            logger.warning(f"Suscripción Paddle {subscription_id} no encontrada")
            return {'status': 'ok'}
        except Exception as e:
            logger.exception(f"Error en payment_failed: {str(e)}")
            return {'status': 'error', 'error': str(e)}


# Registrar gateway en el factory
PaymentGatewayFactory.register_gateway('paddle', PaddleGateway)
