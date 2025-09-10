release: python manage.py setup_railway --skip-checks
web: gunicorn config.wsgi --bind 0.0.0.0:$PORT
