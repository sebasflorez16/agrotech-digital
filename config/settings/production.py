from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
# Permitir el dominio de Railway y configuración por variable de entorno
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[
    "agrotech-digital-production.up.railway.app",
    ".railway.app",  # Permitir cualquier subdominio de Railway
    "localhost",
    "127.0.0.1"
])

# DATABASES
# ------------------------------------------------------------------------------
# Configuración dinámica para Railway - lazy loading REAL de DATABASE_URL
import os
from urllib.parse import urlparse

class DatabaseConfig:
    """Configuración de base de datos con lazy loading real"""
    
    def __init__(self):
        self._config = None
    
    def __getitem__(self, key):
        if self._config is None:
            self._config = self._get_runtime_config()
        return self._config[key]
    
    def get(self, key, default=None):
        if self._config is None:
            self._config = self._get_runtime_config()
        return self._config.get(key, default)
    
    def items(self):
        if self._config is None:
            self._config = self._get_runtime_config()
        return self._config.items()
    
    def keys(self):
        if self._config is None:
            self._config = self._get_runtime_config()
        return self._config.keys()
    
    def values(self):
        if self._config is None:
            self._config = self._get_runtime_config()
        return self._config.values()
    
    def _get_runtime_config(self):
        """Obtener configuración en tiempo de ejecución"""
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url and 'localhost' not in database_url:
            print(f"✅ DATABASE_URL encontrado en runtime: {database_url[:50]}...")
            try:
                url = urlparse(database_url)
                config = {
                    "ENGINE": "django_tenants.postgresql_backend",
                    "NAME": url.path[1:],  # Quitar '/' inicial
                    "USER": url.username,
                    "PASSWORD": url.password,
                    "HOST": url.hostname,
                    "PORT": url.port or 5432,
                    "ATOMIC_REQUESTS": True,
                    "CONN_MAX_AGE": int(os.environ.get("CONN_MAX_AGE", "60")),
                    "OPTIONS": {
                        "connect_timeout": 30,
                        "application_name": "agrotech_railway",
                    }
                }
                print(f"✅ Config DB - HOST: {url.hostname}, NAME: {url.path[1:]}, USER: {url.username}")
                return config
            except Exception as e:
                print(f"❌ Error parseando DATABASE_URL: {e}")
        
        # Solo usar localhost en desarrollo local
        print("⚠️ Usando configuración localhost (desarrollo)")
        return {
            "ENGINE": "django_tenants.postgresql_backend",
            "NAME": "agrotech",
            "USER": "postgres",
            "PASSWORD": "password",
            "HOST": "localhost",
            "PORT": "5432",
            "ATOMIC_REQUESTS": True,
            "CONN_MAX_AGE": 60,
        }

# Usar proxy para lazy loading real
DATABASES = {
    "default": DatabaseConfig()
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
