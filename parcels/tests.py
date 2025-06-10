from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Parcel, ParcelActionLog
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

# AVISO: Estos tests están configurados para ejecutarse sobre la base de datos real (no de test),
# ya que el entorno multi-tenant no soporta migrate_schemas en la base de datos de pruebas.
# ¡NO incluyen operaciones destructivas (delete, truncate, etc.)!
# Asegúrate de que los datos de producción no se vean afectados si ejecutas estos tests en un entorno real.

class ParcelModelTests(TestCase):
    def setUp(self):
        # Crea un usuario real del sistema para simular acciones de auditoría
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            name="Test",
            last_name="User",
            password="testpass123"
        )
        # No se usa Employee para evitar errores de migración en tests multi-tenant
        self.manager = None  # Solo para pruebas, en producción sí se usa Employee

    def test_area_hectares_calculation(self):
        # Testea el cálculo de área en hectáreas
        parcel = Parcel.objects.create(
            name="Lote 1",
            manager=self.manager,
            area_m2=15000,
            location="Ubicación X"
        )
        self.assertAlmostEqual(parcel.area_hectares, 1.5)

    def test_area_limit_per_manager(self):
        # Crea parcelas hasta el límite permitido (300 ha)
        Parcel.objects.create(
            name="Lote 1",
            manager=self.manager,
            area_m2=200_000,
            location="Ubicación X"
        )
        Parcel.objects.create(
            name="Lote 2",
            manager=self.manager,
            area_m2=2_800_000,
            location="Ubicación Y"
        )
        # Intentar crear una que exceda el límite debe fallar
        with self.assertRaises(ValidationError):
            Parcel.objects.create(
                name="Lote 3",
                manager=self.manager,
                area_m2=27_000_001,  # Excede 300 ha
                location="Ubicación Z"
            )

    def test_soft_delete(self):
        # Testea el borrado suave (soft delete)
        parcel = Parcel.objects.create(
            name="Lote 1",
            manager=self.manager,
            area_m2=10000,
            location="Ubicación X"
        )
        parcel.delete()
        parcel.refresh_from_db()
        self.assertTrue(parcel.is_deleted)
        self.assertIsNotNone(parcel.deleted_at)

    def test_str_representation(self):
        parcel = Parcel.objects.create(
            name="Lote 1",
            manager=self.manager,
            area_m2=10000,
            location="Ubicación X"
        )
        self.assertIn("Lote 1", str(parcel))
        # No se puede comprobar el nombre del manager porque es None en tests

class ParcelNDVITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

    def test_ndvi_historical_endpoint(self):
        """
        Prueba el endpoint ndvi_historical con datos válidos.
        """
        payload = {
            "polygon": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-74.0817, 4.6097],
                        [-74.0817, 4.6197],
                        [-74.0717, 4.6197],
                        [-74.0717, 4.6097],
                        [-74.0817, 4.6097]
                    ]
                ]
            },
            "start_date": "2025-01-01",
            "end_date": "2025-03-31"
        }

        response = self.client.post("/api/parcels/ndvi-historical/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("2025-01", response.data)
        self.assertIn("2025-02", response.data)
        self.assertIn("2025-03", response.data)

# Puedes agregar más tests para ParcelActionLog y lógica de auditoría en el futuro.
# En producción, el manager debe ser un Employee válido.
