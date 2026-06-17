"""
Seed de tipos de labor agronomicos profesionales.
Cubre las labores mas comunes en agricultura de precision y manejo agronomico.

Uso:
    python manage.py tenant_command seed_labor_types --schema=<tenant>
"""

from django.core.management.base import BaseCommand
from labores.models import LaborType


LABOR_TYPES = [
    ("Siembra", "Establecimiento de semillas o plantulas en el lote."),
    ("Resiembra", "Reemplazo de fallas para uniformidad del lote."),
    ("Fertilizacion edafica", "Aplicacion de fertilizantes al suelo (fondo, complementaria, mantenimiento)."),
    ("Fertilizacion foliar", "Aplicacion de nutrientes via aspersion al follaje."),
    ("Aplicacion de enmiendas", "Encalado, yeso o materia organica para correccion de suelo."),
    ("Riego", "Riego por gravedad, aspersion, micro o goteo."),
    ("Drenaje", "Mantenimiento de canales y obras de drenaje."),
    ("Control de malezas", "Manual, mecanico o quimico (pre/post emergente)."),
    ("Control de plagas", "Monitoreo y aplicacion de fitosanitarios contra plagas."),
    ("Control de enfermedades", "Monitoreo y aplicacion de fungicidas/bactericidas."),
    ("Aporque", "Acumulacion de suelo en la base de la planta."),
    ("Poda", "Eliminacion de tejido para mejorar arquitectura/produccion."),
    ("Deshije", "Eliminacion de hijos no productivos (banano, cana)."),
    ("Polinizacion asistida", "Manejo de polinizadores o polinizacion manual."),
    ("Cosecha", "Recoleccion del producto agricola."),
    ("Postcosecha", "Manejo, seleccion y empaque inmediato a cosecha."),
    ("Muestreo de suelos", "Toma de muestras para analisis quimico/fisico."),
    ("Muestreo foliar", "Toma de muestras de hojas para diagnostico nutricional."),
    ("Monitoreo fitosanitario", "Recorrido de monitoreo de plagas y enfermedades."),
    ("Mantenimiento de infraestructura", "Cercas, caminos, bodegas, equipos."),
    ("Mecanizacion", "Labranza, rastra, subsolado u otra operacion mecanica."),
]


class Command(BaseCommand):
    help = "Pobla el catalogo de tipos de labor con datos agronomicos verificados."

    def handle(self, *args, **opts):
        creados = 0
        existentes = 0
        for nombre, descripcion in LABOR_TYPES:
            obj, created = LaborType.objects.get_or_create(
                nombre=nombre,
                defaults={"descripcion": descripcion},
            )
            if created:
                creados += 1
                self.stdout.write(f"  + Creado: {nombre}")
            else:
                existentes += 1
                if not obj.descripcion:
                    obj.descripcion = descripcion
                    obj.save(update_fields=["descripcion"])
        self.stdout.write(self.style.SUCCESS(
            f"Resultado: {creados} tipos creados, {existentes} ya existian."
        ))
