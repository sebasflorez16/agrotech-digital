# Dockerfile para Django + GDAL en Railway
FROM python:3.12-slim

# Instala dependencias nativas necesarias para GDAL
RUN apt-get update && \
    apt-get install -y gdal-bin libgdal-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Variables de entorno para GDAL
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8000

# Aplica migraciones antes de arrancar gunicorn
CMD ["/bin/bash", "-c", "python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:8000"]
