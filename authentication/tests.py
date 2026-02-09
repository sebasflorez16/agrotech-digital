"""
Tests para el módulo de autenticación SaaS.

Incluye:
- Tests unitarios del RegisterSerializer (validaciones sin BD)
- Tests unitarios de webhook signature verification
- Tests de integración del flujo completo (requieren PostgreSQL + django-tenants)

Para correr solo unit tests (sin BD):
    pytest authentication/tests.py -v -m "unit"

Para correr todos:
    pytest authentication/tests.py -v
"""
import pytest
import hmac
import hashlib
from unittest.mock import patch, MagicMock, PropertyMock


# ============================================================
# UNIT TESTS - No requieren BD, solo validación de serializer
# ============================================================

def _valid_data(**overrides):
    """Datos válidos base para registro."""
    defaults = {
        'email': 'test@agro.com',
        'username': 'testuser',
        'password': 'TestPass123!',
        'password_confirm': 'TestPass123!',
        'name': 'Juan',
        'last_name': 'Perez',
        'organization_name': 'Finca Test',
    }
    defaults.update(overrides)
    return defaults


def _make_serializer(data):
    from authentication.serializers import RegisterSerializer
    return RegisterSerializer(data=data)


def _mock_all_db():
    """Context manager que mockea todas las queries de BD del serializer."""
    from contextlib import ExitStack
    stack = ExitStack()
    m_user = stack.enter_context(patch('authentication.serializers.User.objects'))
    m_client = stack.enter_context(patch('authentication.serializers.Client.objects'))
    m_plan = stack.enter_context(patch('billing.models.Plan.objects'))
    # Por defecto: no existen duplicados, plan sí existe
    m_user.filter.return_value.exists.return_value = False
    m_client.filter.return_value.exists.return_value = False
    m_plan.filter.return_value.exists.return_value = True
    return stack, m_user, m_client, m_plan


