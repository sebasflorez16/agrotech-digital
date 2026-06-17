"""
Modelos de Alertas Agronómicas Operativas.

Estos modelos persisten las alertas generadas por el motor agronómico
(`agronomic_alerts.engine.AgronomicAlertEngine`) a partir de los índices
satelitales (NDVI / NDMI / SAVI / EVI) y la etapa fenológica del cultivo
(`crop.CropCycle.get_index_interpretation`).

Reglas de diseño:
- App TENANT-scoped (cada cliente tiene sus propias alertas en su schema).
- Las alertas son IDEMPOTENTES: se identifican con un `fingerprint` que
  combina parcela + índice + tipo + fecha de escena. Si una escena vuelve
  a procesarse, no se duplica la alerta.
- Cada alerta lleva contexto agronómico explícito: causa probable,
  recomendación, ventana de acción y valor de referencia.
- Se guarda feedback del productor para construir un dataset de aprendizaje
  (semilla para futuros modelos ML).
"""

import hashlib
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from parcels.models import Parcel


class AlertType(models.TextChoices):
    """Categoría agronómica de la alerta."""

    HUMEDAD = "humedad", "Estrés hídrico / humedad"
    VIGOR = "vigor", "Vigor vegetativo"
    COBERTURA = "cobertura", "Cobertura vegetal"
    ANOMALIA = "anomalia", "Anomalía / desviación"


class AlertSeverity(models.TextChoices):
    """Nivel de urgencia operativa."""

    INFO = "info", "Informativa"
    WARNING = "warning", "Advertencia"
    CRITICAL = "critical", "Crítica"


class AlertStatus(models.TextChoices):
    """Estado del ciclo de vida de la alerta."""

    ACTIVA = "activa", "Activa"
    ATENDIDA = "atendida", "Atendida"
    POSPUESTA = "posponer", "Pospuesta"
    DESCARTADA = "descartada", "Descartada"


class AlertFeedback(models.TextChoices):
    """Feedback del productor sobre la utilidad real de la alerta."""

    UTIL = "util", "Útil — la situación era real"
    NO_UTIL = "no_util", "No fue útil"
    FALSO_POSITIVO = "falso_positivo", "Falso positivo"


class SatelliteIndex(models.TextChoices):
    NDVI = "ndvi", "NDVI"
    NDMI = "ndmi", "NDMI"
    SAVI = "savi", "SAVI"
    EVI = "evi", "EVI"
    NDRE = "ndre", "NDRE"


