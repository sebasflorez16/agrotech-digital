"""
Comando para configurar una suscripción de desarrollo con límites altos.

Uso:
    python manage.py setup_dev_subscription
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import get_tenant_model, schema_context
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Configura una suscripción de desarrollo con límites altos para pruebas'

    def handle(self, *args, **options):
        from billing.models import Plan, Subscription
        from base_agrotech.models import Client
        from django.utils import timezone
        from datetime import timedelta
        
        self.stdout.write(self.style.NOTICE('🔧 Configurando suscripción de desarrollo...'))
        
        # 1. Crear o obtener plan de desarrollo con límites altos
        dev_plan, created = Plan.objects.update_or_create(
            tier='pro',
            defaults={
                'name': 'Plan Desarrollo (Ilimitado)',
                'description': 'Plan de desarrollo con límites muy altos para pruebas',
                'price_cop': 0,
                'price_usd': 0,
                'frequency': 1,
                'limits': {
                    'hectares': 999999,
                    'users': 999,
                    'eosda_requests': 99999,  # Límite muy alto para desarrollo
                    'parcels': 9999,
                    'storage_mb': 999999
                },
                'features_included': [
                    'ndvi',
                    'savi',
                    'ndmi',
                    'evi',
                    'weather_basic',
                    'weather_full',
                    'satellite_imagery',
                    'historical_data',
                    'export_reports',
                    'api_access',
                    'priority_support'
                ],
                'features_excluded': []
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Plan "{dev_plan.name}" creado'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Plan "{dev_plan.name}" actualizado'))
        
        # 2. Obtener todos los tenants (excepto public)
        tenants = Client.objects.exclude(schema_name='public')
        
        if not tenants.exists():
            self.stdout.write(self.style.WARNING('⚠️ No hay tenants configurados (excepto public)'))
            self.stdout.write(self.style.NOTICE('   Creando tenant de prueba "demo"...'))
            
            # Crear tenant demo si no existe
            demo_tenant, created = Client.objects.get_or_create(
                schema_name='demo',
                defaults={
                    'name': 'Demo Tenant',
                }
            )
            if created:
                # Crear el schema
                demo_tenant.save()
                self.stdout.write(self.style.SUCCESS('✅ Tenant "demo" creado'))
            tenants = Client.objects.filter(schema_name='demo')
        
        # 3. Crear suscripción para cada tenant
        for tenant in tenants:
            self.stdout.write(f'   Procesando tenant: {tenant.schema_name}')
            
            try:
                # Verificar si ya tiene suscripción
                existing_sub = Subscription.objects.filter(tenant=tenant).first()
                
                if existing_sub:
                    # Actualizar suscripción existente
                    existing_sub.plan = dev_plan
                    existing_sub.status = 'active'
                    existing_sub.current_period_end = timezone.now() + timedelta(days=365)
                    existing_sub.save()
                    self.stdout.write(self.style.SUCCESS(
                        f'   ✅ Suscripción actualizada para {tenant.schema_name}'
                    ))
                else:
                    # Crear nueva suscripción
                    Subscription.objects.create(
                        tenant=tenant,
                        plan=dev_plan,
                        status='active',
                        current_period_start=timezone.now(),
                        current_period_end=timezone.now() + timedelta(days=365),
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f'   ✅ Suscripción creada para {tenant.schema_name}'
                    ))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'   ❌ Error con tenant {tenant.schema_name}: {str(e)}'
                ))
        
        # 4. Resetear métricas de uso (opcional)
        try:
            from billing.models import UsageMetrics
            for tenant in tenants:
                with schema_context(tenant.schema_name):
                    metrics = UsageMetrics.objects.filter(tenant=tenant).first()
                    if metrics:
                        metrics.eosda_requests = 0
                        metrics.save()
                        self.stdout.write(f'   🔄 Métricas reseteadas para {tenant.schema_name}')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   ⚠️ No se pudieron resetear métricas: {e}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('🎉 Configuración de desarrollo completada'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write('')
        self.stdout.write('Límites configurados:')
        self.stdout.write(f'  • Hectáreas: 999,999')
        self.stdout.write(f'  • Requests EOSDA: 99,999/mes')
        self.stdout.write(f'  • Parcelas: 9,999')
        self.stdout.write(f'  • Usuarios: 999')
        self.stdout.write('')
        self.stdout.write('Ahora puedes reiniciar el servidor y las funciones satelitales funcionarán.')
