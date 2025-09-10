#!/bin/bash
echo "🚀 Iniciando aplicación AgroTech Digital..."

# Configurar Django settings si no está configurado
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"
echo "🔍 DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
echo "🔍 DATABASE_URL: ${DATABASE_URL:0:50}..." # Solo primeros 50 caracteres por seguridad

# Railway proporciona PORT automáticamente, usar ese puerto exacto
DETECTED_PORT=${PORT:-8080}
echo "✅ Railway PORT: $DETECTED_PORT"

#!/bin/bash

echo "🚀 Iniciando aplicación AgroTech Digital..."

# Configurar variables de entorno críticas
export DJANGO_SETTINGS_MODULE="config.settings.production"

# Detectar puerto de Railway
if [ -z "$PORT" ]; then
    export PORT=8080
    echo "⚠️ PORT no configurado, usando 8080 por defecto"
else
    echo "✅ Railway PORT detectado: $PORT"
fi

echo "🔍 DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"

# Verificar DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL no configurado"
    exit 1
else
    echo "✅ DATABASE_URL configurado: ${DATABASE_URL:0:50}..."
fi

echo "🚀 Iniciando Gunicorn en puerto $PORT..."

# Iniciar gunicorn con configuración optimizada para Railway
exec gunicorn config.wsgi 
    --bind 0.0.0.0:$PORT 
    --workers 2 
    --timeout 120 
    --max-requests 1000 
    --max-requests-jitter 100 
    --log-level info 
    --access-logfile - 
    --error-logfile -
