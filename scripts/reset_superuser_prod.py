#!/usr/bin/env python3
"""
Script para crear/actualizar el superusuario de producción en Railway.

Uso:
    railway run python scripts/reset_superuser_prod.py

Las credenciales se leen de variables de entorno:
    SUPERUSER_EMAIL    - Email del superusuario
    SUPERUSER_PASSWORD - Contraseña del superusuario
    SUPERUSER_USERNAME - Username del superusuario
"""
import django
import os
import sys
import getpass

# Railway inyecta DATABASE_URL y demás vars, pero DJANGO_SETTINGS_MODULE
# hay que setearlo explícitamente si no está ya en las vars de Railway.
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.production'

django.setup()

from metrica.users.models import User  # noqa: E402

# Leer credenciales de variables de entorno o solicitar interactivamente
EMAIL = os.environ.get('SUPERUSER_EMAIL')
PASSWORD = os.environ.get('SUPERUSER_PASSWORD')
USERNAME = os.environ.get('SUPERUSER_USERNAME')

if not EMAIL:
    EMAIL = input("📧 Email del superusuario: ").strip()
if not USERNAME:
    USERNAME = input("👤 Username del superusuario: ").strip()
if not PASSWORD:
    PASSWORD = getpass.getpass("🔑 Contraseña del superusuario: ").strip()

if not all([EMAIL, USERNAME, PASSWORD]):
    print("❌ Todos los campos son obligatorios (email, username, password)")
    sys.exit(1)

if len(PASSWORD) < 8:
    print("❌ La contraseña debe tener al menos 8 caracteres")
    sys.exit(1)

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
        name="Admin",
        last_name="AgroTech",
    )
    print(f"✅ PROD creado: {u.email} | username: {u.username} | superuser: {u.is_superuser}")
