"""
Comando de monitoreo continuo de cultivos.
Ejecutar diariamente via cron o Railway scheduler:

    python manage.py monitor_crops

Usa Sentinel-2 (EOSDA) cuando hay imagenes con <30% nubes.
Si no hay datos opticos, usa Sentinel-1 radar como respaldo.
Genera alertas por email cuando detecta cambios significativos.
"""

import logging
import threading
from datetime import date, timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

from base_agrotech.models import Client
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Monitoreo continuo de cultivos: S2 optico + S1 radar con alertas."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Solo diagnosticar, no enviar emails")
        parser.add_argument("--tenant", type=str, help="Schema de un tenant especifico")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        tenant_filter = options.get("tenant")

        tenants = Client.objects.exclude(schema_name="public").order_by("schema_name")
        if tenant_filter:
            tenants = tenants.filter(schema_name=tenant_filter)

        if not tenants.exists():
            self.stdout.write(self.style.WARNING("No hay tenants registrados."))
            return

        total_parcels = 0
        optical_ok = 0
        radar_fallback = 0
        alerts_generated = 0
        emails_sent = 0

        for tenant in tenants:
            with schema_context(tenant.schema_name):
                from parcels.models import Parcel, MonitoringEvent
                from parcels.sentinel1 import get_crop_status_from_radar

                parcels = Parcel.objects.filter(is_deleted=False)
                for parcel in parcels:
                    total_parcels += 1
                    geom = parcel.geom or {}
                    if not geom or geom.get("type") != "Polygon":
                        continue

                    # Intentar obtener NDVI via EOSDA
                    optical_data = self._try_get_optical_data(parcel, tenant)

                    if optical_data and optical_data.get("ndvi"):
                        optical_ok += 1
                        ndvi = float(optical_data["ndvi"])
                        cloud_cover = optical_data.get("cloud_cover", 0)

                        if ndvi < 0.3:
                            alert = {
                                "type": "ndvi_critical",
                                "title": f"NDVI critico en {parcel.name}",
                                "message": f"NDVI={ndvi:.2f}, nubes={cloud_cover}%",
                            }
                            self._create_alert(parcel, alert, dry_run)
                            alerts_generated += 1
                    else:
                        ndvi_last = None
                        try:
                            health = parcel.health_status
                            if health:
                                ndvi_last = health.ndvi_last
                        except Exception:
                            pass

                        result = get_crop_status_from_radar(
                            geom, days_back=14,
                            ndvi_value=ndvi_last
                        )
                        radar_fallback += 1

                        if result.get("change_detected"):
                            info = result.get("change_info", {})
                            alert = {
                                "type": "radar_change",
                                "title": f"Cambio radar en {parcel.name}",
                                "message": f"{info.get('interpretation', 'Cambio detectado')} "
                                           f"(magnitud: {info.get('magnitude', '?')} dB, "
                                           f"escenas: {result.get('scenes_found', 0)})",
                            }
                            self._create_alert(parcel, alert, dry_run)
                            alerts_generated += 1

                    # Enviar email consolidado al admin del tenant si hay alertas nuevas
                    admin = User.objects.filter(is_staff=True, is_active=True).first()
                    if admin and admin.email and alerts_generated > 0 and not dry_run:
                        self._send_alert_email(tenant, parcel, admin)
                        emails_sent += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n{total_parcels} parcelas | {optical_ok} con optico | "
            f"{radar_fallback} con radar | {alerts_generated} alertas | "
            f"{emails_sent} emails"
            f"{' (DRY RUN)' if dry_run else ''}"
        ))

    def _try_get_optical_data(self, parcel, tenant=None):
        """Intentar obtener NDVI actual via EOSDA con filtro de nubes <30%."""
        try:
            from parcels.eosda_client import get_eosda_client
            client = get_eosda_client()
            eosda_key = getattr(settings, "EOSDA_API_KEY", "")
            if not eosda_key or not getattr(parcel, "eosda_id", None):
                return None

            base = "https://gate.eos.com/api/gdw/api"
            headers = {"X-Api-Key": eosda_key, "Content-Type": "application/json"}
            today = date.today().isoformat()
            week_ago = (date.today() - timedelta(days=7)).isoformat()

            # Buscar escenas con <30% nubes
            resp = client.post(
                f"{base}/search",
                {
                    "field_id": parcel.eosda_id,
                    "date_from": week_ago,
                    "date_to": today,
                    "max_cloud": 30,
                    "limit": 1,
                },
                headers=headers,
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                scenes = data.get("scenes", data.get("results", []))
                if scenes:
                    scene = scenes[0]
                    cloud_cover = scene.get("clouds", scene.get("cloud_cover", 0))
                    ndvi_val = scene.get("ndvi", scene.get("ndvi_mean"))
                    if ndvi_val is not None:
                        client.record(tenant, operation="analytics", parcel_id=parcel.pk)
                        return {"ndvi": ndvi_val, "cloud_cover": cloud_cover}
            return None
        except Exception:
            return None

    def _create_alert(self, parcel, alert, dry_run):
        """Crear evento de monitoreo en la DB."""
        if dry_run:
            self.stdout.write(f"  [DRY] {parcel.name}: {alert['title']}")
            return
        try:
            from parcels.models import MonitoringEvent
            MonitoringEvent.objects.create(
                parcel=parcel,
                event_type=alert["type"],
                title=alert["title"],
                description=alert["message"],
                metadata={"source": "monitor_crops"},
            )
        except Exception:
            pass

    def _send_alert_email(self, tenant, parcel, admin):
        """Enviar email de alerta al admin del tenant."""
        try:
            frontend = getattr(settings, "FRONTEND_URL", "http://localhost:8080")
            url = f"{frontend}/templates/parcels/parcels-dashboard.html"
            subject = f"[AgroTech] Alerta de monitoreo - {parcel.name}"

            html = f"""\
<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f7f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7f6;padding:40px 0">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 2px 20px rgba(0,0,0,0.08)">
<tr><td style="background:linear-gradient(135deg,#2FB344,#1a7a2e);padding:32px 40px;text-align:center">
  <h1 style="color:#fff;margin:0;font-size:22px;font-weight:800">Monitoreo de Cultivo</h1>
  <p style="color:#bbf7d0;margin:8px 0 0;font-size:14px">{tenant.name} — {parcel.name}</p>
</td></tr>
<tr><td style="padding:28px 32px">
  <p style="color:#374151;font-size:15px;line-height:1.6;margin:0 0 20px">
    Hola {admin.name}, el sistema de monitoreo continuo detecto actividad en tu parcela.
  </p>
  <div style="background:rgba(47,179,68,0.06);border-left:4px solid #2FB344;padding:14px 18px;border-radius:0 8px 8px 0;margin-bottom:20px">
    <p style="color:#1a7a2e;font-size:14px;margin:0">
      El radar Sentinel-1 vigila tus cultivos incluso cuando hay nubes.
      Revisa tu dashboard para ver los detalles.
    </p>
  </div>
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center">
    <a href="{url}" style="display:inline-block;background:#2FB344;color:#fff;text-decoration:none;padding:14px 40px;border-radius:10px;font-size:15px;font-weight:700">Ver Dashboard</a>
  </td></tr></table>
</td></tr>
<tr><td style="background:#f9fafb;padding:20px 40px;text-align:center">
  <p style="color:#9ca3af;font-size:12px;margin:0">&copy; 2026 AgroTech Digital. Monitoreo continuo automatico.</p>
</td></tr>
</table>
</td></tr>
</table>
</body></html>"""

            text = (
                f"MONITOREO CONTINUO — {tenant.name}\n\n"
                f"Parcela: {parcel.name}\n"
                f"El sistema detecto actividad. Revisa tu dashboard: {url}\n\n"
                f"AgroTech Digital"
            )

            email = EmailMultiAlternatives(
                subject=subject, body=text,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@agrotechcolombia.com"),
                to=[admin.email],
            )
            email.attach_alternative(html, "text/html")
            email.send(fail_silently=True)
            return True
        except Exception as e:
            logger.warning(f"Error enviando alerta: {e}")
            return False
