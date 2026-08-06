"""
Comando para diagnosticar y arreglar el login del superusuario.
Verifica el estado del usuario, su tenant, y resetea la contraseña
usando set_password() de Django (hash correcto con Argon2).
"""
import os

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model, authenticate
from django.db import connection
from django_tenants.utils import get_public_schema_name

User = get_user_model()


class Command(BaseCommand):
    help = 'Diagnostica y arregla el login del superusuario de pruebas'

    def add_arguments(self, parser):
        parser.add_argument('--fix', action='store_true', help='Arreglar el usuario automáticamente')
        parser.add_argument('--username', type=str, default=os.environ.get('FIX_LOGIN_USERNAME', ''))
        parser.add_argument('--password', type=str, default=os.environ.get('FIX_LOGIN_PASSWORD', ''))
        parser.add_argument('--email', type=str, default=os.environ.get('FIX_LOGIN_EMAIL', ''))

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        if not username or not password:
            raise CommandError(
                'Debes proporcionar --username y --password (o las variables de entorno '
                'FIX_LOGIN_USERNAME / FIX_LOGIN_PASSWORD). No se usan credenciales por defecto.'
            )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']
        fix = options['fix']

        # Asegurar que estamos en el schema public
        connection.set_schema(get_public_schema_name())
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"🔍 DIAGNÓSTICO DE LOGIN - Schema: {connection.schema_name}")
        self.stdout.write(f"{'='*60}\n")

        # 1. Verificar si el usuario existe
        self.stdout.write("1️⃣  Buscando usuario...")
        try:
            user = User.objects.get(username=username)
            self.stdout.write(self.style.SUCCESS(f"   ✅ Usuario encontrado: {user.username}"))
            self.stdout.write(f"   📧 Email: {user.email}")
            self.stdout.write(f"   👤 Nombre: {user.name} {user.last_name}")
            self.stdout.write(f"   🔑 is_active: {user.is_active}")
            self.stdout.write(f"   🛡️  is_staff: {user.is_staff}")
            self.stdout.write(f"   👑 is_superuser: {user.is_superuser}")
            self.stdout.write(f"   🏢 Tenant: {user.tenant}")
            self.stdout.write(f"   🔐 Password hash: {user.password[:50]}...")
            self.stdout.write(f"   🎭 Role: {user.role}")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"   ❌ Usuario '{username}' NO existe"))
            if fix:
                self.stdout.write("   🔧 Creando usuario...")
                self._create_user(username, email, password)
            return
        except User.MultipleObjectsReturned:
            self.stdout.write(self.style.ERROR(f"   ❌ HAY MÚLTIPLES usuarios con username '{username}'"))
            users = User.objects.filter(username=username)
            for u in users:
                self.stdout.write(f"      - id={u.id} email={u.email} tenant={u.tenant}")
            return

        # 2. Verificar autenticación
        self.stdout.write("\n2️⃣  Probando autenticación...")
        auth_user = authenticate(username=username, password=password)
        if auth_user:
            self.stdout.write(self.style.SUCCESS(f"   ✅ Autenticación exitosa con username"))
        else:
            self.stdout.write(self.style.ERROR(f"   ❌ Autenticación FALLIDA con username + password"))
            
            # Verificar si el hash es válido
            is_valid = user.check_password(password)
            self.stdout.write(f"   check_password() = {is_valid}")
            
            if not is_valid:
                self.stdout.write(self.style.WARNING(f"   ⚠️  La contraseña NO coincide con el hash guardado"))
                self.stdout.write(f"   Hash actual: {user.password[:80]}")
                
                # Verificar si es un hash válido de Django
                if user.password.startswith('argon2') or user.password.startswith('pbkdf2'):
                    self.stdout.write("   El hash PARECE ser un formato Django válido pero la contraseña no coincide")
                else:
                    self.stdout.write(self.style.ERROR("   ⚠️  El hash NO es un formato Django válido (probablemente se actualizó por SQL directo)"))

        # 3. Verificar por email también
        self.stdout.write("\n3️⃣  Probando búsqueda por email...")
        try:
            user_by_email = User.objects.get(email__iexact=email)
            self.stdout.write(self.style.SUCCESS(f"   ✅ Usuario encontrado por email: {user_by_email.username}"))
            if user_by_email.id != user.id:
                self.stdout.write(self.style.WARNING(f"   ⚠️  ¡Es un usuario DIFERENTE al buscado por username!"))
        except User.DoesNotExist:
            self.stdout.write(self.style.WARNING(f"   ⚠️  No se encontró usuario con email '{email}'"))

        # 4. Verificar tenant
        self.stdout.write("\n4️⃣  Verificando tenant...")
        if user.tenant:
            self.stdout.write(self.style.SUCCESS(f"   ✅ Tenant: {user.tenant.name} (schema: {user.tenant.schema_name})"))
            # Verificar dominio
            from base_agrotech.models import Domain
            domains = Domain.objects.filter(tenant=user.tenant)
            for d in domains:
                self.stdout.write(f"   🌐 Dominio: {d.domain} (primary: {d.is_primary})")
        else:
            self.stdout.write(self.style.WARNING(f"   ⚠️  Usuario NO tiene tenant asignado"))

        # 5. Listar todos los usuarios
        self.stdout.write(f"\n5️⃣  Todos los usuarios en schema public:")
        all_users = User.objects.all()
        for u in all_users:
            self.stdout.write(
                f"   id={u.id} | {u.username} | {u.email} | "
                f"active={u.is_active} | staff={u.is_staff} | "
                f"super={u.is_superuser} | tenant={u.tenant}"
            )

        # 6. FIX - Arreglar el usuario
        if fix:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write("🔧 APLICANDO CORRECCIONES...")
            self.stdout.write(f"{'='*60}\n")
            
            # Resetear contraseña usando set_password (genera hash Argon2 correcto)
            user.set_password(password)
            user.is_active = True
            user.is_staff = True
            user.is_superuser = True
            user.email = email
            user.role = 'admin'
            user.save()
            
            self.stdout.write(self.style.SUCCESS(f"   ✅ Contraseña reseteada con set_password()"))
            self.stdout.write(f"   🔐 Nuevo hash: {user.password[:50]}...")
            
            # Verificar que ahora funciona
            auth_user = authenticate(username=username, password=password)
            if auth_user:
                self.stdout.write(self.style.SUCCESS(f"   ✅ ¡Autenticación verificada exitosamente!"))
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ Aún falla la autenticación después del fix"))
            
            # Asegurar que el tenant esté asignado
            if not user.tenant:
                from base_agrotech.models import Client
                try:
                    tenant = Client.objects.get(schema_name='finca_florez')
                    user.tenant = tenant
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f"   ✅ Tenant 'finca_florez' asignado al usuario"))
                except Client.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"   ❌ Tenant 'finca_florez' no existe"))

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("📋 RESUMEN DE CREDENCIALES:")
        self.stdout.write(f"   Username: {username}")
        self.stdout.write(f"   Email: {email}")
        self.stdout.write(f"   Password: {password}")
        self.stdout.write(f"   URL Login: https://agrotechcolombia.netlify.app/templates/authentication/login.html")
        self.stdout.write(f"   API Login: POST https://agrotechcolombia.com/api/auth/login/")
        self.stdout.write(f"{'='*60}\n")

    def _create_user(self, username, email, password):
        from base_agrotech.models import Client
        try:
            tenant = Client.objects.get(schema_name='finca_florez')
        except Client.DoesNotExist:
            tenant = None
            self.stdout.write(self.style.WARNING("   ⚠️  Tenant finca_florez no encontrado"))

        user = User.objects.create_superuser(
            username=username,
            email=email,
            name='Sebastian',
            last_name='Florez',
            password=password,
        )
        user.tenant = tenant
        user.role = 'admin'
        user.save()
        self.stdout.write(self.style.SUCCESS(f"   ✅ Superusuario creado: {username}"))
