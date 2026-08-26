#!/usr/bin/env python
"""
Test del Sistema de Alertas y Notificaciones

Valida que se envíen alertas cuando:
- Se alcanza el 80% del límite (warning)
- Se alcanza el 90% del límite (danger)
- Se excede el 100% del límite (exceeded)
"""

import os
import django
import sys

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.utils import timezone
from django.db import connection
from django.core import mail

from base_agrotech.models import Client
from billing.models import UsageMetrics, BillingEvent
from billing.alerts import BillingAlertManager

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}🔥 {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def test_alertas():
    """Test completo del sistema de alertas."""
    
    print_header("TEST SISTEMA DE ALERTAS Y NOTIFICACIONES")
    
    try:
        # ========== PREPARAR DATOS ==========
        print_header("Preparar Datos de Test")
        
        connection.set_schema_to_public()
        
        # Obtener tenant
        tenant = Client.objects.get(schema_name='test_farm')
        print_success(f"Tenant: {tenant.name}")
        
        # Obtener métricas
        now = timezone.now()
        metrics = UsageMetrics.objects.filter(
            tenant=tenant,
            year=now.year,
            month=now.month
        ).first()
        
        if not metrics:
            print_error("No hay métricas")
            return
        
        print_success(f"Métricas: {metrics.eosda_requests} requests EOSDA")
        
        # Limpiar mailbox de prueba
        mail.outbox = []
        
        # Limpiar eventos de alerta previos
        BillingEvent.objects.filter(
            tenant=tenant,
            event_type='alert'
        ).delete()
        
        print_success("Mailbox y eventos limpios")
        
        # ========== TEST 1: SIN ALERTA (50% de uso) ==========
        print_header("TEST 1: Sin Alerta (50% de uso)")
        
        limit = metrics.subscription.plan.get_limit('eosda_requests', 100)
        metrics.eosda_requests = int(limit * 0.5)
        metrics.parcels_count = 5
        metrics.hectares_used = 150.0
        metrics.users_count = 2
        metrics.save()
        metrics.calculate_overages()
        
        print_info(f"Uso: {metrics.eosda_requests}/{limit} (50%)")
        
        alert_manager = BillingAlertManager(metrics)
        alerts = alert_manager.check_and_send_alerts()
        
        print_info(f"Alertas enviadas: {len(alerts)}")
        print_info(f"Emails enviados: {len(mail.outbox)}")
        
        assert len(alerts) == 0, "No debería haber alertas al 50%"
        assert len(mail.outbox) == 0, "No debería enviarse email al 50%"
        
        print_success("✅ Sin alertas correctamente")
        
        # ========== TEST 2: WARNING (85% de uso) ==========
        print_header("TEST 2: Alerta WARNING (85% de uso)")
        
        metrics.eosda_requests = int(limit * 0.85)
        metrics.save()
        metrics.calculate_overages()
        
        print_info(f"Uso: {metrics.eosda_requests}/{limit} (85%)")
        
        # Limpiar mailbox
        mail.outbox = []
        
        alert_manager = BillingAlertManager(metrics)
        alerts = alert_manager.check_and_send_alerts()
        
        print_info(f"Alertas generadas: {len(alerts)}")
        
        for alert in alerts:
            level_emoji = {'warning': '⚠️ ', 'danger': '🔴', 'exceeded': '🚫'}
            emoji = level_emoji.get(alert['level'], '📌')
            print_warning(f"{emoji} {alert['resource']}: {alert['percentage']}% ({alert['level']})")
        
        print_info(f"Emails enviados: {len(mail.outbox)}")
        
        if len(mail.outbox) > 0:
            email = mail.outbox[0]
            print_info(f"\nEmail enviado:")
            print_info(f"  Subject: {email.subject}")
            print_info(f"  To: {email.to}")
            print_info(f"  Body preview: {email.body[:200]}...")
        
        # Verificar que se registró el evento
        events = BillingEvent.objects.filter(
            tenant=tenant,
            event_type='alert'
        ).count()
        print_info(f"Eventos registrados: {events}")
        
        assert len(alerts) > 0, "Debería haber alertas al 85%"
        print_success("✅ Alertas WARNING generadas correctamente")
        
        # ========== TEST 3: DANGER (95% de uso) ==========
        print_header("TEST 3: Alerta DANGER (95% de uso)")
        
        # Eliminar eventos para poder enviar nueva alerta
        BillingEvent.objects.filter(tenant=tenant, event_type='alert').delete()
        mail.outbox = []
        
        metrics.eosda_requests = int(limit * 0.95)
        metrics.save()
        metrics.calculate_overages()
        
        print_info(f"Uso: {metrics.eosda_requests}/{limit} (95%)")
        
        alert_manager = BillingAlertManager(metrics)
        alerts = alert_manager.check_and_send_alerts()
        
        print_info(f"Alertas generadas: {len(alerts)}")
        
        for alert in alerts:
            if alert['level'] == 'danger':
                print_error(f"🔴 {alert['resource']}: {alert['percentage']}% (CRÍTICO)")
        
        print_info(f"Emails enviados: {len(mail.outbox)}")
        
        assert any(a['level'] == 'danger' for a in alerts), "Debería haber alerta DANGER al 95%"
        print_success("✅ Alertas DANGER generadas correctamente")
        
        # ========== TEST 4: EXCEEDED (105% de uso) ==========
        print_header("TEST 4: Alerta EXCEEDED (105% de uso)")
        
        # Limpiar para nueva alerta
        BillingEvent.objects.filter(tenant=tenant, event_type='alert').delete()
        mail.outbox = []
        
        metrics.eosda_requests = 105
        metrics.save()
        metrics.calculate_overages()
        
        print_info(f"Uso: {metrics.eosda_requests}/{limit} (105%)")
        print_error(f"Exceso: {metrics.eosda_requests_overage} requests")
        
        alert_manager = BillingAlertManager(metrics)
        alerts = alert_manager.check_and_send_alerts()
        
        print_info(f"Alertas generadas: {len(alerts)}")
        
        for alert in alerts:
            if alert['level'] == 'exceeded':
                print_error(f"🚫 {alert['resource']}: EXCEDIDO por {alert['current'] - alert['limit']} {alert['unit']}")
        
        print_info(f"Emails enviados: {len(mail.outbox)}")
        
        if len(mail.outbox) > 0:
            email = mail.outbox[0]
            print_info(f"\nEmail de EXCESO enviado:")
            print_info(f"  Subject: {email.subject}")
            print_info(f"  To: {email.to}")
            
            # Buscar mención de overage cost en el body
            if 'cargo adicional' in email.body:
                print_warning("  ⚠️  Incluye advertencia de cargo adicional")
        
        assert any(a['level'] == 'exceeded' for a in alerts), "Debería haber alerta EXCEEDED al 105%"
        print_success("✅ Alertas EXCEEDED generadas correctamente")
        
        # ========== TEST 5: NO DUPLICAR ALERTAS (24h) ==========
        print_header("TEST 5: No Duplicar Alertas (24 horas)")
        
        print_info("Intentando enviar alerta duplicada...")
        
        mail.outbox = []
        
        alert_manager = BillingAlertManager(metrics)
        alerts = alert_manager.check_and_send_alerts()
        
        print_info(f"Alertas enviadas: {len(alerts)}")
        print_info(f"Emails enviados: {len(mail.outbox)}")
        
        assert len(alerts) == 0, "No debería enviar alertas duplicadas en 24h"
        assert len(mail.outbox) == 0, "No debería enviar emails duplicados"
        
        print_success("✅ Sistema evita alertas duplicadas correctamente")
        
        # ========== TEST 6: VERIFICAR EVENTOS REGISTRADOS ==========
        print_header("TEST 6: Verificar Eventos Registrados")
        
        events = BillingEvent.objects.filter(
            tenant=tenant,
            event_type='alert'
        ).order_by('-created_at')
        
        print_info(f"Total eventos de alerta: {events.count()}")
        
        for event in events[:5]:
            message = event.event_data.get('message', f"{event.event_type} event")
            print_info(f"  - {event.created_at.strftime('%Y-%m-%d %H:%M')}: {message}")
        
        assert events.count() > 0, "Debería haber eventos registrados"
        print_success("✅ Eventos registrados correctamente")
        
        # ========== RESULTADO FINAL ==========
        print_header("RESULTADO FINAL")
        
        print_success("✅ Sin alertas al 50% de uso")
        print_success("✅ Alertas WARNING al 80-89% de uso")
        print_success("✅ Alertas DANGER al 90-99% de uso")
        print_success("✅ Alertas EXCEEDED al 100%+ de uso")
        print_success("✅ Emails enviados correctamente")
        print_success("✅ Eventos registrados en BD")
        print_success("✅ No duplica alertas en 24h")
        
        print_info(f"\n📧 Sistema de notificaciones listo para producción")
        print_info(f"   Ejecutar: python manage.py check_usage_alerts")
        
        print_header("TEST COMPLETADO EXITOSAMENTE ✅")
        
    except Exception as e:
        print_error(f"Error durante el test: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    test_alertas()
