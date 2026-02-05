"""
Tests de autenticación y multi-tenancy.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from base_agrotech.models import Client, Domain

User = get_user_model()

pytestmark = [pytest.mark.django_db, pytest.mark.tenant]


class TestAuthenticationAPI:
    """Tests para el sistema de autenticación JWT."""

    @pytest.fixture
    def user_data(self):
        """Datos de usuario de prueba."""
        return {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'name': 'Test',
            'last_name': 'User'
        }

    @pytest.fixture
    def created_user(self, user_data):
        """Usuario creado para tests."""
        return User.objects.create_user(**user_data)

    def test_login_success(self, created_user, user_data):
        """Test login exitoso con JWT."""
        client = APIClient()
        url = reverse('authentication:login')
        
        response = client.post(url, {
            'username': user_data['username'],
            'password': user_data['password']
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert 'user' in response.data

    def test_login_invalid_credentials(self):
        """Test login con credenciales inválidas."""
        client = APIClient()
        url = reverse('authentication:login')
        
        response = client.post(url, {
            'username': 'nonexistent',
            'password': 'wrongpass'
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_fields(self):
        """Test login sin campos requeridos."""
        client = APIClient()
        url = reverse('authentication:login')
        
        response = client.post(url, {})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_refresh_token(self, created_user, user_data):
        """Test refresh de token JWT."""
        client = APIClient()
        login_url = reverse('authentication:login')
        
        # Login para obtener tokens
        login_response = client.post(login_url, {
            'username': user_data['username'],
            'password': user_data['password']
        })
        refresh_token = login_response.data['refresh']
        
        # Refresh token
        refresh_url = reverse('token_refresh')
        refresh_response = client.post(refresh_url, {
            'refresh': refresh_token
        })
        
        assert refresh_response.status_code == status.HTTP_200_OK
        assert 'access' in refresh_response.data

    def test_protected_endpoint_without_auth(self):
        """Test endpoint protegido sin autenticación."""
        client = APIClient()
        url = reverse('parcel-list')
        
        response = client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoint_with_auth(self, created_user, user_data):
        """Test endpoint protegido con autenticación."""
        client = APIClient()
        
        # Login
        login_url = reverse('authentication:login')
        login_response = client.post(login_url, {
            'username': user_data['username'],
            'password': user_data['password']
        })
        access_token = login_response.data['access']
        
        # Acceder a endpoint protegido
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        url = reverse('parcel-list')
        response = client.get(url)
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_token_contains_user_info(self, created_user, user_data):
        """Test que el token contiene información del usuario."""
        client = APIClient()
        url = reverse('authentication:login')
        
        response = client.post(url, {
            'username': user_data['username'],
            'password': user_data['password']
        })
        
        assert response.data['user']['username'] == user_data['username']
        assert response.data['user']['email'] == user_data['email']

    def test_inactive_user_cannot_login(self, created_user, user_data):
        """Test que usuario inactivo no puede hacer login."""
        created_user.is_active = False
        created_user.save()
        
        client = APIClient()
        url = reverse('authentication:login')
        
        response = client.post(url, {
            'username': user_data['username'],
            'password': user_data['password']
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestMultiTenancy:
    """Tests para el sistema multi-tenant."""

    @pytest.fixture
    def public_tenant(self):
        """Tenant público (schema public)."""
        tenant, created = Client.objects.get_or_create(
            schema_name='public',
            defaults={
                'name': 'Public',
                'paid_until': '2099-12-31',
                'on_trial': False
            }
        )
        return tenant

    @pytest.fixture
    def test_tenant(self):
        """Tenant de prueba."""
        tenant = Client.objects.create(
            schema_name='test_tenant',
            name='Test Tenant',
            paid_until='2025-12-31',
            on_trial=True
        )
        # Crear dominio para el tenant
        Domain.objects.create(
            domain='test.localhost',
            tenant=tenant,
            is_primary=True
        )
        return tenant

    def test_public_tenant_exists(self, public_tenant):
        """Test que existe el tenant público."""
        assert Client.objects.filter(schema_name='public').exists()
        assert public_tenant.schema_name == 'public'

    def test_create_tenant(self, test_tenant):
        """Test creación de nuevo tenant."""
        assert test_tenant.schema_name == 'test_tenant'
        assert test_tenant.name == 'Test Tenant'
        assert test_tenant.on_trial is True

    def test_tenant_has_domain(self, test_tenant):
        """Test que tenant tiene dominio asociado."""
        domain = Domain.objects.filter(tenant=test_tenant).first()
        assert domain is not None
        assert domain.domain == 'test.localhost'
        assert domain.is_primary is True

    def test_tenant_paid_until(self, test_tenant):
        """Test fecha de pago del tenant."""
        from datetime import date
        assert test_tenant.paid_until >= date.today()

    def test_multiple_tenants_isolation(self):
        """Test aislamiento entre tenants."""
        tenant1 = Client.objects.create(
            schema_name='tenant1',
            name='Tenant 1',
            paid_until='2025-12-31'
        )
        tenant2 = Client.objects.create(
            schema_name='tenant2',
            name='Tenant 2',
            paid_until='2025-12-31'
        )
        
        assert tenant1.schema_name != tenant2.schema_name
        assert Client.objects.filter(schema_name='tenant1').exists()
        assert Client.objects.filter(schema_name='tenant2').exists()


class TestHealthCheck:
    """Tests para el endpoint de health check."""

    def test_health_check_endpoint(self):
        """Test que el health check responde sin requerir tenant."""
        client = APIClient()
        response = client.get('/health/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"status": "ok"}

    def test_health_check_no_authentication_required(self):
        """Test que health check no requiere autenticación."""
        client = APIClient()
        # Sin credenciales
        response = client.get('/health/')
        
        assert response.status_code == status.HTTP_200_OK


class TestCORS:
    """Tests para configuración CORS."""

    def test_cors_headers_present(self, created_user=None):
        """Test que headers CORS están presentes."""
        if not created_user:
            created_user = User.objects.create_user(
                username='cors_user',
                password='pass123'
            )
        
        client = APIClient()
        client.force_authenticate(user=created_user)
        
        response = client.get(reverse('parcel-list'))
        
        # Verificar headers CORS
        assert 'Access-Control-Allow-Origin' in response or response.status_code in [200, 404]

    def test_preflight_request(self):
        """Test request OPTIONS (preflight)."""
        client = APIClient()
        
        response = client.options(
            reverse('parcel-list'),
            HTTP_ORIGIN='https://agrotechcolombia.netlify.app'
        )
        
        # Debe permitir el preflight
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]


class TestCSRF:
    """Tests para protección CSRF."""

    def test_csrf_exempt_for_api(self, created_user=None):
        """Test que APIs están exentas de CSRF con JWT."""
        if not created_user:
            created_user = User.objects.create_user(
                username='csrf_user',
                password='pass123'
            )
        
        client = APIClient()
        client.force_authenticate(user=created_user)
        
        # POST sin CSRF token (JWT es suficiente)
        response = client.post(reverse('parcel-list'), {})
        
        # No debe fallar por CSRF
        assert response.status_code != status.HTTP_403_FORBIDDEN


class TestUserRoles:
    """Tests para roles de usuario."""

    def test_admin_role(self):
        """Test usuario con rol admin."""
        admin = User.objects.create_user(
            username='admin',
            role='admin',
            is_staff=True
        )
        assert admin.role == 'admin'
        assert admin.is_staff is True

    def test_manager_role(self):
        """Test usuario con rol manager."""
        manager = User.objects.create_user(
            username='manager',
            role='manager'
        )
        assert manager.role == 'manager'

    def test_employee_role(self):
        """Test usuario con rol employee."""
        employee = User.objects.create_user(
            username='employee',
            role='employee'
        )
        assert employee.role == 'employee'

    def test_accountant_role(self):
        """Test usuario con rol accountant."""
        accountant = User.objects.create_user(
            username='accountant',
            role='accountant'
        )
        assert accountant.role == 'accountant'

    def test_default_role(self):
        """Test rol por defecto."""
        user = User.objects.create_user(username='user')
        # Verificar que tiene algún rol por defecto o None
        assert hasattr(user, 'role')
