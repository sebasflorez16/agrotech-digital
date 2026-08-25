"""
Tests unitarios para los modelos de Parcel (schema actual, multi-tenant).
"""
import uuid
import pytest
from datetime import datetime, date
from django.utils import timezone

from parcels.models import (
    Parcel, ParcelActionLog, ParcelSceneCache, CacheDatosEOSDA,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenant(db):
    from datetime import timedelta
    from django.core.management import call_command
    from base_agrotech.models import Client

    t = Client.objects.create(
        schema_name="tenant_parcels", name="Tenant Parcels",
        paid_until=date.today() + timedelta(days=30), on_trial=True,
    )
    call_command("migrate_schemas", "--schema", "tenant_parcels", verbosity=0)
    return t


def _ctx(tenant):
    from django_tenants.utils import schema_context
    return schema_context(tenant.schema_name)


def _sample_geojson():
    return {
        "type": "Polygon",
        "coordinates": [[
            [-74.0, 4.0],
            [-74.01, 4.0],
            [-74.01, 4.01],
            [-74.0, 4.01],
            [-74.0, 4.0],
        ]],
    }


class TestParcelModel:
    def test_create_parcel_basic(self, tenant):
        with _ctx(tenant):
            parcel = Parcel.objects.create(
                name="Campo Test", description="Descripción", eosda_id="eosda_001",
                tenant_id=tenant.id, soil_type="arcilloso", topography="plano",
            )
            assert parcel.name == "Campo Test"
            assert parcel.soil_type == "arcilloso"
            assert parcel.topography == "plano"
            assert parcel.state is True
            assert parcel.is_deleted is False
            assert parcel.sync_status == "local"

    def test_parcel_str(self, tenant):
        with _ctx(tenant):
            parcel = Parcel.objects.create(
                name="Mi Parcela", eosda_id="eosda_002",
                soil_type="arenoso", topography="plano",
            )
            assert str(parcel) == "Mi Parcela"

    def test_parcel_unique_id(self, tenant):
        with _ctx(tenant):
            p1 = Parcel.objects.create(
                name="P1", eosda_id="eosda_003", soil_type="arenoso", topography="plano",
            )
            p2 = Parcel.objects.create(
                name="P2", eosda_id="eosda_004", soil_type="arenoso", topography="plano",
            )
            assert isinstance(p1.unique_id, uuid.UUID)
            assert p1.unique_id != p2.unique_id

    def test_parcel_eosda_id_unique(self, tenant):
        with _ctx(tenant):
            Parcel.objects.create(
                name="P1", eosda_id="12345", soil_type="arenoso", topography="plano",
            )
            with pytest.raises(Exception):
                Parcel.objects.create(
                    name="P2", eosda_id="12345", soil_type="arenoso", topography="plano",
                )

    def test_parcel_area_calculation(self, tenant):
        with _ctx(tenant):
            parcel = Parcel.objects.create(
                name="Campo con Área", eosda_id="eosda_area", geom=_sample_geojson(),
                soil_type="arenoso", topography="plano",
            )
            assert parcel.area_hectares() > 0

    def test_parcel_area_without_geom(self, tenant):
        with _ctx(tenant):
            parcel = Parcel.objects.create(
                name="Sin Geometría", eosda_id="eosda_noarea",
                soil_type="arenoso", topography="plano",
            )
            assert parcel.area_hectares() == 0

    def test_parcel_soft_delete_flags(self, tenant):
        with _ctx(tenant):
            parcel = Parcel.objects.create(
                name="Parcela", eosda_id="eosda_del", soil_type="arenoso", topography="plano",
            )
            parcel.is_deleted = True
            parcel.deleted_at = timezone.now()
            parcel.save()
            assert parcel.is_deleted is True
            assert parcel.deleted_at is not None

    def test_parcel_timestamps(self, tenant):
        with _ctx(tenant):
            parcel = Parcel.objects.create(
                name="Parcela", eosda_id="eosda_ts", soil_type="arenoso", topography="plano",
            )
            assert parcel.created_on is not None
            assert parcel.updated_on is not None

    def test_parcel_soil_and_topography(self, tenant):
        with _ctx(tenant):
            for soil in ["arenoso", "arcilloso", "limoso", "franco"]:
                parcel = Parcel.objects.create(
                    name=f"Parcela {soil}", eosda_id=f"eosda_{soil}",
                    soil_type=soil, topography="plano",
                )
                assert parcel.soil_type == soil


class TestParcelActionLogModel:
    @pytest.fixture
    def parcel(self, tenant):
        with _ctx(tenant):
            return Parcel.objects.create(
                name="Parcela Audit", eosda_id="eosda_log",
                soil_type="arenoso", topography="plano",
            )

    def test_create_action_log(self, tenant, parcel):
        with _ctx(tenant):
            log = ParcelActionLog.objects.create(parcel=parcel, action="create")
            assert log.parcel == parcel
            assert log.action == "create"
            assert log.timestamp is not None

    def test_action_choices(self, tenant, parcel):
        with _ctx(tenant):
            for action in ["create", "update", "delete"]:
                log = ParcelActionLog.objects.create(parcel=parcel, action=action)
                assert log.action == action


class TestParcelSceneCacheModel:
    def test_create_scene_cache(self, tenant):
        with _ctx(tenant):
            parcel = Parcel.objects.create(
                name="Parcela Cache", eosda_id="eosda_scene",
                soil_type="arenoso", topography="plano",
            )
            cache = ParcelSceneCache.objects.create(
                parcel=parcel, scene_id="scene_1",
                date=datetime(2024, 1, 15).date(), index_type="NDVI",
            )
            assert cache.parcel == parcel
            assert cache.index_type == "NDVI"


class TestCacheDatosEOSDAModel:
    def test_create_cache_entry(self, tenant):
        with _ctx(tenant):
            cache = CacheDatosEOSDA.objects.create(
                tenant_id=tenant.id, parcela_id=10, indice="NDVI",
                tipo_dato="statistics", geometria_hash="abc123",
                datos={"mean": 0.75}, expira_en=timezone.now(),
            )
            assert cache.tenant_id == tenant.id
            assert cache.indice == "NDVI"
            assert cache.datos["mean"] == 0.75

    def test_cache_timestamps(self, tenant):
        with _ctx(tenant):
            cache = CacheDatosEOSDA.objects.create(
                tenant_id=tenant.id, indice="NDMI", tipo_dato="statistics",
                geometria_hash="xyz789", datos={}, expira_en=timezone.now(),
            )
            assert cache.timestamp is not None
            assert cache.expira_en is not None
