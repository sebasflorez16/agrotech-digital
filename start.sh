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

# Verificar que Django esté disponible antes del setup
echo "🔧 Verificando disponibilidad de Django..."
DJANGO_SETTINGS_MODULE=config.settings.production python -c "import django; print('Django disponible')" 2>/dev/null
django_available=$?

if [ $django_available -eq 0 ]; then
    # Ejecutar setup de Railway con variables de entorno disponibles
    echo "🔧 Ejecutando setup de Railway..."
    echo "📋 Comando: python manage.py setup_railway"

    DJANGO_SETTINGS_MODULE=config.settings.production python manage.py setup_railway 2>&1
    setup_exit_code=$?

    echo "📊 Setup exit code: $setup_exit_code"

    if [ $setup_exit_code -ne 0 ]; then
        echo "❌ Setup de Railway falló con código: $setup_exit_code"
        echo "🚨 Intentando script de emergencia..."
        
        # Fallback: ejecutar script de emergencia
        DJANGO_SETTINGS_MODULE=config.settings.production python fix_railway_tables.py 2>&1
        emergency_exit_code=$?
        
        echo "📊 Emergency script exit code: $emergency_exit_code"
        
        if [ $emergency_exit_code -ne 0 ]; then
            echo "❌ Script de emergencia también falló"
            echo "🚨 Continuando sin setup (puede causar errores)"
        else
            echo "✅ Script de emergencia completado exitosamente"
        fi
    else
        echo "✅ Setup de Railway completado exitosamente"
    fi
else
    echo "⚠️ Django no disponible, saltando setup de Railway"
    echo "🚨 Continuando con inicio del servidor..."
fi

# Recopilar archivos estáticos para producción
echo "📁 Recopilando archivos estáticos..."
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py collectstatic --noinput --clear
collectstatic_exit_code=$?

if [ $collectstatic_exit_code -eq 0 ]; then
    echo "✅ Archivos estáticos recopilados exitosamente"
else
    echo "⚠️ Error recopilando archivos estáticos (código: $collectstatic_exit_code)"
    echo "🚨 Continuando..."
fi

echo "🚀 Iniciando Gunicorn en puerto $PORT..."

# Iniciar gunicorn con configuración optimizada para Railway
exec gunicorn config.wsgi \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --env DJANGO_SETTINGS_MODULE=config.settings.production
