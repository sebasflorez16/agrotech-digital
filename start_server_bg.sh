#!/bin/bash
source $(conda info --base)/etc/profile.d/conda.sh
conda activate agro-rest
export DJANGO_SECRET_KEY="agrotech-dev-secret-key-2024"
export DJANGO_SETTINGS_MODULE="config.settings.local"
cd /Users/sebastianflorez/Documents/agrotech-digital/agrotech-digital
python manage.py runserver 8000