@pytest.mark.unit
class TestRegisterSerializerFieldValidation:
    """Tests unitarios de validación de campos del RegisterSerializer.
    
    Todos los tests mockean queries a BD (User, Client, Plan) para ser
    verdaderos unit tests sin dependencia de PostgreSQL.
    """

    def test_valid_data_passes(self):
        """Datos completos y válidos pasan la validación."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(_valid_data())
            assert serializer.is_valid(), serializer.errors

    def test_email_required(self):
        """Email es obligatorio."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(_valid_data(email=''))
            assert not serializer.is_valid()
            assert 'email' in serializer.errors

    def test_invalid_email_format(self):
        """Email con formato inválido es rechazado."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(_valid_data(email='not-an-email'))
            assert not serializer.is_valid()
            assert 'email' in serializer.errors

    def test_password_mismatch(self):
        """Contraseñas que no coinciden son rechazadas."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(
                _valid_data(password='TestPass123!', password_confirm='Different456!')
            )
            assert not serializer.is_valid()
            assert 'password_confirm' in serializer.errors

    def test_password_too_short(self):
        """Contraseña menor a 8 caracteres es rechazada."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(
                _valid_data(password='Sh0r!', password_confirm='Sh0r!')
            )
            assert not serializer.is_valid()

    def test_username_too_short(self):
        """Username menor a 3 caracteres es rechazado."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(_valid_data(username='ab'))
            assert not serializer.is_valid()
            assert 'username' in serializer.errors

    def test_username_invalid_chars(self):
        """Username con caracteres especiales no permitidos es rechazado."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(_valid_data(username='user@name!'))
            assert not serializer.is_valid()
            assert 'username' in serializer.errors

    def test_username_reserved_word(self):
        """Username con palabra reservada es rechazado."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(_valid_data(username='admin'))
            assert not serializer.is_valid()
            assert 'username' in serializer.errors

    def test_username_reserved_words_list(self):
        """Varias palabras reservadas son rechazadas."""
        for word in ['root', 'system', 'api', 'www', 'public', 'test']:
            with _mock_all_db()[0]:
                serializer = _make_serializer(_valid_data(username=word))
                assert not serializer.is_valid(), f"'{word}' debería ser rechazado"

    def test_organization_name_required(self):
        """Nombre de organización es obligatorio."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(_valid_data(organization_name=''))
            assert not serializer.is_valid()
            assert 'organization_name' in serializer.errors

    def test_organization_name_too_short(self):
        """Nombre de organización menor a 3 caracteres es rechazado."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(_valid_data(organization_name='AB'))
            assert not serializer.is_valid()
            assert 'organization_name' in serializer.errors

    def test_name_required(self):
        """Nombre es obligatorio."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(_valid_data(name=''))
            assert not serializer.is_valid()
            assert 'name' in serializer.errors

    def test_last_name_required(self):
        """Apellido es obligatorio."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(_valid_data(last_name=''))
            assert not serializer.is_valid()
            assert 'last_name' in serializer.errors

    def test_phone_is_optional(self):
        """Teléfono es opcional."""
        with _mock_all_db()[0]:
            data = _valid_data()
            data.pop('phone', None)
            serializer = _make_serializer(data)
            assert serializer.is_valid(), serializer.errors

    def test_disposable_email_rejected(self):
        """Emails de dominios desechables son rechazados."""
        for domain in ['mailinator.com', 'yopmail.com', 'guerrillamail.com', 'tempmail.com']:
            with _mock_all_db()[0]:
                serializer = _make_serializer(_valid_data(email=f'user@{domain}'))
                assert not serializer.is_valid(), f"Email de {domain} debería ser rechazado"
                assert 'email' in serializer.errors

    def test_email_lowercased(self):
        """Email se normaliza a minúsculas."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(_valid_data(email='Test@Agro.COM'))
            assert serializer.is_valid(), serializer.errors
            assert serializer.validated_data['email'] == 'test@agro.com'

    def test_username_lowercased(self):
        """Username se normaliza a minúsculas."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(_valid_data(username='TestUser'))
            assert serializer.is_valid(), serializer.errors
            assert serializer.validated_data['username'] == 'testuser'

    def test_passwords_must_match_in_validate(self):
        """Validación cruzada: password != password_confirm falla."""
        with _mock_all_db()[0]:
            serializer = _make_serializer(
                _valid_data(password='ValidPass123!', password_confirm='NoMatch456!')
            )
            assert not serializer.is_valid()
            assert 'password_confirm' in serializer.errors

    def test_plan_tier_defaults_to_free(self):
        """Plan tier por defecto es 'free'."""
        with _mock_all_db()[0]:
            data = _valid_data()
            data.pop('plan_tier', None)
            serializer = _make_serializer(data)
            assert serializer.is_valid(), serializer.errors
            assert serializer.validated_data.get('plan_tier', 'free') == 'free'

    def test_email_duplicate_rejected(self):
        """Email duplicado es rechazado."""
        stack, m_user, m_client, m_plan = _mock_all_db()
        with stack:
            m_user.filter.return_value.exists.return_value = True  # Email exists
            serializer = _make_serializer(_valid_data())
            assert not serializer.is_valid()
            assert 'email' in serializer.errors

    def test_username_duplicate_rejected(self):
        """Username duplicado es rechazado."""
        stack, m_user, m_client, m_plan = _mock_all_db()
        with stack:
            # email check → False, username check → True
            m_user.filter.return_value.exists.side_effect = [False, True]
            serializer = _make_serializer(_valid_data())
            assert not serializer.is_valid()
            assert 'username' in serializer.errors

    def test_org_name_duplicate_rejected(self):
        """Organización con schema duplicado es rechazada."""
        stack, m_user, m_client, m_plan = _mock_all_db()
        with stack:
            m_client.filter.return_value.exists.return_value = True  # Schema exists
            serializer = _make_serializer(_valid_data())
            assert not serializer.is_valid()
            assert 'organization_name' in serializer.errors


