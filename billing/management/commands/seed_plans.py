"""
Management command para crear los planes iniciales de suscripción.

Uso:
    python manage.py seed_plans
"""
from django.core.management.base import BaseCommand
from billing.models import Plan


class Command(BaseCommand):
    help = 'Crear planes de suscripción iniciales (free, basic, pro)'

    def handle(self, *args, **options):
        plans = [
            {
                'tier': 'free',
                'name': 'Explorador',
                'description': 'Ideal para conocer la plataforma. Incluye monitoreo básico y acceso limitado.',
                'price_cop': 0,
                'price_usd': 0,
                'frequency': 1,
                'trial_days': 14,
                'sort_order': 1,
                'limits': {
                    'hectares': 50,
                    'users': 1,
                    'eosda_requests': 20,
                    'parcels': 3,
                    'storage_mb': 100,
                },
                'features_included': [
                    'Monitoreo satelital básico',
                    'NDVI en tiempo real',
                    'Dashboard simplificado',
                    'Soporte por email',
                ],
                'features_excluded': [
                    'Análisis histórico',
                    'Alertas automáticas',
                    'Reportes PDF',
                    'API access',
                    'Soporte prioritario',
                ],
            },
            {
                'tier': 'basic',
                'name': 'Agricultor',
                'description': 'Para agricultores profesionales. Monitoreo completo con análisis avanzado.',
                'price_cop': 79000,
                'price_usd': 19,
                'frequency': 1,
                'trial_days': 0,
                'sort_order': 2,
                'limits': {
                    'hectares': 300,
                    'users': 3,
                    'eosda_requests': 100,
                    'parcels': 10,
                    'storage_mb': 500,
                },
                'features_included': [
                    'Todo del plan Explorador',
                    'Análisis histórico completo',
                    'Alertas automáticas',
                    'Reportes PDF',
                    'Gestión de labores',
                    'Inventario básico',
                ],
                'features_excluded': [
                    'API access',
                    'Soporte prioritario',
                    'Usuarios ilimitados',
                ],
            },
            {
                'tier': 'pro',
                'name': 'Empresarial',
                'description': 'Para empresas agrícolas. Todo incluido con soporte premium y API.',
                'price_cop': 179000,
                'price_usd': 45,
                'frequency': 1,
                'trial_days': 0,
                'sort_order': 3,
                'limits': {
                    'hectares': 1000,
                    'users': 10,
                    'eosda_requests': 500,
                    'parcels': 50,
                    'storage_mb': 2000,
                },
                'features_included': [
                    'Todo del plan Agricultor',
                    'API access completo',
                    'Soporte prioritario 24/7',
                    'Usuarios ilimitados',
                    'Reportes personalizados',
                    'Integración con ERPs',
                    'Dashboard multi-finca',
                ],
                'features_excluded': [],
            },
            {
                'tier': 'enterprise',
                'name': 'Corporativo',
                'description': 'Para corporaciones agrícolas con múltiples fincas. Soporte dedicado y personalización completa.',
                'price_cop': 350000,
                'price_usd': 89,
                'frequency': 1,
                'trial_days': 0,
                'sort_order': 4,
                'limits': {
                    'hectares': 9999,
                    'users': 50,
                    'eosda_requests': 2000,
                    'parcels': 200,
                    'storage_mb': 10000,
                },
                'features_included': [
                    'Todo del plan Empresarial',
                    'Hectares ilimitadas',
                    'Hasta 50 usuarios',
                    'Account manager dedicado',
                    'SLA de respuesta 4 horas',
                    'Capacitación y onboarding',
                    'Reportes personalizados avanzados',
                    'Integraciones a medida',
                ],
                'features_excluded': [],
            },
        ]

        created = 0
        updated = 0
        for plan_data in plans:
            tier = plan_data.pop('tier')
            obj, was_created = Plan.objects.update_or_create(
                tier=tier,
                defaults=plan_data,
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  ✅ Creado: {obj.name} ({tier})'))
            else:
                updated += 1
                self.stdout.write(self.style.WARNING(f'  🔄 Actualizado: {obj.name} ({tier})'))

        self.stdout.write(self.style.SUCCESS(
            f'\n📋 Resumen: {created} creados, {updated} actualizados'
        ))
