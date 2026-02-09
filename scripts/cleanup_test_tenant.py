"""Script para limpiar el tenant de prueba creado durante testing."""
import os, sys, django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from base_agrotech.models import Client, Domain
from django.db import connection

schema = 'tenant_finca_la_esperanza'
try:
    tenant = Client.objects.get(schema_name=schema)
    Domain.objects.filter(tenant=tenant).delete()
    tenant.delete()
    # Drop schema
    with connection.cursor() as cursor:
        cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
    print(f'✅ Tenant {schema} eliminado')
except Client.DoesNotExist:
    print(f'ℹ️  Tenant {schema} no existe')

print('\n=== TENANTS RESTANTES ===')
for t in Client.objects.all():
    print(f'  {t.schema_name}: {t.name}')
print('\n=== DOMAINS RESTANTES ===')
for d in Domain.objects.select_related('tenant').all():
    print(f'  {d.domain} → {d.tenant.schema_name}')
