"""
Tests unitarios para los modelos de Crop (schema actual, multi-tenant).
"""
import uuid
import pytest
from datetime import date

from crop.models import (
    CropType, CropVariety, Crop, CropStage, CropProgressPhoto,
    CropInput, CropCatalog, PhenologicalStage, CropCycle,
)
from parcels.models import Parcel
from inventario.models import Supplier

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenant(db):
    from datetime import timedelta
    from django.core.management import call_command
    from base_agrotech.models import Client

    t = Client.objects.create(
        schema_name="tenant_crop", name="Tenant Crop",
        paid_until=date.today() + timedelta(days=30), on_trial=True,
    )
    call_command("migrate_schemas", "--schema", "tenant_crop", verbosity=0)
    return t


def _ctx(tenant):
    from django_tenants.utils import schema_context
    return schema_context(tenant.schema_name)


def _parcel(tenant, name="Parcela Test"):
    with _ctx(tenant):
        return Parcel.objects.create(
            name=name, tenant_id=tenant.id,
            soil_type="arcilloso", topography="plano",
        )


class TestCropTypeModel:
    def test_create_crop_type(self, tenant):
        with _ctx(tenant):
            ct = CropType.objects.create(name="Café", description="Arábigo")
            assert ct.name == "Café"
            assert ct.description == "Arábigo"

    def test_crop_type_str(self, tenant):
        with _ctx(tenant):
            assert str(CropType.objects.create(name="Maíz")) == "Maíz"

    def test_crop_type_unique_name(self, tenant):
        with _ctx(tenant):
            CropType.objects.create(name="Arroz")
            with pytest.raises(Exception):
                CropType.objects.create(name="Arroz")

    def test_crop_type_ordering(self, tenant):
        with _ctx(tenant):
            CropType.objects.create(name="Café")
            CropType.objects.create(name="Arroz")
            CropType.objects.create(name="Maíz")
            names = list(CropType.objects.all().values_list("name", flat=True))
            assert names == ["Arroz", "Café", "Maíz"]


class TestCropVarietyModel:
    def test_create_variety(self, tenant):
        with _ctx(tenant):
            ct = CropType.objects.create(name="Arroz")
            variety = CropVariety.objects.create(name="IR-64", crop_type=ct, cycle_days=120)
            assert variety.name == "IR-64"
            assert variety.crop_type == ct
            assert variety.cycle_days == 120

    def test_variety_str(self, tenant):
        with _ctx(tenant):
            ct = CropType.objects.create(name="Maíz")
            variety = CropVariety.objects.create(name="ICA V-305", crop_type=ct)
            assert str(variety) == "ICA V-305 (Maíz)"

    def test_variety_unique_per_type(self, tenant):
        with _ctx(tenant):
            ct = CropType.objects.create(name="Café")
            CropVariety.objects.create(name="Castillo", crop_type=ct)
            with pytest.raises(Exception):
                CropVariety.objects.create(name="Castillo", crop_type=ct)


