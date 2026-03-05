#!/bin/bash
set -e

echo "🚀 Iniciando aplicación AgroTech Digital..."

# ============================================================
# 1. VERIFICACIÓN DE VARIABLES DE ENTORNO
# ============================================================
echo "🔍 Verificando variables críticas de Railway..."
env | grep -E "(DATABASE|POSTGRES|DB_|RAILWAY)" | head -10

# Verificar DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️ DATABASE_URL no está configurado, buscando variables alternativas..."
    
    if [ ! -z "$PGHOST" ] && [ ! -z "$PGDATABASE" ]; then
        export DATABASE_URL="postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE"
        echo "✅ DATABASE_URL construido desde variables PG: ${DATABASE_URL:0:50}..."
    else
        echo "❌ No se pueden construir credenciales de base de datos"
        exit 1
    fi
else
    echo "✅ DATABASE_URL configurado: ${DATABASE_URL:0:50}..."
fi

# Configurar variables de entorno
export DJANGO_SETTINGS_MODULE="config.settings.production"

if [ -z "$PORT" ]; then
    export PORT=8080
    echo "⚠️ PORT no configurado, usando 8080 por defecto"
else
    echo "✅ Railway PORT detectado: $PORT"
fi

echo "🔍 DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"

# ============================================================
# 2. ESPERAR CONEXIÓN A BASE DE DATOS
# ============================================================
echo "==> Esperando conexión a base de datos..."
max_retries=30
count=0
until python -c "
import os, psycopg2
psycopg2.connect(os.environ['DATABASE_URL'])
print('✅ Conexión a base de datos exitosa')
" 2>/dev/null || [ $count -eq $max_retries ]; do
    count=$((count+1))
    echo "Intento $count/$max_retries..."
    sleep 2
done

if [ $count -eq $max_retries ]; then
    echo "❌ No se pudo conectar a la base de datos después de $max_retries intentos"
    exit 1
fi

# ============================================================
# 3. SETUP INICIAL (tablas base multi-tenant)
# ============================================================
echo "🔧 Ejecutando setup de Railway (tablas base multi-tenant)..."
python manage.py setup_railway 2>&1 || {
    echo "⚠️ Setup de Railway falló, intentando script de emergencia..."
    python fix_railway_tables.py 2>&1 || echo "⚠️ Script de emergencia también falló, continuando..."
}

# ============================================================
# 4. MIGRACIONES DE DJANGO (django-tenants)
# ============================================================
echo "🔄 Ejecutando migraciones del esquema público (shared)..."
python manage.py migrate_schemas --shared --noinput 2>&1
echo "✅ Migraciones shared completadas"

echo "🔄 Ejecutando migraciones de tenants..."
python manage.py migrate_schemas --noinput 2>&1
echo "✅ Migraciones de tenants completadas"

# ============================================================
# 5. DATOS INICIALES
# ============================================================
echo "📦 Cargando datos iniciales..."
python manage.py seed_plans 2>&1 || echo "⚠️ seed_plans falló (puede que ya existan)"
python manage.py seed_crop_types 2>&1 || echo "⚠️ seed_crop_types falló (puede que ya existan)"
python manage.py populate_crop_catalog 2>&1 || echo "⚠️ populate_crop_catalog falló (puede que ya existan)"

# ============================================================
# 5b. SUPERUSUARIO (solo si DJANGO_SUPERUSER_EMAIL está definido)
# ============================================================
if [ ! -z "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "👤 Creando/actualizando superusuario: $DJANGO_SUPERUSER_EMAIL"
    python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()
from metrica.users.models import User
email = os.environ['DJANGO_SUPERUSER_EMAIL']
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'changeme123!')
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', email.split('@')[0])
try:
    u = User.objects.get(email=email)
    u.set_password(password); u.is_staff=True; u.is_superuser=True; u.is_active=True; u.save()
    print(f'✅ Superusuario actualizado: {email}')
except User.DoesNotExist:
    u = User.objects.create_superuser(username=username, email=email, password=password, name='Admin', last_name='AgroTech')
    print(f'✅ Superusuario creado: {email}')
" 2>&1 || echo "⚠️ No se pudo crear el superusuario"
fi

# ============================================================
# 6. ARCHIVOS ESTÁTICOS
# ============================================================
echo "📁 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput 2>/dev/null || echo "⚠️ collectstatic falló"

# ============================================================
# 7. INICIAR SERVIDOR
# ============================================================
echo "🚀 Iniciando Gunicorn en puerto $PORT..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