# ============================================================
# UNIT TESTS - Webhook signature verification
# ============================================================

@pytest.mark.unit
class TestMercadoPagoWebhookSignature:
    """Tests unitarios para verificación de firma de webhook MercadoPago."""

    def _make_gateway(self):
        from billing.mercadopago_gateway import MercadoPagoGateway
        return MercadoPagoGateway()

    def test_no_secret_configured_allows_webhook(self):
        """Sin secret configurado, webhook es aceptado (con warning)."""
        gateway = self._make_gateway()
        request = MagicMock()
        
        with patch('billing.mercadopago_gateway.settings') as mock_settings:
            mock_settings.MERCADOPAGO_WEBHOOK_SECRET = ''
            mock_settings.MERCADOPAGO_ACCESS_TOKEN = 'test'
            result = gateway._verify_webhook_signature(request)
            assert result is True

    def test_missing_headers_rejected(self):
        """Con secret configurado, sin headers x-signature → rechazado."""
        gateway = self._make_gateway()
        request = MagicMock()
        request.META = {'HTTP_X_REQUEST_ID': 'req_123'}  # Sin x-signature
        
        with patch('billing.mercadopago_gateway.settings') as mock_settings:
            mock_settings.MERCADOPAGO_WEBHOOK_SECRET = 'test_secret'
            mock_settings.MERCADOPAGO_ACCESS_TOKEN = 'test'
            result = gateway._verify_webhook_signature(request)
            assert result is False

    def test_missing_request_id_rejected(self):
        """Con secret, sin x-request-id → rechazado."""
        gateway = self._make_gateway()
        request = MagicMock()
        request.META = {'HTTP_X_SIGNATURE': 'ts=123,v1=abc'}  # Sin x-request-id
        
        with patch('billing.mercadopago_gateway.settings') as mock_settings:
            mock_settings.MERCADOPAGO_WEBHOOK_SECRET = 'test_secret'
            mock_settings.MERCADOPAGO_ACCESS_TOKEN = 'test'
            result = gateway._verify_webhook_signature(request)
            assert result is False

    def test_valid_hmac_accepted(self):
        """Webhook con HMAC SHA-256 válido es aceptado."""
        gateway = self._make_gateway()
        
        secret = 'test_secret_key'
        data_id = '12345'
        request_id = 'req_abc123'
        ts = '1234567890'
        
        manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
        expected_hash = hmac.new(
            secret.encode('utf-8'),
            manifest.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        request = MagicMock()
        request.META = {
            'HTTP_X_SIGNATURE': f'ts={ts},v1={expected_hash}',
            'HTTP_X_REQUEST_ID': request_id,
        }
        request.data = {'data': {'id': data_id}}
        
        with patch('billing.mercadopago_gateway.settings') as mock_settings:
            mock_settings.MERCADOPAGO_WEBHOOK_SECRET = secret
            mock_settings.MERCADOPAGO_ACCESS_TOKEN = 'test'
            result = gateway._verify_webhook_signature(request)
            assert result is True

    def test_invalid_hmac_rejected(self):
        """Webhook con HMAC inválido es rechazado."""
        gateway = self._make_gateway()
        
        request = MagicMock()
        request.META = {
            'HTTP_X_SIGNATURE': 'ts=123,v1=invalid_hash_here',
            'HTTP_X_REQUEST_ID': 'req_123',
        }
        request.data = {'data': {'id': '456'}}
        
        with patch('billing.mercadopago_gateway.settings') as mock_settings:
            mock_settings.MERCADOPAGO_WEBHOOK_SECRET = 'real_secret'
            mock_settings.MERCADOPAGO_ACCESS_TOKEN = 'test'
            result = gateway._verify_webhook_signature(request)
            assert result is False

    def test_hmac_hash_length(self):
        """HMAC SHA-256 genera hash de 64 caracteres hex."""
        secret = 'test_secret'
        message = 'id:123;request-id:abc;ts:12345;'
        result = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        assert len(result) == 64


@pytest.mark.unit
class TestPaddleWebhookSignature:
    """Tests unitarios para verificación de firma de webhook Paddle."""

    def _make_gateway(self):
        from billing.paddle_gateway import PaddleGateway
        return PaddleGateway()

    def test_classic_missing_p_signature_rejected(self):
        """Paddle Classic sin p_signature es rechazado."""
        gateway = self._make_gateway()
        request = MagicMock()
        request.META = {}
        request.POST = MagicMock()
        request.POST.dict.return_value = {'alert_name': 'test'}
        result = gateway._verify_paddle_classic_signature(request)
        assert result is False

    def test_classic_missing_public_key_passes_with_warning(self):
        """Paddle Classic sin public key pasa con warning."""
        gateway = self._make_gateway()
        gateway.public_key = ''  # Sin public key
        
        request = MagicMock()
        request.POST = MagicMock()
        request.POST.dict.return_value = {
            'alert_name': 'test',
            'p_signature': 'some_base64_signature',
        }
        result = gateway._verify_paddle_classic_signature(request)
        assert result is True

    def test_billing_v2_no_secret_passes_with_warning(self):
        """Paddle Billing v2 sin secret pasa con warning."""
        gateway = self._make_gateway()
        request = MagicMock()
        signature_header = "ts=12345;h1=somehash"
        
        with patch('billing.paddle_gateway.settings') as mock_settings:
            mock_settings.PADDLE_WEBHOOK_SECRET = ''
            mock_settings.PADDLE_VENDOR_ID = ''
            mock_settings.PADDLE_API_KEY = ''
            mock_settings.PADDLE_PUBLIC_KEY = ''
            mock_settings.PADDLE_SANDBOX = True
            result = gateway._verify_paddle_billing_signature(request, signature_header)
            assert result is True

    def test_billing_v2_valid_hmac_accepted(self):
        """Paddle Billing v2 con HMAC válido es aceptado."""
        gateway = self._make_gateway()
        
        secret = 'paddle_test_secret'
        ts = '1234567890'
        raw_body = '{"event_type":"subscription.created"}'
        
        signed_payload = f"{ts}:{raw_body}"
        expected_hash = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        request = MagicMock()
        request.body = raw_body.encode('utf-8')
        signature_header = f"ts={ts};h1={expected_hash}"
        
        with patch('billing.paddle_gateway.settings') as mock_settings:
            mock_settings.PADDLE_WEBHOOK_SECRET = secret
            mock_settings.PADDLE_VENDOR_ID = ''
            mock_settings.PADDLE_API_KEY = ''
            mock_settings.PADDLE_PUBLIC_KEY = ''
            mock_settings.PADDLE_SANDBOX = True
            result = gateway._verify_paddle_billing_signature(request, signature_header)
            assert result is True

    def test_billing_v2_invalid_hmac_rejected(self):
        """Paddle Billing v2 con HMAC inválido es rechazado."""
        gateway = self._make_gateway()
        
        request = MagicMock()
        request.body = b'{"event_type":"test"}'
        signature_header = "ts=123;h1=totally_invalid_hash"
        
        with patch('billing.paddle_gateway.settings') as mock_settings:
            mock_settings.PADDLE_WEBHOOK_SECRET = 'real_secret'
            mock_settings.PADDLE_VENDOR_ID = ''
            mock_settings.PADDLE_API_KEY = ''
            mock_settings.PADDLE_PUBLIC_KEY = ''
            mock_settings.PADDLE_SANDBOX = True
            result = gateway._verify_paddle_billing_signature(request, signature_header)
            assert result is False

    def test_webhook_dispatch_billing_v2_header(self):
        """Dispatcher usa Billing v2 cuando Paddle-Signature presente."""
        gateway = self._make_gateway()
        
        request = MagicMock()
        request.META = {'HTTP_PADDLE_SIGNATURE': 'ts=123;h1=abc'}
        
        with patch.object(gateway, '_verify_paddle_billing_signature', return_value=True) as mock_billing:
            result = gateway._verify_webhook_signature(request)
            mock_billing.assert_called_once_with(request, 'ts=123;h1=abc')
            assert result is True

    def test_webhook_dispatch_classic_when_no_header(self):
        """Dispatcher usa Classic cuando no hay Paddle-Signature."""
        gateway = self._make_gateway()
        
        request = MagicMock()
        request.META = {}
        
        with patch.object(gateway, '_verify_paddle_classic_signature', return_value=True) as mock_classic:
            result = gateway._verify_webhook_signature(request)
            mock_classic.assert_called_once_with(request)
            assert result is True


# ============================================================
# UNIT TESTS - Views (con mocking de servicios)
# ============================================================

@pytest.mark.unit
class TestRegisterViewValidation:
    """Tests unitarios para RegisterView - solo validación HTTP."""

    def _post_register(self, data, server_name='127.0.0.1'):
        from rest_framework.test import APIRequestFactory
        from authentication.views import RegisterView
        factory = APIRequestFactory()
        request = factory.post('/api/auth/register/', data, format='json',
                               SERVER_NAME=server_name)
        view = RegisterView.as_view()
        # Desactivar throttling para tests
        with patch.object(view.view_class, 'throttle_classes', []):
            return view(request)

    def test_empty_body_returns_400(self):
        """Body vacío retorna 400."""
        with _mock_all_db()[0]:
            response = self._post_register({})
            assert response.status_code == 400
            assert response.data['success'] is False
            assert 'errors' in response.data

    def test_missing_email_returns_400(self):
        """Sin email retorna error específico."""
        with _mock_all_db()[0]:
            data = _valid_data()
            del data['email']
            response = self._post_register(data)
            assert response.status_code == 400
            assert 'email' in response.data['errors']

    def test_missing_password_returns_400(self):
        """Sin password retorna error específico."""
        with _mock_all_db()[0]:
            data = _valid_data()
            del data['password']
            response = self._post_register(data)
            assert response.status_code == 400
            assert 'password' in response.data['errors']

    def test_missing_organization_returns_400(self):
        """Sin nombre de organización retorna error específico."""
        with _mock_all_db()[0]:
            data = _valid_data()
            del data['organization_name']
            response = self._post_register(data)
            assert response.status_code == 400
            assert 'organization_name' in response.data['errors']


@pytest.mark.unit
class TestLoginViewValidation:
    """Tests unitarios para LoginView - validación de inputs."""

    def _post_login(self, data, server_name='127.0.0.1'):
        from rest_framework.test import APIRequestFactory
        from authentication.views import LoginView
        factory = APIRequestFactory()
        request = factory.post('/api/auth/login/', data, format='json',
                               SERVER_NAME=server_name)
        view = LoginView.as_view()
        with patch.object(view.view_class, 'throttle_classes', []):
            return view(request)

    def test_empty_credentials_returns_400(self):
        """Sin credenciales retorna 400."""
        response = self._post_login({})
        assert response.status_code == 400
        assert response.data['success'] is False

    def test_missing_password_returns_400(self):
        """Sin password retorna 400."""
        response = self._post_login({'username': 'test'})
        assert response.status_code == 400

    def test_missing_username_returns_400(self):
        """Sin username retorna 400."""
        response = self._post_login({'password': 'test'})
        assert response.status_code == 400

    @patch('authentication.views.authenticate', return_value=None)
    @patch('authentication.views.User.objects')
    def test_wrong_credentials_returns_401(self, mock_user_qs, mock_auth):
        """Credenciales incorrectas retorna 401."""
        mock_user_qs.get.side_effect = Exception("DoesNotExist")
        response = self._post_login({
            'username': 'nonexistent',
            'password': 'WrongPass123!',
        })
        assert response.status_code == 401


@pytest.mark.unit
class TestMeViewAuth:
    """Tests unitarios para MeView - autenticación."""

    def test_unauthenticated_returns_401(self):
        """Sin token retorna 401."""
        from rest_framework.test import APIRequestFactory
        from authentication.views import MeView
        factory = APIRequestFactory()
        request = factory.get('/api/auth/me/')
        # No authenticate → AnonymousUser
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        view = MeView.as_view()
        response = view(request)
        assert response.status_code in (401, 403)


# ============================================================
# INTEGRATION TESTS - Requieren PostgreSQL + django-tenants
# Estos tests se conectan a la BD real local
# Marcar con @pytest.mark.integration y @pytest.mark.django_db
# ============================================================

@pytest.mark.integration
@pytest.mark.django_db
class TestRegisterEndpointIntegration:
    """Tests de integración para el endpoint de registro.
    
    Estos tests crean tenants reales en PostgreSQL y verifican el flujo completo.
    Requieren: PostgreSQL corriendo con BD 'agrotech' y planes existentes.
    """

    @pytest.fixture(autouse=True)
    def disable_throttling(self):
        """Desactivar throttling en tests de integración."""
        from authentication.views import RegisterView, LoginView
        orig_register = RegisterView.throttle_classes
        orig_login = LoginView.throttle_classes
        RegisterView.throttle_classes = []
        LoginView.throttle_classes = []
        yield
        RegisterView.throttle_classes = orig_register
        LoginView.throttle_classes = orig_login

    @pytest.fixture
    def api_client(self):
        from rest_framework.test import APIClient
        return APIClient()

    @pytest.fixture
    def unique_payload(self):
        import uuid
        uid = uuid.uuid4().hex[:6]
        return {
            'email': f'test_{uid}@agrotest.com',
            'username': f'testuser_{uid}',
            'password': 'SecurePass2026!',
            'password_confirm': 'SecurePass2026!',
            'name': 'Test',
            'last_name': 'User',
            'organization_name': f'Finca Test {uid}',
        }

    @pytest.fixture(autouse=True)
    def cleanup_tenants(self, unique_payload):
        """Limpiar tenants creados después de cada test."""
        yield
        # Cleanup: borrar tenants de test creados
        try:
            from base_agrotech.models import Client
            test_tenants = Client.objects.exclude(
                schema_name__in=['public', 'test_farm']
            ).filter(schema_name__startswith='tenant_')
            for t in test_tenants:
                # Solo borrar los recién creados (con emails @agrotest.com)
                if 'finca_test_' in t.schema_name or 'otra_finca' in t.schema_name:
                    try:
                        from django.db import connection
                        with connection.cursor() as cursor:
                            cursor.execute(f'DROP SCHEMA IF EXISTS "{t.schema_name}" CASCADE')
                    except Exception:
                        pass
                    t.delete()
        except Exception:
            pass

    def test_register_returns_201(self, api_client, unique_payload):
        """Registro exitoso retorna 201."""
        response = api_client.post(
            '/api/auth/register/', unique_payload, format='json',
            SERVER_NAME='127.0.0.1'
        )
        assert response.status_code == 201, response.json()

    def test_register_returns_tokens(self, api_client, unique_payload):
        """Registro exitoso retorna JWT tokens."""
        response = api_client.post(
            '/api/auth/register/', unique_payload, format='json',
            SERVER_NAME='127.0.0.1'
        )
        data = response.json()
        assert data['success'] is True
        assert 'tokens' in data['data']
        assert 'access' in data['data']['tokens']
        assert 'refresh' in data['data']['tokens']
        # Tokens son strings no vacíos
        assert len(data['data']['tokens']['access']) > 20
        assert len(data['data']['tokens']['refresh']) > 20

    def test_register_creates_tenant(self, api_client, unique_payload):
        """Registro crea tenant con datos correctos."""
        response = api_client.post(
            '/api/auth/register/', unique_payload, format='json',
            SERVER_NAME='127.0.0.1'
        )
        data = response.json()
        assert 'tenant' in data['data']
        assert data['data']['tenant']['name'] == unique_payload['organization_name']
        assert data['data']['tenant']['on_trial'] is True
        assert data['data']['tenant']['schema_name'].startswith('tenant_')

    def test_register_creates_subscription(self, api_client, unique_payload):
        """Registro crea suscripción trial automática."""
        response = api_client.post(
            '/api/auth/register/', unique_payload, format='json',
            SERVER_NAME='127.0.0.1'
        )
        data = response.json()
        sub = data['data'].get('subscription')
        assert sub is not None
        assert sub['status'] == 'trialing'

    def test_register_duplicate_email_400(self, api_client, unique_payload):
        """Email duplicado retorna 400."""
        # Primer registro
        response1 = api_client.post(
            '/api/auth/register/', unique_payload, format='json',
            SERVER_NAME='127.0.0.1'
        )
        assert response1.status_code == 201

        # Segundo con mismo email
        import uuid
        uid2 = uuid.uuid4().hex[:6]
        payload2 = {
            'email': unique_payload['email'],  # Mismo email
            'username': f'other_{uid2}',
            'password': 'SecurePass2026!',
            'password_confirm': 'SecurePass2026!',
            'name': 'Other',
            'last_name': 'User',
            'organization_name': f'Otra Finca {uid2}',
        }
        response2 = api_client.post(
            '/api/auth/register/', payload2, format='json',
            SERVER_NAME='127.0.0.1'
        )
        assert response2.status_code == 400
        assert 'email' in response2.json().get('errors', {})


@pytest.mark.integration
@pytest.mark.django_db
class TestLoginEndpointIntegration:
    """Tests de integración para login."""

    @pytest.fixture(autouse=True)
    def disable_throttling(self):
        """Desactivar throttling en tests de integración."""
        from authentication.views import RegisterView, LoginView
        orig_register = RegisterView.throttle_classes
        orig_login = LoginView.throttle_classes
        RegisterView.throttle_classes = []
        LoginView.throttle_classes = []
        yield
        RegisterView.throttle_classes = orig_register
        LoginView.throttle_classes = orig_login

    @pytest.fixture
    def api_client(self):
        from rest_framework.test import APIClient
        return APIClient()

    @pytest.fixture
    def registered_user(self, api_client):
        """Registrar un usuario y retornar sus credenciales."""
        import uuid
        uid = uuid.uuid4().hex[:6]
        payload = {
            'email': f'login_{uid}@agrotest.com',
            'username': f'loginuser_{uid}',
            'password': 'SecurePass2026!',
            'password_confirm': 'SecurePass2026!',
            'name': 'Login',
            'last_name': 'Test',
            'organization_name': f'Finca Login {uid}',
        }
        response = api_client.post(
            '/api/auth/register/', payload, format='json',
            SERVER_NAME='127.0.0.1'
        )
        assert response.status_code == 201, f"Setup falló: {response.json()}"
        return payload

    @pytest.fixture(autouse=True)
    def cleanup_tenants(self):
        """Limpiar tenants creados después de cada test."""
        yield
        try:
            from base_agrotech.models import Client
            from django.db import connection
            test_tenants = Client.objects.filter(
                schema_name__startswith='tenant_finca_login_'
            )
            for t in test_tenants:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f'DROP SCHEMA IF EXISTS "{t.schema_name}" CASCADE')
                except Exception:
                    pass
            test_tenants.delete()
        except Exception:
            pass

    def test_login_with_username(self, api_client, registered_user):
        """Login con username retorna 200 + tokens."""
        response = api_client.post('/api/auth/login/', {
            'username': registered_user['username'],
            'password': registered_user['password'],
        }, format='json', SERVER_NAME='127.0.0.1')
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'tokens' in data
        assert 'access' in data['tokens']

    def test_login_with_email(self, api_client, registered_user):
        """Login con email como username retorna 200."""
        response = api_client.post('/api/auth/login/', {
            'username': registered_user['email'],
            'password': registered_user['password'],
        }, format='json', SERVER_NAME='127.0.0.1')
        assert response.status_code == 200

    def test_login_wrong_password(self, api_client, registered_user):
        """Login con contraseña incorrecta retorna 401."""
        response = api_client.post('/api/auth/login/', {
            'username': registered_user['username'],
            'password': 'WrongPassword!',
        }, format='json', SERVER_NAME='127.0.0.1')
        assert response.status_code == 401
        assert response.json()['success'] is False

    def test_login_nonexistent_user(self, api_client):
        """Login con usuario inexistente retorna 401."""
        response = api_client.post('/api/auth/login/', {
            'username': 'nonexistent_user_xyz',
            'password': 'SomePass123!',
        }, format='json', SERVER_NAME='127.0.0.1')
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.django_db
class TestMeEndpointIntegration:
    """Tests de integración para /me."""

    @pytest.fixture(autouse=True)
    def disable_throttling(self):
        """Desactivar throttling en tests de integración."""
        from authentication.views import RegisterView, LoginView
        orig_register = RegisterView.throttle_classes
        orig_login = LoginView.throttle_classes
        RegisterView.throttle_classes = []
        LoginView.throttle_classes = []
        yield
        RegisterView.throttle_classes = orig_register
        LoginView.throttle_classes = orig_login

    @pytest.fixture
    def api_client(self):
        from rest_framework.test import APIClient
        return APIClient()

    @pytest.fixture
    def auth_tokens(self, api_client):
        """Registrar usuario y obtener tokens."""
        import uuid
        uid = uuid.uuid4().hex[:6]
        payload = {
            'email': f'me_{uid}@agrotest.com',
            'username': f'meuser_{uid}',
            'password': 'SecurePass2026!',
            'password_confirm': 'SecurePass2026!',
            'name': 'Me',
            'last_name': 'Test',
            'organization_name': f'Finca Me {uid}',
        }
        response = api_client.post(
            '/api/auth/register/', payload, format='json',
            SERVER_NAME='127.0.0.1'
        )
        assert response.status_code == 201
        return response.json()['data']['tokens']

    @pytest.fixture(autouse=True)
    def cleanup_tenants(self):
        """Limpiar tenants creados después de cada test."""
        yield
        try:
            from base_agrotech.models import Client
            from django.db import connection
            test_tenants = Client.objects.filter(
                schema_name__startswith='tenant_finca_me_'
            )
            for t in test_tenants:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f'DROP SCHEMA IF EXISTS "{t.schema_name}" CASCADE')
                except Exception:
                    pass
            test_tenants.delete()
        except Exception:
            pass

    def test_me_with_valid_token(self, api_client, auth_tokens):
        """Endpoint /me con token válido retorna datos del usuario."""
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {auth_tokens['access']}")
        response = api_client.get('/api/auth/me/', SERVER_NAME='127.0.0.1')
        assert response.status_code == 200
        data = response.json()
        assert 'user' in data
        assert 'email' in data['user']
        assert 'username' in data['user']

    def test_me_without_token(self, api_client):
        """Endpoint /me sin token retorna 401."""
        response = api_client.get('/api/auth/me/', SERVER_NAME='127.0.0.1')
        assert response.status_code == 401

    def test_me_with_invalid_token(self, api_client):
        """Endpoint /me con token inválido retorna 401."""
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid.token.here")
        response = api_client.get('/api/auth/me/', SERVER_NAME='127.0.0.1')
        assert response.status_code == 401
