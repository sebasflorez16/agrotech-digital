"""
Configuración compartida de pytest para todos los tests.
"""
import sys
import os
from pathlib import Path

# manage.py agrega ./metrica a sys.path; pytest no lo hace.
# Sin esto, 'from users.serializers import ...' falla al resolver URLs.
_METRICA_DIR = str(Path(__file__).parent / "metrica")
if _METRICA_DIR not in sys.path:
    sys.path.insert(0, _METRICA_DIR)

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture(scope='session')
def django_db_setup():
    """
    Setup de base de datos para tests.
    
    Para tests de integración con django-tenants se usa la BD PostgreSQL real.
    El conftest NO sobrescribe DATABASES para mantener la config del settings
    (django_tenants.postgresql_backend → PostgreSQL local).
    
    Los tests unitarios que no usan BD (marcados @pytest.mark.unit) no
    necesitan esta fixture en absoluto.
    """
    pass


@pytest.fixture
def api_client():
    """Cliente API REST para tests."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def admin_user():
    """Usuario administrador para tests."""
    return User.objects.create_superuser(
        username='admin_test',
        email='admin@test.com',
        password='adminpass123',
        name='Admin',
        last_name='Test'
    )


@pytest.fixture
def regular_user():
    """Usuario regular para tests."""
    return User.objects.create_user(
        username='user_test',
        email='user@test.com',
        password='userpass123',
        name='User',
        last_name='Test'
    )


@pytest.fixture
def authenticated_client(regular_user):
    """Cliente autenticado para tests."""
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=regular_user)
    return client


@pytest.fixture
def sample_employee(regular_user):
    """Empleado de ejemplo para tests."""
    from RRHH.models import Employee
    return Employee.objects.create(
        user=regular_user,
        name=f"{regular_user.name} {regular_user.last_name}",
        job_title="Agrónomo"
    )


@pytest.fixture
def sample_parcel(sample_employee):
    """Parcela de ejemplo para tests."""
    from parcels.models import Parcel
    return Parcel.objects.create(
        name="Parcela Test",
        description="Parcela de prueba",
        manager=sample_employee,
        soil_type="arcilloso",
        topography="plano",
        geom={
            "type": "Polygon",
            "coordinates": [[
                [-74.0, 4.0],
                [-74.01, 4.0],
                [-74.01, 4.01],
                [-74.0, 4.01],
                [-74.0, 4.0]
            ]]
        }
    )


@pytest.fixture
def sample_crop_type():
    """Tipo de cultivo de ejemplo."""
    from crop.models import CropType
    return CropType.objects.create(
        name="Café",
        description="Cultivo de café arábigo"
    )


@pytest.fixture
def sample_crop(sample_parcel, sample_crop_type):
    """Cultivo de ejemplo para tests."""
    from crop.models import Crop
    from datetime import date
    return Crop.objects.create(
        name="Café Lote 1",
        crop_type=sample_crop_type,
        parcel=sample_parcel,
        area=2.5,
        sowing_date=date(2024, 1, 15),
        manager=sample_parcel.manager
    )


@pytest.fixture(scope="session", autouse=True)
def clear_throttle_cache(django_db_setup):
    """Limpia la caché al inicio de la sesión para evitar throttling residual.

    El LoginThrottle usa la caché (FileBasedCache en /tmp/agrotech-cache) y
    persiste entre ejecuciones; sin esta limpieza los tests de login acaban
    devolviendo 429 tras varias corridas.
    """
    from django.core.cache import cache
    cache.clear()


@pytest.fixture(scope="session", autouse=True)
def seed_subscription_plans(django_db_setup, django_db_blocker):
    """Siembra los planes de suscripción (free/basic/pro) una vez por sesión.

    Varios tests (registro, límites de billing) requieren que existan los planes.
    `seed_plans` delega en `create_billing_plans`, que es idempotente.
    """
    from django.core.management import call_command
    with django_db_blocker.unblock():
        call_command("seed_plans", verbosity=0)


@pytest.fixture
def sample_supplier():
    """Proveedor de ejemplo para tests."""
    from inventario.models import Supplier
    return Supplier.objects.create(
        name="Agroquímicos del Sur",
        nit="900123456-7",
        phone="+573001234567",
        email="ventas@agrosur.com"
    )


@pytest.fixture
def sample_supply():
    """Insumo de ejemplo para tests."""
    from inventario.models import Supply
    return Supply.objects.create(
        name="Fertilizante NPK 15-15-15",
        quantity=1000,
        unit_value=35000,
        category="fertilizante"
    )


@pytest.fixture
def mock_eosda_response():
    """Respuesta mock de EOSDA API."""
    return {
        'results': [
            {
                'id': 'scene_test_1',
                'date': '2024-01-15',
                'cloud_cover': 5,
                'coverage': 98,
                'satellite': 'Sentinel-2'
            }
        ]
    }


@pytest.fixture
def mock_eosda_stats():
    """Estadísticas mock de EOSDA."""
    return {
        'ndvi': {
            'mean': 0.75,
            'std': 0.05,
            'min': 0.65,
            'max': 0.85,
            'count': 1000
        },
        'ndmi': {
            'mean': 0.65,
            'std': 0.04,
            'min': 0.55,
            'max': 0.75,
            'count': 1000
        },
        'evi': {
            'mean': 0.70,
            'std': 0.06,
            'min': 0.60,
            'max': 0.80,
            'count': 1000
        }
    }


# Configuración de markers personalizados
def pytest_configure(config):
    """Configurar markers personalizados de pytest."""
    config.addinivalue_line("markers", "unit: marca tests unitarios")
    config.addinivalue_line("markers", "integration: marca tests de integración")
    config.addinivalue_line("markers", "slow: marca tests lentos")
    config.addinivalue_line("markers", "eosda: marca tests que usan EOSDA API")
    config.addinivalue_line("markers", "tenant: marca tests de multi-tenancy")
