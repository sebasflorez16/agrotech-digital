"""Ejecuta las tareas periódicas de billing en un solo comando.

Pensado para un cron de Railway (o un worker) que corra cada hora/día:

    python manage.py run_billing_maintenance

Cada tarea es independiente: si una falla, las demás siguen y el comando
termina con código 1 para que el cron quede marcado como fallido.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Ejecuta renovaciones, dunning, recordatorios y alertas de uso.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip',
            nargs='*',
            default=[],
            help='Comandos a omitir: check_subscriptions charge_recurring renewal_reminders check_usage_alerts',
        )

    def handle(self, *args, **options):
        tasks = [
            'check_subscriptions',
            'charge_recurring',
            'renewal_reminders',
            'check_usage_alerts',
        ]
        skip = set(options.get('skip') or [])
        failures = []

        for task in tasks:
            if task in skip:
                self.stdout.write(self.style.WARNING(f'⏭️  {task} omitido'))
                continue
            self.stdout.write(f'▶️  {task}...')
            try:
                call_command(task, verbosity=options.get('verbosity', 1))
            except Exception as exc:
                failures.append(task)
                self.stderr.write(self.style.ERROR(f'❌ {task} falló: {exc}'))

        if failures:
            self.stderr.write(self.style.ERROR(
                f'Terminaron con error: {", ".join(failures)}'
            ))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS('✅ Mantenimiento de billing completado'))
