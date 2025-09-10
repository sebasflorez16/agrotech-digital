#!/bin/bash
echo "🚀 Iniciando aplicación AgroTech Digital..."
echo "🔍 Puerto detectado: ${PORT:-'NO CONFIGURADO'}"
echo "🔍 DJANGO_SETTINGS_MODULE: ${DJANGO_SETTINGS_MODULE:-'NO CONFIGURADO'}"
echo "🔍 DATABASE_URL: ${DATABASE_URL:0:50}..." # Solo primeros 50 caracteres por seguridad

# Usar puerto por defecto si no está configurado
DETECTED_PORT=${PORT:-8080}
echo "✅ Usando puerto: $DETECTED_PORT"

# Iniciar Gunicorn con configuración optimizada para Railway
exec gunicorn config.wsgi \
    --bind 0.0.0.0:$DETECTED_PORT \
    --workers 2 \
    --timeout 120 \
    --keepalive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --worker-class sync
