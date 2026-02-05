#!/usr/bin/env python
"""
Crear usuario de prueba en PostgreSQL para AgroTech
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
os.environ['DJANGO_SECRET_KEY'] = 'test-key-local-only'

# Agregar al path
sys.path.insert(0, '/Users/sebastianflorez/Documents/agrotech-digital/agrotech-digital')

# Setup Django
django.setup()

from django.contrib.auth import get_user_model
from base_agrotech.models import Client
from django.db import connection

User = get_user_model()

print("🔍 Verificando tenants...")

# Listar tenants
tenants = Client.objects.all()
print(f"\n📋 Tenants disponibles ({tenants.count()}):")
for tenant in tenants:
    print(f"  - {tenant.schema_name}: {tenant.name}")

if tenants.count() == 0:
    print("\n⚠️ No hay tenants. Creando tenant de prueba...")
    tenant = Client.objects.create(
        schema_name='demo',
        name='Demo AgroTech',
        paid_until='2030-12-31',
        on_trial=False
    )
    print(f"✅ Tenant creado: {tenant.name}")
else:
    # Usar el primer tenant
    tenant = tenants.first()
    print(f"\n✅ Usando tenant: {tenant.name} ({tenant.schema_name})")

# Cambiar al schema del tenant
connection.set_tenant(tenant)

print(f"\n👤 Creando usuario en tenant '{tenant.schema_name}'...")

username = 'admin'
password = 'admin123'
email = 'admin@agrotech.com'

# Verificar si existe
if User.objects.filter(username=username).exists():
    user = User.objects.get(username=username)
    user.set_password(password)
    user.save()
    print(f"✅ Contraseña actualizada para '{username}'")
else:
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        first_name='Admin',
        last_name='Demo'
    )
    print(f"✅ Usuario creado: {username}")

print("\n" + "="*60)
print("🎉 CREDENCIALES LISTAS:")
print("="*60)
print(f"  URL:      http://localhost:8080/templates/authentication/login.html")
print(f"  Username: {username}")
print(f"  Password: {password}")
print(f"  Tenant:   {tenant.schema_name}")
print("="*60)
