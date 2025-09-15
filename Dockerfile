# Usa una imagen oficial de Python - versión slim para mejor rendimiento
FROM python:3.11-slim-bullseye

# Establece el directorio de trabajo
WORKDIR /app

# Instala dependencias del sistema necesarias para psycopg2 y otras librerías
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

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
