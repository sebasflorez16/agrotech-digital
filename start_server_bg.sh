#!/bin/bash
source $(conda info --base)/etc/profile.d/conda.sh
conda activate agro-rest

# Cargar variables de .env si existe
if [ -f .env ]; then
    set -a; source .env; set +a
fi

export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')}"
export DJANGO_SETTINGS_MODULE="config.settings.local"
cd /Users/sebastianflorez/Documents/agrotech-digital/agrotech-digital
python manage.py runserver 8000
