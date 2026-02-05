"""
Abstract Payment Gateway y Factory Pattern para múltiples pasarelas.

Soporta:
- MercadoPago (Colombia - COP)
- Paddle (Internacional - USD)
- Extensible para Stripe u otras
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class PaymentGateway(ABC):
    """
    Interfaz abstracta para pasarelas de pago.
    
    Todas las pasarelas deben implementar estos métodos.
    """
    
    @abstractmethod
    def create_subscription(self, user, plan, payment_method_token=None) -> Dict[str, Any]:
        """
        Crear una suscripción recurrente.
        
        Args:
            user: Usuario Django
            plan: Instancia de Plan
            payment_method_token: Token del método de pago (si aplica)
            
        Returns:
            dict con:
                - success: bool
                - subscription_id: str (ID en la pasarela)
                - checkout_url: str (URL para completar pago, si aplica)
                - error: str (si success=False)
        """
        pass
    
    @abstractmethod
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Cancelar una suscripción.
        
        Args:
            subscription_id: ID de la suscripción en la pasarela
            
        Returns:
            dict con success: bool y error: str (si aplica)
        """
        pass
    
    @abstractmethod
    def get_subscription_status(self, subscription_id: str) -> Dict[str, Any]:
        """
        Obtener estado actual de una suscripción.
        
        Args:
            subscription_id: ID de la suscripción en la pasarela
            
        Returns:
            dict con status y detalles de la suscripción
        """
        pass
    
    @abstractmethod
    def handle_webhook(self, request) -> Dict[str, Any]:
        """
        Procesar webhooks de la pasarela.
        
        Args:
            request: Django request object
            
        Returns:
            dict con resultado del procesamiento
        """
        pass
    
    @abstractmethod
    def get_payment_method_info(self, subscription_id: str) -> Dict[str, Any]:
        """
        Obtener información del método de pago asociado.
        
        Args:
            subscription_id: ID de la suscripción
            
        Returns:
            dict con información del método de pago
        """
        pass


class PaymentGatewayFactory:
    """
    Factory para crear instancias de pasarelas de pago.
    """
    
    _gateways = {}
    
    @classmethod
    def register_gateway(cls, name: str, gateway_class):
        """
        Registrar una nueva pasarela.
        
        Args:
            name: Nombre de la pasarela ('mercadopago', 'paddle', etc.)
            gateway_class: Clase que implementa PaymentGateway
        """
        cls._gateways[name] = gateway_class
    
    @classmethod
    def create(cls, gateway_name: str) -> PaymentGateway:
        """
        Crear instancia de una pasarela.
        
        Args:
            gateway_name: Nombre de la pasarela
            
        Returns:
            Instancia de PaymentGateway
            
        Raises:
            ValueError: Si la pasarela no está registrada
        """
        gateway_class = cls._gateways.get(gateway_name)
        if not gateway_class:
            raise ValueError(
                f"Gateway '{gateway_name}' no registrado. "
                f"Disponibles: {list(cls._gateways.keys())}"
            )
        
        return gateway_class()
    
    @classmethod
    def get_available_gateways(cls):
        """Obtener lista de pasarelas disponibles."""
        return list(cls._gateways.keys())


def get_gateway_for_country(country_code: str) -> str:
    """
    Determinar qué pasarela usar según el país del cliente.
    
    Args:
        country_code: Código ISO del país (ej: 'CO', 'US', 'ES')
        
    Returns:
        Nombre de la pasarela a usar
    """
    # Colombia usa MercadoPago
    if country_code == 'CO':
        return 'mercadopago'
    
    # Resto del mundo usa Paddle (Merchant of Record)
    return 'paddle'


def get_gateway_for_user(user) -> PaymentGateway:
    """
    Obtener la pasarela apropiada para un usuario.
    
    Args:
        user: Usuario Django
        
    Returns:
        Instancia de PaymentGateway
    """
    # Intentar obtener país del perfil del usuario
    country = None
    
    if hasattr(user, 'profile') and hasattr(user.profile, 'country'):
        country = user.profile.country
    
    # Si no hay país en el perfil, usar default
    if not country:
        # TODO: Implementar detección por GeoIP
        country = getattr(settings, 'DEFAULT_COUNTRY', 'CO')
    
    gateway_name = get_gateway_for_country(country)
    
    return PaymentGatewayFactory.create(gateway_name)


def get_gateway_for_currency(currency: str) -> str:
    """
    Determinar pasarela según la moneda.
    
    Args:
        currency: Código de moneda ('COP', 'USD', etc.)
        
    Returns:
        Nombre de la pasarela
    """
    if currency == 'COP':
        return 'mercadopago'
    
    # USD, EUR, etc. usan Paddle
    return 'paddle'
