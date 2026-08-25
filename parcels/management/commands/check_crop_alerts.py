"""
Comando de alertas agronomicas automaticas.
Ejecutar diariamente via cron o Railway scheduler:

    python manage.py check_crop_alerts

Verifica todas las parcelas activas con CropHealthStatus (por schema de tenant)
y genera alertas: NDVI critico, estres hidrico, sin observacion reciente.
Envia email al admin de cada tenant si hay alertas activas.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import schema_context

from base_agrotech.models import Client
from parcels.models import CropHealthStatus, MonitoringEvent, Parcel

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Verifica salud de cultivos por tenant y envia alertas por email."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Solo diagnosticar, no enviar emails")
        parser.add_argument("--parcel-id", type=int, help="Verificar solo una parcela especifica")
        parser.add_argument("--tenant", type=str, help="Verificar solo un tenant (schema_name)")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        parcel_id = options.get("parcel_id")
        tenant_filter = options.get("tenant")

        tenants = Client.objects.exclude(schema_name="public").order_by("schema_name")
        if tenant_filter:
            tenants = tenants.filter(schema_name=tenant_filter)

        if not tenants.exists():
            self.stdout.write(self.style.WARNING("No hay tenants registrados."))
            return

        total_checked = 0
        total_alerts = 0
        emails_sent = 0

        for tenant in tenants:
            with schema_context(tenant.schema_name):
                parcels_qs = Parcel.objects.filter(is_deleted=False)
                if parcel_id:
                    parcels_qs = parcels_qs.filter(pk=parcel_id)

                for parcel in parcels_qs:
                    health = None
                    try:
                        health = CropHealthStatus.objects.filter(parcel=parcel).first()
                    except Exception:
                        continue

                    if not health or health.ndvi_last is None:
                        continue

                    total_checked += 1
                    ndvi = health.ndvi_last
                    ndmi = health.ndmi_last
                    days = health.days_without_observation or 0
                    alerts = []

                    if ndvi < 0.3:
                        alerts.append({
                            "type": "ndvi_critical", "severity": "critical",
                            "title": f"NDVI critico en {parcel.name}",
                            "message": f"NDVI={ndvi:.2f} — muy por debajo de lo esperado. Inspecciona en campo.",
                        })
                    elif ndvi < 0.5:
                        alerts.append({
                            "type": "ndvi_low", "severity": "warning",
                            "title": f"NDVI bajo en {parcel.name}",
                            "message": f"NDVI={ndvi:.2f}. El cultivo podria estar bajo estres.",
                        })
                    if ndmi is not None and ndmi < 0.2:
                        alerts.append({
                            "type": "water_stress", "severity": "warning",
                            "title": f"Estres hidrico en {parcel.name}",
                            "message": f"NDMI={ndmi:.2f} — posible deficit de agua.",
                        })
                    if days > 14:
                        alerts.append({
                            "type": "no_observation", "severity": "info",
                            "title": f"Sin observacion reciente en {parcel.name}",
                            "message": f"{days} dias sin imagen utilizable.",
                        })

                    if not alerts:
                        continue

                    total_alerts += len(alerts)

                    for alert in alerts:
                        MonitoringEvent.objects.create(
                            parcel=parcel,
                            tenant_id=getattr(parcel, "tenant_id", None),
                            event_type=alert["type"],
                            title=alert["title"],
                            description=alert["message"],
                            metadata={"severity": alert["severity"]},
                        )

                    owner = tenant.owner if hasattr(tenant, "owner") else None
                    if not dry_run and owner and owner.email:
                        sent = self._send_alert_email(parcel, alerts, owner)
                        if sent:
                            emails_sent += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"  {tenant.schema_name}/{parcel.name}: {len(alerts)} alerta(s) "
                            f"NDVI={ndvi:.2f}"
                        )
                    )

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ {total_checked} parcelas, {total_alerts} alertas, {emails_sent} emails"
            f"{' (DRY RUN)' if dry_run else ''}"
        ))

    def _send_alert_email(self, parcel, alerts, owner):
        try:
            alert_lines = "\n".join(f"• {a['title']}: {a['message']}" for a in alerts)
            subject = f"[AgroTech] {len(alerts)} alerta(s) en {parcel.name}"
            body = (
                f"Hola {owner.name},\n\n"
                f"Alertas en '{parcel.name}':\n\n{alert_lines}\n\n"
                f"Dashboard: {getattr(settings, 'SITE_URL', 'https://agrotechcolombia.com')}\n\n"
                f"AgroTech Digital"
            )
            send_mail(
                subject=subject, message=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "contacto@agrotechcolombia.com"),
                recipient_list=[owner.email], fail_silently=True,
            )
            return True
        except Exception as e:
            logger.warning(f"No se pudo enviar alerta: {e}")
            return False
