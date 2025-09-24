# Usar imagen Ubuntu con Python (evita problemas con Docker Hub)
FROM ubuntu:22.04

# Instalar Python y dependencias
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-pip \
    python3.11-dev \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear enlace simbólico para python
RUN ln -s /usr/bin/python3.11 /usr/bin/python && \
    ln -s /usr/bin/pip3.11 /usr/bin/pip

# Establece el directorio de trabajo
WORKDIR /app

# Instala dependencias del sistema necesarias para psycopg2 y otras librerías
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Establece la variable de entorno para Django en producción
ENV DJANGO_SETTINGS_MODULE=config.settings.production

# Copia requirements primero para aprovechar cache de Docker
COPY requirements.txt /app/

# Instala las dependencias Python
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia el resto de archivos del proyecto
COPY . /app

# Hace el script de inicio ejecutable
RUN chmod +x start.sh

# Expone el puerto para Railway
EXPOSE 8080

# Usa el script de inicio optimizado para Railway
CMD ["./start.sh"]
