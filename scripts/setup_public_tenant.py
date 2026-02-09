"""
Script para crear el tenant público necesario para django-tenants.
El tenant público sirve las URLs de PUBLIC_SCHEMA_URLCONF: registro, login, planes.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

django.setup()

from base_agrotech.models import Client, Domain
from datetime import date, timedelta


def setup():
    # 1. Crear tenant público
    public_tenant, created = Client.objects.get_or_create(
        schema_name='public',
        defaults={
            'name': 'AgroTech Digital (Public)',
            'paid_until': date.today() + timedelta(days=365 * 10),
            'on_trial': False,
        }
    )
    if created:
        print(f'✅ Tenant público creado: schema=public')
    else:
        print(f'ℹ️  Tenant público ya existe: schema=public')

    # 2. Asignar 127.0.0.1 al tenant público (para desarrollo local)
    domain_127, created = Domain.objects.get_or_create(
        domain='127.0.0.1',
        defaults={
            'tenant': public_tenant,
            'is_primary': True,
        }
    )
    if created:
        print(f'✅ Domain 127.0.0.1 → public')
    else:
        if domain_127.tenant != public_tenant:
            domain_127.tenant = public_tenant
            domain_127.save()
            print(f'✅ Domain 127.0.0.1 reasignado → public')
        else:
            print(f'ℹ️  Domain 127.0.0.1 ya apunta a public')

    # 3. Mostrar estado final
    print('\n=== DOMINIOS CONFIGURADOS ===')
    for d in Domain.objects.select_related('tenant').all():
        print(f'  {d.domain:45s} → {d.tenant.schema_name} (primary={d.is_primary})')


if __name__ == '__main__':
    setup()
