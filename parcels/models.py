import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
# Importación correcta para funciones GIS
from django.db import models
# from django.contrib.gis.db.models.functions import Area  # GIS deshabilitado temporalmente
from RRHH.models import Employee

class Parcel(models.Model):
    tenant_id = models.IntegerField(db_index=True, null=True, blank=True, verbose_name="ID del Tenant")
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
    tenant_id = models.IntegerField(db_index=True, null=True, blank=True, verbose_name="ID del Tenant")
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
    tenant_id = models.IntegerField(db_index=True, null=True, blank=True, verbose_name="ID del Tenant")
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


# ── Modelos de cache y estadisticas de EOSDA (con tenant scoping) ──────────

class CacheDatosEOSDA(models.Model):
    """
    Cache de datos satelitales EOSDA con tenant scoping.
    Almacena resultados de Statistics API indexados por tenant y geometria.
    """
    tenant_id = models.IntegerField(
        db_index=True,
        verbose_name="ID del Tenant",
        help_text="Client.id del tenant propietario de este cache"
    )
    parcela_id = models.IntegerField(null=True, blank=True, verbose_name="ID de Parcela")
    indice = models.CharField(max_length=10, verbose_name="Indice espectral")  # NDVI, NDMI, SAVI, EVI
    tipo_dato = models.CharField(max_length=50, verbose_name="Tipo de dato")
    geometria_hash = models.CharField(
        max_length=64,
        db_index=True,
        verbose_name="Hash SHA-256 de geometria"
    )
    datos = models.JSONField(verbose_name="Datos cacheados")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Fecha de creacion")
    expira_en = models.DateTimeField(db_index=True, verbose_name="Fecha de expiracion")

    class Meta:
        verbose_name = "Cache de datos EOSDA"
        verbose_name_plural = "Cache de datos EOSDA"
        indexes = [
            models.Index(fields=["tenant_id", "indice"]),
            models.Index(fields=["tenant_id", "geometria_hash"]),
        ]

    def __str__(self):
        return f"Cache[{self.indice}] tenant={self.tenant_id} | {self.timestamp}"

    @classmethod
    def limpiar_expirados(cls):
        """Elimina registros expirados. Retorna cantidad eliminada."""
        from django.utils import timezone
        deleted, _ = cls.objects.filter(expira_en__lt=timezone.now()).delete()
        return deleted


class EstadisticaUsoEOSDA(models.Model):
    """
    Registro de uso de EOSDA API con tenant scoping.
    Cada llamada a EOSDA API queda registrada para metricas y auditoria.
    """
    tenant_id = models.IntegerField(
        db_index=True,
        verbose_name="ID del Tenant",
        help_text="Client.id del tenant que realizo la solicitud"
    )
    endpoint = models.CharField(max_length=200, verbose_name="Endpoint llamado")
    tipo_request = models.CharField(max_length=50, verbose_name="Tipo de request")
    exitoso = models.BooleanField(default=True, verbose_name="Fue exitoso?")
    desde_cache = models.BooleanField(default=False, verbose_name="Provino de cache?")
    codigo_estado = models.IntegerField(null=True, blank=True, verbose_name="Codigo HTTP")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Fecha del request")

    class Meta:
        verbose_name = "Estadistica de uso EOSDA"
        verbose_name_plural = "Estadisticas de uso EOSDA"
        indexes = [
            models.Index(fields=["tenant_id", "timestamp"]),
            models.Index(fields=["tenant_id", "exitoso"]),
        ]

    def __str__(self):
        status = "OK" if self.exitoso else "FAIL"
        return f"EOSDA[{self.tipo_request}] tenant={self.tenant_id} {status} | {self.timestamp}"

    @classmethod
    def obtener_metricas_mes_actual(cls, tenant_id=None):
        """
        Retorna metricas de uso del mes actual.
        Si tenant_id es None, retorna metricas globales.
        """
        from django.utils import timezone
        now = timezone.now()
        inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        qs = cls.objects.filter(timestamp__gte=inicio_mes)
        if tenant_id is not None:
            qs = qs.filter(tenant_id=tenant_id)
        total = qs.count()
        desde_cache = qs.filter(desde_cache=True).count()
        errores = qs.filter(exitoso=False).count()
        return {
            'total_requests': total,
            'desde_cache': desde_cache,
            'desde_api': total - desde_cache,
            'tasa_cache': round((desde_cache / total * 100) if total > 0 else 0, 2),
            'errores': errores,
        }


# ── Mixins de seguridad multi-tenant ──────────────────────────────────────

class TenantScopedQueryMixin:
    """
    Mixin para Views/ViewSets que fuerza filtrado por tenant_id.
    Compatible con modelos que tienen campo tenant_id (IntegerField).
    
    Uso:
        class MiVista(TenantScopedQueryMixin, APIView):
            def get(self, request):
                qs = self.filter_by_tenant(MiModelo.objects.all())
    """
    tenant_field = 'tenant_id'

    def get_tenant_id(self):
        """
        Obtiene el tenant_id desde request.tenant.
        Retorna None si es schema public o no hay tenant.
        """
        tenant = getattr(self.request, 'tenant', None)
        if tenant and tenant.schema_name != 'public':
            return tenant.id
        return None

    def filter_by_tenant(self, queryset):
        """
        Aplica filtro tenant_id al queryset si el modelo tiene ese campo.
        Si no tiene el campo o no hay tenant, retorna el queryset sin modificar.
        """
        tid = self.get_tenant_id()
        if tid is not None and hasattr(queryset.model, self.tenant_field):
            return queryset.filter(**{self.tenant_field: tid})
        return queryset


class TenantScopedModelMixin:
    """
    Mixin para ModelViewSet que agrega verificacion de tenant en get_queryset.
    Defensa en profundidad — no reemplaza el aislamiento por schema de django-tenants,
    lo complementa.
    
    Si el modelo tiene campo 'tenant_id', filtra automaticamente.
    Si no lo tiene, retorna el queryset sin modificar (cero impacto).
    
    Uso:
        class MiViewSet(TenantScopedModelMixin, viewsets.ModelViewSet):
            queryset = MiModelo.objects.all()
    """
    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant and tenant.schema_name != 'public':
            if hasattr(qs.model, 'tenant_id'):
                return qs.filter(tenant_id=tenant.id)
        return qs


