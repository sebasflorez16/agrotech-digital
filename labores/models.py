from django.db import models
from django.conf import settings
from parcels.models import Parcel
from RRHH.models import Employee
from crop.models import Crop

class LaborType(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Tipo de labor")
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Tipo de labor"
        verbose_name_plural = "Tipos de labor"
        ordering = ["nombre"]

class Labor(models.Model):
    """
    Representa una labor agrícola realizada o planificada sobre una o varias parcelas.
    Ejemplos: Siembra, fertilización, riego, cosecha, aplicación de fitosanitarios, etc.
    """
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la labor")
    tipo = models.ForeignKey(LaborType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tipo de labor")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    parcelas = models.ManyToManyField(Parcel, related_name="labores", verbose_name="Parcelas involucradas", blank=True)
    responsables = models.ManyToManyField(Employee, related_name="labores_asignadas", verbose_name="Responsables", blank=True)
    cultivos = models.ManyToManyField(Crop, related_name="labores", verbose_name="Cultivos involucrados", blank=True)
    fecha_programada = models.DateField(verbose_name="Fecha programada", blank=True, null=True)
    fecha_realizada = models.DateField(blank=True, null=True, verbose_name="Fecha de realización")
    estado = models.CharField(max_length=20, choices=[
        ("pendiente", "Pendiente"),
        ("en_progreso", "En progreso"),
        ("completada", "Completada"),
        ("cancelada", "Cancelada")
    ], default="pendiente", verbose_name="Estado")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    # --- RUTA FIRME: Campos adicionales para integración profesional ---
    # Relación directa con un solo cultivo principal (además del ManyToMany existente)
    cultivo_principal = models.ForeignKey(Crop, on_delete=models.SET_NULL, null=True, blank=True, related_name="labores_principales", verbose_name="Cultivo principal")
    # Duración estimada o real de la labor (en horas)
    duracion = models.FloatField(blank=True, null=True, verbose_name="Duración (horas)")
    # Costo total de la labor (calculado o editable)
    costo_total = models.FloatField(blank=True, null=True, verbose_name="Costo total")
    # --- Fotos de labor: hasta 3 imágenes por labor ---
    # Se usará un modelo LaborPhoto relacionado (ver abajo)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="labores_creadas", verbose_name="Creado por")
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Creado en")
    actualizado_en = models.DateTimeField(auto_now=True, verbose_name="Actualizado en")
    # Historial de cambios
    from simple_history.models import HistoricalRecords
    historical = HistoricalRecords()

    def calcular_costo_insumos(self):
        # Suma el costo de todos los insumos asociados a esta labor
        return sum(i.supply.costo_unitario * i.quantity for i in self.insumos.all() if i.supply and hasattr(i.supply, 'costo_unitario'))

    def calcular_costo_mano_obra(self):
        # Suma el costo de todos los responsables (si hay modelo de horas/costo)
        # Aquí se puede personalizar según la estructura de Employee
        return 0  # Placeholder

    def calcular_costo_total(self):
        return (self.calcular_costo_insumos() or 0) + (self.calcular_costo_mano_obra() or 0)

    def __str__(self):
        tipo = self.tipo.nombre if self.tipo else "Sin tipo"
        fecha = self.fecha_programada if self.fecha_programada else "Sin fecha"
        nombre = self.nombre if self.nombre else "Sin nombre"
        return f"{nombre} ({tipo}) - {fecha}"

# --- RUTA FIRME: Modelo para fotos de labor (máx. 3 por labor) ---
class LaborPhoto(models.Model):
    labor = models.ForeignKey(Labor, on_delete=models.CASCADE, related_name="fotos")
    image = models.ImageField(upload_to="labor_photos/", verbose_name="Foto de labor")
    date = models.DateField(verbose_name="Fecha de la foto")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuario")
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Creado en")
    actualizado_en = models.DateTimeField(auto_now=True, verbose_name="Actualizado en")
    from simple_history.models import HistoricalRecords
    historical = HistoricalRecords()

    def clean(self):
        # Validación: máximo 3 fotos por labor
        if self.labor and self.labor.fotos.count() >= 3 and not self.pk:
            from django.core.exceptions import ValidationError
            raise ValidationError("Solo se permiten 3 fotos por labor.")

    def __str__(self):
        return f"Foto {self.date} - {self.labor.nombre}"

    class Meta:
        verbose_name = "Foto de labor"
        verbose_name_plural = "Fotos de labores"
        ordering = ["-date"]
