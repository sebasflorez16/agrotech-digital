"""
Comando de alertas de inventario automaticas.
Ejecutar diariamente via cron o Railway scheduler:

    python manage.py check_inventory_alerts

Verifica todos los insumos por tenant, detecta stock bajo y envia email HTML al admin.
"""

import logging
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

from base_agrotech.models import Client
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Verifica stock bajo de insumos por tenant y envia alertas por email."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Solo diagnosticar, no enviar emails")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        tenants = Client.objects.exclude(schema_name="public").order_by("schema_name")
        if not tenants.exists():
            self.stdout.write(self.style.WARNING("No hay tenants registrados."))
            return

        total_alerts = 0
        emails_sent = 0

        for tenant in tenants:
            with schema_context(tenant.schema_name):
                from inventario.models import Supply, Warehouse

                low_stock_supplies = []
                for supply in Supply.objects.select_related("warehouse").all():
                    qty = float(supply.quantity or 0)
                    min_stock = float(supply.minimum_stock or 5)
                    if qty <= min_stock:
                        low_stock_supplies.append({
                            "name": supply.name,
                            "quantity": qty,
                            "minimum_stock": min_stock,
                            "unit": supply.unit or "unidades",
                            "warehouse": supply.warehouse.name if supply.warehouse else "Sin almacen",
                            "status": "critico" if qty == 0 else "bajo",
                        })

                if not low_stock_supplies:
                    continue

                total_alerts += len(low_stock_supplies)

                admin_users = User.objects.filter(is_staff=True, is_active=True)
                if not dry_run and admin_users.exists():
                    for admin in admin_users:
                        if admin.email:
                            self._send_alert_email(tenant, low_stock_supplies, admin)
                            emails_sent += 1

                self.stdout.write(
                    self.style.WARNING(
                        f"  {tenant.schema_name}: {len(low_stock_supplies)} insumo(s) con stock bajo"
                    )
                )

        self.stdout.write(self.style.SUCCESS(
            f"\n{total_alerts} insumos con stock bajo detectados, {emails_sent} emails enviados"
            f"{' (DRY RUN)' if dry_run else ''}"
        ))

    def _send_alert_email(self, tenant, supplies, admin):
        try:
            site_url = getattr(settings, "FRONTEND_URL", "http://localhost:8080")
            inventory_url = f"{site_url}/templates/inventory/inventario-dashboard.html"

            rows = ""
            for s in supplies:
                color = "#DC2626" if s["status"] == "critico" else "#F59E0B"
                emoji = "🔴" if s["status"] == "critico" else "🟡"
                rows += f"""
                <tr>
                    <td style="padding:12px 14px;border-bottom:1px solid rgba(0,0,0,0.04)">{emoji}</td>
                    <td style="padding:12px 14px;border-bottom:1px solid rgba(0,0,0,0.04)"><strong>{s["name"]}</strong></td>
                    <td style="padding:12px 14px;border-bottom:1px solid rgba(0,0,0,0.04);color:{color};font-weight:700">{s["quantity"]} {s["unit"]}</td>
                    <td style="padding:12px 14px;border-bottom:1px solid rgba(0,0,0,0.04)">{s["minimum_stock"]} {s["unit"]}</td>
                    <td style="padding:12px 14px;border-bottom:1px solid rgba(0,0,0,0.04)">{s["warehouse"]}</td>
                </tr>"""

            subject = f"[AgroTech] {len(supplies)} insumo(s) con stock bajo en {tenant.name}"
            html = f"""\
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f7f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7f6;padding:40px 0">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 2px 20px rgba(0,0,0,0.08)">
<tr><td style="background:linear-gradient(135deg,#dc2626,#b91c1c);padding:32px 40px;text-align:center">
  <h1 style="color:#fff;margin:0;font-size:22px;font-weight:800">Alerta de Stock Bajo</h1>
  <p style="color:#fecaca;margin:8px 0 0;font-size:14px">{tenant.name} — {len(supplies)} insumo(s) necesitan atencion</p>
</td></tr>
<tr><td style="padding:28px 32px">
  <p style="color:#374151;font-size:15px;line-height:1.6;margin:0 0 20px">
    Hola {admin.name}, los siguientes insumos estan por debajo de su nivel minimo de stock:
  </p>
  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:24px">
    <thead>
      <tr style="background:rgba(220,38,38,0.06)">
        <th style="padding:12px 14px;text-align:left;font-size:11px;text-transform:uppercase;color:#dc2626;border-bottom:2px solid rgba(220,38,38,0.15)"></th>
        <th style="padding:12px 14px;text-align:left;font-size:11px;text-transform:uppercase;color:#dc2626;border-bottom:2px solid rgba(220,38,38,0.15)">Insumo</th>
        <th style="padding:12px 14px;text-align:left;font-size:11px;text-transform:uppercase;color:#dc2626;border-bottom:2px solid rgba(220,38,38,0.15)">Stock Actual</th>
        <th style="padding:12px 14px;text-align:left;font-size:11px;text-transform:uppercase;color:#dc2626;border-bottom:2px solid rgba(220,38,38,0.15)">Minimo</th>
        <th style="padding:12px 14px;text-align:left;font-size:11px;text-transform:uppercase;color:#dc2626;border-bottom:2px solid rgba(220,38,38,0.15)">Almacen</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center">
    <a href="{inventory_url}" style="display:inline-block;background:#dc2626;color:#fff;text-decoration:none;padding:14px 40px;border-radius:10px;font-size:15px;font-weight:700">Gestionar Inventario</a>
  </td></tr></table>
</td></tr>
<tr><td style="background:#f9fafb;padding:20px 40px;text-align:center">
  <p style="color:#9ca3af;font-size:12px;margin:0">&copy; 2026 AgroTech Digital. Alerta automatica de inventario.</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""

            text = f"ALERTA STOCK BAJO — {tenant.name}\n\n"
            for s in supplies:
                text += f"• {s['name']}: {s['quantity']} {s['unit']} (min: {s['minimum_stock']}) — {s['warehouse']}\n"
            text += f"\nGestionar: {inventory_url}"

            email = EmailMultiAlternatives(
                subject=subject,
                body=text,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@agrotechcolombia.com"),
                to=[admin.email],
            )
            email.attach_alternative(html, "text/html")
            email.send(fail_silently=True)
            logger.info(f"Alerta inventario enviada a {admin.email} ({len(supplies)} insumos)")
            return True
        except Exception as e:
            logger.warning(f"No se pudo enviar alerta de inventario: {e}")
            return False
