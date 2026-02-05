#!/bin/bash

# Script para iniciar el servidor Django en desarrollo
# Ubicación: agrotech-digital/start_dev_server.sh

cd "$(dirname "$0")"

# Variables de entorno necesarias
export DJANGO_SECRET_KEY="django-insecure-dev-key-local-only-not-for-production-12345"
export DJANGO_SETTINGS_MODULE="config.settings.local"
export DEBUG="True"

# Activar conda y correr servidor
echo "🚀 Iniciando servidor Django en http://localhost:8000"
echo "📝 Usando configuración: config.settings.local"
echo ""

conda run -n agro-rest python manage.py runserver 0.0.0.0:8000
