#!/usr/bin/env python
"""
Script para revisar configuración actual de dominios y tenants
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
os.environ['DJANGO_SECRET_KEY'] = os.environ.get('DJANGO_SECRET_KEY', 'dev-local-only')
sys.path.insert(0, '.')
django.setup()

from base_agrotech.models import Client, Domain

print("\n" + "="*70)
print("🔍 CONFIGURACIÓN ACTUAL DE DOMINIOS Y TENANTS")
print("="*70 + "\n")

# 1. Listar todos los tenants
print("📦 TENANTS CONFIGURADOS:")
print("-" * 70)
tenants = Client.objects.all()
if not tenants:
    print("⚠️  No hay tenants configurados")
else:
    for tenant in tenants:
        print(f"\n🏢 Tenant: {tenant.name}")
        print(f"   Schema: {tenant.schema_name}")
        print(f"   Creado: {tenant.created_on}")
        print(f"   Activo: {'✅ Sí' if not hasattr(tenant, 'is_active') or tenant.is_active else '❌ No'}")
        
        # Listar dominios de este tenant
        domains = Domain.objects.filter(tenant=tenant)
        if domains:
            print(f"   🌐 Dominios:")
            for d in domains:
                primary = "⭐ PRIMARY" if d.is_primary else ""
                print(f"      - {d.domain} {primary}")
        else:
            print(f"   ⚠️  Sin dominios configurados")

# 2. Configuración esperada para producción
print("\n" + "="*70)
print("🎯 CONFIGURACIÓN ESPERADA PARA PRODUCCIÓN")
print("="*70 + "\n")

print("Para que funcione en producción, necesitas:")
print("\n1️⃣  Dominio principal del SaaS:")
print("   - agrotechcolombia.com → Apuntando a Railway")
print("   - www.agrotechcolombia.com → Redirect a agrotechcolombia.com")

print("\n2️⃣  Frontend estático:")
print("   - agrotechcolombia.netlify.app → Netlify")

print("\n3️⃣  Si quieres multi-tenant con subdominios:")
print("   - cliente1.agrotechcolombia.com")
print("   - cliente2.agrotechcolombia.com")
print("   - *.agrotechcolombia.com → Wildcard DNS a Railway")

print("\n4️⃣  Si tienes 'historical' como producto separado:")
print("   Opción A: Subdominio → historical.agrotechcolombia.com")
print("   Opción B: Dominio propio → tudominio.com")

print("\n" + "="*70)
print("📋 PRÓXIMOS PASOS PARA CONFIGURAR")
print("="*70 + "\n")

print("1. Revisa Railway:")
print("   - https://railway.app → Tu proyecto → Settings → Domains")
print("   - Anota qué dominios ves ahí")

print("\n2. Revisa tu proveedor DNS (GoDaddy, Namecheap, etc.):")
print("   - ¿Qué registros A/CNAME tienes para agrotechcolombia.com?")

print("\n3. Responde estas preguntas:")
print("   a) ¿Qué dominio usabas para 'historical'?")
print("   b) ¿Quieres que 'historical' sea:")
print("      - Un tenant separado en este mismo sistema?")
print("      - Una aplicación completamente separada?")
print("   c) ¿Quieres que tus clientes tengan subdominios?")

print("\n" + "="*70 + "\n")
