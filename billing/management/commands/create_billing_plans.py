"""
Management command para crear planes iniciales de suscripción.

NOTA: Este comando es equivalente a seed_plans.py. Se mantiene por compatibilidad.

Uso:
    python manage.py create_billing_plans

Planes:
    - Explorador (Gratis): 20ha, 15 análisis/mes, solo NDVI, sin clima
    - Agricultor ($89.000/mes): 100ha, 60 análisis/mes, NDVI+SAVI, clima básico
    - Empresarial ($259.000/mes): 500ha, 300 análisis/mes, todos los índices, clima completo
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
                'description': 'Ideal para conocer la plataforma. Monitoreo NDVI básico para parcelas pequeñas.',
                'price_cop': 0,
                'price_usd': 0,
                'frequency': 1,
                'limits': {
                    'hectares': 20,
                    'users': 1,
                    'eosda_requests': 15,
                    'parcels': 2,
                    'storage_mb': 100,
                },
                'features_included': [
                    'ndvi',
                ],
                'features_excluded': [
                    'savi',
                    'ndmi',
                    'evi',
                    'weather_basic',
                    'weather_full',
                ],
                'is_active': True,
                'trial_days': 14,
                'sort_order': 1,
            },
            {
                'tier': 'basic',
                'name': 'Agricultor',
                'description': 'Para agricultores profesionales. NDVI + SAVI con pronóstico climático básico.',
                'price_cop': 89000,
                'price_usd': 21,
                'frequency': 1,
                'limits': {
                    'hectares': 100,
                    'users': 3,
                    'eosda_requests': 60,
                    'parcels': 5,
                    'storage_mb': 500,
                },
                'features_included': [
                    'ndvi',
                    'savi',
                    'weather_basic',
                ],
                'features_excluded': [
                    'ndmi',
                    'evi',
                    'weather_full',
                ],
                'is_active': True,
                'trial_days': 14,
                'sort_order': 2,
            },
            {
                'tier': 'pro',
                'name': 'Empresarial',
                'description': 'Para empresas agrícolas. Todos los índices satelitales con clima completo.',
                'price_cop': 259000,
                'price_usd': 62,
                'frequency': 1,
                'limits': {
                    'hectares': 500,
                    'users': 5,
                    'eosda_requests': 300,
                    'parcels': 20,
                    'storage_mb': 2000,
                },
                'features_included': [
                    'ndvi',
                    'savi',
                    'ndmi',
                    'evi',
                    'weather_full',
                ],
                'features_excluded': [],
                'is_active': True,
                'trial_days': 14,
                'sort_order': 3,
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
        
        # Desactivar planes que no sean free/basic/pro
        valid_tiers = ['free', 'basic', 'pro']
        deactivated = Plan.objects.exclude(tier__in=valid_tiers).filter(is_active=True).update(is_active=False)
        if deactivated:
            self.stdout.write(self.style.WARNING(f'⚠️  {deactivated} plan(es) antiguo(s) desactivado(s)'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Proceso completado: {created_count} creados, {updated_count} actualizados'
            )
        )
        
        # Mostrar resumen
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('PLANES ACTIVOS:')
        self.stdout.write('=' * 70)
        
        for plan in Plan.objects.filter(is_active=True).order_by('sort_order'):
            self.stdout.write(
                f"  {plan.tier:8} | {plan.name:15} | "
                f"COP ${plan.price_cop:>10,.0f} | "
                f"{plan.limits.get('hectares')}ha | "
                f"{plan.limits.get('eosda_requests')} req/mes | "
                f"{plan.limits.get('users')} users | "
                f"{plan.limits.get('parcels')} parcelas"
            )
        
        self.stdout.write('=' * 70)
        self.stdout.write('\n💡 NOTA: Usuarios limitados a máximo 3 en todos los planes.')
        self.stdout.write('💰 COSTOS EOSDA: Plan Innovator $125/mes (20,000 requests)')
        self.stdout.write('🎯 BREAK-EVEN: ~15-18 clientes pagos (mes 3-4)')
        self.stdout.write('=' * 80 + '\n')
