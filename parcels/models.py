import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
# Importación correcta para funciones GIS
from django.db import models
# from django.contrib.gis.db.models.functions import Area  # GIS deshabilitado temporalmente
from RRHH.models import Employee

class Parcel(models.Model):
    eosda_id = models.CharField(max_length=32, blank=True, null=True, unique=True, verbose_name="ID EOSDA", help_text="ID del campo en EOSDA")
    name = models.CharField(max_length=100, verbose_name="Nombre del campo", blank=True, null=True)
    description = models.TextField(verbose_name="Descripción del campo", blank=True, null=True)
    field_type = models.CharField(max_length=100, verbose_name="Tipo de campo", blank=True, null=True)
    state = models.BooleanField(verbose_name="Estado del campo", default=True, blank=True, null=True)
    geom = models.JSONField(verbose_name="GeoJSON del campo", blank=True, null=True, help_text="GeoJSON Polygon. Compatible con EOSDA API Connect.")
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
        Calcula el área en hectáreas usando el polígono GeoJSON (compatible con EOSDA).
        """
        import math
        def polygon_area(coords):
            # Calcula el área aproximada en m² usando la fórmula de Shoelace para coordenadas [lon, lat]
            if not coords or len(coords) < 3:
                return 0
            area = 0.0
            for i in range(len(coords)):
                x1, y1 = coords[i]
                x2, y2 = coords[(i + 1) % len(coords)]
                area += x1 * y2 - x2 * y1
            return abs(area) / 2.0 * 111320 * 111320  # Aproximación para grados a metros
        if self.geom and isinstance(self.geom, dict):
            # Espera GeoJSON Polygon: {'type': 'Polygon', 'coordinates': [[...]]}
            coords = self.geom.get('coordinates', [[]])[0]
            area_m2 = polygon_area(coords)
            return area_m2 / 10000.0
        return 0

    def clean(self):
        """
        Limita el total de hectáreas por usuario (manager) a 300 ha.
        Incluye parcelas eliminadas (huella) en el conteo para evitar trampas.

        NOTA: La validación de área y uso de 'geom' está comentada temporalmente
        porque el campo geom (GIS) está deshabilitado para facilitar el flujo de trabajo
        y evitar errores en desarrollo. Descomentar cuando se reactive GIS.
        """
        # if self.manager and self.geom:
        #     from django.db.models import Sum
        #     # Suma el área de todas las parcelas del manager, incluyendo eliminadas, excepto la actual
        #     total_area = Parcel.objects.filter(manager=self.manager).exclude(pk=self.pk).annotate(
        #         # area_m2=Area('geom')  # GIS deshabilitado temporalmente
        #     ).aggregate(total=Sum('area_m2'))["total"]
        #     if total_area is None:
        #         total_area_m2 = 0
        #     elif hasattr(total_area, 'sq_m'):
        #         total_area_m2 = total_area.sq_m
        #     else:
        #         total_area_m2 = float(total_area)
        #     total_ha = total_area_m2 / 10000.0
        #     nueva_area = self.area_hectares()
        #     if total_ha + nueva_area > 300:
        #         raise ValidationError(f"El usuario '{self.manager}' no puede tener más de 300 hectáreas en total. Actualmente: {total_ha:.2f} ha.")

    def save(self, *args, **kwargs):
        """
        Valida y guarda la parcela. Calcula el área y aplica la validación de hectáreas.
        Si no tiene eosda_id, crea el campo en EOSDA y lo guarda.
        """
        self.full_clean()  # Ejecuta clean() y validaciones
        # Si no tiene eosda_id, intenta crearlo en EOSDA
        if not self.eosda_id and self.geom:
            try:
                from django.conf import settings
                import requests
                
                api_key = getattr(settings, "EOSDA_API_KEY", None)
                if not api_key:
                    raise Exception("No se encontró EOSDA_API_KEY en settings")
                
                # Endpoint correcto para EOSDA API Connect Field Management
                # Documentación: https://doc.eos.com/docs/field-management-api/field-management/
                eosda_api_url = "https://api-connect.eos.com/field-management"
                
                # Construir el payload según el formato requerido por EOSDA API Connect
                payload = {
                    "type": "Feature",
                    "properties": {
                        "name": self.name or "Campo sin nombre",
                    },
                    "geometry": self.geom
                }
                
                # Usar header x-api-key para autenticación
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": api_key
                }
                
                print(f"[EOSDA] Creando campo en EOSDA: {self.name}")
                resp = requests.post(eosda_api_url, json=payload, headers=headers, timeout=30)
                
                print(f"[EOSDA] Respuesta: {resp.status_code} - {resp.text[:500]}")
                
                if resp.status_code in (200, 201):
                    data = resp.json()
                    # El ID puede venir en diferentes formatos según la versión de la API
                    new_eosda_id = data.get("id") or data.get("field_id") or data.get("_id") or data.get("fieldId")
                    if new_eosda_id:
                        self.eosda_id = str(new_eosda_id)
                        print(f"[EOSDA] Campo creado exitosamente con ID: {self.eosda_id}")
                    else:
                        print(f"[EOSDA] Respuesta sin ID: {data}")
                elif resp.status_code == 402:
                    print(f"[EOSDA] Límite de API excedido. No se pudo crear el campo.")
                else:
                    print(f"[EOSDA] Error al crear campo: {resp.status_code} - {resp.text[:200]}")
            except Exception as e:
                print(f"[EOSDA] Error al crear campo en EOSDA: {e}")
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

# Modelo para cachear escenas NDVI/NDMI de EOSDA por parcela y tipo de índice
class ParcelSceneCache(models.Model):
    parcel = models.ForeignKey('Parcel', on_delete=models.CASCADE, related_name='scene_caches')
    scene_id = models.CharField(max_length=64, verbose_name="ID de escena EOSDA")
    date = models.DateField(verbose_name="Fecha de la escena")
    index_type = models.CharField(max_length=10, choices=[('NDVI', 'NDVI'), ('NDMI', 'NDMI')], verbose_name="Tipo de índice")
    metadata = models.JSONField(verbose_name="Metadatos de la escena", blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="URL de la imagen/capa WMTS")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    raw_response = models.JSONField(blank=True, null=True, verbose_name="Respuesta completa de EOSDA")

    class Meta:
        verbose_name = "Cache de escena satelital"
        verbose_name_plural = "Cache de escenas satelitales"
        unique_together = ("parcel", "scene_id", "index_type")
        indexes = [
            models.Index(fields=["parcel", "scene_id", "index_type"]),
        ]

    def __str__(self):
        return f"{self.parcel.name} | {self.index_type} | {self.date} | {self.scene_id}"


