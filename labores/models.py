from django.db import models
from django.conf import settings
from parcels.models import Parcel
from RRHH.models import Employee
from crop.models import Crop
from inventario.models import Supply, Machinery

class LaborType(models.Model):
    tenant_id = models.IntegerField(db_index=True, null=True, blank=True, verbose_name="ID del Tenant")
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
    tenant_id = models.IntegerField(db_index=True, null=True, blank=True, verbose_name="ID del Tenant")
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la labor")
    tipo = models.ForeignKey(LaborType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tipo de labor")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    parcelas = models.ManyToManyField(Parcel, related_name="labores", verbose_name="Parcelas involucradas", blank=True)
    responsables = models.ManyToManyField(Employee, related_name="labores_asignadas", verbose_name="Responsables", blank=True)
    cultivos = models.ManyToManyField(Crop, related_name="labores", verbose_name="Cultivos involucrados", blank=True)
    fecha_programada = models.DateField(verbose_name="Fecha programada", blank=True, null=True)
    fecha_realizada = models.DateField(blank=True, null=True, verbose_name="Fecha de realizacion")
    maquinaria = models.ManyToManyField(Machinery, related_name="labores", verbose_name="Maquinaria utilizada", blank=True)
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
        """Suma el costo de los insumos asociados a esta labor (unit_value * cantidad)."""
        from decimal import Decimal, InvalidOperation

        total = Decimal("0")
        for i in self.insumos.all():
            if i.supply and i.supply.unit_value is not None:
                try:
                    total += i.supply.unit_value * Decimal(str(i.quantity))
                except (InvalidOperation, TypeError, ValueError):
                    continue
        return total

    def calcular_costo_maquinaria(self):
        """Suma el valor de referencia de la maquinaria utilizada en la labor."""
        from decimal import Decimal

        total = Decimal("0")
        for m in self.maquinaria.all():
            if m.current_value is not None:
                total += m.current_value
            elif m.purchase_value is not None:
                total += m.purchase_value
        return total

    def calcular_costo_mano_obra(self):
        # Suma el costo de todos los responsables (si hay modelo de horas/costo)
        # Aquí se puede personalizar según la estructura de Employee
        return 0  # Placeholder

    def calcular_costo_total(self):
        return (
            (self.calcular_costo_insumos() or 0)
            + (self.calcular_costo_maquinaria() or 0)
            + (self.calcular_costo_mano_obra() or 0)
        )

    @property
    def progreso(self):
        """Porcentaje de fases completadas."""
        fases = self.fases.count()
        if fases == 0:
            return 0
        completadas = self.fases.filter(estado='completada').count()
        return round((completadas / fases) * 100)

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


class LaborPhase(models.Model):
    """Fase individual de una labor agricola. Permite seguimiento por etapas con progreso."""

    labor = models.ForeignKey(Labor, on_delete=models.CASCADE, related_name="fases")
    nombre = models.CharField(max_length=150, verbose_name="Nombre de la fase")
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden")
    estado = models.CharField(max_length=20, choices=[
        ("pendiente", "Pendiente"),
        ("en_progreso", "En progreso"),
        ("completada", "Completada"),
        ("cancelada", "Cancelada"),
    ], default="pendiente", verbose_name="Estado")
    fecha_inicio = models.DateField(blank=True, null=True, verbose_name="Fecha de inicio")
    fecha_fin = models.DateField(blank=True, null=True, verbose_name="Fecha de finalizacion")
    notas = models.TextField(blank=True, null=True, verbose_name="Notas / Inconvenientes")
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.orden}. {self.nombre} ({self.estado})"

    class Meta:
        ordering = ["orden"]
        verbose_name = "Fase de labor"
        verbose_name_plural = "Fases de labor"


class LaborInput(models.Model):
    """Insumo aplicado como parte de una labor agricola."""
    labor = models.ForeignKey("labores.Labor", on_delete=models.CASCADE, related_name="insumos")
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="labor_insumos")
    supply = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Insumo")
    quantity = models.FloatField(verbose_name="Cantidad aplicada")
    unit = models.CharField(max_length=20, verbose_name="Unidad")
    application_date = models.DateField(verbose_name="Fecha de aplicacion")
    notes = models.TextField(verbose_name="Notas", blank=True, null=True)
    from simple_history.models import HistoricalRecords
    historical = HistoricalRecords()

    def __str__(self):
        return f"{self.supply} - {self.labor.nombre} ({self.crop.name})"

    class Meta:
        db_table = 'crop_laborinput'
        verbose_name = "Insumo en labor"
        verbose_name_plural = "Insumos en labores"
        ordering = ["-application_date"]
