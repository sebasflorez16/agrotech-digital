import os

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
    "127.0.0.1",
    "agrotechcolombia.netlify.app",  # Sin protocolo https://
])

# DATABASES - Ya configurado automáticamente en base.py cuando IS_RAILWAY=True
# No es necesario reconfigurar aquí


# MIDDLEWARE - Agregar WhiteNoise y HealthCheck para producción
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    'config.middleware.HealthCheckMiddleware',  # PRIMERO: Intercepta /health/ para Railway
    'corsheaders.middleware.CorsMiddleware',
    'config.middleware.SmartTenantMiddleware',  # Reemplaza TenantMainMiddleware: fuerza public en billing/auth
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Para servir archivos estáticos
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",  
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "billing.middleware.SubscriptionLimitMiddleware",  # Verificar suscripción activa
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
    "https://agrotechcolombia.netlify.app",  # Frontend Netlify empresa
    "https://frontend-cliente-agrotech.netlify.app",  # Frontend Netlify cliente
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

# CORS Configuration - Para resolver problemas de peticiones entre dominios
# ------------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    "https://www.agrotechcolombia.com", 
    "https://agrotechcolombia.com", 
    "https://agrotech-digital-production.up.railway.app",
    "https://agrotechcolombia.netlify.app",  # ✅ Frontend en Netlify
    "https://frontend-cliente-agrotech.netlify.app",  # ✅ Frontend landing
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # Solo dominios específicos

# Headers permitidos para CORS
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Configuraciones específicas para frontend estático separado
# ------------------------------------------------------------------------------
# Regex para permitir subdominios de clientes multi-tenant
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://[\w\-]+\.agrotechcolombia\.com$",  # Subdominios de clientes
    r"^https://[\w\-]+\.railway\.app$",  # Cualquier subdominio de Railway
]

# URL del sitio para callbacks de pagos (MercadoPago back_url)
SITE_URL = env('SITE_URL', default='https://agrotech-digital-production.up.railway.app')

# URL del frontend estático (Netlify) para redirecciones post-pago
FRONTEND_URL = env('FRONTEND_URL', default='https://frontend-cliente-agrotech.netlify.app')

# Redirigir al frontend estático después del login
LOGIN_REDIRECT_URL = "https://agrotechcolombia.netlify.app/templates/vertical_base.html"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# SMTP Configuration
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="AgroTech Digital <noreply@agrotechcolombia.com>",
)
SERVER_EMAIL = env("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
EMAIL_SUBJECT_PREFIX = env("EMAIL_SUBJECT_PREFIX", default="[AgroTech] ")

# Verificación de email obligatoria en producción
ACCOUNT_EMAIL_VERIFICATION = "mandatory"

# Admin notification emails
ADMINS = [
    (admin.split(':')[0], admin.split(':')[1])
    for admin in env.list("DJANGO_ADMINS", default=["Admin:admin@agrotechcolombia.com"])
]
MANAGERS = ADMINS
