"""
Test completo del flujo SaaS con billing, suscripciones y EOSDA.

Ejecutar: python manage.py test_saas_flow
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import GEOSGeometry
from django.db import connection
from base_agrotech.models import Client
from billing.models import Plan, Subscription, UsageMetrics
from parcels.models import Parcel
from datetime import datetime, timedelta
from decimal import Decimal
import json
import sys

User = get_user_model()

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'='*80}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(80)}{RESET}")
    print(f"{BOLD}{BLUE}{'='*80}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text):
    print(f"{BLUE}ℹ️  {text}{RESET}")


class Command(BaseCommand):
    help = 'Test completo del flujo SaaS con billing y EOSDA'
    
    def __init__(self):
        super().__init__()
        self.tenant = None
        self.user = None
        self.subscription = None
        self.parcel = None
        self.test_results = []
    
    def handle(self, *args, **options):
        print_header("TEST COMPLETO DE FLUJO SAAS")
        print_info("Este test creará un tenant de prueba y probará todo el flujo")
        print_info("con billing, suscripciones y EOSDA API")
        print()
        
        try:
            self.cleanup_previous_tests()
            self.create_tenant_with_subscription()
            self.create_test_parcel()
            self.test_scene_search()
            self.test_image_generation()
            self.test_analytics()
            self.test_limit_enforcement()
            
        except Exception as e:
            print_error(f"Test interrumpido: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.print_final_report()
    
    def cleanup_previous_tests(self):
        """Limpiar tests anteriores"""
        print_header("LIMPIEZA DE TESTS ANTERIORES")
        
        try:
            old_tenants = Client.objects.filter(schema_name__startswith='test_saas_')
            if old_tenants.exists():
                count = old_tenants.count()
                for tenant in old_tenants:
                    print_info(f"Eliminando tenant antiguo: {tenant.schema_name}")
                    tenant.delete()
                print_success(f"Eliminados {count} tenants de prueba antiguos")
            else:
                print_info("No hay tenants antiguos para eliminar")
                
        except Exception as e:
            print_warning(f"Error en limpieza: {str(e)}")
    
    def create_tenant_with_subscription(self):
        """Paso 1: Crear tenant con suscripción BASIC"""
        print_header("PASO 1: CREAR TENANT CON SUSCRIPCIÓN BASIC")
        
        try:
            # Verificar que existe plan BASIC
            try:
                plan_basic = Plan.objects.get(code='BASIC')
                print_success(f"Plan BASIC encontrado: {plan_basic.name} - {plan_basic.price_monthly} COP/mes")
                print_info(f"Límites: {plan_basic.limits}")
            except Plan.DoesNotExist:
                print_error("Plan BASIC no existe. Ejecuta: python manage.py create_billing_plans")
                sys.exit(1)
            
            # Crear tenant
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            schema_name = f'test_saas_{timestamp}'
            
            self.tenant = Client.objects.create(
                schema_name=schema_name,
                name=f'Test SaaS Flow {timestamp}',
                paid_until=datetime.now().date() + timedelta(days=30),
                on_trial=True
            )
            print_success(f"Tenant creado: {self.tenant.schema_name}")
            print_info(f"Nombre: {self.tenant.name}")
            
            # Crear usuario
            self.user = User.objects.create_user(
                username=f'admin_{schema_name}',
                email=f'admin_{schema_name}@test.com',
                password='test123',
                first_name='Admin',
                last_name='Test'
            )
            print_success(f"Usuario creado: {self.user.username}")
            
            # Crear suscripción
            self.subscription = Subscription.objects.create(
                tenant=self.tenant,
                plan=plan_basic,
                status='active',
                current_period_start=datetime.now().date(),
                current_period_end=datetime.now().date() + timedelta(days=30)
            )
            print_success(f"Suscripción creada: Plan {self.subscription.plan.name}")
            print_info(f"Estado: {self.subscription.status}")
            
            # Métricas iniciales
            metrics = UsageMetrics.get_or_create_current(self.tenant)
            print_success(f"Métricas iniciales creadas")
            print_info(f"EOSDA requests: {metrics.eosda_requests}/{plan_basic.limits.get('eosda_requests', 0)}")
            
            self.test_results.append({
                'test': 'Creación de tenant y suscripción',
                'status': 'PASS',
                'details': f'Tenant: {self.tenant.schema_name}, Plan: {plan_basic.name}'
            })
            
        except Exception as e:
            print_error(f"Error: {str(e)}")
            self.test_results.append({'test': 'Creación de tenant y suscripción', 'status': 'FAIL', 'error': str(e)})
            raise
    
    def create_test_parcel(self):
        """Paso 2: Crear parcela de prueba"""
        print_header("PASO 2: CREAR PARCELA DE PRUEBA")
        
        try:
            connection.set_tenant(self.tenant)
            
            # Geometría de prueba (zona cafetera Colombia)
            geojson = {
                "type": "Polygon",
                "coordinates": [[
                    [-75.6039, 4.9825],
                    [-75.6029, 4.9825],
                    [-75.6029, 4.9815],
                    [-75.6039, 4.9815],
                    [-75.6039, 4.9825]
                ]]
            }
            
            geom = GEOSGeometry(json.dumps(geojson))
            
            self.parcel = Parcel.objects.create(
                name='Lote Café Test',
                area_hectares=Decimal('5.5'),
                geom=geom,
                crop_type='cafe',
                owner=self.user,
                is_deleted=False
            )
            
            print_success(f"Parcela creada: {self.parcel.name}")
            print_info(f"ID: {self.parcel.id}, Área: {self.parcel.area_hectares} ha")
            
            # Actualizar métricas
            metrics = UsageMetrics.get_or_create_current(self.tenant)
            metrics.hectares_used = float(self.parcel.area_hectares)
            metrics.save()
            print_success(f"Métricas actualizadas: {metrics.hectares_used} ha")
            
            self.test_results.append({
                'test': 'Creación de parcela',
                'status': 'PASS',
                'details': f'{self.parcel.name}, {self.parcel.area_hectares} ha'
            })
            
        except Exception as e:
            print_error(f"Error: {str(e)}")
            self.test_results.append({'test': 'Creación de parcela', 'status': 'FAIL', 'error': str(e)})
            raise
        finally:
            connection.set_schema_to_public()
    
    def test_scene_search(self):
        """Paso 3: Probar búsqueda de escenas"""
        print_header("PASO 3: BÚSQUEDA DE ESCENAS SATELITALES")
        
        try:
            from parcels.views import EosdaScenesView
            from rest_framework.test import APIRequestFactory
            
            metrics_before = UsageMetrics.get_or_create_current(self.tenant)
            requests_before = metrics_before.eosda_requests
            print_info(f"Requests antes: {requests_before}")
            
            # Obtener field_id
            connection.set_tenant(self.tenant)
            if not self.parcel.eosda_id:
                self.parcel.create_eosda_field()
                self.parcel.refresh_from_db()
            field_id = self.parcel.eosda_id
            connection.set_schema_to_public()
            
            factory = APIRequestFactory()
            request = factory.post('/api/parcels/eosda-scenes/', {'field_id': field_id}, format='json')
            request.user = self.user
            request.tenant = self.tenant
            request.subscription = self.subscription
            
            print_info(f"Buscando escenas para field_id: {field_id}")
            print_warning("⏳ Esto puede tomar 5-10 segundos...")
            
            view = EosdaScenesView.as_view()
            response = view(request)
            
            print_info(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                scenes = response.data.get('scenes', [])
                print_success(f"{len(scenes)} escenas encontradas")
                
                metrics_after = UsageMetrics.get_or_create_current(self.tenant)
                increment = metrics_after.eosda_requests - requests_before
                
                print_success(f"Requests después: {metrics_after.eosda_requests} (+{increment})")
                
                if increment > 0:
                    print_success("✅ DECORADOR FUNCIONANDO")
                else:
                    print_warning("Cache hit - contador no incrementó")
                
                self.test_results.append({
                    'test': 'Búsqueda de escenas',
                    'status': 'PASS',
                    'details': f'{len(scenes)} escenas, +{increment} requests'
                })
            elif response.status_code == 429:
                print_error("Límite excedido (esperado si ya usó 100 requests)")
                self.test_results.append({'test': 'Búsqueda de escenas', 'status': 'BLOCKED', 'details': 'Límite alcanzado'})
            else:
                print_error(f"Error: {response.status_code}")
                self.test_results.append({'test': 'Búsqueda de escenas', 'status': 'FAIL', 'error': str(response.data)})
                
        except Exception as e:
            print_error(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.test_results.append({'test': 'Búsqueda de escenas', 'status': 'FAIL', 'error': str(e)})
    
    def test_image_generation(self):
        """Paso 4: Generar imagen NDVI"""
        print_header("PASO 4: GENERACIÓN DE IMAGEN NDVI")
        
        try:
            from parcels.views import EosdaImageView
            from rest_framework.test import APIRequestFactory
            
            metrics_before = UsageMetrics.get_or_create_current(self.tenant)
            requests_before = metrics_before.eosda_requests
            
            connection.set_tenant(self.tenant)
            field_id = self.parcel.eosda_id
            connection.set_schema_to_public()
            
            factory = APIRequestFactory()
            request = factory.post('/api/parcels/eosda-image/', {
                'field_id': field_id,
                'view_id': 'S2A_tile_20231201_18NWP_0',
                'type': 'ndvi',
                'format': 'png'
            }, format='json')
            
            request.user = self.user
            request.tenant = self.tenant
            request.subscription = self.subscription
            
            print_info("Generando imagen NDVI...")
            
            view = EosdaImageView.as_view()
            response = view(request)
            
            if response.status_code == 200:
                print_success(f"Request ID: {response.data.get('request_id')}")
                
                metrics_after = UsageMetrics.get_or_create_current(self.tenant)
                increment = metrics_after.eosda_requests - requests_before
                print_success(f"Incremento: +{increment}")
                
                self.test_results.append({'test': 'Generación NDVI', 'status': 'PASS', 'details': f'+{increment} requests'})
            elif response.status_code == 429:
                print_error("Límite excedido")
                self.test_results.append({'test': 'Generación NDVI', 'status': 'BLOCKED'})
            else:
                print_error(f"Error: {response.status_code}")
                self.test_results.append({'test': 'Generación NDVI', 'status': 'FAIL'})
                
        except Exception as e:
            print_error(f"Error: {str(e)}")
            self.test_results.append({'test': 'Generación NDVI', 'status': 'FAIL', 'error': str(e)})
    
    def test_analytics(self):
        """Paso 5: Analytics"""
        print_header("PASO 5: ANALYTICS (solo NDVI por defecto)")
        
        try:
            from parcels.views import EosdaSceneAnalyticsView
            from rest_framework.test import APIRequestFactory
            
            metrics_before = UsageMetrics.get_or_create_current(self.tenant)
            
            connection.set_tenant(self.tenant)
            field_id = self.parcel.eosda_id
            connection.set_schema_to_public()
            
            factory = APIRequestFactory()
            request = factory.post('/api/parcels/eosda-scene-analytics/', {
                'field_id': field_id,
                'view_id': 'S2A_tile_20231201_18NWP_0',
                'scene_date': '2023-12-01'
            }, format='json')
            
            request.user = self.user
            request.tenant = self.tenant
            request.subscription = self.subscription
            
            view = EosdaSceneAnalyticsView.as_view()
            response = view(request)
            
            if response.status_code == 200:
                indices = list(response.data.get('analytics', {}).keys())
                print_success(f"Analytics para: {indices}")
                
                if indices == ['ndvi']:
                    print_success("✅ OPTIMIZACIÓN OK: Solo NDVI")
                else:
                    print_warning(f"Devolvió {len(indices)} índices")
                
                self.test_results.append({'test': 'Analytics', 'status': 'PASS', 'details': f'Índices: {indices}'})
            elif response.status_code == 429:
                self.test_results.append({'test': 'Analytics', 'status': 'BLOCKED'})
            else:
                self.test_results.append({'test': 'Analytics', 'status': 'FAIL'})
                
        except Exception as e:
            print_error(f"Error: {str(e)}")
            self.test_results.append({'test': 'Analytics', 'status': 'FAIL', 'error': str(e)})
    
    def test_limit_enforcement(self):
        """Paso 6: Bloqueo al exceder límite"""
        print_header("PASO 6: PRUEBA DE BLOQUEO")
        
        try:
            metrics = UsageMetrics.get_or_create_current(self.tenant)
            plan_limit = self.subscription.plan.limits.get('eosda_requests', 100)
            
            print_info(f"Requests actuales: {metrics.eosda_requests}/{plan_limit}")
            print_warning(f"Simulando límite alcanzado...")
            
            metrics.eosda_requests = plan_limit
            metrics.save()
            
            from parcels.views import EosdaScenesView
            from rest_framework.test import APIRequestFactory
            
            connection.set_tenant(self.tenant)
            field_id = self.parcel.eosda_id
            connection.set_schema_to_public()
            
            factory = APIRequestFactory()
            request = factory.post('/api/parcels/eosda-scenes/', {'field_id': field_id}, format='json')
            request.user = self.user
            request.tenant = self.tenant
            request.subscription = self.subscription
            
            view = EosdaScenesView.as_view()
            response = view(request)
            
            if response.status_code == 429:
                print_success("✅ BLOQUEO FUNCIONANDO: HTTP 429")
                print_info(f"Mensaje: {response.data.get('message', 'N/A')}")
                self.test_results.append({'test': 'Bloqueo límite', 'status': 'PASS', 'details': 'HTTP 429 correcto'})
            else:
                print_error(f"❌ NO BLOQUEÓ: Status {response.status_code}")
                self.test_results.append({'test': 'Bloqueo límite', 'status': 'FAIL', 'error': 'No bloqueó'})
                
        except Exception as e:
            print_error(f"Error: {str(e)}")
            self.test_results.append({'test': 'Bloqueo límite', 'status': 'FAIL', 'error': str(e)})
    
    def print_final_report(self):
        """Reporte final"""
        print_header("REPORTE FINAL")
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        blocked = sum(1 for r in self.test_results if r['status'] == 'BLOCKED')
        
        print(f"\n{BOLD}RESUMEN:{RESET}")
        print(f"  Total: {total}")
        print(f"  {GREEN}Exitosos: {passed}{RESET}")
        print(f"  {RED}Fallidos: {failed}{RESET}")
        print(f"  {YELLOW}Bloqueados: {blocked}{RESET}")
        
        print(f"\n{BOLD}DETALLE:{RESET}\n")
        for i, r in enumerate(self.test_results, 1):
            color = GREEN if r['status'] == 'PASS' else (YELLOW if r['status'] == 'BLOCKED' else RED)
            icon = '✅' if r['status'] == 'PASS' else ('⚠️' if r['status'] == 'BLOCKED' else '❌')
            print(f"{i}. {r['test']}: {color}{icon} {r['status']}{RESET}")
            if 'details' in r:
                print(f"   → {r['details']}")
        
        if self.tenant:
            metrics = UsageMetrics.get_or_create_current(self.tenant)
            print(f"\n{BOLD}MÉTRICAS FINALES:{RESET}")
            print(f"  Tenant: {self.tenant.schema_name}")
            print(f"  Plan: {self.subscription.plan.name}")
            print(f"  EOSDA: {metrics.eosda_requests}/{self.subscription.plan.limits.get('eosda_requests')}")
            print(f"  Hectáreas: {metrics.hectares_used}/{self.subscription.plan.limits.get('hectares')}")
        
        if failed == 0:
            print(f"\n{GREEN}✅ TODOS LOS TESTS PASARON{RESET}")
        else:
            print(f"\n{RED}❌ ALGUNOS TESTS FALLARON{RESET}")
