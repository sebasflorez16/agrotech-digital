#!/usr/bin/env python
"""
Test del Dashboard de Métricas de Uso

Valida que el dashboard retorne correctamente:
- Información de suscripción
- Métricas de uso actuales
- Alertas cuando se exceden límites
- Preview de facturación con overages
"""

import os
import django
import sys

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import connection
from datetime import timedelta
from django_tenants.utils import tenant_context

from base_agrotech.models import Client
from billing.models import Plan, Subscription, UsageMetrics
from parcels.models import Parcel

User = get_user_model()

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


def test_dashboard_metricas():
    """Test completo del dashboard de métricas."""
    
    print_header("TEST DASHBOARD DE MÉTRICAS")
    
    try:
        # ========== PREPARAR DATOS ==========
        print_header("Preparar Datos de Test")
        
        # Cambiar a schema público
        connection.set_schema_to_public()
        
        # Obtener o crear tenant de test
        try:
            tenant = Client.objects.get(schema_name='test_farm')
            print_success(f"Tenant existente: {tenant.name}")
        except Client.DoesNotExist:
            print_error("No existe el tenant test_farm")
            print_info("Ejecuta primero test_saas_complete.py")
            return
        
        # Obtener suscripción
        try:
            subscription = tenant.subscription
            print_success(f"Suscripción: {subscription.plan.name} ({subscription.status})")
        except Subscription.DoesNotExist:
            print_error("No existe suscripción para este tenant")
            return
        
        # Obtener métricas actuales
        now = timezone.now()
        metrics, created = UsageMetrics.objects.get_or_create(
            tenant=tenant,
            year=now.year,
            month=now.month
        )
        
        if created:
            print_info("Métricas creadas para el mes actual")
        else:
            print_success(f"Métricas existentes: {metrics.eosda_requests} requests EOSDA")
        
        # ========== TEST 1: DASHBOARD CON USO NORMAL ==========
        print_header("TEST 1: Dashboard con Uso Normal (50% del límite)")
        
        # Configurar uso al 50%
        limit = subscription.plan.get_limit('eosda_requests', 100)
        metrics.eosda_requests = int(limit * 0.5)
        metrics.parcels_count = 5
        metrics.hectares_used = 150.0
        metrics.users_count = 2
        metrics.save()
        metrics.calculate_overages()
        
        print_info(f"Configurado: {metrics.eosda_requests}/{limit} requests EOSDA (50%)")
        
        # Simular request al dashboard
        from billing.views import usage_dashboard_view
        from rest_framework.test import APIRequestFactory, force_authenticate
        
        factory = APIRequestFactory()
        request = factory.get('/api/billing/usage/dashboard/')
        
        # Configurar usuario y tenant en el request
        connection.set_tenant(tenant)
        user = User.objects.filter(username='agricultor_test').first()
        if not user:
            print_error("Usuario agricultor_test no existe")
            return
        
        # Forzar autenticación
        force_authenticate(request, user=user)
        request.tenant = tenant
        
        # Llamar a la vista directamente (ya maneja DRF internamente)
        response = usage_dashboard_view(request)
        
        if response.status_code == 200:
            data = response.data
            
            print_success("Dashboard retornó correctamente")
            print_info(f"\nSuscripción:")
            print_info(f"  - Plan: {data['subscription']['plan_name']}")
            print_info(f"  - Estado: {data['subscription']['status']}")
            print_info(f"  - Días restantes: {data['subscription']['days_remaining']}")
            
            print_info(f"\nUso Actual:")
            eosda = data['current_usage']['eosda_requests']
            print_info(f"  - EOSDA: {eosda['used']}/{eosda['limit']} ({eosda['percentage']}%) - Status: {eosda['status']}")
            
            parcels = data['current_usage']['parcels']
            print_info(f"  - Parcelas: {parcels['used']}/{parcels['limit']} ({parcels['percentage']}%)")
            
            print_info(f"\nAlertas: {len(data['alerts'])}")
            for alert in data['alerts']:
                if alert['type'] == 'error':
                    print_error(f"  {alert['message']}")
                else:
                    print_warning(f"  {alert['message']}")
            
            print_info(f"\nFacturación:")
            billing = data['billing_preview']
            print_info(f"  - Base: {billing['base_cost']:,} COP")
            print_info(f"  - Overages: {billing['overage_cost']:,} COP")
            print_info(f"  - TOTAL: {billing['total_cost']:,} COP")
            
            # Validaciones
            assert eosda['status'] == 'ok', "Status debería ser 'ok' al 50%"
            assert len(data['alerts']) == 0, "No debería haber alertas al 50%"
            assert billing['overage_cost'] == 0, "No debería haber overages al 50%"
            
            print_success("\n✅ Todas las validaciones pasaron")
        else:
            print_error(f"Error: {response.status_code}")
            print_error(f"Respuesta: {response.data}")
            return
        
        # ========== TEST 2: DASHBOARD CON USO AL 85% (WARNING) ==========
        print_header("TEST 2: Dashboard con Uso al 85% (WARNING)")
        
        metrics.eosda_requests = int(limit * 0.85)
        metrics.users_count = 3  # 100% de usuarios
        metrics.save()
        metrics.calculate_overages()
        
        print_info(f"Configurado: {metrics.eosda_requests}/{limit} requests EOSDA (85%)")
        
        response = usage_dashboard_view(request)
        
        if response.status_code == 200:
            data = response.data
            eosda = data['current_usage']['eosda_requests']
            users = data['current_usage']['users']
            
            print_success(f"EOSDA: {eosda['used']}/{eosda['limit']} ({eosda['percentage']}%) - Status: {eosda['status']}")
            print_success(f"Users: {users['used']}/{users['limit']} ({users['percentage']}%) - Status: {users['status']}")
            
            print_info(f"\nAlertas generadas: {len(data['alerts'])}")
            for alert in data['alerts']:
                print_warning(f"  {alert['message']}")
            
            # Validaciones
            assert eosda['status'] == 'warning', "Status debería ser 'warning' al 85%"
            assert len(data['alerts']) > 0, "Debería haber alertas al 85%"
            
            print_success("\n✅ Alertas generadas correctamente")
        else:
            print_error(f"Error: {response.status_code}")
            return
        
        # ========== TEST 3: DASHBOARD CON EXCESO (EXCEEDED) ==========
        print_header("TEST 3: Dashboard con Exceso de Límite")
        
        metrics.eosda_requests = 105  # 5 sobre el límite
        metrics.save()
        metrics.calculate_overages()
        
        print_info(f"Configurado: {metrics.eosda_requests}/{limit} requests EOSDA (105%)")
        print_info(f"Exceso: {metrics.eosda_requests_overage} requests")
        
        response = usage_dashboard_view(request)
        
        if response.status_code == 200:
            data = response.data
            eosda = data['current_usage']['eosda_requests']
            billing = data['billing_preview']
            
            print_success(f"EOSDA: {eosda['used']}/{eosda['limit']} ({eosda['percentage']}%) - Status: {eosda['status']}")
            print_error(f"Exceso: {eosda.get('overage', 0)} requests")
            
            print_info(f"\nAlertas de exceso:")
            for alert in data['alerts']:
                if alert['type'] == 'error':
                    print_error(f"  {alert['message']}")
            
            print_info(f"\nFacturación con Overages:")
            print_info(f"  - Base: {billing['base_cost']:,} COP")
            print_error(f"  - Overages: {billing['overage_cost']:,} COP")
            print_info(f"  - TOTAL: {billing['total_cost']:,} COP")
            
            if billing.get('overage_details'):
                details = billing['overage_details']
                print_info(f"\nDetalles de Exceso:")
                print_info(f"  - Requests extra: {details['eosda_requests_extra']}")
                print_info(f"  - Costo por request: {details['cost_per_request']} COP")
            
            # Validaciones
            assert eosda['status'] == 'exceeded', "Status debería ser 'exceeded' al 105%"
            assert 'overage' in eosda, "Debería incluir campo 'overage'"
            assert eosda['overage'] == 5, "Overage debería ser 5"
            assert billing['overage_cost'] == 2500, "Overage cost debería ser 2500 COP (5 × 500)"
            assert billing['total_cost'] == billing['base_cost'] + 2500, "Total incorrecto"
            
            print_success("\n✅ Cálculo de overages correcto")
        else:
            print_error(f"Error: {response.status_code}")
            return
        
        # ========== TEST 4: HISTORIAL DE USO ==========
        print_header("TEST 4: Historial de Uso Mensual")
        
        # Crear métricas de meses anteriores
        for i in range(1, 4):
            past_date = now - timedelta(days=30 * i)
            past_metrics, _ = UsageMetrics.objects.get_or_create(
                tenant=tenant,
                year=past_date.year,
                month=past_date.month,
                defaults={
                    'eosda_requests': 50 + (i * 10),
                    'parcels_count': 5,
                    'hectares_used': 120.0,
                    'users_count': 2
                }
            )
        
        print_info("Creadas métricas de meses anteriores")
        
        # Llamar a historial
        from billing.views import usage_history_view
        from rest_framework.test import force_authenticate
        
        request = factory.get('/api/billing/usage/history/?months=6')
        force_authenticate(request, user=user)
        request.tenant = tenant
        
        response = usage_history_view(request)
        
        if response.status_code == 200:
            data = response.data
            
            print_success(f"Historial retornado: {len(data['history'])} meses")
            print_info(f"Tenant: {data['tenant_name']}")
            
            print_info("\nHistorial:")
            for month_data in data['history']:
                print_info(f"  - {month_data['period']}: {month_data['eosda_requests']} requests")
            
            # Validaciones
            assert len(data['history']) >= 3, "Debería haber al menos 3 meses"
            
            print_success("\n✅ Historial generado correctamente")
        else:
            print_error(f"Error: {response.status_code}")
            return
        
        # ========== RESULTADO FINAL ==========
        print_header("RESULTADO FINAL")
        
        print_success("✅ Dashboard básico funcionando")
        print_success("✅ Alertas al 80% del límite")
        print_success("✅ Detección de excesos correcta")
        print_success("✅ Cálculo de overages preciso")
        print_success("✅ Historial mensual disponible")
        
        print_info(f"\n📊 Endpoints disponibles:")
        print_info(f"  - GET /billing/api/usage/dashboard/")
        print_info(f"  - GET /billing/api/usage/history/?months=6")
        
        print_header("TEST COMPLETADO EXITOSAMENTE ✅")
        
    except Exception as e:
        print_error(f"Error durante el test: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    test_dashboard_metricas()
