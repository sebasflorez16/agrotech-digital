"""
Tests unitarios para el modelo Parcel.
"""
import pytest
import uuid
from datetime import datetime
from django.core.exceptions import ValidationError
from parcels.models import Parcel, ParcelAudit, CacheDatosEOSDA
from RRHH.models import Employee

pytestmark = pytest.mark.django_db


class TestParcelModel:
    """Tests para el modelo Parcel."""

    @pytest.fixture
    def manager(self):
        """Fixture para crear un manager."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            username="manager_test",
            email="manager@test.com",
            name="Manager",
            last_name="Test"
        )
        return Employee.objects.create(
            user=user,
            name="Manager Test",
            job_title="Gerente Agrícola"
        )

    @pytest.fixture
    def sample_geojson(self):
        """Fixture con GeoJSON de ejemplo."""
        return {
            "type": "Polygon",
            "coordinates": [[
                [-74.0, 4.0],
                [-74.01, 4.0],
                [-74.01, 4.01],
                [-74.0, 4.01],
                [-74.0, 4.0]
            ]]
        }

    def test_create_parcel_basic(self, manager, sample_geojson):
        """Test creación básica de parcela."""
        parcel = Parcel.objects.create(
            name="Campo Test",
            description="Descripción de prueba",
            geom=sample_geojson,
            manager=manager,
            soil_type="arcilloso",
            topography="plano"
        )
        assert parcel.name == "Campo Test"
        assert parcel.description == "Descripción de prueba"
        assert parcel.manager == manager
        assert parcel.soil_type == "arcilloso"
        assert parcel.topography == "plano"
        assert parcel.state is True
        assert parcel.is_deleted is False
        assert parcel.deleted_at is None

    def test_parcel_str_representation(self, manager):
        """Test representación string de parcela."""
        parcel = Parcel.objects.create(
            name="Mi Parcela",
            manager=manager
        )
        assert str(parcel) == "Mi Parcela"

    def test_parcel_unique_id_generation(self, manager):
        """Test que se genera UUID único automáticamente."""
        parcel1 = Parcel.objects.create(name="Parcela 1", manager=manager)
        parcel2 = Parcel.objects.create(name="Parcela 2", manager=manager)
        
        assert parcel1.unique_id is not None
        assert parcel2.unique_id is not None
        assert parcel1.unique_id != parcel2.unique_id
        assert isinstance(parcel1.unique_id, uuid.UUID)

    def test_parcel_eosda_id_unique(self, manager):
        """Test que eosda_id debe ser único."""
        Parcel.objects.create(
            name="Parcela 1",
            eosda_id="12345",
            manager=manager
        )
        with pytest.raises(Exception):  # IntegrityError
            Parcel.objects.create(
                name="Parcela 2",
                eosda_id="12345",
                manager=manager
            )

    def test_parcel_area_calculation(self, manager, sample_geojson):
        """Test cálculo de área en hectáreas."""
        parcel = Parcel.objects.create(
            name="Campo con Área",
            geom=sample_geojson,
            manager=manager
        )
        area = parcel.area_hectares()
        assert area > 0
        assert isinstance(area, float)
        # El área debería ser aproximadamente 1.23 ha según las coordenadas

    def test_parcel_area_without_geom(self, manager):
        """Test que área retorna 0 sin geometría."""
        parcel = Parcel.objects.create(
            name="Campo sin Geometría",
            manager=manager
        )
        assert parcel.area_hectares() == 0

    def test_parcel_soft_delete_flags(self, manager):
        """Test flags de soft delete."""
        parcel = Parcel.objects.create(
            name="Parcela",
            manager=manager
        )
        # Simular soft delete (normalmente hecho por el viewset)
        parcel.is_deleted = True
        parcel.deleted_at = datetime.now()
        parcel.save()
        
        assert parcel.is_deleted is True
        assert parcel.deleted_at is not None

    def test_parcel_timestamps(self, manager):
        """Test que se generan timestamps automáticamente."""
        parcel = Parcel.objects.create(
            name="Parcela",
            manager=manager
        )
        assert parcel.created_on is not None
        assert parcel.updated_on is not None
        assert parcel.created_on <= parcel.updated_on

    def test_parcel_update_timestamp(self, manager):
        """Test que updated_on se actualiza al guardar."""
        parcel = Parcel.objects.create(
            name="Parcela",
            manager=manager
        )
        original_updated = parcel.updated_on
        
        parcel.name = "Parcela Actualizada"
        parcel.save()
        
        assert parcel.updated_on > original_updated

    def test_parcel_soil_types(self, manager):
        """Test diferentes tipos de suelo."""
        soil_types = ["arenoso", "arcilloso", "limoso", "franco"]
        for soil in soil_types:
            parcel = Parcel.objects.create(
                name=f"Parcela {soil}",
                soil_type=soil,
                manager=manager
            )
            assert parcel.soil_type == soil

    def test_parcel_topography_types(self, manager):
        """Test diferentes tipos de topografía."""
        topographies = ["plano", "inclinado", "ondulado", "montañoso"]
        for topo in topographies:
            parcel = Parcel.objects.create(
                name=f"Parcela {topo}",
                topography=topo,
                manager=manager
            )
            assert parcel.topography == topo


class TestParcelAudit:
    """Tests para el modelo ParcelAudit."""

    @pytest.fixture
    def manager(self):
        """Fixture para crear un manager."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            username="manager_audit",
            email="audit@test.com"
        )
        return Employee.objects.create(user=user, name="Manager")

    @pytest.fixture
    def parcel(self, manager):
        """Fixture para crear una parcela."""
        return Parcel.objects.create(
            name="Parcela Audit",
            manager=manager
        )

    def test_create_audit_log(self, parcel):
        """Test creación de log de auditoría."""
        audit = ParcelAudit.objects.create(
            parcel=parcel,
            action="CREATE",
            description="Parcela creada"
        )
        assert audit.parcel == parcel
        assert audit.action == "CREATE"
        assert audit.description == "Parcela creada"
        assert audit.timestamp is not None

    def test_audit_actions(self, parcel):
        """Test diferentes acciones de auditoría."""
        actions = ["CREATE", "UPDATE", "DELETE", "VIEW"]
        for action in actions:
            audit = ParcelAudit.objects.create(
                parcel=parcel,
                action=action,
                description=f"Acción: {action}"
            )
            assert audit.action == action


