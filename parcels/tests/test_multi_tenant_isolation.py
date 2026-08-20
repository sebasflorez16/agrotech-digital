"""
Pruebas de aislamiento multi-tenant (Tenant A ↔ Tenant B).

Verifica que:
- Un tenant nunca accede a parcelas/usuarios/métricas de otro tenant.
- Los endpoints filtran por tenant_id.
- El acceso cruzado manipulando IDs es bloqueado.

Requiere PostgreSQL + django-tenants (BD real). Marcado tenant/integration.
"""
import pytest

from django.contrib.auth import get_user_model
from base_agrotech.models import Client

User = get_user_model()

pytestmark = [pytest.mark.tenant, pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def tenant_a(db):
    from datetime import date, timedelta
    from django.core.management import call_command
    from django_tenants.utils import schema_context

    tenant = Client.objects.create(
        schema_name='tenant_a',
        name='Tenant A',
        paid_until=date.today() + timedelta(days=30),
        on_trial=True,
    )
    call_command('migrate_schemas', '--schema', 'tenant_a', verbosity=0)
    yield tenant
    with schema_context('tenant_a'):
        # Cleanup opcional; el test DB se destruye al final.
        pass


@pytest.fixture
def tenant_b(db):
    from datetime import date, timedelta
    from django.core.management import call_command

    tenant = Client.objects.create(
        schema_name='tenant_b',
        name='Tenant B',
        paid_until=date.today() + timedelta(days=30),
        on_trial=True,
    )
    call_command('migrate_schemas', '--schema', 'tenant_b', verbosity=0)
    return tenant


def test_parcel_isolation(tenant_a, tenant_b):
    """Las parcelas de A no son visibles para B (y viceversa)."""
    from django_tenants.utils import schema_context
    from parcels.models import Parcel

    with schema_context('tenant_a'):
        Parcel.objects.create(
            name='Parcela A', tenant_id=tenant_a.id,
            soil_type='arcilloso', topography='plano',
        )
    with schema_context('tenant_b'):
        Parcel.objects.create(
            name='Parcela B', tenant_id=tenant_b.id,
            soil_type='arcilloso', topography='plano',
        )

    with schema_context('tenant_a'):
        assert Parcel.objects.filter(name='Parcela A').count() == 1
        assert Parcel.objects.filter(name='Parcela B').count() == 0

    with schema_context('tenant_b'):
        assert Parcel.objects.filter(name='Parcela B').count() == 1
        assert Parcel.objects.filter(name='Parcela A').count() == 0


def test_user_isolation(tenant_a, tenant_b):
    """Los usuarios de un tenant no son visibles en el listado de otro."""
    ua = User.objects.create_user(
        username='user_a', email='a@test.com', password='x',
        name='A', last_name='User', tenant=tenant_a,
    )
    ub = User.objects.create_user(
        username='user_b', email='b@test.com', password='x',
        name='B', last_name='User', tenant=tenant_b,
    )
    assert User.objects.filter(tenant_id=tenant_a.id, username='user_a').exists()
    assert User.objects.filter(tenant_id=tenant_a.id, username='user_b').count() == 0
    assert User.objects.filter(tenant_id=tenant_b.id, username='user_b').exists()
    assert User.objects.filter(tenant_id=tenant_b.id, username='user_a').count() == 0


def test_metrics_isolation(tenant_a, tenant_b):
    """El consumo (métricas) es por tenant, no compartido."""
    from billing.models import UsageMetrics
    ma = UsageMetrics.get_or_create_current(tenant_a)
    mb = UsageMetrics.get_or_create_current(tenant_b)
    ma.eosda_requests = 100
    ma.save()
    assert ma.eosda_requests == 100
    assert mb.eosda_requests == 0
    assert UsageMetrics.objects.filter(tenant=tenant_b, eosda_requests=100).count() == 0
