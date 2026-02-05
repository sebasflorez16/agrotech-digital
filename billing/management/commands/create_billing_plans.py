"""
Management command para crear planes iniciales de suscripción.

Uso:
    python manage.py create_billing_plans
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
                'description': 'Plan gratuito para probar AgroTech Digital. Perfecto para parcelas pequeñas.',
                'price_cop': 0,
                'price_usd': 0,
                'frequency': 1,
                'limits': {
                    'hectares': 50,
                    'users': 1,
                    'eosda_requests': 20,
                    'parcels': 3,
                    'storage_mb': 100,
                    'historical_months': 3
                },
                'features_included': [
                    'Análisis NDVI básico',
                    'Clima actual',
                    'Mapa base satelital',
                    'Gestión de parcelas',
                    'Registro de labores básico'
                ],
                'features_excluded': [
                    'NDMI, EVI, SAVI',
                    'Históricos extensos',
                    'Reportes PDF',
                    'API access',
                    'Soporte prioritario'
                ],
                'is_active': True,
                'trial_days': 14,
                'sort_order': 1
            },
            {
                'tier': 'basic',
                'name': 'Agricultor',
                'description': 'Plan para agricultores profesionales con parcelas medianas. Incluye análisis avanzados.',
                'price_cop': 79000,  # Ajustado según costos reales EOSDA
                'price_usd': 20,
                'frequency': 1,
                'limits': {
                    'hectares': 300,
                    'users': 2,  # Máximo 2 usuarios
                    'eosda_requests': 100,
                    'parcels': 10,
                    'storage_mb': 500,
                    'historical_months': 12
                },
                'features_included': [
                    'Todos los índices (NDVI, NDMI, EVI)',
                    'Pronóstico 7 días',
                    'Alertas por correo',
                    'Exportar datos CSV',
                    'Histórico 12 meses',
                    'Soporte email 24h',
                    '2 usuarios simultáneos'
                ],
                'features_excluded': [
                    'API REST',
                    'Reportes automatizados',
                    'Integraciones',
                    'Dashboard personalizado',
                    'Pronóstico 14 días'
                ],
                'is_active': True,
                'trial_days': 14,
                'sort_order': 2
            },
            {
                'tier': 'pro',
                'name': 'Empresarial',
                'description': 'Plan profesional para agroempresas y cooperativas. Análisis ilimitados y API completa.',
                'price_cop': 179000,  # Ajustado según costos reales EOSDA
                'price_usd': 45,
                'frequency': 1,
                'limits': {
                    'hectares': 1000,
                    'users': 3,  # Máximo 3 usuarios
                    'eosda_requests': 500,
                    'parcels': 50,
                    'storage_mb': 2000,
                    'historical_months': 36
                },
                'features_included': [
                    'API REST limitada (100 req/día)',
                    'Reportes PDF automatizados',
                    'Integración Zapier/Webhooks',
                    'Análisis multi-espectral',
                    'Dashboard personalizado',
                    'Histórico 36 meses',
                    'Soporte prioritario 12h',
                    'Exportación avanzada',
                    '3 usuarios simultáneos',
                    'Pronóstico clima 14 días',
                    'Alertas personalizadas'
                ],
                'features_excluded': [
                    'API ilimitada',
                    'Servidor dedicado',
                    'SLA 99.9%',
                    'Soporte 24/7',
                    'Capacitación on-site',
                    'White-label'
                ],
                'is_active': True,
                'trial_days': 14,
                'sort_order': 3
            },600000,  # Precio base mínimo
                'price_usd': 150,
                'frequency': 1,
                'limits': {
                    'hectares': 'unlimited',
                    'users': 3,  # Máximo 3 usuarios (no unlimited)
                    'eosda_requests': 'custom',  # Custom según contrato
                    'parcels': 'unlimited',
                    'storage_mb': 'unlimited',
                    'historical_months': 'unlimited'
                },
                'features_included': [
                    'Todo en Pro +',
                    'API completa ilimitada',
                    'Servidor dedicado',
                    'SLA 99.9%',
                    'Capacitación on-site',
                    'Integración ERP custom',
                    'Soporte 24/7',
                    'Account manager dedicado',
                    'Análisis personalizados',
                    'Hasta 3 usuarios',
                    'Requests EOSDA personalizados',
                    'White-label (opcional)'
                ],
                'features_excluded': [],
                'is_active': True,
                'is_custom': True,
                'trial_days': 30,
                'sort_order': 4,
                'notes': 'Precio según volumen de hectáreas y requests. Mínimo $600,000 COP/mes.'
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for plan_data in plans_data:
            plan, created = Plan.objects.update_or_create(
                tier=plan_data['tier'],
                defaults=plan_data
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
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Proceso completado: {created_count} creados, {updated_count} actualizados'
            )
        )
        
        # Mostrar resumen
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('PLANES CONFIGURADOS (Precios ajustados según costos reales EOSDA):')
        self.stdout.write('=' * 80)
        
        for plan in Plan.objects.all().order_by('sort_order'):
            users_limit = plan.limits.get('users', 'N/A')
            self.stdout.write(
                f"\n{plan.tier.upper():12} | {plan.name:15} | "
                f"COP ${plan.price_cop:>10,.0f} | USD ${plan.price_usd:>6.2f} | "
                f"Usuarios: {users_limit}"
            )
            self.stdout.write(f"             Límites: {plan.limits}")
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('\n💡 NOTA: Usuarios limitados a máximo 3 en todos los planes.')
        self.stdout.write('💰 COSTOS EOSDA: Plan Innovator $125/mes (20,000 requests)')
        self.stdout.write('🎯 BREAK-EVEN: ~15-18 clientes pagos (mes 3-4)')
        self.stdout.write('=' * 80 + '\n')
