"""
Management command para crear planes iniciales de suscripción.

Uso:
    python manage.py create_billing_plans

Planes (pricing validado con costos reales EOSDA — RESUMEN_EJECUTIVO_PRICING.md):
    - Explorador (Gratis): 50ha, 20 análisis/mes, solo NDVI, sin clima. Embudo.
    - Agricultor ($79.000/mes): 300ha, 100 análisis/mes, NDVI+NDMI+SAVI, clima básico.
    - Empresarial ($179.000/mes): 1.000ha, 500 análisis/mes, todos los índices, monitoreo continuo.
    - Corporativo ($600.000+/mes): límites superiores y soporte dedicado.
"""

from django.core.management.base import BaseCommand
from billing.models import Plan


class Command(BaseCommand):
    help = 'Crea los planes iniciales de suscripción para AgroTech Digital'

    def handle(self, *args, **options):
        """Crear planes iniciales."""

        plans_data = [
            {
                'tier': 'free',
                'name': 'Explorador',
                'description': 'Gratis para siempre. Ideal para conocer la plataforma con NDVI básico en parcelas pequeñas.',
                'price_cop': 0,
                'price_usd': 0,
                'frequency': 1,
                'limits': {
                    'hectares': 50,
                    'users': 1,
                    'eosda_requests': 20,
                    'parcels': 5,
                    'storage_mb': 100,
                },
                'features_included': [
                    'ndvi',
                ],
                'features_excluded': [
                    'ndmi',
                    'evi',
                    'savi',
                    'weather_basic',
                    'weather_full',
                    'continuous_monitoring',
                    'pdf_reports',
                    'advanced_analytics',
                    'api_access',
                    'historical',
                ],
                'is_active': True,
                'trial_days': 0,  # Free es permanente, no trial
                'sort_order': 1,
            },
            {
                'tier': 'basic',
                'name': 'Agricultor',
                'description': 'Para agricultores profesionales. NDVI + NDMI (estrés hídrico) con pronóstico climático.',
                'price_cop': 79000,
                'price_usd': 20,
                'frequency': 1,
                'limits': {
                    'hectares': 100,
                    'users': 2,
                    'eosda_requests': 100,
                    'parcels': 10,
                    'storage_mb': 500,
                },
                'features_included': [
                    'ndvi',
                    'ndmi',
                    'savi',
                    'weather_basic',
                    'historical',
                ],
                'features_excluded': [
                    'evi',
                    'weather_full',
                    'continuous_monitoring',
                    'pdf_reports',
                    'advanced_analytics',
                    'api_access',
                ],
                'is_active': True,
                'trial_days': 14,
                'sort_order': 2,
            },
            {
                'tier': 'pro',
                'name': 'Empresarial',
                'description': 'Para empresas agrícolas. Todos los índices, monitoreo continuo de salud del cultivo y reportes PDF.',
                'price_cop': 179000,
                'price_usd': 45,
                'frequency': 1,
                'limits': {
                    'hectares': 300,
                    'users': 3,
                    'eosda_requests': 500,
                    'parcels': 50,
                    'storage_mb': 2000,
                },
                'features_included': [
                    'ndvi',
                    'ndmi',
                    'evi',
                    'savi',
                    'weather_full',
                    'continuous_monitoring',
                    'pdf_reports',
                    'advanced_analytics',
                    'api_access',
                    'historical',
                ],
                'features_excluded': [],
                'is_active': True,
                'trial_days': 14,
                'sort_order': 3,
            },
            {
                'tier': 'enterprise',
                'name': 'Corporativo',
                'description': 'Para corporaciones y agronegocios. Todo ilimitado con soporte dedicado y onboarding asistido.',
                'price_cop': 600000,
                'price_usd': 150,
                'frequency': 1,
                'limits': {
                    'hectares': 99999,
                    'users': 10,
                    'eosda_requests': 99999,
                    'parcels': 9999,
                    'storage_mb': 99999,
                },
                'features_included': [
                    'ndvi',
                    'ndmi',
                    'evi',
                    'savi',
                    'weather_full',
                    'continuous_monitoring',
                    'pdf_reports',
                    'advanced_analytics',
                    'api_access',
                    'historical',
                    'support_priority',
                    'dedicated_account',
                ],
                'features_excluded': [],
                'is_active': False,
                'is_custom': True,
                'trial_days': 0,
                'sort_order': 4,
            },
        ]

        created_count = 0
        updated_count = 0

        for plan_data in plans_data:
            plan, created = Plan.objects.update_or_create(
                tier=plan_data['tier'],
                defaults={k: v for k, v in plan_data.items() if k != 'tier'},
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Plan "{plan.name}" creado')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'→ Plan "{plan.name}" actualizado')
                )

        # Desactivar planes que no sean free/basic/pro/enterprise
        valid_tiers = ['free', 'basic', 'pro', 'enterprise']
        deactivated = Plan.objects.exclude(tier__in=valid_tiers).filter(is_active=True).update(is_active=False)
        if deactivated:
            self.stdout.write(self.style.WARNING(f'⚠️  {deactivated} plan(es) antiguo(s) desactivado(s)'))

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Proceso completado: {created_count} creados, {updated_count} actualizados'
            )
        )

        # Mostrar resumen
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('PLANES ACTIVOS:')
        self.stdout.write('=' * 80)

        for plan in Plan.objects.filter(is_active=True).order_by('sort_order'):
            self.stdout.write(
                f"  {plan.tier:10} | {plan.name:15} | "
                f"COP ${plan.price_cop:>10,.0f} | "
                f"{plan.limits.get('hectares')}ha | "
                f"{plan.limits.get('eosda_requests')} req/mes | "
                f"{plan.limits.get('users')} users | "
                f"{plan.limits.get('parcels')} parcelas"
            )

        self.stdout.write('=' * 80)
        self.stdout.write('\n💡 FREE = embudo permanente (NDVI básico, 20 análisis/mes).')
        self.stdout.write('💰 COSTOS EOSDA: Plan Innovator $125/mes (20,000 requests)')
        self.stdout.write('🎯 BREAK-EVEN: ~15-18 clientes pagos (mes 3-4)')
        self.stdout.write('=' * 80 + '\n')