class TestCacheDatosEOSDA:
    """Tests para el modelo CacheDatosEOSDA."""

    @pytest.fixture
    def manager(self):
        """Fixture para crear un manager."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            username="manager_cache",
            email="cache@test.com"
        )
        return Employee.objects.create(user=user, name="Manager")

    @pytest.fixture
    def parcel(self, manager):
        """Fixture para crear una parcela."""
        return Parcel.objects.create(
            name="Parcela Cache",
            eosda_id="cache123",
            manager=manager
        )

    def test_create_cache_entry(self, parcel):
        """Test creación de entrada de cache."""
        cache = CacheDatosEOSDA.objects.create(
            parcel=parcel,
            fecha_inicio="2024-01-01",
            fecha_fin="2024-01-31",
            tipo_dato="ndvi",
            hash_parametros="abc123",
            datos_json={"mean": 0.75, "std": 0.05}
        )
        assert cache.parcel == parcel
        assert cache.tipo_dato == "ndvi"
        assert cache.hash_parametros == "abc123"
        assert cache.datos_json["mean"] == 0.75

    def test_cache_expiration(self, parcel):
        """Test que se genera timestamp de expiración."""
        cache = CacheDatosEOSDA.objects.create(
            parcel=parcel,
            tipo_dato="ndmi",
            hash_parametros="xyz789",
            datos_json={}
        )
        assert cache.timestamp is not None
        assert cache.expira_en is not None

    def test_cache_tipos_dato(self, parcel):
        """Test diferentes tipos de datos cacheados."""
        tipos = ["ndvi", "ndmi", "evi", "mt_stats", "weather"]
        for tipo in tipos:
            cache = CacheDatosEOSDA.objects.create(
                parcel=parcel,
                tipo_dato=tipo,
                hash_parametros=f"hash_{tipo}",
                datos_json={"test": True}
            )
            assert cache.tipo_dato == tipo
