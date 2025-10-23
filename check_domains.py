#!/usr/bin/env python
"""
Script para verificar la configuración de dominios en la base de datos
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from base_agrotech.models import Domain, Client

def check_domains():
    print("\n" + "="*60)
    print("VERIFICACIÓN DE DOMINIOS Y TENANTS")
    print("="*60)
    
    # Listar todos los tenants
    print("\n📋 CLIENTES (TENANTS):")
    print("-" * 60)
    clients = Client.objects.all()
    for client in clients:
        print(f"  • Schema: {client.schema_name}")
        print(f"    - Nombre: {client.name}")
        print(f"    - Pagado hasta: {client.paid_until}")
        print(f"    - En prueba: {client.on_trial}")
        print()
    
    # Listar todos los dominios
    print("\n🌐 DOMINIOS CONFIGURADOS:")
    print("-" * 60)
    domains = Domain.objects.all().select_related('tenant')
    for domain in domains:
        print(f"  • Dominio: {domain.domain}")
        print(f"    - Tenant: {domain.tenant.schema_name} ({domain.tenant.name})")
        print(f"    - Es primario: {domain.is_primary}")
        print()
    
    # Verificar dominio público
    print("\n🔍 VERIFICACIÓN DEL SCHEMA PÚBLICO:")
    print("-" * 60)
    public_domains = Domain.objects.filter(tenant__schema_name='public')
    if public_domains.exists():
        print(f"  ✅ Schema público tiene {public_domains.count()} dominio(s):")
        for domain in public_domains:
            print(f"     - {domain.domain} (primario: {domain.is_primary})")
    else:
        print("  ❌ El schema público NO tiene dominios configurados")
        print("     Esto puede causar problemas con django-tenants")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        check_domains()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
