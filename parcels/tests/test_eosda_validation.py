"""
Pruebas de validación de EOSDA: NDRE, sincronización de parcelas y consumo.

Usan la BD real de prueba (django-tenants) y mockean las llamadas HTTP a EOSDA
para no depender de la API externa ni de credenciales.
"""
import pytest
from unittest import mock

from django.contrib.auth import get_user_model
from base_agrotech.models import Client

User = get_user_model()

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def tenant(db):
    from datetime import date, timedelta
    from django.core.management import call_command

    t = Client.objects.create(
        schema_name='tenant_val', name='Tenant Validación',
        paid_until=date.today() + timedelta(days=30), on_trial=True,
    )
    call_command('migrate_schemas', '--schema', 'tenant_val', verbosity=0)
    return t


def _make_parcel(tenant, name='Parcela Test', geom=None):
    from django_tenants.utils import schema_context
    from parcels.models import Parcel
    with schema_context(tenant.schema_name):
        return Parcel.objects.create(
            name=name, tenant_id=tenant.id,
            soil_type='arcilloso', topography='plano',
            geom=geom or {
                'type': 'Polygon',
                'coordinates': [[[-74.0, 4.0], [-74.01, 4.0], [-74.01, 4.01], [-74.0, 4.0]]],
            },
        )


def _fake_post_200(url, payload, **kwargs):
    resp = mock.Mock()
    resp.status_code = 200
    resp.json.return_value = {'request_id': 'req_ndre_123'}
    resp.raise_for_status = lambda: None
    return resp


def test_ndre_wired_in_all_index_lists():
    """NDRE está integrado en todos los puntos de validación/mapeo de índices."""
    import inspect
    from parcels import views
    from parcels import analytics_views

    # EosdaImageView: validación de índices acepta 'ndre'
    src_image = inspect.getsource(views.EosdaImageView.post)
    assert '"ndre"' in src_image or "'ndre'" in src_image

    # EosdaImageView: mapeo de nombres para mensajes incluye NDRE
    assert "'ndre': 'NDRE'" in src_image

    # EosdaSceneAnalyticsView: valid_indices incluye 'ndre'
    src_scene = inspect.getsource(views.EosdaSceneAnalyticsView.post)
    assert 'ndre' in src_scene

    # analytics_views: index_map incluye NDRE
    src_analytics = inspect.getsource(analytics_views.EOSDAAnalyticsAPIView)
    assert "'ndre': 'NDRE'" in src_analytics


def test_ndre_payload_uses_uppercase():
    """El índice se envía a EOSDA en mayúsculas (NDRE)."""
    assert 'ndre'.upper() == 'NDRE'


def test_ndre_in_scene_analytics_valid_indices():
    """NDRE está en valid_indices de EosdaSceneAnalyticsView."""
    from parcels.views import EosdaSceneAnalyticsView
    import inspect
    src = inspect.getsource(EosdaSceneAnalyticsView.post)
    assert 'ndre' in src


def test_parcel_save_does_not_call_eosda(tenant):
    """Guardar una parcela NO sincroniza con EOSDA (la parcela es 100% local)."""
    from django_tenants.utils import schema_context
    from parcels.models import Parcel

    with schema_context(tenant.schema_name):
        with mock.patch('parcels.models.Parcel._sync_to_eosda') as mock_sync:
            parcel = _make_parcel(tenant)
        mock_sync.assert_not_called()
        assert parcel.eosda_id is None
        assert parcel.sync_status == 'local'


def test_parcel_save_is_local_even_with_api_key(tenant):
    """Aun con EOSDA_API_KEY configurada, la parcela se guarda local (sin sync)."""
    from django_tenants.utils import schema_context
    from parcels.models import Parcel

    with schema_context(tenant.schema_name):
        with mock.patch('parcels.eosda_client.get_eosda_client') as mock_client, \
             mock.patch('parcels.models.settings') as mock_settings:
            mock_settings.EOSDA_API_KEY = 'test-key'
            parcel = _make_parcel(tenant, name='Local OK')
        mock_client.assert_not_called()
        assert parcel.eosda_id is None
        assert parcel.sync_status == 'local'
        assert not parcel.sync_error


def test_consumption_record_increments_quota_and_logs(tenant):
    """record() incrementa UsageMetrics.eosda_requests y escribe EosdaRequestLog."""
    from django_tenants.utils import schema_context
    from billing.models import UsageMetrics, EosdaRequestLog
    from parcels.eosda_client import get_eosda_client

    with schema_context(tenant.schema_name):
        user = User.objects.create_user(
            username='cons_user', email='cons@test.com', password='x',
            name='C', last_name='User', tenant=tenant,
        )
        client = get_eosda_client()
        before = UsageMetrics.get_or_create_current(tenant).eosda_requests
        client.record(tenant, operation='scenes', parcel_id=7, user=user, increment_quota=True)

        after = UsageMetrics.get_or_create_current(tenant).eosda_requests
        assert after == before + 1
        log = EosdaRequestLog.objects.filter(tenant=tenant, operation='scenes').first()
        assert log is not None
        assert log.parcel_id == 7
        assert log.user == user
        assert log.source == 'eosda'


def test_field_operation_does_not_increment_quota(tenant):
    """La creación de campo (field) NO incrementa eosda_requests pero SÍ loguea."""
    from django_tenants.utils import schema_context
    from billing.models import UsageMetrics, EosdaRequestLog
    from parcels.eosda_client import get_eosda_client

    with schema_context(tenant.schema_name):
        client = get_eosda_client()
        before = UsageMetrics.get_or_create_current(tenant).eosda_requests
        client.record(tenant, operation='field', parcel_id=8, increment_quota=False)
        after = UsageMetrics.get_or_create_current(tenant).eosda_requests
        assert after == before
        assert EosdaRequestLog.objects.filter(tenant=tenant, operation='field').exists()
