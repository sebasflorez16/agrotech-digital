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
import hmac
import json
from typing import Dict, Any
from urllib.parse import urlencode
from collections import OrderedDict
from django.conf import settings
from django.utils import timezone
from django.db import transaction
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
        
        Paddle Classic envía p_signature (RSA-SHA1) en cada webhook.
        Paddle Billing (v2) envía Paddle-Signature header (HMAC-SHA256 con H1 scheme).
        
        Documentación:
        - Classic: https://developer.paddle.com/webhook-reference/verifying-webhooks
        - Billing: https://developer.paddle.com/webhooks/signature-verification
        """
        # Intentar Paddle Billing (v2) primero, luego Classic
        paddle_signature = request.META.get('HTTP_PADDLE_SIGNATURE', '')
        
        if paddle_signature:
            return self._verify_paddle_billing_signature(request, paddle_signature)
        else:
            return self._verify_paddle_classic_signature(request)
    
    def _verify_paddle_billing_signature(self, request, signature_header: str) -> bool:
        """
        Verificar firma de Paddle Billing (v2) usando HMAC-SHA256.
        
        Header format: "ts=<timestamp>;h1=<hash>"
        
        SEGURIDAD: En producción, RECHAZA webhooks si no hay secret configurado.
        """
        webhook_secret = getattr(settings, 'PADDLE_WEBHOOK_SECRET', '')
        is_production = not getattr(settings, 'DEBUG', True)
        
        # FAIL-SAFE: En producción sin secret, RECHAZAR
        if not webhook_secret:
            if is_production:
                logger.error(
                    "PADDLE_WEBHOOK_SECRET no configurado en producción. "
                    "Webhook RECHAZADO por seguridad. Configure la variable de entorno."
                )
                return False
            else:
                logger.warning(
                    "PADDLE_WEBHOOK_SECRET no configurado en desarrollo. "
                    "Webhook aceptado SIN verificación. Configúralo para producción."
                )
                return True
        
        try:
            # Parsear ts y h1 del header
            parts = {}
            for part in signature_header.split(';'):
                key_value = part.split('=', 1)
                if len(key_value) == 2:
                    parts[key_value[0].strip()] = key_value[1].strip()
            
            ts = parts.get('ts')
            received_hash = parts.get('h1')
            
            if not ts or not received_hash:
                logger.warning("Formato de Paddle-Signature inválido")
                return False
            
            # Obtener body raw
            raw_body = request.body.decode('utf-8') if isinstance(request.body, bytes) else request.body
            
            # Construir signed payload: "ts:body"
            signed_payload = f"{ts}:{raw_body}"
            
            # Calcular HMAC-SHA256
            expected_hash = hmac.new(
                webhook_secret.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(expected_hash, received_hash)
            
            if not is_valid:
                logger.warning("Firma Paddle Billing inválida")
            
            return is_valid
            
        except Exception as e:
            logger.exception(f"Error verificando firma Paddle Billing: {str(e)}")
            return False
    
    def _verify_paddle_classic_signature(self, request) -> bool:
        """
        Verificar firma de Paddle Classic usando RSA-SHA1 + phpserialize.
        
        Paddle Classic envía p_signature en el body POST.
        Requiere la public key de Paddle para verificar.
        """
        try:
            import base64
            
            data = request.POST.dict() if hasattr(request.POST, 'dict') else dict(request.POST)
            signature = data.pop('p_signature', None)
            
            if not signature:
                logger.warning("Webhook Paddle Classic sin p_signature")
                return False
            
            if not self.public_key:
                is_production = not getattr(settings, 'DEBUG', True)
                if is_production:
                    logger.error(
                        "PADDLE_PUBLIC_KEY no configurado en producción. "
                        "Webhook RECHAZADO por seguridad. Configure la variable de entorno."
                    )
                    return False
                else:
                    logger.warning(
                        "PADDLE_PUBLIC_KEY no configurado en desarrollo. "
                        "Webhook aceptado SIN verificación. Configúralo para producción."
                    )
                    return True
            
            # Ordenar datos alfabéticamente
            sorted_data = OrderedDict(sorted(data.items()))
            
            # Serializar en formato PHP (Paddle usa PHP serialize)
            serialized = self._php_serialize(sorted_data)
            
            # Verificar firma RSA-SHA1
            try:
                from cryptography.hazmat.primitives import hashes, serialization
                from cryptography.hazmat.primitives.asymmetric import padding
                
                # Cargar public key
                public_key = serialization.load_pem_public_key(
                    self.public_key.encode('utf-8')
                )
                
                # Decodificar firma base64
                decoded_signature = base64.b64decode(signature)
                
                # Verificar
                public_key.verify(
                    decoded_signature,
                    serialized.encode('utf-8'),
                    padding.PKCS1v15(),
                    hashes.SHA1(),
                )
                return True
                
            except ImportError:
                logger.warning(
                    "cryptography no instalado. "
                    "Instálalo con: pip install cryptography. "
                    "Webhook aceptado SIN verificación RSA."
                )
                return True
            except Exception as verify_error:
                logger.warning(f"Firma Paddle Classic inválida: {verify_error}")
                return False
                
        except Exception as e:
            logger.exception(f"Error verificando firma Paddle Classic: {str(e)}")
            return False
    
    def _php_serialize(self, data: dict) -> str:
        """
        Serializar dict al formato PHP serialize que Paddle usa.
        Implementación simplificada para los tipos que Paddle envía.
        """
        parts = []
        for key, value in data.items():
            key_serialized = f's:{len(str(key))}:"{key}"'
            if isinstance(value, (int, float)):
                val_serialized = f'i:{value}' if isinstance(value, int) else f'd:{value}'
            else:
                value = str(value)
                val_serialized = f's:{len(value)}:"{value}"'
            parts.append(f'{key_serialized};{val_serialized};')
        return f'a:{len(data)}:{{{"".join(parts)}}}'
    
    def _serialize_paddle_data(self, data):
        """
        Serializar datos según el formato de Paddle (legacy).
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
        Manejar pago exitoso con transacción atómica.
        
        SEGURIDAD: Usa transaction.atomic para garantizar consistencia.
        Si falla cualquier operación, se revierte todo.
        """
        try:
            subscription_id = data.get('subscription_id')
            order_id = data.get('order_id')
            
            # Idempotencia: verificar si ya procesamos este evento
            if order_id and BillingEvent.objects.filter(external_event_id=str(order_id)).exists():
                logger.info(f"Evento Paddle {order_id} ya procesado - ignorando duplicado")
                return {'status': 'ok', 'message': 'Already processed'}
            
            with transaction.atomic():
                subscription = Subscription.objects.select_for_update().get(
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
                    paddle_payment_id=order_id,
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
                
                # Registrar evento para idempotencia
                BillingEvent.objects.create(
                    tenant=subscription.tenant,
                    subscription=subscription,
                    event_type='invoice.paid',
                    event_data={
                        'invoice_number': invoice.invoice_number,
                        'order_id': order_id,
                        'amount': float(data.get('sale_gross', 0)),
                        'gateway': 'paddle'
                    },
                    external_event_id=str(order_id) if order_id else None
                )
                
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
        Manejar pago fallido con transacción atómica.
        
        SEGURIDAD: Usa transaction.atomic para garantizar consistencia.
        """
        try:
            subscription_id = data.get('subscription_id')
            
            with transaction.atomic():
                subscription = Subscription.objects.select_for_update().get(
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
