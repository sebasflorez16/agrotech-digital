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


# ── Estado de salud del cultivo (Monitoreo Continuo Fase 1) ────────────

class CropHealthStatus(models.Model):
    """
    Estado de salud del cultivo persistente.
    Mantiene el ultimo estado conocido incluso cuando no hay imagenes nuevas.
    Permite al agricultor saber que su cultivo sigue siendo monitoreado.
    """
    parcel = models.OneToOneField(
        'Parcel',
        on_delete=models.CASCADE,
        related_name='health_status',
        verbose_name="Parcela"
    )
    tenant_id = models.IntegerField(db_index=True, null=True, blank=True, verbose_name="ID del Tenant")

    # Ultimos indices conocidos
    ndvi_last = models.FloatField(null=True, blank=True, verbose_name="Ultimo NDVI")
    ndmi_last = models.FloatField(null=True, blank=True, verbose_name="Ultimo NDMI")
    evi_last = models.FloatField(null=True, blank=True, verbose_name="Ultimo EVI")

    # Fecha de la ultima observacion valida
    last_observation_date = models.DateTimeField(null=True, blank=True, verbose_name="Ultima observacion")
    last_image_date = models.DateField(null=True, blank=True, verbose_name="Fecha de la ultima imagen")

    # Calidad de la observacion
    QUALITY_CHOICES = [
        ('excellent', 'Excelente — Imagen reciente, baja nubosidad'),
        ('good', 'Buena — Imagen utilizable con algunas limitaciones'),
        ('limited', 'Limitada — Alta nubosidad, analisis parcial'),
        ('no_observation', 'Sin observacion confiable — No hay datos opticos validos'),
    ]
    observation_quality = models.CharField(
        max_length=20, choices=QUALITY_CHOICES,
        default='no_observation', verbose_name="Calidad de observacion"
    )

    # Confianza del estado actual (0-100)
    confidence_score = models.IntegerField(default=0, verbose_name="Confianza del estado (0-100)")

    # Numero de dias sin observacion optica
    days_without_observation = models.IntegerField(default=0, verbose_name="Dias sin observacion")

    # Alertas activas
    active_alerts = models.JSONField(default=list, blank=True, verbose_name="Alertas activas")

    # Fechas de actualizacion
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estado de salud del cultivo"
        verbose_name_plural = "Estados de salud de cultivos"
        indexes = [
            models.Index(fields=["tenant_id"]),
            models.Index(fields=["parcel", "updated_at"]),
        ]

    def __str__(self):
        return f"Salud {self.parcel.name} | NDVI:{self.ndvi_last} | {self.observation_quality} | {self.updated_at:%Y-%m-%d}"

    @property
    def status_badge(self):
        """Retorna el badge visual para el frontend."""
        if self.observation_quality == 'excellent' and self.confidence_score >= 80:
            return {'emoji': '🟢', 'label': 'Excelente', 'color': '#22c55e'}
        elif self.observation_quality in ('good', 'excellent') and self.confidence_score >= 60:
            return {'emoji': '🟢', 'label': 'Bueno', 'color': '#22c55e'}
        elif self.observation_quality in ('good', 'limited') and self.confidence_score >= 30:
            return {'emoji': '🟡', 'label': 'Atencion', 'color': '#eab308'}
        elif self.observation_quality == 'limited' or self.days_without_observation > 14:
            return {'emoji': '🟠', 'label': 'Limitado', 'color': '#f97316'}
        else:
            return {'emoji': '🔴', 'label': 'Sin datos', 'color': '#ef4444'}

    @property
    def status_message(self):
        """Mensaje descriptivo para el agricultor."""
        if self.days_without_observation == 0:
            return f"Tu cultivo fue observado hoy. NDVI: {self.ndvi_last:.2f} — {self.get_quality_label()}"
        elif self.days_without_observation <= 7:
            return f"Tu cultivo fue observado hace {self.days_without_observation} dias. NDVI estimado: {self.ndvi_last:.2f}. Seguimos monitoreando."
        elif self.days_without_observation <= 14:
            return f"Ultima observacion hace {self.days_without_observation} dias. NDVI: {self.ndvi_last:.2f}. Esperando proxima imagen sin nubes."
        else:
            return f"Sin observacion reciente ({self.days_without_observation} dias). NDVI historico: {self.ndvi_last:.2f}. Usamos datos complementarios para seguir vigilando."

    def get_quality_label(self):
        return dict(self.QUALITY_CHOICES).get(self.observation_quality, 'Desconocido')

    def update_from_observation(self, ndvi=None, ndmi=None, evi=None, image_date=None, cloud_cover=None):
        """Actualiza el estado con una nueva observacion."""
        from django.utils import timezone

        if ndvi is not None:
            self.ndvi_last = ndvi
        if ndmi is not None:
            self.ndmi_last = ndmi
        if evi is not None:
            self.evi_last = evi

        self.last_observation_date = timezone.now()
        if image_date:
            self.last_image_date = image_date
        if cloud_cover is not None:
            if cloud_cover < 10:
                self.observation_quality = 'excellent'
                self.confidence_score = 95
            elif cloud_cover < 30:
                self.observation_quality = 'good'
                self.confidence_score = 75
            elif cloud_cover < 70:
                self.observation_quality = 'limited'
                self.confidence_score = 40
            else:
                self.observation_quality = 'limited'
                self.confidence_score = 20
        self.days_without_observation = 0
        self.save()

    @classmethod
    def get_or_create_for_parcel(cls, parcel):
        """Obtiene o crea el estado de salud para una parcela."""
        obj, _ = cls.objects.get_or_create(
            parcel=parcel,
            defaults={'tenant_id': parcel.tenant_id}
        )
        return obj


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