class TestCropModel:
    @pytest.fixture
    def setup_data(self, tenant):
        parcel = _parcel(tenant, "Parcela Café")
        with _ctx(tenant):
            crop_type = CropType.objects.create(name="Café")
            variety = CropVariety.objects.create(name="Castillo", crop_type=crop_type)
            supplier = Supplier.objects.create(name="Semillas del Sur", tax_id="900123456")
        return {
            "tenant": tenant,
            "parcel": parcel,
            "crop_type": crop_type,
            "variety": variety,
            "supplier": supplier,
        }

    def test_create_crop_basic(self, setup_data):
        with _ctx(setup_data["tenant"]):
            crop = Crop.objects.create(
                name="Café Lote 1",
                crop_type=setup_data["crop_type"],
                variety=setup_data["variety"],
                parcel=setup_data["parcel"],
                area=2.5,
            )
            assert crop.name == "Café Lote 1"
            assert crop.variety == setup_data["variety"]
            assert crop.area == 2.5
            assert crop.is_deleted is False

    def test_crop_str(self, setup_data):
        with _ctx(setup_data["tenant"]):
            crop = Crop.objects.create(
                name="Mi Cultivo",
                variety=setup_data["variety"],
                parcel=setup_data["parcel"],
            )
            assert str(crop) == f"Mi Cultivo ({setup_data['variety']}) - Parcela Café"

    def test_crop_unique_id(self, setup_data):
        with _ctx(setup_data["tenant"]):
            crop = Crop.objects.create(name="Cultivo 1", parcel=setup_data["parcel"])
            assert crop.unique_id is not None
            assert isinstance(crop.unique_id, uuid.UUID)

    def test_crop_dates(self, setup_data):
        with _ctx(setup_data["tenant"]):
            crop = Crop.objects.create(
                name="Cultivo Fechas", parcel=setup_data["parcel"],
                sowing_date=date(2024, 1, 15), harvest_date=date(2024, 7, 15),
            )
            assert crop.sowing_date == date(2024, 1, 15)
            assert crop.harvest_date == date(2024, 7, 15)

    def test_crop_yield(self, setup_data):
        with _ctx(setup_data["tenant"]):
            crop = Crop.objects.create(
                name="Cultivo Rendimiento", parcel=setup_data["parcel"],
                expected_yield=3.5, actual_yield=3.8,
            )
            assert crop.expected_yield == 3.5
            assert crop.actual_yield == 3.8

    def test_crop_irrigation(self, setup_data):
        with _ctx(setup_data["tenant"]):
            crop = Crop.objects.create(
                name="Cultivo Riego", parcel=setup_data["parcel"], irrigation_type="goteo",
            )
            assert crop.irrigation_type == "goteo"

    def test_crop_seed_supplier(self, setup_data):
        with _ctx(setup_data["tenant"]):
            crop = Crop.objects.create(
                name="Cultivo Proveedor", parcel=setup_data["parcel"],
                seed_supplier=setup_data["supplier"],
            )
            assert crop.seed_supplier == setup_data["supplier"]

    def test_crop_timestamps(self, setup_data):
        with _ctx(setup_data["tenant"]):
            crop = Crop.objects.create(name="Cultivo TS", parcel=setup_data["parcel"])
            assert crop.created_on is not None
            assert crop.updated_on is not None

    def test_crop_soft_delete(self, setup_data):
        with _ctx(setup_data["tenant"]):
            crop = Crop.objects.create(name="Cultivo Delete", parcel=setup_data["parcel"])
            crop.is_deleted = True
            crop.save()
            assert crop.is_deleted is True

    def test_crop_parcel_relation(self, setup_data):
        with _ctx(setup_data["tenant"]):
            Crop.objects.create(name="C1", parcel=setup_data["parcel"])
            Crop.objects.create(name="C2", parcel=setup_data["parcel"])
            assert setup_data["parcel"].crops.count() == 2


class TestCropStageModel:
    def test_create_stage(self, tenant):
        with _ctx(tenant):
            crop = Crop.objects.create(name="Cultivo", parcel=_parcel(tenant))
            stage = CropStage.objects.create(
                crop=crop, name="Germinación", start_date=date(2024, 1, 15)
            )
            assert stage.crop == crop
            assert stage.name == "Germinación"


class TestCropProgressPhotoModel:
    def test_create_photo(self, tenant):
        with _ctx(tenant):
            crop = Crop.objects.create(name="Cultivo", parcel=_parcel(tenant))
            photo = CropProgressPhoto.objects.create(
                crop=crop, image="crop_progress/test.jpg", date=date(2024, 2, 1)
            )
            assert photo.crop == crop
            assert photo.date == date(2024, 2, 1)


class TestCropInputModel:
    def test_create_input(self, tenant):
        with _ctx(tenant):
            crop = Crop.objects.create(name="Cultivo", parcel=_parcel(tenant))
            app = CropInput.objects.create(
                crop=crop, input_type="fertilizante",
                quantity=10.5, unit="kg", application_date=date.today(),
            )
            assert app.crop == crop
            assert app.quantity == 10.5


class TestCropCatalogModel:
    def test_create_catalog(self, tenant):
        with _ctx(tenant):
            cat = CropCatalog.objects.create(name="Arroz", category="cereals")
            assert cat.name == "Arroz"
            assert cat.category == "cereals"

    def test_catalog_unique(self, tenant):
        with _ctx(tenant):
            CropCatalog.objects.create(name="Café")
            with pytest.raises(Exception):
                CropCatalog.objects.create(name="Café")


class TestPhenologicalStageModel:
    def test_create_stage(self, tenant):
        with _ctx(tenant):
            cat = CropCatalog.objects.create(name="Arroz")
            stage = PhenologicalStage.objects.create(
                crop_catalog=cat, name="Macollamiento", order=2,
                day_start=20, day_end=40, ndvi_optimal=0.6,
            )
            assert stage.crop_catalog == cat
            assert stage.name == "Macollamiento"
            assert stage.ndvi_optimal == 0.6

    def test_stage_str(self, tenant):
        with _ctx(tenant):
            cat = CropCatalog.objects.create(name="Arroz")
            stage = PhenologicalStage.objects.create(
                crop_catalog=cat, name="Floración", order=1, day_start=50, day_end=70,
            )
            assert "Arroz" in str(stage)


class TestCropCycleModel:
    def test_create_cycle(self, tenant):
        with _ctx(tenant):
            parcel = _parcel(tenant)
            cat = CropCatalog.objects.create(name="Arroz")
            cycle = CropCycle.objects.create(
                parcel=parcel, crop_catalog=cat,
                planting_date=date(2024, 3, 1), status="active",
            )
            assert cycle.parcel == parcel
            assert cycle.crop_catalog == cat
            assert cycle.days_since_planting >= 0
