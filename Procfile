release: python manage.py setup_railway
web: gunicorn config.wsgi --bind 0.0.0.0:$PORT