# ---------------------------------------------------------------------------
# Zonificación de manejo (precision farming)
# ---------------------------------------------------------------------------

class ParcelZonification(models.Model):
    """Agrupa K zonas de manejo derivadas de un índice satelital."""

    parcel_id = models.IntegerField(db_index=True, verbose_name="Parcela")

    scene_date = models.DateField(verbose_name="Fecha de la escena base")
    index_base = models.CharField(
        max_length=10, default="ndvi",
        choices=[
            ("ndvi", "NDVI"), ("ndmi", "NDMI"),
            ("savi", "SAVI"), ("ndre", "NDRE"),
        ],
        help_text="Índice satelital usado para clusterizar",
    )
    method = models.CharField(
        max_length=20, default="kmeans",
        choices=[
            ("kmeans", "K-means"), ("isodata", "ISODATA"),
            ("jenks", "Jenks (natural breaks)"),
            ("percentiles", "Percentiles fijos"), ("manual", "Manual"),
        ],
    )
    k_zones = models.IntegerField(default=5, verbose_name="Número de zonas (k)")
    status = models.CharField(
        max_length=20, default="pending",
        choices=[
            ("pending", "Pendiente"), ("processing", "Procesando"),
            ("ready", "Lista"), ("failed", "Fallo"),
        ],
    )
    total_pixels = models.IntegerField(default=0)
    pixel_resolution_m = models.FloatField(default=10.0, verbose_name="Resolución del pixel (m)")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Zonificación de parcela"
        verbose_name_plural = "Zonificaciones de parcela"
        ordering = ["-scene_date", "-created_at"]
        indexes = [
            models.Index(fields=["parcel_id", "-scene_date"]),
        ]

    def __str__(self):
        return f"Zonif #{self.id} parcela={self.parcel_id} ({self.index_base}, k={self.k_zones})"


class ParcelZone(models.Model):
    """Zona de manejo individual dentro de una zonificación."""

    zonification = models.ForeignKey(
        ParcelZonification, on_delete=models.CASCADE,
        related_name="zones",
    )
    cluster_id = models.IntegerField(verbose_name="ID de cluster (k-means)")
    label = models.CharField(max_length=40, verbose_name="Etiqueta")
    category = models.CharField(
        max_length=20, default="mid",
        choices=[
            ("low", "Bajo vigor"), ("mid_low", "Vigor medio-bajo"),
            ("mid", "Vigor medio"), ("mid_high", "Vigor medio-alto"),
            ("high", "Alto vigor"),
        ],
    )
    pixel_count = models.IntegerField(default=0)
    area_ha = models.FloatField(default=0.0)
    ndvi_mean = models.FloatField(null=True, blank=True)
    ndvi_std = models.FloatField(null=True, blank=True)
    ndvi_min = models.FloatField(null=True, blank=True)
    ndvi_max = models.FloatField(null=True, blank=True)
    ndmi_mean = models.FloatField(null=True, blank=True)
    ndmi_std = models.FloatField(null=True, blank=True)
    savi_mean = models.FloatField(null=True, blank=True)
    savi_std = models.FloatField(null=True, blank=True)
    ndre_mean = models.FloatField(null=True, blank=True)
    ndre_std = models.FloatField(null=True, blank=True)
    geometry_geojson = models.JSONField(null=True, blank=True, verbose_name="Polígono GeoJSON")
    recomendacion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Zona de manejo"
        verbose_name_plural = "Zonas de manejo"
        ordering = ["zonification", "cluster_id"]
        unique_together = [["zonification", "cluster_id"]]

    def __str__(self):
        return f"Zona {self.cluster_id} ({self.label})"
