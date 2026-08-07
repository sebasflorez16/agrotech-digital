"""
Management command para crear los planes iniciales de suscripción.
Redirige a create_billing_plans (comando canónico con pricing unificado).

Uso:
    python manage.py seed_plans
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crear planes de suscripción iniciales (delega en create_billing_plans)'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Sembrando planes de suscripción (unificado)...')
        call_command('create_billing_plans', *args, **options)
        self.stdout.write(self.style.SUCCESS('✅ Planes creados/actualizados.'))
