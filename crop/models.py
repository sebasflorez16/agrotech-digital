
import uuid
from django.db import models
from parcels.models import Parcel
from RRHH.models import Employee
from inventario.models import Supplier, Supply
from simple_history.models import HistoricalRecords
from django.conf import settings

class CropType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Tipo de cultivo")
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Tipo de cultivo"
        verbose_name_plural = "Tipos de cultivo"
        ordering = ["name"]

class Crop(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre del cultivo")
    crop_type = models.ForeignKey(CropType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tipo de cultivo")
    variety = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Variedad")
    parcel = models.ForeignKey(Parcel, on_delete=models.CASCADE, related_name="crops", verbose_name="Parcela", blank=True, null=True)
    area = models.FloatField(verbose_name="Área asignada (ha)", blank=True, null=True)
    sowing_date = models.DateField(verbose_name="Fecha de siembra", blank=True, null=True)
    harvest_date = models.DateField(verbose_name="Fecha de cosecha", blank=True, null=True)
    expected_yield = models.FloatField(verbose_name="Rendimiento esperado (t/ha)", blank=True, null=True)
    actual_yield = models.FloatField(verbose_name="Rendimiento real (t/ha)", blank=True, null=True)
    irrigation_type = models.CharField(max_length=50, verbose_name="Tipo de riego", blank=True, null=True)
    seed_supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Proveedor de semilla")
    image = models.ImageField(upload_to="crop_images/", blank=True, null=True, verbose_name="Imagen del cultivo")
    notes = models.TextField(verbose_name="Notas", blank=True, null=True)
    manager = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Responsable")
    created_on = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_on = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="ID Único")
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name="Eliminado")
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False, verbose_name="Fecha de eliminación")
    historical = HistoricalRecords()

    def __str__(self):
        return f"{self.name} ({self.variety}) - {self.parcel.name if self.parcel else 'Sin parcela'}"

    class Meta:
        verbose_name = "Cultivo"
        verbose_name_plural = "Cultivos"
        ordering = ["-sowing_date", "name"]

# Etapas fenológicas y eventos importantes
class CropStage(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="stages")
    name = models.CharField(max_length=100, verbose_name="Etapa")
    start_date = models.DateField(verbose_name="Inicio", blank=True, null=True)
    end_date = models.DateField(verbose_name="Fin", blank=True, null=True)
    notes = models.TextField(verbose_name="Notas", blank=True, null=True)
    historical = HistoricalRecords()

# Seguimiento fotográfico y evolución del cultivo
class CropProgressPhoto(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="progress_photos")
    stage = models.ForeignKey(CropStage, on_delete=models.SET_NULL, null=True, blank=True, related_name="photos", verbose_name="Etapa")
    image = models.ImageField(upload_to="crop_progress/", verbose_name="Foto de avance")
    date = models.DateField(verbose_name="Fecha de la foto")
    description = models.TextField(verbose_name="Descripción", blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuario")
    historical = HistoricalRecords()

    def __str__(self):
        return f"Foto {self.date} - {self.crop.name} ({self.stage.name if self.stage else 'Sin etapa'})"

    class Meta:
        verbose_name = "Foto de avance de cultivo"
        verbose_name_plural = "Fotos de avance de cultivos"
        ordering = ["-date"]


# Insumos aplicados directamente al cultivo
class CropInput(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="inputs")
    supply = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Insumo")
    input_type = models.CharField(max_length=50, verbose_name="Tipo de insumo")
    quantity = models.FloatField(verbose_name="Cantidad aplicada")
    unit = models.CharField(max_length=20, verbose_name="Unidad")
    application_date = models.DateField(verbose_name="Fecha de aplicación")
    notes = models.TextField(verbose_name="Notas", blank=True, null=True)
    historical = HistoricalRecords()

    def __str__(self):
        return f"{self.supply} ({self.input_type}) - {self.crop.name}"

    class Meta:
        verbose_name = "Insumo aplicado"
        verbose_name_plural = "Insumos aplicados"
        ordering = ["-application_date"]


# Insumos aplicados como parte de una labor
class LaborInput(models.Model):
    labor = models.ForeignKey("labores.Labor", on_delete=models.CASCADE, related_name="insumos")
    crop = models.ForeignKey("crop.Crop", on_delete=models.CASCADE, related_name="labor_insumos")
    supply = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Insumo")
    quantity = models.FloatField(verbose_name="Cantidad aplicada")
    unit = models.CharField(max_length=20, verbose_name="Unidad")
    application_date = models.DateField(verbose_name="Fecha de aplicación")
    notes = models.TextField(verbose_name="Notas", blank=True, null=True)
    historical = HistoricalRecords()

    def __str__(self):
        return f"{self.supply} - {self.labor.nombre} ({self.crop.name})"

    class Meta:
        verbose_name = "Insumo en labor"
        verbose_name_plural = "Insumos en labores"
        ordering = ["-application_date"]

# Eventos relevantes (riego, plagas, monitoreo, etc)
class CropEvent(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=50, verbose_name="Tipo de evento")
    description = models.TextField(verbose_name="Descripción")
    event_date = models.DateTimeField(verbose_name="Fecha y hora")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuario")
    historical = HistoricalRecords()

    def __str__(self):
        return f"{self.event_type} - {self.crop.name} ({self.event_date:%Y-%m-%d})"

    class Meta:
        verbose_name = "Evento de cultivo"
        verbose_name_plural = "Eventos de cultivos"
        ordering = ["-event_date"]
