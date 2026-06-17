"""
Notificador de alertas agronómicas.

Convierte una `AlertaOperativa` en un correo electrónico y lo envía a los
destinatarios apropiados del tenant. Mantiene registro de envíos en
`AlertNotification` para idempotencia y auditoría.

Reglas:
- Sólo se notifica si la severidad alcanza el umbral configurado del plan
  (por defecto `warning`; ENTERPRISE puede subir a `info` para SMS, etc.).
- Sólo se notifica si NO existe ya una `AlertNotification` para la misma
  (alerta, canal, destinatario) — evita reenvíos.
- Si el envío falla, se registra `fallida` con mensaje y queda pendiente
  para reintento manual o por command.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError
from django.template.loader import render_to_string
from django.utils.module_loading import import_string

from .models import (
    AlertaOperativa,
    AlertNotification,
    AlertSeverity,
    NotificationChannel,
    NotificationStatus,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

SEVERITY_RANK = {
    AlertSeverity.INFO: 0,
    AlertSeverity.WARNING: 1,
    AlertSeverity.CRITICAL: 2,
}

DEFAULT_MIN_SEVERITY = AlertSeverity.WARNING
DEFAULT_FROM_EMAIL = "contacto@agrotechcolombia.com"


@dataclass
class NotifyResult:
    sent: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


# ---------------------------------------------------------------------------
# Resolución de destinatarios
# ---------------------------------------------------------------------------

def default_recipients_resolver(alerta: AlertaOperativa) -> list[str]:
    """
    Devuelve la lista de correos a notificar para una alerta.

    Estrategia por defecto: usuarios staff/superuser del schema activo
    (que en django-tenants son los administradores del cliente actual).
    """
    User = get_user_model()
    emails = (
        User.objects
        .filter(is_active=True)
        .filter(email__isnull=False)
        .exclude(email="")
        .filter(is_staff=True)
        .values_list("email", flat=True)
        .distinct()
    )
    result = list(emails)
    if not result:
        # Fallback: cualquier usuario activo con email del schema
        result = list(
            User.objects
            .filter(is_active=True, email__isnull=False)
            .exclude(email="")
            .values_list("email", flat=True)
            .distinct()
        )
    return result


def _resolve_recipients(alerta: AlertaOperativa) -> list[str]:
    path = getattr(settings, "AGRONOMIC_ALERTS_RECIPIENTS_CALLABLE", None)
    if path:
        try:
            resolver = import_string(path)
            return list(resolver(alerta) or [])
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Resolver de destinatarios falló (%s): %s. Uso default.",
                path, exc,
            )
    return default_recipients_resolver(alerta)


# ---------------------------------------------------------------------------
# Feature gating del envío por correo
# ---------------------------------------------------------------------------

def _tenant_has_email_feature() -> bool:
    """
    Verifica que el tenant actual tenga la feature `alerts_email` en su plan.

    Defensivo: si `billing` no está disponible, no hay subscription activa, o
    el modelo falla por cualquier razón, retorna True para no bloquear el
    envío (modo dev / setups sin billing). En producción la subscription
    siempre debe existir.
    """
    if getattr(settings, "AGRONOMIC_ALERTS_BYPASS_FEATURE_GATE", False):
        return True
    try:
        from billing.models import Subscription  # import local: evita ciclos
    except Exception:  # noqa: BLE001
        return True
    try:
        sub = (
            Subscription.objects
            .select_related("plan")
            .filter(status__in=("active", "trialing"))
            .order_by("-created_at")
            .first()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo verificar feature 'alerts_email': %s", exc)
        return True
    if not sub or not sub.plan:
        return False
    return sub.plan.has_feature("alerts_email")


# ---------------------------------------------------------------------------
# AlertNotifier
# ---------------------------------------------------------------------------

class AlertNotifier:
    """Envía notificaciones por correo de una lista de alertas."""

    def __init__(
        self,
        *,
        min_severity: str = DEFAULT_MIN_SEVERITY,
        from_email: Optional[str] = None,
        site_name: str = "AgroTech Digital",
    ):
        self.min_severity = min_severity
        self.from_email = from_email or getattr(
            settings, "AGRONOMIC_ALERTS_FROM_EMAIL", DEFAULT_FROM_EMAIL,
        )
        self.site_name = site_name

    # ---- API pública ----
    def notify_many(self, alertas: Iterable[AlertaOperativa]) -> NotifyResult:
        result = NotifyResult()
        for alerta in alertas:
            self._notify_one(alerta, result)
        return result

    def notify(self, alerta: AlertaOperativa) -> NotifyResult:
        result = NotifyResult()
        self._notify_one(alerta, result)
        return result

    # ---- Lógica interna ----
    def _notify_one(self, alerta: AlertaOperativa, result: NotifyResult) -> None:
        if not self._severity_ok(alerta.severidad):
            result.skipped += 1
            return

        if not _tenant_has_email_feature():
            logger.info(
                "Alerta %s no notificada: plan del tenant no incluye 'alerts_email'.",
                alerta.pk,
            )
            result.skipped += 1
            return

        destinatarios = _resolve_recipients(alerta)
        if not destinatarios:
            logger.warning(
                "Alerta %s sin destinatarios en este tenant.", alerta.pk,
            )
            result.skipped += 1
            return

        for email in destinatarios:
            self._send_to(alerta, email, result)

    def _severity_ok(self, severidad: str) -> bool:
        return SEVERITY_RANK.get(severidad, 0) >= SEVERITY_RANK.get(self.min_severity, 1)

    def _send_to(
        self, alerta: AlertaOperativa, email: str, result: NotifyResult,
    ) -> None:
        notif, created = self._reserve_slot(alerta, email)
        if not created:
            # Ya existía una notificación para este (alerta, canal, destinatario):
            # sólo reintentar si está fallida o pendiente, no si fue enviada.
            if notif.estado == NotificationStatus.ENVIADA:
                result.skipped += 1
                return

        subject, text_body, html_body = self._render(alerta)
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=self.from_email,
                to=[email],
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send(fail_silently=False)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Fallo al enviar alerta %s a %s: %s", alerta.pk, email, exc)
            notif.marcar_fallida(str(exc))
            result.failed += 1
            result.errors.append({"email": email, "error": str(exc)})
            return

        notif.marcar_enviada()
        result.sent += 1

    def _reserve_slot(
        self, alerta: AlertaOperativa, email: str,
    ) -> tuple[AlertNotification, bool]:
        """Crea (o recupera) el registro de notificación. Idempotente."""
        try:
            return AlertNotification.objects.get_or_create(
                alerta=alerta,
                canal=NotificationChannel.EMAIL,
                destinatario=email,
                defaults={"estado": NotificationStatus.PENDIENTE},
            )
        except IntegrityError:
            notif = AlertNotification.objects.get(
                alerta=alerta, canal=NotificationChannel.EMAIL, destinatario=email,
            )
            return notif, False

    # ---- Render del correo ----
    def _render(self, alerta: AlertaOperativa) -> tuple[str, str, str]:
        ctx = {
            "alerta": alerta,
            "parcela": alerta.parcel,
            "site_name": self.site_name,
            "severidad_label": alerta.get_severidad_display(),
            "tipo_label": alerta.get_tipo_display(),
            "indice_label": alerta.get_indice_afectado_display(),
            "valor": alerta.valor_observado,
            "umbral_min": alerta.valor_umbral_min,
            "umbral_max": alerta.valor_umbral_max,
            "ventana_dias": alerta.ventana_dias,
            "fecha_escena": alerta.fecha_escena_origen,
            "causa": alerta.causa_probable,
            "recomendacion": alerta.recomendacion,
            "zona": alerta.zona,
            "contexto": alerta.contexto or {},
        }
        prefix = "[Crítica] " if alerta.severidad == AlertSeverity.CRITICAL else "[Alerta] "
        subject = f"{prefix}{alerta.titulo}"
        html_body = render_to_string("agronomic_alerts/email_alert.html", ctx)
        text_body = render_to_string("agronomic_alerts/email_alert.txt", ctx)
        return subject, text_body, html_body
