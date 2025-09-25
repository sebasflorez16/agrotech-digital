FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV DJANGO_SETTINGS_MODULE=config.settings.production

COPY requirements.txt /app/

RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY . /app

RUN chmod +x start.sh

EXPOSE 8080

CMD ["./start.sh"]