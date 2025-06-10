import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
# Importación correcta para funciones GIS
from django.contrib.gis.db import models
from django.contrib.gis.db.models.functions import Area
from RRHH.models import Employee

class Parcel(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre del campo", blank=True, null=True)
    description = models.TextField(verbose_name="Descripción del campo", blank=True, null=True)
    field_type = models.CharField(max_length=100, verbose_name="Tipo de campo", blank=True, null=True)
    state = models.BooleanField(verbose_name="Estado del campo", default=True, blank=True, null=True)
    geom = models.PolygonField(verbose_name="Área geográfica del campo", blank=True, null=True)
    created_on =models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación", blank=True, null=True)
    updated_on =models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización", blank=True, null=True)
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="ID Único", blank=True, null=True)
    manager = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name="Responsable del campo", blank=True, null=True)
    soil_type = models.CharField(max_length=20, verbose_name='Tipo de suelo', help_text='Especifica si es arenoso, arcillozo, etc')
    topography = models.CharField(max_length=20, verbose_name='Topografìa', help_text='Indica si es plano, inclinido, etc')
    # Soft delete: huella de eliminación
    is_deleted = models.BooleanField(default=False, editable=False, verbose_name="Eliminado")
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False, verbose_name="Fecha de eliminación")

    def __str__(self):  
        return self.name

    def area_hectares(self):
        """
        Calcula el área en hectáreas (1 ha = 10,000 m²), transformando a un SRID proyectado para obtener el área real.
        """
        if self.geom:
            # Transforma a Web Mercator (SRID 3857) antes de calcular el área
            geom_proj = self.geom.transform(3857, clone=True)
            return geom_proj.area / 10000.0
        return 0

    def clean(self):
        """
        Limita el total de hectáreas por usuario (manager) a 300 ha.
        Incluye parcelas eliminadas (huella) en el conteo para evitar trampas.
        """
        if self.manager and self.geom:
            from django.db.models import Sum
            # Suma el área de todas las parcelas del manager, incluyendo eliminadas, excepto la actual
            total_area = Parcel.objects.filter(manager=self.manager).exclude(pk=self.pk).annotate(
                area_m2=Area('geom')
            ).aggregate(total=Sum('area_m2'))["total"]
            if total_area is None:
                total_area_m2 = 0
            elif hasattr(total_area, 'sq_m'):
                total_area_m2 = total_area.sq_m
            else:
                total_area_m2 = float(total_area)
            total_ha = total_area_m2 / 10000.0
            nueva_area = self.area_hectares()
            if total_ha + nueva_area > 300:
                raise ValidationError(f"El usuario '{self.manager}' no puede tener más de 300 hectáreas en total. Actualmente: {total_ha:.2f} ha.")

    def save(self, *args, **kwargs):
        """
        Valida y guarda la parcela. Calcula el área y aplica la validación de hectáreas.
        """
        self.full_clean()  # Ejecuta clean() y validaciones
        # Si tienes un campo area, puedes calcularlo aquí (opcional)
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """
        Soft delete: marca la parcela como eliminada y guarda la fecha de eliminación.
        No elimina físicamente el registro.
        """
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    class Meta:
        verbose_name = "Campo"
        verbose_name_plural = "Campos"

#Registra cada accion relevante sobre la parcela
# Se puede usar para auditoría o para mostrar en el frontend
class ParcelActionLog(models.Model):
    ACTION_CHOICES = [
        ("create", "Creación"),
        ("update", "Actualización"),
        ("delete", "Eliminación"),
    ]
    parcel = models.ForeignKey('Parcel', on_delete=models.CASCADE, related_name='logs')
    # El campo user ahora apunta al modelo de usuario real del sistema (users.User)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Usuario",
        help_text="Opcional. Apunta al usuario real del sistema para auditoría multiusuario."
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True, help_text="Detalles adicionales de la acción")

    def __str__(self):
        return f"{self.get_action_display()} - {self.parcel.name} - {self.timestamp:%Y-%m-%d %H:%M}"

    class Meta:
        verbose_name = "Log de acción de parcela"
        verbose_name_plural = "Logs de acciones de parcelas"
        ordering = ["-timestamp"]
        # Documentación: Este modelo está preparado para multiusuario real (users.User), pero el campo user es opcional y no afecta el funcionamiento actual del SaaS.
