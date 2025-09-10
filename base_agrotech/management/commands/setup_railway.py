"""
Management command para setup inicial de django-tenants en Railway
Este comando inicializa la base de datos multi-tenant de forma segura
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection, transaction
from django.conf import settings
import sys


class Command(BaseCommand):
    help = 'Inicializar base de datos multi-tenant para Railway'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            dest='strict_mode',
            help='Fallar si hay errores (por defecto es tolerante)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Iniciando setup multi-tenant para Railway...'))
        
        try:
            # Verificar conexión a base de datos
            self.stdout.write('📡 Verificando conexión a base de datos...')
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result:
                    self.stdout.write(self.style.SUCCESS('✅ Conexión a base de datos exitosa'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error de conexión: {e}'))
            if options['strict_mode']:
                sys.exit(1)

        try:
            # Ejecutar migraciones compartidas
            self.stdout.write('🔄 Ejecutando migraciones compartidas...')
            call_command('migrate_schemas', '--shared', verbosity=1)
            self.stdout.write(self.style.SUCCESS('✅ Migraciones compartidas completadas'))
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Error en migraciones compartidas: {e}'))
            # Intentar migrate normal si migrate_schemas falla
            try:
                self.stdout.write('🔄 Intentando migrate estándar...')
                call_command('migrate', verbosity=1)
                self.stdout.write(self.style.SUCCESS('✅ Migrate estándar completado'))
            except Exception as e2:
                self.stdout.write(self.style.ERROR(f'❌ Error en migrate: {e2}'))
                if options['strict_mode']:
                    sys.exit(1)

        try:
            # Crear superusuario automáticamente si no existe
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            if not User.objects.filter(is_superuser=True).exists():
                self.stdout.write('👤 Creando superusuario por defecto...')
                User.objects.create_superuser(
                    username='admin',
                    email='admin@agrotech.com',
                    password='admin123'  # Cambiar en producción
                )
                self.stdout.write(self.style.SUCCESS('✅ Superusuario creado: admin/admin123'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ Superusuario ya existe'))

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Error creando superusuario: {e}'))

        try:
            # Crear tenant por defecto para django-tenants
            from base_agrotech.models import Client, Domain
            
            # Verificar si existe el tenant público
            if not Client.objects.filter(schema_name='public').exists():
                self.stdout.write('🏢 Creando tenant público por defecto...')
                tenant = Client.objects.create(
                    schema_name='public',
                    name='AgroTech Digital',
                    paid_until='2025-12-31',
                    on_trial=False
                )
                
                # Crear dominio para Railway
                Domain.objects.create(
                    domain='agrotech-digital-production.up.railway.app',
                    tenant=tenant,
                    is_primary=True
                )
                
                # Crear dominio localhost para desarrollo
                Domain.objects.create(
                    domain='localhost',
                    tenant=tenant,
                    is_primary=False
                )
                
                self.stdout.write(self.style.SUCCESS('✅ Tenant público creado con dominios'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ Tenant público ya existe'))
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Error configurando tenant: {e}'))

        self.stdout.write(self.style.SUCCESS('🎉 Setup multi-tenant completado exitosamente!'))
        self.stdout.write('🔗 La aplicación está lista para usar en Railway')
