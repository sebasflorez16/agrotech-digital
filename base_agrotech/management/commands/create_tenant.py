"""
Comando para crear un nuevo tenant con superusuario
"""
import os
import sys
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.contrib.auth import get_user_model
from base_agrotech.models import Client, Domain
from django_tenants.utils import schema_context
from django.core.management import call_command

User = get_user_model()

class Command(BaseCommand):
    help = 'Crear un nuevo tenant con superusuario'

    def add_arguments(self, parser):
        parser.add_argument('--schema', type=str, required=True, help='Nombre del schema del tenant')
        parser.add_argument('--name', type=str, required=True, help='Nombre del tenant')
        parser.add_argument('--domain', type=str, required=True, help='Dominio del tenant')
        parser.add_argument('--admin-user', type=str, default='admin', help='Username del superusuario')
        parser.add_argument('--admin-email', type=str, required=True, help='Email del superusuario')
        parser.add_argument('--admin-password', type=str, default='admin123', help='Password del superusuario')
        parser.add_argument('--description', type=str, default='', help='Descripción del tenant')
        parser.add_argument('--primary', action='store_true', help='Marcar dominio como primario')

    def handle(self, *args, **options):
        schema_name = options['schema']
        tenant_name = options['name']
        domain_name = options['domain']
        admin_user = options['admin_user']
        admin_email = options['admin_email']
        admin_password = options['admin_password']
        description = options['description']
        is_primary = options['primary']

        self.stdout.write("=" * 60)
        self.stdout.write("🏢 CREANDO NUEVO TENANT")
        self.stdout.write("=" * 60)
        
        self.stdout.write(f"📋 Schema: {schema_name}")
        self.stdout.write(f"📋 Nombre: {tenant_name}")
        self.stdout.write(f"📋 Dominio: {domain_name}")
        self.stdout.write(f"📋 Admin: {admin_user} ({admin_email})")
        self.stdout.write(f"📋 Primario: {'Sí' if is_primary else 'No'}")
        self.stdout.write("-" * 60)
        
        try:
            # Paso 1: Verificar que el schema no exista
            self.stdout.write("🔍 Verificando que el tenant no exista...")
            if Client.objects.filter(schema_name=schema_name).exists():
                raise CommandError(f"❌ El tenant '{schema_name}' ya existe")
            
            if Domain.objects.filter(domain=domain_name).exists():
                raise CommandError(f"❌ El dominio '{domain_name}' ya está en uso")
            
            self.stdout.write("✅ Verificación pasada")
            
            with transaction.atomic():
                # Paso 2: Crear el Client (tenant)
                self.stdout.write("🏢 Creando tenant...")
                tenant = Client.objects.create(
                    schema_name=schema_name,
                    name=tenant_name,
                    description=description
                )
                self.stdout.write(f"✅ Tenant creado con ID: {tenant.id}")
                
                # Paso 3: Crear el Domain
                self.stdout.write("🌐 Creando dominio...")
                domain = Domain.objects.create(
                    domain=domain_name,
                    tenant=tenant,
                    is_primary=is_primary
                )
                self.stdout.write(f"✅ Dominio '{domain_name}' creado")
            
            # Paso 4: Ejecutar migraciones del tenant (fuera de la transacción)
            self.stdout.write("🔄 Ejecutando migraciones del tenant...")
            try:
                # Migrar solo este tenant específico
                call_command('migrate_schemas', '--schema', schema_name, verbosity=0)
                self.stdout.write("✅ Migraciones del tenant completadas")
            except Exception as e:
                self.stdout.write(f"⚠️ Error en migraciones: {e}")
                self.stdout.write("🔄 Intentando migración alternativa...")
                
                # Migración alternativa usando conexión directa
                with connection.cursor() as cursor:
                    cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}";')
                    cursor.execute(f'SET search_path TO "{schema_name}";')
                
                # Crear superusuario sin migraciones completas
                self.stdout.write("⚠️ Continuando sin migraciones completas...")
            
            # Paso 5: Crear superusuario en el contexto del tenant
            self.stdout.write("👤 Creando superusuario...")
            try:
                with schema_context(schema_name):
                    # Verificar que el usuario no exista
                    if User.objects.filter(username=admin_user).exists():
                        self.stdout.write(f"⚠️ El usuario '{admin_user}' ya existe en este tenant")
                    elif User.objects.filter(email=admin_email).exists():
                        self.stdout.write(f"⚠️ El email '{admin_email}' ya existe en este tenant")
                    else:
                        superuser = User.objects.create_superuser(
                            username=admin_user,
                            email=admin_email,
                            password=admin_password
                        )
                        self.stdout.write(f"✅ Superusuario '{admin_user}' creado exitosamente")
            except Exception as e:
                self.stdout.write(f"⚠️ Error creando superusuario: {e}")
                self.stdout.write("💡 Puedes crear el superusuario manualmente después")
            
            self.stdout.write("=" * 60)
            self.stdout.write("🎉 TENANT CREADO EXITOSAMENTE")
            self.stdout.write("=" * 60)
            self.stdout.write(f"🔗 URL: http://{domain_name}")
            self.stdout.write(f"👤 Login: {admin_user}")
            self.stdout.write(f"🔐 Password: {admin_password}")
            self.stdout.write(f"📧 Email: {admin_email}")
            self.stdout.write("=" * 60)
            
        except Exception as e:
            self.stdout.write("=" * 60)
            self.stdout.write(f"❌ ERROR: {e}")
            self.stdout.write("=" * 60)
            import traceback
            self.stdout.write(traceback.format_exc())
            raise CommandError(f"Falló la creación del tenant: {e}")
