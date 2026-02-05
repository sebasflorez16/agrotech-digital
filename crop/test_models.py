"""
Tests unitarios para los modelos de Crop.
"""
import pytest
import uuid
from datetime import date, timedelta
from crop.models import CropType, Crop, PhenologicalStage, CropPhoto, SupplyApplication
from parcels.models import Parcel
from RRHH.models import Employee
from inventario.models import Supply, Supplier

pytestmark = pytest.mark.django_db


class TestCropTypeModel:
    """Tests para el modelo CropType."""

    def test_create_crop_type(self):
        """Test creación de tipo de cultivo."""
        crop_type = CropType.objects.create(
            name="Café",
            description="Cultivo de café arábigo"
        )
        assert crop_type.name == "Café"
        assert crop_type.description == "Cultivo de café arábigo"

    def test_crop_type_str(self):
        """Test representación string."""
        crop_type = CropType.objects.create(name="Maíz")
        assert str(crop_type) == "Maíz"

    def test_crop_type_unique_name(self):
        """Test que el nombre debe ser único."""
        CropType.objects.create(name="Arroz")
        with pytest.raises(Exception):  # IntegrityError
            CropType.objects.create(name="Arroz")

    def test_crop_type_ordering(self):
        """Test ordenamiento por nombre."""
        CropType.objects.create(name="Café")
        CropType.objects.create(name="Arroz")
        CropType.objects.create(name="Maíz")
        
        types = list(CropType.objects.all().values_list('name', flat=True))
        assert types == ["Arroz", "Café", "Maíz"]


