#!/bin/bash
echo "🚀 Iniciando aplicación AgroTech Digital..."

# Configurar Django settings si no está configurado
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"
echo "🔍 DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
echo "🔍 DATABASE_URL: ${DATABASE_URL:0:50}..." # Solo primeros 50 caracteres por seguridad

# Railway proporciona PORT automáticamente, usar ese puerto exacto
DETECTED_PORT=${PORT:-8080}
echo "✅ Railway PORT: $DETECTED_PORT"

# Iniciar Gunicorn en 0.0.0.0 con el puerto exacto de Railway
exec gunicorn config.wsgi \
    --bind 0.0.0.0:$DETECTED_PORT \
    --workers 2 \
    --timeout 120 \
    --max-requests 1000 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --worker-class sync
