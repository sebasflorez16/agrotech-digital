#!/usr/bin/env python
"""
Configurar dominio de producción para el tenant test_farm
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
os.environ['DJANGO_SECRET_KEY'] = 'test-key'
sys.path.insert(0, '.')
django.setup()

from base_agrotech.models import Client, Domain

print("\n" + "="*70)
print("🌐 CONFIGURANDO DOMINIO DE PRODUCCIÓN")
print("="*70 + "\n")

# Obtener el tenant
tenant = Client.objects.get(schema_name='test_farm')
print(f"✅ Tenant encontrado: {tenant.name}")

# Verificar dominios actuales
current_domains = Domain.objects.filter(tenant=tenant)
print(f"\n📋 Dominios actuales:")
for d in current_domains:
    print(f"   - {d.domain} (primary: {d.is_primary})")

# Agregar dominios de producción
dominios_produccion = [
    'agrotechcolombia.netlify.app',
    'agrotech-digital-production.up.railway.app',
]

print(f"\n🔧 Agregando dominios de producción...")
for dominio in dominios_produccion:
    if not Domain.objects.filter(domain=dominio).exists():
        # El primero será primary
        is_primary = dominio == 'agrotechcolombia.netlify.app'
        Domain.objects.create(
            domain=dominio,
            tenant=tenant,
            is_primary=is_primary
        )
        primary_text = "⭐ PRIMARY" if is_primary else ""
        print(f"   ✅ Agregado: {dominio} {primary_text}")
    else:
        print(f"   ⏭️  Ya existe: {dominio}")

# Mostrar configuración final
print(f"\n" + "="*70)
print("📊 CONFIGURACIÓN FINAL DE DOMINIOS")
print("="*70 + "\n")

all_domains = Domain.objects.filter(tenant=tenant).order_by('-is_primary')
for d in all_domains:
    primary = "⭐ PRIMARY" if d.is_primary else ""
    print(f"   - {d.domain} {primary}")

print("\n" + "="*70)
print("✅ CONFIGURACIÓN COMPLETADA")
print("="*70 + "\n")

print("🎯 Ahora tu sistema funcionará con estos dominios:")
print(f"   - Frontend: https://agrotechcolombia.netlify.app")
print(f"   - Backend:  https://agrotech-digital-production.up.railway.app")
print(f"   - Local:    http://localhost:8080 → http://localhost:8000")

print("\n💡 Para que funcione en producción:")
print("   1. Haz commit y push de los cambios")
print("   2. Netlify se desplegará automáticamente")
print("   3. Railway ya está desplegado (lo viste en el screenshot)")
print("\n")
