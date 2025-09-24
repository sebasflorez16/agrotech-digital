import os
import sys
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import time

class Command(BaseCommand):
    help = 'Setup Railway con diagnostico completo y retry logic'

    def handle(self, *args, **options):
        print("=" * 50)
        print("RAILWAY SETUP - DIAGNOSTICO COMPLETO")
        print("=" * 50)
        sys.stdout.flush()
        
        # Verificar variables de entorno
        print("Verificando variables de entorno...")
        database_url = os.environ.get('DATABASE_URL', 'NO CONFIGURADO')
        django_settings = os.environ.get('DJANGO_SETTINGS_MODULE', 'NO CONFIGURADO')
        
        print(f"DJANGO_SETTINGS_MODULE: {django_settings}")
        if database_url != 'NO CONFIGURADO':
            print(f"DATABASE_URL: {database_url[:50]}...")
        else:
            print(f"DATABASE_URL: {database_url}")
        sys.stdout.flush()
        
        # Verificar configuracion Django
        print("Verificando configuracion de Django...")
        try:
            db_config = settings.DATABASES['default']
            print(f"ENGINE: {db_config.get('ENGINE', 'NO CONFIGURADO')}")
            print(f"HOST: {db_config.get('HOST', 'NO CONFIGURADO')}")
            print(f"PORT: {db_config.get('PORT', 'NO CONFIGURADO')}")
            print(f"NAME: {db_config.get('NAME', 'NO CONFIGURADO')}")
            print(f"USER: {db_config.get('USER', 'NO CONFIGURADO')}")
            sys.stdout.flush()
        except Exception as e:
            print(f"Error accediendo a configuracion: {e}")
            sys.stdout.flush()
            return
        
        if database_url == 'NO CONFIGURADO':
            print("DATABASE_URL no esta configurado")
            sys.stdout.flush()
            return
        
        # Retry logic para conexión
        max_retries = 5
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"Intento de conexión {attempt + 1}/{max_retries}...")
                sys.stdout.flush()
                
                # Conectar y crear tablas
                with connection.cursor() as cursor:
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]
                    print(f"PostgreSQL conectado exitosamente: {version}")
                    sys.stdout.flush()
                    
                    print("Creando tablas base...")
                    sys.stdout.flush()
                    
                    # Tabla Client
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS base_agrotech_client (
                            id SERIAL PRIMARY KEY,
                            schema_name VARCHAR(63) UNIQUE NOT NULL,
                            name VARCHAR(100) NOT NULL,
                            description TEXT,
                            created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            uuid UUID DEFAULT gen_random_uuid()
                        );
                    """)
                    
                    # Tabla Domain
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS base_agrotech_domain (
                            id SERIAL PRIMARY KEY,
                            domain VARCHAR(253) UNIQUE NOT NULL,
                            tenant_id INTEGER REFERENCES base_agrotech_client(id) ON DELETE CASCADE,
                            is_primary BOOLEAN DEFAULT FALSE
                        );
                    """)
                    
                    print("Tablas base creadas exitosamente")
                    sys.stdout.flush()
                    
                    print("Configurando tenant publico...")
                    sys.stdout.flush()
                    
                    # Crear tenant publico
                    cursor.execute("SELECT COUNT(*) FROM base_agrotech_client WHERE schema_name = 'public';")
                    public_exists = cursor.fetchone()[0] > 0
                    
                    if not public_exists:
                        cursor.execute("""
                            INSERT INTO base_agrotech_client (schema_name, name, description)
                            VALUES ('public', 'Public Schema', 'Schema publico para Railway')
                            ON CONFLICT (schema_name) DO NOTHING;
                        """)
                        print("Tenant publico creado")
                    else:
                        print("Tenant publico ya existe")
                    
                    sys.stdout.flush()
                    
                    # Obtener ID del tenant
                    cursor.execute("SELECT id FROM base_agrotech_client WHERE schema_name = 'public';")
                    tenant_id = cursor.fetchone()[0]
                    
                    # Crear dominios
                    domains = [
                        ('agrotech-digital-production.up.railway.app', True),
                        ('localhost', False)
                    ]
                    
                    for domain_name, is_primary in domains:
                        cursor.execute("""
                            INSERT INTO base_agrotech_domain (domain, tenant_id, is_primary)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (domain) DO NOTHING;
                        """, [domain_name, tenant_id, is_primary])
                        print(f"Dominio {domain_name} configurado")
                        sys.stdout.flush()
                    
                    print("=" * 50)
                    print("SETUP COMPLETADO EXITOSAMENTE")
                    print("=" * 50)
                    sys.stdout.flush()
                    
                    # Si llegamos aquí, todo salió bien
                    return
                    
            except Exception as e:
                print(f"Intento {attempt + 1} falló: {e}")
                sys.stdout.flush()
                
                if attempt < max_retries - 1:
                    print(f"Reintentando en {retry_delay} segundos...")
                    sys.stdout.flush()
                    time.sleep(retry_delay)
                else:
                    print("=" * 50)
                    print(f"Error final después de {max_retries} intentos: {e}")
                    print("=" * 50)
                    sys.stdout.flush()
                    import traceback
                    print(traceback.format_exc())
                    sys.stdout.flush()
                    sys.exit(1)