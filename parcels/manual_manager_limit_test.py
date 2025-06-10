"""
Script manual para validar la restricción de hectáreas por manager en desarrollo.

DOCUMENTACIÓN DEL TEST
----------------------
Este script permite validar manualmente la lógica de restricción de área máxima (300 ha) por manager en el modelo Parcel, incluyendo la huella de hectáreas (soft delete).

Flujo del test:
1. Crea datos de prueba en la base de datos de desarrollo:
    - Un Department (Depto Test)
    - Un Position (Cargo Test)
    - Un Employee (Test Manager) con identification_number aleatorio
    - Dos Parcelas (Lote A y Lote B) de 150 ha cada una (total 300 ha)
2. Intenta crear una tercera parcela de 10 ha (debe lanzar ValidationError por superar el límite).
3. Borra (soft delete) una de las parcelas de 150 ha.
4. Intenta crear una nueva parcela de 10 ha (debe seguir lanzando ValidationError porque la huella de área borrada cuenta para el límite).
5. (Opcional) Limpieza de los datos de prueba al final del script (comentado por defecto).

Recomendaciones:
- Ejecutar SOLO en entornos de desarrollo, nunca en producción.
- Si se desea limpiar la base de datos tras la prueba, descomentar la sección de limpieza al final del script.

Salida esperada:
----------------
Área total asignada: 300.00 ha
Intentando crear una tercera parcela de 10 ha...
¡Restricción de hectáreas por manager funciona! {'__all__': ["El usuario 'Test Manager' no puede tener más de 300 hectáreas en total. Actualmente: 300.00 ha."]}
Borrando (soft delete) una parcela de 150 ha...
Intentando crear una nueva parcela de 10 ha tras el borrado...
¡Restricción de hectáreas por manager (huella) funciona! {'__all__': ["El usuario 'Test Manager' no puede tener más de 300 hectáreas en total. Actualmente: 300.00 ha."]}
"""
from RRHH.models import Employee, Position, Department
from parcels.models import Parcel
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import Polygon
import random

# Crea un departamento y un cargo de prueba (requeridos por Employee)
dep = Department.objects.create(name="Depto Test", description="Depto test")
pos = Position.objects.create(name="Cargo Test", description="Cargo test")

# Genera un identification_number aleatorio para evitar conflictos
identification_number = random.randint(10000000, 99999999)

# Crea un empleado de prueba (Employee requiere varios campos obligatorios)
manager = Employee.objects.create(
    identification_number=identification_number,
    first_name="Test",
    last_name="Manager",
    address="Calle 123",
    phone=1234567890,
    email=f"test.manager{identification_number}@example.com",
    date_of_hire="2024-01-01",
    position=pos,
    department=dep
)

def create_square_polygon(area_m2, origin_x=0, origin_y=0):
    side = area_m2 ** 0.5
    return Polygon([
        (origin_x, origin_y),
        (origin_x + side, origin_y),
        (origin_x + side, origin_y + side),
        (origin_x, origin_y + side),
        (origin_x, origin_y)
    ])

# Crea dos parcelas de 150 ha cada una (1,500,000 m2)
p1 = Parcel.objects.create(
    name="Lote A",
    manager=manager,
    geom=create_square_polygon(1_500_000),
    soil_type="Franco",
    topography="Plana"
)
p2 = Parcel.objects.create(
    name="Lote B",
    manager=manager,
    geom=create_square_polygon(1_500_000, 2000, 0),
    soil_type="Franco",
    topography="Plana"
)
print(f"Área total asignada: {p1.area_hectares() + p2.area_hectares():.2f} ha")

print("Intentando crear una tercera parcela de 10 ha...")
def test_limite():
    try:
        Parcel.objects.create(
            name="Lote C",
            manager=manager,
            geom=create_square_polygon(100_000, 0, 2000),
            soil_type="Franco",
            topography="Plana"
        )
    except ValidationError as e:
        print("¡Restricción de hectáreas por manager funciona!", e)
    else:
        print("ERROR: Se permitió exceder el límite de hectáreas")

test_limite()

print("Borrando (soft delete) una parcela de 150 ha...")
p1.delete()

print("Intentando crear una nueva parcela de 10 ha tras el borrado...")
def test_limite_huella():
    try:
        Parcel.objects.create(
            name="Lote D",
            manager=manager,
            geom=create_square_polygon(100_000, 0, 3000),
            soil_type="Franco",
            topography="Plana"
        )
    except ValidationError as e:
        print("¡Restricción de hectáreas por manager (huella) funciona!", e)
    else:
        print("ERROR: Se permitió exceder el límite de hectáreas (huella)")

test_limite_huella()

# Limpieza automática de los datos de prueba para mantener la base limpia tras la validación
p2.delete()
manager.delete()
pos.delete()
dep.delete()
Parcel.objects.filter(manager=manager).delete()  # Borra todas las parcelas del manager (incluidas soft delete)
