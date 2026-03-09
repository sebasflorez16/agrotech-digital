#!/usr/bin/env python3
"""
Script para crear/actualizar el superusuario de producción en Railway.

Uso:
    railway run python scripts/reset_superuser_prod.py
"""
import django
import os

# Railway inyecta DATABASE_URL y demás vars, pero DJANGO_SETTINGS_MODULE
# hay que setearlo explícitamente si no está ya en las vars de Railway.
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.production'

django.setup()

from metrica.users.models import User  # noqa: E402

EMAIL = "juansebastianflorezescobar@gmail.com"
PASSWORD = "guibsonsid.16"
USERNAME = "juansebastianflorezescobar"

try:
    u = User.objects.get(email=EMAIL)
    u.set_password(PASSWORD)
    u.is_staff = True
    u.is_superuser = True
    u.is_active = True
    u.save()
    print(f"✅ PROD actualizado: {u.email} | username: {u.username} | superuser: {u.is_superuser}")
except User.DoesNotExist:
    u = User.objects.create_superuser(
        username=USERNAME,
        email=EMAIL,
        password=PASSWORD,
        name="Juan Sebastian",
        last_name="Florez Escobar",
    )
    print(f"✅ PROD creado: {u.email} | username: {u.username} | superuser: {u.is_superuser}")
