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
    pip install --no-cache-dir numpy && \
    pip install --no-cache-dir GDAL==$(gdal-config --version) && \
    pip install --no-cache-dir -r requirements.txt


# Mostrar versión de GDAL para debug
RUN echo "GDAL version instalada:" && gdalinfo --version

# Copiar código de la aplicación
COPY . .

# Asegurar que start.sh sea ejecutable
RUN chmod +x /app/start.sh

EXPOSE $PORT

CMD ["/app/start.sh"]
