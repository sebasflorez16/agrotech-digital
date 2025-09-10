"""
Management command para setup inicial de django-tenants en Railway
Versión simplificada con enfoque en crear tablas base
"""
import os
import sys
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.conf import settings

class Command(BaseCommand):
    help = 'Setup simplificado para django-tenants en Railway'

    def handle(self, *args, **options):
        # Forzar salida inmediata
        print("=" * 60)
        print("🚀 RAILWAY SETUP - INICIANDO")
        print("=" * 60)
        sys.stdout.flush()
        
        try:
            # 1. Verificar conexión
            print("📡 Verificando conexión a base de datos...")
            sys.stdout.flush()
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                print(f"✅ PostgreSQL conectado: {version[:50]}")
                sys.stdout.flush()
            
            # 2. Crear tablas con migrate simple
            print("� Creando tablas base...")
            sys.stdout.flush()
            
            call_command('migrate', '--run-syncdb', verbosity=2, interactive=False)
            print("✅ Tablas base creadas")
            sys.stdout.flush()
            
            # 3. Verificar si base_agrotech_client existe
            print("🔍 Verificando tabla base_agrotech_client...")
            sys.stdout.flush()
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'base_agrotech_client'
                    );
                """)
                table_exists = cursor.fetchone()[0]
                
                if table_exists:
                    print("✅ Tabla base_agrotech_client existe")
                else:
                    print("❌ Tabla base_agrotech_client NO existe")
                    # Crear manualmente
                    print("🔧 Creando tabla manualmente...")
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
                    print("✅ Tabla base_agrotech_client creada manualmente")
                sys.stdout.flush()
            
            # 4. Crear tabla domain si no existe
            print("🔍 Verificando tabla base_agrotech_domain...")
            sys.stdout.flush()
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'base_agrotech_domain'
                    );
                """)
                domain_exists = cursor.fetchone()[0]
                
                if not domain_exists:
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
                else:
                    print("✅ Tabla base_agrotech_domain existe")
                sys.stdout.flush()
            
            # 5. Crear tenant público
            print("🏢 Creando tenant público...")
            sys.stdout.flush()
            
            with connection.cursor() as cursor:
                # Verificar si existe
                cursor.execute("SELECT COUNT(*) FROM base_agrotech_client WHERE schema_name = 'public'")
                public_exists = cursor.fetchone()[0]
                
                if public_exists == 0:
                    cursor.execute("""
                        INSERT INTO base_agrotech_client (schema_name, name, paid_until, on_trial)
                        VALUES ('public', 'Public Schema', '2025-12-31', FALSE)
                        ON CONFLICT (schema_name) DO NOTHING
                    """)
                    print("✅ Tenant público creado")
                else:
                    print("✅ Tenant público ya existe")
                
                # Obtener ID del tenant público
                cursor.execute("SELECT id FROM base_agrotech_client WHERE schema_name = 'public'")
                tenant_id = cursor.fetchone()[0]
                
                # Crear dominios
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
                
                sys.stdout.flush()
            
            print("=" * 60)
            print("🎉 RAILWAY SETUP - COMPLETADO EXITOSAMENTE")
            print("=" * 60)
            sys.stdout.flush()
            
        except Exception as e:
            print("=" * 60)
            print(f"❌ ERROR CRÍTICO: {e}")
            print("=" * 60)
            import traceback
            print(traceback.format_exc())
            sys.stdout.flush()
            sys.exit(1)