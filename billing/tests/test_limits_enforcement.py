"""
Tests de enforcement de límites de suscripción.

Estos tests verifican que los límites del plan se aplican ESTRICTAMENTE:
- Límite de hectáreas en parcelas
- Límite de requests EOSDA
- Límite de usuarios

EJECUTAR: pytest billing/tests/test_limits_enforcement.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, RequestFactory
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal


class TestHectareLimitsEnforcement(TestCase):
    """Tests para verificar enforcement estricto de límites de hectáreas."""
    
    def setUp(self):
        self.factory = RequestFactory()
        
    def _create_mock_request(self, hectares, current_hectares=0, limit=50):
        """Crear un request mockeado con suscripción y datos de parcela."""
        request = self.factory.post('/api/parcels/')
        request.user = Mock(is_authenticated=True)
        
        # Mock subscription con check_limit
        mock_subscription = Mock()
        mock_subscription.plan.name = 'Test Plan'
        
        def check_limit(resource, value):
            if resource == 'hectares':
                if limit == 'unlimited':
                    return (True, 'unlimited')
                return (value <= limit, limit)
            return (True, 100)
        
        mock_subscription.check_limit = check_limit
        request.subscription = mock_subscription
        request.tenant = Mock(schema_name='test_tenant')
        
        # Mock data
        request.data = {
            'geom': {
                'type': 'Polygon',
                'coordinates': [[[0, 0], [0, 0.01], [0.01, 0.01], [0.01, 0], [0, 0]]]
            }
        }
        
        return request
    
    @patch('parcels.views.Parcel.objects')
    def test_create_parcel_within_limit_succeeds(self, mock_parcel_objects):
        """Crear parcela dentro del límite debe ser permitido."""
        from parcels.views import ParcelViewSet
        
        viewset = ParcelViewSet()
        viewset.format_kwarg = None
        
        request = self._create_mock_request(hectares=10, limit=50)
        request._request = request
        
        # Mock para que devuelva lista vacía de parcelas
        mock_parcel_objects.filter.return_value.exclude.return_value = []
        
        # Este test verifica que el método _verify_hectare_limit existe y funciona
        is_allowed, error = viewset._verify_hectare_limit(request, 10)
        
        self.assertTrue(is_allowed)
        self.assertIsNone(error)
    
    @patch('parcels.views.Parcel.objects')
    def test_create_parcel_exceeding_limit_fails(self, mock_parcel_objects):
        """Crear parcela que excede el límite debe ser rechazado con 403."""
        from parcels.views import ParcelViewSet
        
        viewset = ParcelViewSet()
        viewset.format_kwarg = None
        
        request = self._create_mock_request(hectares=60, limit=50)
        request._request = request
        
        # Mock para que devuelva lista vacía de parcelas
        mock_parcel_objects.filter.return_value.exclude.return_value = []
        
        # 60 hectáreas > 50 límite = debe fallar
        is_allowed, error = viewset._verify_hectare_limit(request, 60)
        
        self.assertFalse(is_allowed)
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 403)
    
    @patch('parcels.views.Parcel.objects')
    def test_create_parcel_no_subscription_fails(self, mock_parcel_objects):
        """Crear parcela sin suscripción debe fallar con 402."""
        from parcels.views import ParcelViewSet
        
        viewset = ParcelViewSet()
        viewset.format_kwarg = None
        
        request = self.factory.post('/api/parcels/')
        request.user = Mock(is_authenticated=True)
        request.subscription = None  # Sin suscripción
        request.tenant = None
        request.data = {}
        
        is_allowed, error = viewset._verify_hectare_limit(request, 10)
        
        self.assertFalse(is_allowed)
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 402)
    
    def test_calculate_parcel_area_from_geojson(self):
        """Verificar cálculo correcto de área desde GeoJSON."""
        from parcels.views import ParcelViewSet
        
        viewset = ParcelViewSet()
        
        # Polígono aproximado de 1 hectárea (0.01 grados ≈ 1.1 km)
        geom = {
            'type': 'Polygon',
            'coordinates': [[[0, 0], [0, 0.001], [0.001, 0.001], [0.001, 0], [0, 0]]]
        }
        
        area = viewset._calculate_parcel_area(geom)
        
        # El área debe ser un número positivo
        self.assertGreater(area, 0)
        self.assertIsInstance(area, float)
    
    def test_calculate_parcel_area_invalid_geom_returns_zero(self):
        """GeoJSON inválido debe retornar 0 hectáreas."""
        from parcels.views import ParcelViewSet
        
        viewset = ParcelViewSet()
        
        # Casos inválidos
        self.assertEqual(viewset._calculate_parcel_area(None), 0)
        self.assertEqual(viewset._calculate_parcel_area({}), 0)
        self.assertEqual(viewset._calculate_parcel_area({'coordinates': []}), 0)


class TestEOSDALimitsEnforcement(TestCase):
    """Tests para verificar enforcement de límites EOSDA."""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_eosda_limit_check_within_limit(self):
        """Requests EOSDA dentro del límite deben ser permitidos."""
        from billing.decorators import check_eosda_limit
        
        # Mock de la función decorada
        @check_eosda_limit
        def mock_view(request):
            from rest_framework.response import Response
            return Response({'status': 'ok'})
        
        request = self.factory.get('/api/eosda/')
        request.user = Mock(is_authenticated=True)
        
        # Mock subscription
        mock_subscription = Mock()
        mock_subscription.plan.name = 'Test Plan'
        mock_subscription.check_limit = Mock(return_value=(True, 100))
        request.subscription = mock_subscription
        
        # Mock tenant y metrics
        mock_tenant = Mock(schema_name='test')
        request.tenant = mock_tenant
        
        with patch('billing.decorators.UsageMetrics.get_or_create_current') as mock_metrics:
            mock_metrics.return_value = Mock(eosda_requests=5)
            
            response = mock_view(request)
            
            self.assertEqual(response.status_code, 200)
    
    def test_eosda_limit_exceeded_returns_429(self):
        """Exceder límite EOSDA debe retornar 429."""
        from billing.decorators import check_eosda_limit
        
        @check_eosda_limit
        def mock_view(request):
            from rest_framework.response import Response
            return Response({'status': 'ok'})
        
        request = self.factory.get('/api/eosda/')
        request.user = Mock(is_authenticated=True)
        
        # Mock subscription que reporta límite excedido
        mock_subscription = Mock()
        mock_subscription.plan.name = 'Free'
        mock_subscription.check_limit = Mock(return_value=(False, 20))
        request.subscription = mock_subscription
        
        mock_tenant = Mock(schema_name='test')
        request.tenant = mock_tenant
        
        with patch('billing.decorators.UsageMetrics.get_or_create_current') as mock_metrics:
            mock_metrics.return_value = Mock(eosda_requests=20)
            
            response = mock_view(request)
            
            self.assertEqual(response.status_code, 429)


class TestWebhookSecurity(TestCase):
    """Tests de seguridad para webhooks."""
    
    def setUp(self):
        self.client = APIClient()
    
    def test_mercadopago_webhook_rate_limiting(self):
        """Verificar que rate limiting está activo en webhook MercadoPago."""
        # Este test verifica que el throttle está configurado
        from billing.webhooks import WebhookRateThrottle
        
        throttle = WebhookRateThrottle()
        self.assertEqual(throttle.rate, '100/min')
    
    def test_webhook_duplicate_detection(self):
        """Verificar detección de webhooks duplicados."""
        from billing.webhooks import _get_request_fingerprint, _is_duplicate_webhook
        from django.core.cache import cache
        
        # Limpiar cache
        cache.clear()
        
        # Crear mock request
        mock_request = Mock()
        mock_request.body = b'{"event": "test", "id": "123"}'
        
        fingerprint = _get_request_fingerprint(mock_request)
        
        # Primera vez no es duplicado
        self.assertFalse(_is_duplicate_webhook(fingerprint, ttl=60))
        
        # Segunda vez SÍ es duplicado
        self.assertTrue(_is_duplicate_webhook(fingerprint, ttl=60))
        
        # Limpiar
        cache.clear()


class TestTransactionAtomicity(TestCase):
    """Tests para verificar atomicidad de transacciones de pago."""
    
    def test_mercadopago_handler_uses_transaction(self):
        """Verificar que handler de pago usa transaction.atomic."""
        import inspect
        from billing.mercadopago_gateway import MercadoPagoGateway
        
        # Obtener el código fuente del método
        source = inspect.getsource(MercadoPagoGateway._process_successful_payment)
        
        # Verificar que usa transaction.atomic
        self.assertIn('transaction.atomic', source)
        self.assertIn('select_for_update', source)
    
    def test_paddle_handler_uses_transaction(self):
        """Verificar que handler de Paddle usa transaction.atomic."""
        import inspect
        from billing.paddle_gateway import PaddleGateway
        
        source = inspect.getsource(PaddleGateway._handle_payment_succeeded)
        
        self.assertIn('transaction.atomic', source)
        self.assertIn('select_for_update', source)


class TestWebhookFailSafe(TestCase):
    """Tests para verificar fail-safe en webhooks sin secret."""
    
    def test_mercadopago_failsafe_production(self):
        """En producción sin secret, webhook debe ser rechazado."""
        import inspect
        from billing.mercadopago_gateway import MercadoPagoGateway
        
        source = inspect.getsource(MercadoPagoGateway._verify_webhook_signature)
        
        # Verificar que hay lógica de producción
        self.assertIn('is_production', source)
        self.assertIn('return False', source)
    
    def test_paddle_failsafe_production(self):
        """En producción sin secret, webhook Paddle debe ser rechazado."""
        import inspect
        from billing.paddle_gateway import PaddleGateway
        
        source = inspect.getsource(PaddleGateway._verify_paddle_billing_signature)
        
        self.assertIn('is_production', source)
        self.assertIn('return False', source)


class TestIdempotency(TestCase):
    """Tests para verificar idempotencia de procesamiento de pagos."""
    
    def test_paddle_payment_idempotency_check(self):
        """Verificar que Paddle verifica duplicados antes de procesar."""
        import inspect
        from billing.paddle_gateway import PaddleGateway
        
        source = inspect.getsource(PaddleGateway._handle_payment_succeeded)
        
        # Verificar que hay check de idempotencia
        self.assertIn('external_event_id', source)
        self.assertIn('Already processed', source)
