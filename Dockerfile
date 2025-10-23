# Dockerfile para Django + GDAL + django-tenants en Railway
FROM python:3.11-slim

# Variables de entorno para evitar prompts interactivos
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema (GDAL + PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    gcc \
    g++ \
    make \
    postgresql-client \
    binutils \
    && rm -rf /var/lib/apt/lists/*

# Configurar variables de entorno para GDAL y PROJ
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal \
    C_INCLUDE_PATH=/usr/include/gdal \
    GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so.32 \
    GDAL_DATA=/usr/share/gdal \
    PROJ_LIB=/usr/share/proj

WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .

# Instalar pip y numpy primero (para que GDAL lo encuentre al compilar)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Mostrar versión de GDAL para debug
RUN echo "GDAL version instalada:" && gdalinfo --version

# Copiar código de la aplicación
COPY . .

# Script de inicio con retry logic para la base de datos
RUN echo '#!/bin/bash\n\
set -e\n\
echo "==> Esperando conexión a base de datos..."\n\
max_retries=30\n\
count=0\n\
until python -c "import psycopg2; psycopg2.connect(\"$DATABASE_URL\")" 2>/dev/null || [ $count -eq $max_retries ]; do\n\
  count=$((count+1))\n\
  echo "Intento $count/$max_retries..."\n\
  sleep 2\n\
done\n\
\n\
if [ $count -eq $max_retries ]; then\n\
  echo "ERROR: No se pudo conectar a la base de datos"\n\
  exit 1\n\
fi\n\
\n\
echo "==> Ejecutando migraciones del esquema público..."\n\
python manage.py migrate_schemas --shared --noinput\n\
\n\
echo "==> Ejecutando migraciones de tenants..."\n\
python manage.py migrate_schemas --noinput\n\
\n\
echo "==> Iniciando servidor Gunicorn..."\n\
exec gunicorn config.wsgi:application \\\n\
  --bind 0.0.0.0:$PORT \\\n\
  --workers 2 \\\n\
  --timeout 120 \\\n\
  --log-level info \\\n\
  --access-logfile - \\\n\
  --error-logfile -\n\
' > /app/start.sh && chmod +x /app/start.sh

EXPOSE $PORT

CMD ["/app/start.sh"]
