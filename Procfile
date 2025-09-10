release: python manage.py migrate_schemas --shared
web: gunicorn config.wsgi --bind 0.0.0.0:$PORT