class TestCropModel:
    """Tests para el modelo Crop."""

    @pytest.fixture
    def setup_data(self):
        """Fixture para crear datos de prueba."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Usuario y empleado
        user = User.objects.create_user(
            username="manager_crop",
            email="crop@test.com"
        )
        manager = Employee.objects.create(user=user, name="Manager Crop")
        
        # Parcela
        parcel = Parcel.objects.create(
            name="Parcela Café",
            manager=manager
        )
        
        # Tipo de cultivo
        crop_type = CropType.objects.create(name="Café")
        
        # Proveedor
        supplier = Supplier.objects.create(
            name="Semillas del Sur",
            nit="900123456",
            phone="3001234567"
        )
        
        # Variedad (Supply)
        variety = Supply.objects.create(
            name="Café Arábigo Colombia",
            quantity=100,
            unit_value=5000
        )
        
        return {
            'manager': manager,
            'parcel': parcel,
            'crop_type': crop_type,
            'supplier': supplier,
            'variety': variety
        }

    def test_create_crop_basic(self, setup_data):
        """Test creación básica de cultivo."""
        crop = Crop.objects.create(
            name="Café Lote 1",
            crop_type=setup_data['crop_type'],
            variety=setup_data['variety'],
            parcel=setup_data['parcel'],
            area=2.5,
            manager=setup_data['manager']
        )
        assert crop.name == "Café Lote 1"
        assert crop.crop_type == setup_data['crop_type']
        assert crop.area == 2.5
        assert crop.is_deleted is False

    def test_crop_str_representation(self, setup_data):
        """Test representación string del cultivo."""
        crop = Crop.objects.create(
            name="Mi Cultivo",
            variety=setup_data['variety'],
            parcel=setup_data['parcel']
        )
        expected = f"Mi Cultivo ({setup_data['variety']}) - Parcela Café"
        assert str(crop) == expected

    def test_crop_unique_id_generation(self, setup_data):
        """Test generación automática de UUID."""
        crop = Crop.objects.create(
            name="Cultivo 1",
            parcel=setup_data['parcel']
        )
        assert crop.unique_id is not None
        assert isinstance(crop.unique_id, uuid.UUID)

    def test_crop_with_dates(self, setup_data):
        """Test cultivo con fechas de siembra y cosecha."""
        sowing = date(2024, 1, 15)
        harvest = date(2024, 7, 15)
        
        crop = Crop.objects.create(
            name="Cultivo con Fechas",
            parcel=setup_data['parcel'],
            sowing_date=sowing,
            harvest_date=harvest
        )
        assert crop.sowing_date == sowing
        assert crop.harvest_date == harvest

    def test_crop_yield_data(self, setup_data):
        """Test datos de rendimiento."""
        crop = Crop.objects.create(
            name="Cultivo Rendimiento",
            parcel=setup_data['parcel'],
            expected_yield=3.5,
            actual_yield=3.8
        )
        assert crop.expected_yield == 3.5
        assert crop.actual_yield == 3.8

    def test_crop_irrigation_type(self, setup_data):
        """Test tipos de riego."""
        irrigation_types = ["goteo", "aspersión", "gravedad", "micro-aspersión"]
        for irrigation in irrigation_types:
            crop = Crop.objects.create(
                name=f"Cultivo {irrigation}",
                parcel=setup_data['parcel'],
                irrigation_type=irrigation
            )
            assert crop.irrigation_type == irrigation

    def test_crop_with_supplier(self, setup_data):
        """Test cultivo con proveedor de semilla."""
        crop = Crop.objects.create(
            name="Cultivo con Proveedor",
            parcel=setup_data['parcel'],
            seed_supplier=setup_data['supplier']
        )
        assert crop.seed_supplier == setup_data['supplier']

    def test_crop_timestamps(self, setup_data):
        """Test timestamps automáticos."""
        crop = Crop.objects.create(
            name="Cultivo Timestamps",
            parcel=setup_data['parcel']
        )
        assert crop.created_on is not None
        assert crop.updated_on is not None

    def test_crop_soft_delete(self, setup_data):
        """Test soft delete."""
        crop = Crop.objects.create(
            name="Cultivo Delete",
            parcel=setup_data['parcel']
        )
        crop.is_deleted = True
        crop.deleted_at = date.today()
        crop.save()
        
        assert crop.is_deleted is True
        assert crop.deleted_at is not None

    def test_crop_historical_records(self, setup_data):
        """Test registro histórico de cambios."""
        crop = Crop.objects.create(
            name="Cultivo Histórico",
            parcel=setup_data['parcel']
        )
        assert crop.historical.count() == 1
        
        crop.name = "Cultivo Modificado"
        crop.save()
        assert crop.historical.count() == 2

    def test_crop_ordering(self, setup_data):
        """Test ordenamiento por fecha de siembra y nombre."""
        today = date.today()
        
        Crop.objects.create(
            name="Cultivo A",
            parcel=setup_data['parcel'],
            sowing_date=today - timedelta(days=10)
        )
        Crop.objects.create(
            name="Cultivo B",
            parcel=setup_data['parcel'],
            sowing_date=today - timedelta(days=5)
        )
        
        crops = list(Crop.objects.all().values_list('name', flat=True))
        # Ordenado por -sowing_date (más reciente primero)
        assert crops == ["Cultivo B", "Cultivo A"]

    def test_crop_parcel_relationship(self, setup_data):
        """Test relación con parcela (related_name='crops')."""
        crop1 = Crop.objects.create(name="Cultivo 1", parcel=setup_data['parcel'])
        crop2 = Crop.objects.create(name="Cultivo 2", parcel=setup_data['parcel'])
        
        parcel_crops = setup_data['parcel'].crops.all()
        assert crop1 in parcel_crops
        assert crop2 in parcel_crops
        assert parcel_crops.count() == 2


class TestPhenologicalStage:
    """Tests para el modelo PhenologicalStage."""

    @pytest.fixture
    def crop(self):
        """Fixture para crear un cultivo."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(username="user_pheno")
        manager = Employee.objects.create(user=user, name="Manager")
        parcel = Parcel.objects.create(name="Parcela", manager=manager)
        
        return Crop.objects.create(
            name="Cultivo Fenología",
            parcel=parcel
        )

    def test_create_phenological_stage(self, crop):
        """Test creación de etapa fenológica."""
        stage = PhenologicalStage.objects.create(
            crop=crop,
            stage_name="Germinación",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 25),
            description="Etapa inicial de germinación"
        )
        assert stage.crop == crop
        assert stage.stage_name == "Germinación"
        assert stage.start_date == date(2024, 1, 15)

    def test_phenological_stages_ordering(self, crop):
        """Test ordenamiento por fecha de inicio."""
        PhenologicalStage.objects.create(
            crop=crop,
            stage_name="Floración",
            start_date=date(2024, 3, 1)
        )
        PhenologicalStage.objects.create(
            crop=crop,
            stage_name="Germinación",
            start_date=date(2024, 1, 1)
        )
        
        stages = list(PhenologicalStage.objects.all().values_list('stage_name', flat=True))
        assert stages == ["Germinación", "Floración"]


class TestSupplyApplication:
    """Tests para el modelo SupplyApplication."""

    @pytest.fixture
    def setup_supply(self):
        """Fixture para crear datos de prueba."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.create_user(username="user_supply")
        manager = Employee.objects.create(user=user, name="Manager")
        parcel = Parcel.objects.create(name="Parcela", manager=manager)
        crop = Crop.objects.create(name="Cultivo", parcel=parcel)
        supply = Supply.objects.create(name="Fertilizante", quantity=100)
        
        return {'crop': crop, 'supply': supply, 'manager': manager}

    def test_create_supply_application(self, setup_supply):
        """Test aplicación de insumo."""
        application = SupplyApplication.objects.create(
            crop=setup_supply['crop'],
            supply=setup_supply['supply'],
            quantity=10.5,
            application_date=date.today(),
            applied_by=setup_supply['manager']
        )
        assert application.crop == setup_supply['crop']
        assert application.supply == setup_supply['supply']
        assert application.quantity == 10.5

    def test_supply_application_method(self, setup_supply):
        """Test método de aplicación."""
        application = SupplyApplication.objects.create(
            crop=setup_supply['crop'],
            supply=setup_supply['supply'],
            quantity=5.0,
            application_method="Foliar"
        )
        assert application.application_method == "Foliar"
