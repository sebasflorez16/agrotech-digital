"""
Management command para crear/actualizar el superusuario desde variables
de entorno. Útil para Railway donde no hay acceso SSH directo.

Uso en start.sh:
    python manage.py ensure_superuser

Variables de entorno requeridas:
    DJANGO_SUPERUSER_EMAIL
    DJANGO_SUPERUSER_PASSWORD
    DJANGO_SUPERUSER_USERNAME  (opcional, default: parte del email)
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Crea o actualiza el superusuario desde variables de entorno'

    def handle(self, *args, **options):
        User = get_user_model()

        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '').strip()
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()

        if not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    'ensure_superuser: DJANGO_SUPERUSER_EMAIL o '
                    'DJANGO_SUPERUSER_PASSWORD no configurados. Saltando.'
                )
            )
            return

        if not username:
            username = email.split('@')[0].replace('.', '_').replace('-', '_')

        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.username = username
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Superusuario actualizado: {email} | username: {username}'
                )
            )
        except User.DoesNotExist:
            try:
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    name='Admin',
                    last_name='AgroTech',
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Superusuario creado: {email} | username: {username}'
                    )
                )
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f'❌ Error creando superusuario: {e}')
                )
