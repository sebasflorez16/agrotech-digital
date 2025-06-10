import uuid
from django.db import models
from django.contrib.gis.db import models
from django_tenants.utils import get_tenant_model
from RRHH.models import Employee
from simple_history.models import HistoricalRecords
from base_agrotech.models import BaseModel


# Create your models here.

class Field(BaseModel):
    name = models.CharField(max_length=100, verbose_name="Nombre del campo", blank=True, null=True)
    description = models.TextField(verbose_name="Descripción del campo", blank=True, null=True)
    field_type = models.CharField(max_length=100, verbose_name="Tipo de campo", blank=True, null=True)
    state = models.BooleanField(verbose_name="Estado del campo", default=True, blank=True, null=True)
    geom = models.PolygonField(verbose_name="Área geográfica del campo", blank=True, null=True)
    created_on =models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación", blank=True, null=True)
    updated_on =models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización", blank=True, null=True)
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="ID Único", blank=True, null=True)
    manager = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name="Responsable del campo", blank=True, null=True)
    soil_type = models.CharField(max_length=40, verbose_name='Tipo de suelo', help_text='Especifica si es arenoso, arcillozo, etc')
    topography = models.CharField(max_length=40, verbose_name='Topografìa', help_text='Indica si es plano, inclinido, etc', default='Plano')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.geom:
            self.area = self.geom.area  # Calcular el área del polígono
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Campo"
        verbose_name_plural = "Campos"