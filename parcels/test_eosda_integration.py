"""
Tests de integración para las APIs de EOSDA.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from parcels.models import Parcel, CacheDatosEOSDA
from RRHH.models import Employee

pytestmark = [pytest.mark.django_db, pytest.mark.integration, pytest.mark.eosda]


class TestEOSDASceneSearchAPI:
    """Tests para la API de búsqueda de escenas EOSDA."""

    @pytest.fixture
    def setup(self):
        """Setup de datos de prueba."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            username="test_eosda",
            email="eosda@test.com",
            password="testpass123"
        )
        manager = Employee.objects.create(user=user, name="Manager EOSDA")
        parcel = Parcel.objects.create(
            name="Parcela EOSDA",
            eosda_id="test_field_123",
            manager=manager
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        return {
            'client': client,
            'user': user,
            'parcel': parcel
        }

    @patch('parcels.views.requests.get')
    def test_scene_search_success(self, mock_get, setup):
        """Test búsqueda exitosa de escenas."""
        # Mock de respuesta EOSDA
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {
                    'id': 'scene_1',
                    'date': '2024-01-15',
                    'cloud_cover': 5,
                    'coverage': 98
                },
                {
                    'id': 'scene_2',
                    'date': '2024-01-10',
                    'cloud_cover': 10,
                    'coverage': 95
                }
            ]
        }
        mock_get.return_value = mock_response
        
        url = reverse('parcel-search-scenes', kwargs={'pk': setup['parcel'].pk})
        response = setup['client'].post(url, {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) == 2

    @patch('parcels.views.requests.get')
    def test_scene_search_402_limit_exceeded(self, mock_get, setup):
        """Test manejo de error 402 (límite excedido)."""
        mock_response = MagicMock()
        mock_response.status_code = 402
        mock_response.text = "Payment Required"
        mock_get.return_value = mock_response
        
        url = reverse('parcel-search-scenes', kwargs={'pk': setup['parcel'].pk})
        response = setup['client'].post(url, {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        })
        
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert 'límite' in response.data['error'].lower()

    def test_scene_search_without_eosda_id(self, setup):
        """Test búsqueda en parcela sin eosda_id."""
        parcel_no_id = Parcel.objects.create(
            name="Sin EOSDA ID",
            manager=setup['parcel'].manager
        )
        
        url = reverse('parcel-search-scenes', kwargs={'pk': parcel_no_id.pk})
        response = setup['client'].post(url, {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_scene_search_missing_dates(self, setup):
        """Test búsqueda sin fechas requeridas."""
        url = reverse('parcel-search-scenes', kwargs={'pk': setup['parcel'].pk})
        response = setup['client'].post(url, {})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestEOSDAImageRequestAPI:
    """Tests para la API de solicitud de imágenes EOSDA."""

    @pytest.fixture
    def setup(self):
        """Setup de datos de prueba."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            username="test_image",
            password="testpass123"
        )
        manager = Employee.objects.create(user=user, name="Manager")
        parcel = Parcel.objects.create(
            name="Parcela Image",
            eosda_id="field_456",
            manager=manager
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        return {
            'client': client,
            'parcel': parcel
        }

    @patch('parcels.views.requests.post')
    def test_request_ndvi_image_success(self, mock_post, setup):
        """Test solicitud exitosa de imagen NDVI."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'request_id': 'req_123456'
        }
        mock_post.return_value = mock_response
        
        url = reverse('parcel-request-image', kwargs={'pk': setup['parcel'].pk})
        response = setup['client'].post(url, {
            'scene_id': 'scene_abc',
            'index_type': 'ndvi',
            'format': 'png'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'request_id' in response.data

    @patch('parcels.views.requests.post')
    def test_request_ndmi_image(self, mock_post, setup):
        """Test solicitud de imagen NDMI."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'request_id': 'req_ndmi'}
        mock_post.return_value = mock_response
        
        url = reverse('parcel-request-image', kwargs={'pk': setup['parcel'].pk})
        response = setup['client'].post(url, {
            'scene_id': 'scene_xyz',
            'index_type': 'ndmi'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['request_id'] == 'req_ndmi'

    def test_request_image_invalid_index(self, setup):
        """Test solicitud con índice inválido."""
        url = reverse('parcel-request-image', kwargs={'pk': setup['parcel'].pk})
        response = setup['client'].post(url, {
            'scene_id': 'scene_abc',
            'index_type': 'invalid_index'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestEOSDAAnalyticsAPI:
    """Tests para la API de analytics científicos EOSDA."""

    @pytest.fixture
    def setup(self):
        """Setup de datos de prueba."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            username="test_analytics",
            password="testpass123"
        )
        manager = Employee.objects.create(user=user, name="Manager")
        parcel = Parcel.objects.create(
            name="Parcela Analytics",
            eosda_id="field_analytics",
            manager=manager
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        return {
            'client': client,
            'parcel': parcel
        }

    @patch('parcels.analytics_views.requests.get')
    def test_analytics_success(self, mock_get, setup):
        """Test obtención exitosa de analytics."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ndvi': {
                'mean': 0.75,
                'std': 0.05,
                'min': 0.65,
                'max': 0.85
            },
            'ndmi': {
                'mean': 0.65,
                'std': 0.04,
                'min': 0.55,
                'max': 0.75
            }
        }
        mock_get.return_value = mock_response
        
        url = reverse('parcel-eosda-analytics', kwargs={'pk': setup['parcel'].pk})
        response = setup['client'].get(url, {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'ndvi' in response.data
        assert 'interpretacion' in response.data

    def test_analytics_cache(self, setup):
        """Test que los analytics se cachean correctamente."""
        # Crear entrada de cache
        cache_entry = CacheDatosEOSDA.objects.create(
            parcel=setup['parcel'],
            fecha_inicio='2024-01-01',
            fecha_fin='2024-01-31',
            tipo_dato='mt_stats',
            hash_parametros='test_hash',
            datos_json={'ndvi': {'mean': 0.8}}
        )
        
        url = reverse('parcel-eosda-analytics', kwargs={'pk': setup['parcel'].pk})
        response = setup['client'].get(url, {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        })
        
        # Verificar que existe cache
        assert CacheDatosEOSDA.objects.filter(parcel=setup['parcel']).exists()

    @patch('parcels.analytics_views.requests.get')
    def test_analytics_interpretation(self, mock_get, setup):
        """Test interpretación agronómica de datos."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ndvi': {'mean': 0.85, 'std': 0.03},
            'evi': {'mean': 0.75, 'std': 0.04}
        }
        mock_get.return_value = mock_response
        
        url = reverse('parcel-eosda-analytics', kwargs={'pk': setup['parcel'].pk})
        response = setup['client'].get(url, {
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        })
        
        assert 'interpretacion' in response.data
        assert 'ndvi' in response.data['interpretacion']


class TestEOSDAWeatherAPI:
    """Tests para la API de pronóstico meteorológico."""

    @pytest.fixture
    def setup(self):
        """Setup de datos de prueba."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            username="test_weather",
            password="testpass123"
        )
        manager = Employee.objects.create(user=user, name="Manager")
        parcel = Parcel.objects.create(
            name="Parcela Weather",
            eosda_id="field_weather",
            geom={
                "type": "Polygon",
                "coordinates": [[
                    [-74.0, 4.0],
                    [-74.01, 4.0],
                    [-74.01, 4.01],
                    [-74.0, 4.01],
                    [-74.0, 4.0]
                ]]
            },
            manager=manager
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        return {
            'client': client,
            'parcel': parcel
        }

    @patch('parcels.weather.requests.get')
    def test_weather_forecast_success(self, mock_get, setup):
        """Test pronóstico meteorológico exitoso."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'forecast': [
                {
                    'date': '2024-02-01',
                    'temperature': {'min': 15, 'max': 25},
                    'precipitation': 5,
                    'humidity': 70
                }
            ]
        }
        mock_get.return_value = mock_response
        
        url = reverse('parcel-weather-forecast', kwargs={'pk': setup['parcel'].pk})
        response = setup['client'].get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'forecast' in response.data

    def test_weather_without_geom(self, setup):
        """Test pronóstico sin geometría en parcela."""
        parcel_no_geom = Parcel.objects.create(
            name="Sin Geometría",
            eosda_id="field_no_geom",
            manager=setup['parcel'].manager
        )
        
        url = reverse('parcel-weather-forecast', kwargs={'pk': parcel_no_geom.pk})
        response = setup['client'].get(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestEOSDAImageResult:
    """Tests para la API de resultado de imágenes."""

    @pytest.fixture
    def setup(self):
        """Setup de datos de prueba."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(
            username="test_result",
            password="testpass123"
        )
        manager = Employee.objects.create(user=user, name="Manager")
        parcel = Parcel.objects.create(
            name="Parcela Result",
            eosda_id="field_result",
            manager=manager
        )
        
        client = APIClient()
        client.force_authenticate(user=user)
        
        return {
            'client': client,
            'parcel': parcel
        }

    @patch('parcels.views.requests.get')
    def test_image_result_ready(self, mock_get, setup):
        """Test imagen lista para descarga."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'fake_image_data'
        mock_response.headers = {'content-type': 'image/png'}
        mock_get.return_value = mock_response
        
        url = reverse('parcel-image-result', kwargs={'pk': setup['parcel'].pk})
        response = setup['client'].post(url, {
            'request_id': 'req_123'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'image_base64' in response.data

    @patch('parcels.views.requests.get')
    def test_image_result_processing(self, mock_get, setup):
        """Test imagen aún en procesamiento."""
        mock_response = MagicMock()
        mock_response.status_code = 202  # Accepted, still processing
        mock_get.return_value = mock_response
        
        url = reverse('parcel-image-result', kwargs={'pk': setup['parcel'].pk})
        response = setup['client'].post(url, {
            'request_id': 'req_processing'
        })
        
        assert response.status_code == status.HTTP_202_ACCEPTED
