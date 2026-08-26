#!/bin/bash

# Script para iniciar el servidor Django en desarrollo
# Ubicación: agrotech-digital/start_dev_server.sh

cd "$(dirname "$0")"

# Cargar variables de .env si existe
if [ -f .env ]; then
    set -a; source .env; set +a
fi

# Variables de entorno necesarias (genera secret key temporal si no existe)
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')}"
export DJANGO_SETTINGS_MODULE="config.settings.local"
export DEBUG="True"

# Activar conda y correr servidor
echo "🚀 Iniciando servidor Django en http://localhost:8000"
echo "📝 Usando configuración: config.settings.local"
echo ""

conda run -n agro-rest python manage.py runserver 0.0.0.0:8000