def _build_fingerprint(parcel_id, indice, tipo, fecha_escena, zona):
    """Genera un hash determinista para evitar alertas duplicadas."""
    zona_norm = (zona or "").strip().lower()
    raw = f"{parcel_id}|{indice}|{tipo}|{fecha_escena.isoformat()}|{zona_norm}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AlertaOperativa(models.Model):
    """
    Alerta agronómica operativa derivada de una escena satelital concreta.

    Estructura obligatoria (acuerdo del producto):
    - QUÉ pasa (`tipo`, `severidad`, `indice_afectado`)
    - DÓNDE (`parcel`, `zona`)
    - POR QUÉ (`causa_probable`, `valor_observado` vs umbrales)
    - QUÉ HACER (`recomendacion`)
    - CUÁNDO (`ventana_dias`, `fecha_escena_origen`)
    """

    uuid = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True,
    )

    parcel = models.ForeignKey(
        Parcel,
        on_delete=models.CASCADE,
        related_name="alertas_agronomicas",
        verbose_name="Parcela",
    )
    crop_cycle = models.ForeignKey(
        "crop.CropCycle",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="alertas_agronomicas",
        verbose_name="Ciclo de cultivo",
        help_text="Ciclo activo cuando se detectó la alerta (puede ser nulo).",
    )

    # ---- QUÉ ----
    tipo = models.CharField(
        max_length=20, choices=AlertType.choices, verbose_name="Tipo",
    )
    severidad = models.CharField(
        max_length=20, choices=AlertSeverity.choices,
        default=AlertSeverity.WARNING, verbose_name="Severidad",
    )
    indice_afectado = models.CharField(
        max_length=10, choices=SatelliteIndex.choices,
        verbose_name="Índice afectado",
    )
    titulo = models.CharField(
        max_length=200, verbose_name="Título corto",
        help_text="Resumen en una línea para listas y notificaciones.",
    )

    # ---- DÓNDE ----
    zona = models.CharField(
        max_length=100, blank=True, default="",
        verbose_name="Zona del lote",
        help_text="Descripción humana de la zona afectada (ej. 'Norte', 'A1-A4').",
    )

    # ---- POR QUÉ ----
    causa_probable = models.TextField(
        verbose_name="Causa probable",
        help_text="Explicación agronómica del por qué del índice observado.",
    )
    valor_observado = models.FloatField(verbose_name="Valor observado")
    valor_umbral_min = models.FloatField(
        null=True, blank=True, verbose_name="Umbral mínimo esperado",
    )
    valor_umbral_max = models.FloatField(
        null=True, blank=True, verbose_name="Umbral máximo esperado",
    )
    desviacion_pct = models.FloatField(
        null=True, blank=True,
        verbose_name="Desviación (%)",
        help_text="% de desviación respecto al rango esperado de la etapa.",
    )

    # ---- QUÉ HACER ----
    recomendacion = models.TextField(
        verbose_name="Recomendación",
        help_text="Acción concreta sugerida al productor.",
    )

    # ---- CUÁNDO ----
    ventana_dias = models.PositiveSmallIntegerField(
        default=7,
        verbose_name="Ventana de acción (días)",
        help_text="Días en los que conviene actuar.",
    )
    fecha_escena_origen = models.DateField(
        verbose_name="Fecha de la escena satelital",
        help_text="Fecha de la imagen Sentinel-2 que originó la alerta.",
    )
    fecha_deteccion = models.DateTimeField(
        auto_now_add=True, verbose_name="Detectada en",
    )

    # ---- Estado y feedback ----
    estado = models.CharField(
        max_length=20, choices=AlertStatus.choices,
        default=AlertStatus.ACTIVA, verbose_name="Estado",
    )
    atendida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="alertas_atendidas",
        verbose_name="Atendida por",
    )
    fecha_estado = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha cambio de estado",
    )
    feedback = models.CharField(
        max_length=20, choices=AlertFeedback.choices,
        blank=True, default="", verbose_name="Feedback",
    )
    feedback_comentario = models.TextField(
        blank=True, default="", verbose_name="Comentario del feedback",
    )
    fecha_feedback = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha del feedback",
    )

    # ---- Idempotencia ----
    fingerprint = models.CharField(
        max_length=64, unique=True, db_index=True,
        verbose_name="Huella única",
        help_text="Hash sha256 para evitar alertas duplicadas.",
    )

    # ---- Contexto adicional (para futuro ML) ----
    contexto = models.JSONField(
        default=dict, blank=True,
        verbose_name="Contexto agronómico",
        help_text="Etapa fenológica, cultivo, índices acompañantes, etc.",
    )

    class Meta:
        verbose_name = "Alerta agronómica"
        verbose_name_plural = "Alertas agronómicas"
        ordering = ["-fecha_deteccion"]
        indexes = [
            models.Index(fields=["parcel", "estado"]),
            models.Index(fields=["severidad", "estado"]),
            models.Index(fields=["fecha_escena_origen"]),
        ]

    def __str__(self):
        return f"[{self.severidad}] {self.titulo} ({self.parcel_id})"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @classmethod
    def build_fingerprint(cls, *, parcel_id, indice, tipo, fecha_escena, zona=""):
        """Helper público para que el motor calcule el fingerprint antes de crear."""
        return _build_fingerprint(parcel_id, indice, tipo, fecha_escena, zona)

    def marcar_atendida(self, *, usuario=None, feedback=None, comentario=""):
        """Marca la alerta como atendida y guarda feedback opcional."""
        self.estado = AlertStatus.ATENDIDA
        self.atendida_por = usuario
        self.fecha_estado = timezone.now()
        if feedback:
            self.feedback = feedback
            self.feedback_comentario = comentario or ""
            self.fecha_feedback = self.fecha_estado
        self.save(update_fields=[
            "estado", "atendida_por", "fecha_estado",
            "feedback", "feedback_comentario", "fecha_feedback",
        ])

    def posponer(self, dias=7):
        """Pospone la ventana de acción."""
        self.estado = AlertStatus.POSPUESTA
        self.ventana_dias = (self.ventana_dias or 0) + dias
        self.fecha_estado = timezone.now()
        self.save(update_fields=["estado", "ventana_dias", "fecha_estado"])

    def descartar(self, *, usuario=None, comentario=""):
        """Descarta la alerta como no relevante."""
        self.estado = AlertStatus.DESCARTADA
        self.atendida_por = usuario
        self.feedback = AlertFeedback.FALSO_POSITIVO
        self.feedback_comentario = comentario or ""
        self.fecha_estado = timezone.now()
        self.fecha_feedback = self.fecha_estado
        self.save(update_fields=[
            "estado", "atendida_por",
            "feedback", "feedback_comentario",
            "fecha_estado", "fecha_feedback",
        ])


