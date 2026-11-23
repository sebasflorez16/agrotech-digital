"""
Management command: run_daily_jobs

Tareas diarias de la plataforma (para el cron de Railway):

1. Mantenimiento de suscripciones (trials vencidos, pagos vencidos).
2. Detección de alertas agronómicas con índices Sentinel-2 reales.

Uso:
    python manage.py run_daily_jobs
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ejecuta tareas diarias: mantenimiento de suscripciones + alertas agronómicas."

    def handle(self, *args, **opts):
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n== Mantenimiento de suscripciones =="
        ))
        call_command("run_billing_maintenance")

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n== Alertas agronómicas (Sentinel-2) =="
        ))
        # Sin correo por ahora: las alertas se muestran en el dashboard.
        call_command("detectar_alertas", "--no-notify")

        self.stdout.write(self.style.SUCCESS("\n✓ Tareas diarias completadas"))
