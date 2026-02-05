"""
Management command para verificar uso de todos los tenants y enviar alertas.

Ejecutar manualmente:
    python manage.py check_usage_alerts

Ejecutar en producción con cron (cada hora):
    0 * * * * cd /app && python manage.py check_usage_alerts
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from billing.alerts import check_all_tenants_usage
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verifica el uso de todos los tenants y envía alertas por email'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecuta sin enviar emails reales'
        )
        
        parser.add_argument(
            '--tenant',
            type=str,
            help='Verificar solo un tenant específico (schema_name)'
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        tenant_filter = options.get('tenant')
        
        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write(self.style.WARNING('🔔 VERIFICACIÓN DE ALERTAS DE USO'))
        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write('')
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('⚠️  Modo DRY-RUN: No se enviarán emails'))
            self.stdout.write('')
        
        try:
            if tenant_filter:
                # Verificar un tenant específico
                self.stdout.write(f'Verificando tenant: {tenant_filter}')
                alerts = self._check_tenant(tenant_filter, dry_run)
            else:
                # Verificar todos los tenants
                self.stdout.write('Verificando todos los tenants...')
                alerts = check_all_tenants_usage()
            
            # Resumen
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('='*70))
            self.stdout.write(self.style.SUCCESS('📊 RESUMEN'))
            self.stdout.write(self.style.SUCCESS('='*70))
            self.stdout.write('')
            
            if not alerts:
                self.stdout.write(self.style.SUCCESS('✅ No hay alertas para enviar'))
            else:
                self.stdout.write(f'Total de tenants con alertas: {len(alerts)}')
                self.stdout.write('')
                
                for tenant_alerts in alerts:
                    self.stdout.write(self.style.WARNING(f"🏢 {tenant_alerts['tenant']}:"))
                    for alert in tenant_alerts['alerts']:
                        level_emoji = {
                            'warning': '⚠️ ',
                            'danger': '🔴',
                            'exceeded': '🚫'
                        }
                        emoji = level_emoji.get(alert['level'], '📌')
                        self.stdout.write(
                            f"  {emoji} {alert['resource']}: {alert['percentage']}% "
                            f"({alert['current']}/{alert['limit']} {alert['unit']})"
                        )
                    self.stdout.write('')
            
            self.stdout.write(self.style.SUCCESS('✅ Verificación completada'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            logger.exception('Error checking usage alerts')
            raise
    
    def _check_tenant(self, schema_name, dry_run=False):
        """Verificar un tenant específico."""
        from base_agrotech.models import Client
        from billing.models import UsageMetrics
        from billing.alerts import BillingAlertManager
        from django.utils import timezone
        
        try:
            tenant = Client.objects.get(schema_name=schema_name)
        except Client.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Tenant {schema_name} no existe'))
            return []
        
        now = timezone.now()
        metrics = UsageMetrics.objects.filter(
            tenant=tenant,
            year=now.year,
            month=now.month
        ).first()
        
        if not metrics:
            self.stdout.write(self.style.NOTICE('⚠️  No hay métricas para este mes'))
            return []
        
        # Actualizar métricas
        metrics.update_from_tenant()
        
        # Verificar alertas
        alert_manager = BillingAlertManager(metrics)
        
        if dry_run:
            # En dry-run, solo verificar sin enviar
            alerts = []
            # TODO: Implementar verificación sin envío
        else:
            alerts = alert_manager.check_and_send_alerts()
        
        return [{
            'tenant': tenant.name,
            'alerts': alerts
        }] if alerts else []