# ---------------------------------------------------------------------------
# Notificaciones
# ---------------------------------------------------------------------------

class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Correo electrónico"
    IN_APP = "in_app", "Dentro de la aplicación"
    WEBHOOK = "webhook", "Webhook"


class NotificationStatus(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    ENVIADA = "enviada", "Enviada"
    FALLIDA = "fallida", "Fallida"


class AlertNotification(models.Model):
    """
    Registro de notificaciones disparadas por una alerta.

    Sirve para:
    - Evitar enviar el mismo correo dos veces.
    - Auditar entregas y fallos.
    - Soportar reintentos.
    """

    alerta = models.ForeignKey(
        AlertaOperativa,
        on_delete=models.CASCADE,
        related_name="notificaciones",
        verbose_name="Alerta",
    )
    canal = models.CharField(
        max_length=20, choices=NotificationChannel.choices,
        default=NotificationChannel.EMAIL, verbose_name="Canal",
    )
    destinatario = models.CharField(
        max_length=255, verbose_name="Destinatario",
        help_text="Email, id de usuario o URL de webhook.",
    )
    estado = models.CharField(
        max_length=20, choices=NotificationStatus.choices,
        default=NotificationStatus.PENDIENTE, verbose_name="Estado",
    )
    intentos = models.PositiveSmallIntegerField(default=0, verbose_name="Intentos")
    mensaje_error = models.TextField(blank=True, default="", verbose_name="Mensaje de error")
    payload = models.JSONField(default=dict, blank=True, verbose_name="Payload")

    enviado_en = models.DateTimeField(null=True, blank=True, verbose_name="Enviado en")
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Creado en")
    actualizado_en = models.DateTimeField(auto_now=True, verbose_name="Actualizado en")

    class Meta:
        verbose_name = "Notificación de alerta"
        verbose_name_plural = "Notificaciones de alertas"
        ordering = ["-creado_en"]
        constraints = [
            # Evita reenviar la misma alerta por el mismo canal al mismo destinatario.
            models.UniqueConstraint(
                fields=["alerta", "canal", "destinatario"],
                name="uq_notif_alerta_canal_destinatario",
            ),
        ]

    def __str__(self):
        return f"{self.canal} → {self.destinatario} ({self.estado})"

    def marcar_enviada(self):
        self.estado = NotificationStatus.ENVIADA
        self.enviado_en = timezone.now()
        self.intentos = (self.intentos or 0) + 1
        self.mensaje_error = ""
        self.save(update_fields=["estado", "enviado_en", "intentos", "mensaje_error"])

    def marcar_fallida(self, error_msg):
        self.estado = NotificationStatus.FALLIDA
        self.intentos = (self.intentos or 0) + 1
        self.mensaje_error = str(error_msg)[:2000]
        self.save(update_fields=["estado", "intentos", "mensaje_error"])
