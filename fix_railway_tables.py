#!/usr/bin/env python
"""
Script de emergencia para crear tablas django-tenants en Railway
Ejecutar directamente: python fix_railway_tables.py
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django.db import connection

def main():
    print("🚨 SCRIPT DE EMERGENCIA - CREANDO TABLAS DJANGO-TENANTS")
    print("=" * 60)
    
    try:
        with connection.cursor() as cursor:
            # 1. Verificar conexión
            print("📡 Verificando conexión...")
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"✅ PostgreSQL: {version[:50]}")
            
            # 2. Crear tabla Client
            print("🔧 Creando tabla base_agrotech_client...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS base_agrotech_client (
                    id SERIAL PRIMARY KEY,
                    schema_name VARCHAR(63) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    paid_until DATE,
                    on_trial BOOLEAN DEFAULT FALSE,
                    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    uuid UUID DEFAULT gen_random_uuid()
                );
            """)
            print("✅ Tabla base_agrotech_client creada")
            
            # 3. Crear tabla Domain
            print("🔧 Creando tabla base_agrotech_domain...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS base_agrotech_domain (
                    id SERIAL PRIMARY KEY,
                    domain VARCHAR(253) UNIQUE NOT NULL,
                    is_primary BOOLEAN DEFAULT FALSE,
                    tenant_id INTEGER REFERENCES base_agrotech_client(id) ON DELETE CASCADE
                );
            """)
            print("✅ Tabla base_agrotech_domain creada")
            
            # 4. Crear tenant público
            print("🏢 Creando tenant público...")
            cursor.execute("""
                INSERT INTO base_agrotech_client (schema_name, name, paid_until, on_trial)
                VALUES ('public', 'Public Schema', '2025-12-31', FALSE)
                ON CONFLICT (schema_name) DO NOTHING
                RETURNING id;
            """)
            
            result = cursor.fetchone()
            if result:
                tenant_id = result[0]
                print(f"✅ Tenant público creado con ID: {tenant_id}")
            else:
                cursor.execute("SELECT id FROM base_agrotech_client WHERE schema_name = 'public'")
                tenant_id = cursor.fetchone()[0]
                print(f"✅ Tenant público existe con ID: {tenant_id}")
            
            # 5. Crear dominios
            print("🌐 Creando dominios...")
            domains = [
                ('agrotech-digital-production.up.railway.app', True),
                ('localhost', False)
            ]
            
            for domain, is_primary in domains:
                cursor.execute("""
                    INSERT INTO base_agrotech_domain (domain, is_primary, tenant_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (domain) DO NOTHING
                """, [domain, is_primary, tenant_id])
                print(f"✅ Dominio {domain} configurado")
            
            print("=" * 60)
            print("🎉 TABLAS CREADAS EXITOSAMENTE")
            print("🚀 Railway está listo para funcionar")
            print("=" * 60)
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
