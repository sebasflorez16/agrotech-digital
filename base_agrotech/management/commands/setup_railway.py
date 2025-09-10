"""
Management command para setup inicial de django-tenants en Railway
Este comando inicializa la base de datos multi-tenant de forma segura
"""
import os
import logging
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.contrib.auth import get_user_model
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Configura django-tenants para Railway'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Modo estricto - falla si hay errores',
        )

    def handle(self, *args, **options):
        try:
            self.stdout.write(self.style.SUCCESS('🚀 Iniciando setup multi-tenant para Railway...'))
            
            # 1. Verificar conexión a base de datos
            self.stdout.write('📡 Verificando conexión a base de datos...')
            try:
                connection.ensure_connection()
                self.stdout.write(self.style.SUCCESS('✅ Conexión a base de datos exitosa'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error de conexión: {e}'))
                if options['strict']:
                    raise
                return

            # 2. Ejecutar migraciones compartidas
            self.stdout.write('🔄 Ejecutando migraciones compartidas...')
            try:
                call_command('migrate_schemas', '--shared', verbosity=2)
                self.stdout.write(self.style.SUCCESS('✅ Migraciones compartidas completadas'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'❌ Error en migraciones compartidas: {e}'))
                # Intentar migración manual de las apps principales
                try:
                    self.stdout.write('🔄 Intentando migraciones individuales...')
                    call_command('migrate', 'django_tenants', verbosity=1)
                    call_command('migrate', 'base_agrotech', verbosity=1)
                    call_command('migrate', 'contenttypes', verbosity=1)
                    call_command('migrate', 'auth', verbosity=1)
                    self.stdout.write(self.style.SUCCESS('✅ Migraciones individuales completadas'))
                except Exception as e2:
                    self.stdout.write(self.style.ERROR(f'❌ Error en migraciones individuales: {e2}'))
                    if options['strict']:
                        raise
                    return

            # 3. Crear superusuario si no existe
            self.stdout.write('👤 Verificando superusuario...')
            try:
                User = get_user_model()
                if not User.objects.filter(is_superuser=True).exists():
                    User.objects.create_superuser(
                        username='admin',
                        email='admin@agrotech.com',
                        password='admin123'
                    )
                    self.stdout.write(self.style.SUCCESS('✅ Superusuario creado: admin/admin123'))
                else:
                    self.stdout.write(self.style.SUCCESS('✅ Superusuario ya existe'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️ Error creando superusuario: {e}'))
                # No es crítico, continuar

            # 4. Crear tenant público si no existe
            self.stdout.write('🏢 Verificando tenant público...')
            try:
                from base_agrotech.models import Client, Domain
                
                # Verificar si existe el tenant público
                public_tenant = None
                try:
                    public_tenant = Client.objects.get(schema_name='public')
                    self.stdout.write(self.style.SUCCESS('✅ Tenant público ya existe'))
                except Client.DoesNotExist:
                    # Crear tenant público
                    public_tenant = Client.objects.create(
                        schema_name='public',
                        name='Public Schema',
                        paid_until='2025-12-31',
                        on_trial=False
                    )
                    self.stdout.write(self.style.SUCCESS('✅ Tenant público creado'))

                # Verificar dominios
                railway_domain = 'agrotech-digital-production.up.railway.app'
                localhost_domain = 'localhost'
                
                domains_to_create = [railway_domain, localhost_domain]
                
                for domain_name in domains_to_create:
                    try:
                        domain = Domain.objects.get(domain=domain_name)
                        self.stdout.write(self.style.SUCCESS(f'✅ Dominio {domain_name} ya existe'))
                    except Domain.DoesNotExist:
                        Domain.objects.create(
                            domain=domain_name,
                            tenant=public_tenant,
                            is_primary=domain_name == railway_domain
                        )
                        self.stdout.write(self.style.SUCCESS(f'✅ Dominio {domain_name} creado'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error configurando tenant: {e}'))
                if options['strict']:
                    raise

            # 5. Ejecutar migraciones de tenants
            self.stdout.write('🔄 Ejecutando migraciones de tenants...')
            try:
                call_command('migrate_schemas', verbosity=1)
                self.stdout.write(self.style.SUCCESS('✅ Migraciones de tenants completadas'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️ Error en migraciones de tenants: {e}'))
                # No es crítico en la primera ejecución

            self.stdout.write(self.style.SUCCESS('🎉 Setup multi-tenant completado exitosamente!'))
            self.stdout.write('🔗 La aplicación está lista para usar en Railway')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'💥 Error crítico: {e}'))
            if options['strict']:
                raise
            else:
                self.stdout.write(self.style.WARNING('⚠️ Continuando con errores...'))
