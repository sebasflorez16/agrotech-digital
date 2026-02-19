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

class CropVariety(models.Model):
    """Variedad de un tipo de cultivo (ej. Arroz IR-64, Maíz ICA V-305)"""
    name = models.CharField(max_length=150, verbose_name="Nombre de la variedad")
    crop_type = models.ForeignKey(
        CropType, on_delete=models.CASCADE,
        related_name="varieties", verbose_name="Tipo de cultivo"
    )
    cycle_days = models.IntegerField(
        null=True, blank=True,
        verbose_name="Días de ciclo (aprox.)"
    )
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")

    def __str__(self):
        return f"{self.name} ({self.crop_type.name})"

    class Meta:
        verbose_name = "Variedad de cultivo"
        verbose_name_plural = "Variedades de cultivo"
        ordering = ["crop_type", "name"]
        unique_together = [("name", "crop_type")]


class Crop(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre del cultivo")
    crop_type = models.ForeignKey(CropType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tipo de cultivo")
    variety = models.ForeignKey(CropVariety, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Variedad")
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


# =============================================================================
# CATALOGO DE CULTIVOS CON DATOS AGRONOMICOS
# =============================================================================

class CropCatalog(models.Model):
    """
    Catalogo dinamico de tipos de cultivo con informacion agronomica.
    Cada cultivo tiene etapas fenologicas con rangos optimos de indices satelitales.
    Fuentes: FAO, CIMMYT, IRRI, Cenicafe, CIAT, Agrosavia.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre del cultivo")
    scientific_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre cientifico")
    family = models.CharField(max_length=100, blank=True, null=True, verbose_name="Familia botanica")
    description = models.TextField(blank=True, null=True, verbose_name="Descripcion")

    CATEGORY_CHOICES = [
        ('cereals', 'Cereales'),
        ('legumes', 'Leguminosas'),
        ('fruits', 'Frutales'),
        ('vegetables', 'Hortalizas'),
        ('industrial', 'Industriales'),
        ('forage', 'Pastos y Forrajes'),
        ('tubers', 'Tuberculos'),
        ('oilseeds', 'Oleaginosas'),
        ('other', 'Otros'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='cereals', verbose_name="Categoria")

    cycle_days_min = models.IntegerField(default=90, verbose_name="Ciclo minimo (dias)")
    cycle_days_max = models.IntegerField(default=150, verbose_name="Ciclo maximo (dias)")
    temp_min = models.FloatField(default=15.0, verbose_name="Temperatura minima optima (C)")
    temp_max = models.FloatField(default=35.0, verbose_name="Temperatura maxima optima (C)")
    rainfall_min = models.FloatField(default=500.0, verbose_name="Precipitacion minima anual (mm)")
    rainfall_max = models.FloatField(default=2000.0, verbose_name="Precipitacion maxima anual (mm)")

    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cultivo (Catalogo)"
        verbose_name_plural = "Cultivos (Catalogo)"
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class PhenologicalStage(models.Model):
    """
    Etapa fenologica de un cultivo del catalogo.
    Define rangos optimos de NDVI, NDMI y SAVI para cada etapa,
    permitiendo interpretar indices satelitales con contexto agronomico.
    """
    crop_catalog = models.ForeignKey(CropCatalog, on_delete=models.CASCADE, related_name='stages')

    name = models.CharField(max_length=100, verbose_name="Nombre de la etapa")
    description = models.TextField(blank=True, null=True, verbose_name="Descripcion")
    order = models.IntegerField(default=0, verbose_name="Orden")

    day_start = models.IntegerField(verbose_name="Dia inicio (desde siembra)")
    day_end = models.IntegerField(verbose_name="Dia fin (desde siembra)")

    # Rangos optimos NDVI
    ndvi_min = models.FloatField(default=0.0, verbose_name="NDVI minimo esperado")
    ndvi_max = models.FloatField(default=1.0, verbose_name="NDVI maximo esperado")
    ndvi_optimal = models.FloatField(default=0.5, verbose_name="NDVI optimo")

    # Rangos optimos NDMI
    ndmi_min = models.FloatField(default=-1.0, verbose_name="NDMI minimo esperado")
    ndmi_max = models.FloatField(default=1.0, verbose_name="NDMI maximo esperado")
    ndmi_optimal = models.FloatField(default=0.2, verbose_name="NDMI optimo")

    # Rangos optimos SAVI
    savi_min = models.FloatField(default=0.0, verbose_name="SAVI minimo esperado")
    savi_max = models.FloatField(default=1.0, verbose_name="SAVI maximo esperado")
    savi_optimal = models.FloatField(default=0.4, verbose_name="SAVI optimo")

    water_need = models.IntegerField(default=3, verbose_name="Necesidad hidrica (1-5)")
    is_critical = models.BooleanField(default=False, verbose_name="Etapa critica")
    critical_alert = models.TextField(blank=True, null=True, verbose_name="Alerta en etapa critica")

    class Meta:
        verbose_name = "Etapa Fenologica"
        verbose_name_plural = "Etapas Fenologicas"
        ordering = ['crop_catalog', 'order', 'day_start']
        unique_together = ['crop_catalog', 'order']

    def __str__(self):
        return f"{self.crop_catalog.name} - {self.name} (Dia {self.day_start}-{self.day_end})"


class CropCycle(models.Model):
    """
    Ciclo de cultivo: vincula opcionalmente una parcela con un cultivo del catalogo
    durante un periodo. Permite interpretar indices satelitales segun la etapa
    fenologica actual del cultivo.
    """
    parcel = models.ForeignKey(Parcel, on_delete=models.CASCADE, related_name='crop_cycles')
    crop_catalog = models.ForeignKey(CropCatalog, on_delete=models.PROTECT, related_name='cycles')

    variety = models.CharField(max_length=150, blank=True, null=True, verbose_name="Variedad")
    planting_date = models.DateField(verbose_name="Fecha de siembra")
    estimated_harvest_date = models.DateField(blank=True, null=True, verbose_name="Fecha estimada de cosecha")
    actual_harvest_date = models.DateField(blank=True, null=True, verbose_name="Fecha real de cosecha")

    STATUS_CHOICES = [
        ('planned', 'Planificado'),
        ('active', 'Activo'),
        ('harvested', 'Cosechado'),
        ('cancelled', 'Cancelado'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Estado")

    planting_density = models.FloatField(blank=True, null=True, verbose_name="Densidad de siembra (plantas/ha)")
    seed_amount = models.FloatField(blank=True, null=True, verbose_name="Cantidad de semilla (kg/ha)")
    expected_yield = models.FloatField(blank=True, null=True, verbose_name="Rendimiento esperado (ton/ha)")
    actual_yield = models.FloatField(blank=True, null=True, verbose_name="Rendimiento real (ton/ha)")
    notes = models.TextField(blank=True, null=True, verbose_name="Notas")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ciclo de Cultivo"
        verbose_name_plural = "Ciclos de Cultivo"
        ordering = ['-planting_date']

    def __str__(self):
        return f"{self.crop_catalog.name} en {self.parcel.name} ({self.planting_date})"

    @property
    def days_since_planting(self):
        from django.utils import timezone
        today = timezone.now().date()
        return (today - self.planting_date).days

    @property
    def current_stage(self):
        days = self.days_since_planting
        return self.crop_catalog.stages.filter(
            day_start__lte=days,
            day_end__gte=days
        ).first()

    @property
    def progress_percent(self):
        if not self.estimated_harvest_date:
            return 0
        total_days = (self.estimated_harvest_date - self.planting_date).days
        if total_days <= 0:
            return 100
        elapsed = self.days_since_planting
        return min(round((elapsed / total_days) * 100, 1), 100)

    def get_index_interpretation(self, index_type, index_value):
        """
        Interpreta un valor de indice segun la etapa fenologica actual.
        Retorna diccionario con diagnostico, nivel de alerta y recomendacion.
        """
        stage = self.current_stage
        if not stage:
            return {
                'status': 'unknown',
                'message': 'No se puede determinar la etapa fenologica actual',
                'stage': None
            }

        if index_type == 'ndvi':
            optimal = stage.ndvi_optimal
            range_min = stage.ndvi_min
            range_max = stage.ndvi_max
        elif index_type == 'ndmi':
            optimal = stage.ndmi_optimal
            range_min = stage.ndmi_min
            range_max = stage.ndmi_max
        elif index_type == 'savi':
            optimal = stage.savi_optimal
            range_min = stage.savi_min
            range_max = stage.savi_max
        else:
            return {'status': 'unknown', 'message': f'Indice {index_type} no soportado'}

        deviation = abs(index_value - optimal)
        range_size = range_max - range_min
        deviation_percent = (deviation / range_size * 100) if range_size > 0 else 0

        if range_min <= index_value <= range_max:
            if deviation_percent <= 15:
                alert_level = 'optimal'
                message = f'{index_type.upper()} optimo para {self.crop_catalog.name} en etapa de {stage.name}'
            else:
                alert_level = 'normal'
                message = f'{index_type.upper()} dentro del rango esperado para {stage.name}'
        elif index_value < range_min:
            deficit = range_min - index_value
            if deficit > range_size * 0.3:
                alert_level = 'critical'
                message = f'{index_type.upper()} muy por debajo del rango para {self.crop_catalog.name} en {stage.name}'
            else:
                alert_level = 'warning'
                message = f'{index_type.upper()} por debajo del esperado para {stage.name}'
        else:
            alert_level = 'high'
            message = f'{index_type.upper()} por encima del rango esperado para {stage.name}'

        result = {
            'status': alert_level,
            'message': message,
            'stage': {
                'name': stage.name,
                'day_start': stage.day_start,
                'day_end': stage.day_end,
                'is_critical': stage.is_critical,
                'water_need': stage.water_need,
            },
            'index': {
                'type': index_type,
                'value': index_value,
                'optimal': optimal,
                'range': [range_min, range_max],
                'deviation_percent': round(deviation_percent, 1),
            },
            'crop': {
                'name': self.crop_catalog.name,
                'category': self.crop_catalog.category,
            },
            'days_since_planting': self.days_since_planting,
            'progress_percent': self.progress_percent,
        }

        if stage.is_critical and alert_level in ['warning', 'critical']:
            result['critical_alert'] = stage.critical_alert or (
                f'ATENCION: {stage.name} es una etapa critica. '
                f'Los problemas ahora pueden afectar significativamente el rendimiento.'
            )

        return result
