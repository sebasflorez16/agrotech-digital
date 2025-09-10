import os
import sys
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Setup Railway con diagnostico completo'

    def handle(self, *args, **options):
        self.stdout.write("RAILWAY SETUP - DIAGNOSTICO COMPLETO")
        
        database_url = os.environ.get('DATABASE_URL', 'NO CONFIGURADO')
        django_settings = os.environ.get('DJANGO_SETTINGS_MODULE', 'NO CONFIGURADO')
        
        self.stdout.write(f"DJANGO_SETTINGS_MODULE: {django_settings}")
        if database_url != 'NO CONFIGURADO':
            self.stdout.write(f"DATABASE_URL: {database_url[:50]}...")
        else:
            self.stdout.write(f"DATABASE_URL: {database_url}")
        
        try:
            from django.conf import settings
            db_config = settings.DATABASES['default']
            self.stdout.write(f"ENGINE: {db_config.get('ENGINE', 'NO CONFIGURADO')}")
            self.stdout.write(f"HOST: {db_config.get('HOST', 'NO CONFIGURADO')}")
            self.stdout.write(f"PORT: {db_config.get('PORT', 'NO CONFIGURADO')}")
            self.stdout.write(f"NAME: {db_config.get('NAME', 'NO CONFIGURADO')}")
            self.stdout.write(f"USER: {db_config.get('USER', 'NO CONFIGURADO')}")
        except Exception as e:
            self.stdout.write(f"Error accediendo a configuracion: {e}")
            return
        
        if database_url == 'NO CONFIGURADO':
            self.stdout.write("DATABASE_URL no esta configurado")
            return
        
        try:
            self.stdout.write("Verificando conexion a base de datos...")
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                self.stdout.write(f"PostgreSQL conectado: {version}")
                
                self.stdout.write("Creando tablas base...")
                
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
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS base_agrotech_domain (
                        id SERIAL PRIMARY KEY,
                        domain VARCHAR(253) UNIQUE NOT NULL,
                        tenant_id INTEGER REFERENCES base_agrotech_client(id) ON DELETE CASCADE,
                        is_primary BOOLEAN DEFAULT FALSE
                    );
                """)
                
                self.stdout.write("Tablas base creadas")
                
                cursor.execute("SELECT COUNT(*) FROM base_agrotech_client WHERE schema_name = 'public';")
                public_exists = cursor.fetchone()[0] > 0
                
                if not public_exists:
                    cursor.execute("""
                        INSERT INTO base_agrotech_client (schema_name, name, description)
                        VALUES ('public', 'Public Schema', 'Schema publico para Railway')
                        ON CONFLICT (schema_name) DO NOTHING;
                    """)
                    self.stdout.write("Tenant publico creado")
                else:
                    self.stdout.write("Tenant publico ya existe")
                
                cursor.execute("SELECT id FROM base_agrotech_client WHERE schema_name = 'public';")
                tenant_id = cursor.fetchone()[0]
                
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
                    self.stdout.write(f"Dominio {domain_name} configurado")
                
                self.stdout.write("SETUP COMPLETADO EXITOSAMENTE")
                
        except Exception as e:
            self.stdout.write(f"Error de conexion: {e}")
            import traceback
            self.stdout.write(traceback.format_exc())
            raise
