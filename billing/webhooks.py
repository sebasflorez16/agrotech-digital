"""
Webhooks endpoints para pasarelas de pago.

Endpoints:
- /api/webhooks/mercadopago/
- /api/webhooks/paddle/
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .gateways import PaymentGatewayFactory
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])  # Webhooks no usan autenticación normal
def mercadopago_webhook(request):
    """
    Webhook endpoint para MercadoPago.
    
    POST /api/webhooks/mercadopago/
    
    MercadoPago envía notificaciones cuando:
    - Se procesa un pago
    - Cambia el estado de una suscripción
    - Falla un pago
    """
    try:
        gateway = PaymentGatewayFactory.create('mercadopago')
        result = gateway.handle_webhook(request)
        
        logger.info(f"Webhook MercadoPago procesado: {result}")
        
        return Response(result, status=200)
    
    except Exception as e:
        logger.exception(f"Error procesando webhook MercadoPago: {str(e)}")
        return Response({
            'status': 'error',
            'error': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def paddle_webhook(request):
    """
    Webhook endpoint para Paddle.
    
    POST /api/webhooks/paddle/
    
    Paddle envía notificaciones cuando:
    - Se crea una suscripción
    - Se actualiza una suscripción
    - Se cancela una suscripción
    - Se procesa un pago (éxito o fallo)
    """
    try:
        gateway = PaymentGatewayFactory.create('paddle')
        result = gateway.handle_webhook(request)
        
        logger.info(f"Webhook Paddle procesado: {result}")
        
        return Response(result, status=200)
    
    except Exception as e:
        logger.exception(f"Error procesando webhook Paddle: {str(e)}")
        return Response({
            'status': 'error',
            'error': str(e)
        }, status=500)
