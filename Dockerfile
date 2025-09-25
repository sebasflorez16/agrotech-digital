# Usar imagen Ubuntu con Python por defecto (3.10)
FROM ubuntu:22.04

# Evitar prompts interactivos durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instalar Python y dependencias (usando la versión por defecto)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear enlace simbólico para python
RUN ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip

# Establece el directorio de trabajo
WORKDIR /app

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