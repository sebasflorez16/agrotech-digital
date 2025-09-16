from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
# Permitir el dominio de Railway y configuración por variable de entorno
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[
    "agrotechcolombia.com",
    "www.agrotechcolombia.com",
    "agrotech-digital-production.up.railway.app",
    ".railway.app",  # Permitir cualquier subdominio de Railway
    "localhost",
    "127.0.0.1"
])

# DATABASES
# ------------------------------------------------------------------------------
# Configuración optimizada para Railway con django-tenants
import os
from urllib.parse import urlparse

# Intentar obtener DATABASE_URL inmediatamente
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL and 'localhost' not in DATABASE_URL:
    # Parsear URL de Railway
    print(f"✅ Railway DATABASE_URL detectado: {DATABASE_URL[:50]}...")
    url = urlparse(DATABASE_URL)
    
    DATABASES = {
        "default": {
            "ENGINE": "django_tenants.postgresql_backend",
            "NAME": url.path[1:],  # Quitar '/' inicial
            "USER": url.username,
            "PASSWORD": url.password,
            "HOST": url.hostname,
            "PORT": url.port or 5432,
            "ATOMIC_REQUESTS": False,  # Importante para django-tenants
            "CONN_MAX_AGE": 0,  # Desactivar pooling para evitar problemas con schemas
        }
    }
    print(f"✅ DB Config - HOST: {url.hostname}, NAME: {url.path[1:]}")
    
else:
    # Configuración por defecto solo para desarrollo local
    print("⚠️ DATABASE_URL no encontrado, usando localhost")
    DATABASES = {
        "default": {
            "ENGINE": "django_tenants.postgresql_backend",
            "NAME": "agrotech",
            "USER": "postgres",
            "PASSWORD": "password",
            "HOST": "localhost",
            "PORT": "5432",
            "ATOMIC_REQUESTS": False,
            "CONN_MAX_AGE": 0,
        }
    }
    


# MIDDLEWARE - Agregar WhiteNoise después de SecurityMiddleware
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django_tenants.middleware.main.TenantMainMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Para servir archivos estáticos
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",  
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",  # Requerido por django-allauth
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# STATIC FILES (WhiteNoise)
# ------------------------------------------------------------------------------
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# LOGGING
# ------------------------------------------------------------------------------
# Configuración optimizada para producción - reduce logs innecesarios
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
    "loggers": {
        "django.db.backends": {
            "level": "ERROR",  # Solo errores de base de datos
            "handlers": ["console"],
            "propagate": False,
        },
        "django.server": {
            "level": "ERROR",  # Solo errores del servidor
            "handlers": ["console"],
            "propagate": False,
        },
        "gunicorn.access": {
            "level": "WARNING",  # Reduce logs de acceso de Gunicorn
            "handlers": ["console"],
            "propagate": False,
        },
        "django.request": {
            "level": "ERROR",  # Solo errores de requests
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

# Desactivar logs de desarrollo en producción
DEBUG = False

# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
    "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Mimicing memcache behavior.
            # https://github.com/jazzband/django-redis#memcached-exceptions-behavior
            "IGNORE_EXCEPTIONS": True,
        },
    }
}

# CSRF Configuration for multi-tenant
# ------------------------------------------------------------------------------
CSRF_TRUSTED_ORIGINS = [
    "https://agrotechcolombia.com",
    "https://www.agrotechcolombia.com",
    "https://agrotech-digital-production.up.railway.app",
    "https://*.agrotechcolombia.com",  # Para subdominios de clientes
    "https://*.railway.app",
]

# Cookie settings for multi-tenant
CSRF_COOKIE_DOMAIN = None  # Permite que cada tenant maneje sus propias cookies
CSRF_COOKIE_SECURE = True  # Solo HTTPS en producción
CSRF_COOKIE_HTTPONLY = True  # Seguridad adicional
CSRF_COOKIE_SAMESITE = 'Lax'  # Compatibilidad con subdominios

# Session settings
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Configuración adicional para django-tenants
USE_TZ = True
CSRF_USE_SESSIONS = False  # Usar cookies en lugar de sesiones para CSRF
