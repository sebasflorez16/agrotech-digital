"""
Base settings to build other settings files upon.
"""

import os
os.environ["GDAL_LIBRARY_PATH"] = "/opt/homebrew/opt/gdal/lib/libgdal.dylib"
os.environ["GEOS_LIBRARY_PATH"] = "/opt/homebrew/opt/geos/lib/libgeos_c.dylib"
from pathlib import Path
import environ

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
# metrica/
APPS_DIR = ROOT_DIR / "metrica"
env = environ.Env()

# Si READ_DOT_ENV_FILE es True, Django leerá las variables del archivo .env.
# Esto permite configurar variables sensibles (como claves API) sin incluirlas en el código.
# Si es False, Django solo usará las variables de entorno del sistema operativo.
# Las variables del sistema tienen prioridad sobre las del archivo .env.
READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=True)
if READ_DOT_ENV_FILE:
    env.read_env(str(ROOT_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)

# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
# Configuración base para ALLOWED_HOSTS - se sobrescribe en production.py
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "agrotech-digital-production.up.railway.app",
    ".railway.app",
    ".localhost"
]
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "UTC"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "es"
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(ROOT_DIR / "locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

# Configuración base para desarrollo local
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': "agrotech",
        'USER': "postgres",
        'PASSWORD': "guibsonsid.16",
        'HOST': "localhost",
        'PORT': "5432",
        'ATOMIC_REQUESTS': True,
    }
}


DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"





# Cesium Token (usar environ para leer correctamente .env)
CESIUM_ACCESS_TOKEN = env("CESIUM_ACCESS_TOKEN", default="TU_CESIUM_ACCESS_TOKEN")



# Eliminado: OpenWeather API. Ahora los datos climáticos se obtienen de EOSDA.


# EOSDA API KEY

# EOSDA API KEY
EOSDA_API_KEY = os.getenv('EOSDA_API_KEY', 'TU_EOSDA_API_KEY') # Valor por defecto solo para desarrollo local, reemplaza en .env

# EOSDA DATASET ID (por defecto Sentinel-2 L2A)
EOSDA_DATASET_ID = os.getenv('EOSDA_DATASET_ID', 'S2L2A')


# APPS
# ------------------------------------------------------------------------------
# SHARED_APPS: aplicaciones que se comparten entre todos los tenants
SHARED_APPS = [
    'django_tenants',
    'rest_framework',
    "corsheaders",
    'django.contrib.contenttypes',
    "django.contrib.auth",
    # 'django.contrib.gis',  # GIS deshabilitado temporalmente
    # 'rest_framework_gis', # GIS deshabilitado temporalmente
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.forms",
    "base_agrotech", 
    "RRHH",
    "parcels",
    "labores",  # Gestión de labores agrícolas
    
    # Aplicaciones de terceros
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_browser_reload",
    # "leaflet",  # Deshabilitado para evitar dependencias GIS
    
    # Tus aplicaciones locales que deben ser accesibles por todos los tenants
    "metrica.users.apps.UsersConfig",  
    "inventario",  # Registro de la app de inventario
    "crop",  # Gestión de cultivos
]

TENANT_APPS = [
    # Django apps
    "django.contrib.admin",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "metrica.dashboard.apps.DashboardConfig",  
    "simple_history",
    "base_agrotech",
    "RRHH",
    "parcels",
    "inventario",
    "labores",  # Gestión de labores agrícolas
    "crop",  # Gestión de cultivos
]

# Combina las aplicaciones compartidas y específicas de los tenants
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]


CORS_ALLOW_ALL_ORIGINS = False
# Permite el envío de cookies/tokens JWT de sesión entre frontend y backend
CORS_ALLOW_CREDENTIALS = True
# Permitimos solo orígenes locales seguros (React, Django, etc.) para evitar exposición del API a todo el mundo.
# Usamos expresiones regulares para aceptar subdominios tipo tenant1.localhost:3000 y acceso directo a localhost:3000/8000
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://[\w\-]+\.localhost:3000$",  # Por ejemplo: tenant1.localhost:3000
    r"^https?://localhost:3000$",             # También acceso directo
    r"^https?://[\w\-]+\.localhost:8000$",  # Por si acceden directo al backend
    r"^https://agrotech-digital-production\.up\.railway\.app$",  # Backend en Railway
]

# NOTA: No se usa CORS_ALLOW_ALL_ORIGINS=True para evitar riesgos de seguridad y exposición del API key de EOSDA.


LOGIN_REDIRECT_URL = "/authentication/dashboard/"  # Redirige al dashboard después de login
LOGIN_URL = "/authentication/login/"  # Redirige a la página de login si no estás autenticado
ACCOUNT_LOGOUT_REDIRECT_URL = "/authentication/login/"  # Redirige al login después de logout


# Configuraciones adicionales (opcional)
#ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "none"  # Verificación obligatoria se pondra none para el desarrollo
#ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS = True  # Redirigir después del login

# django-tenants settings
TENANT_MODEL = "base_agrotech.Client"  # Define el modelo que representa los tenants
TENANT_DOMAIN_MODEL = "base_agrotech.Domain"  # Define el modelo para los dominios asociados con los tenants

# TEST RUNNER personalizado para ejecutar migrate_schemas en la base de datos de test
TEST_RUNNER = "config.testrunner.TenantMigrateSchemasTestRunner"


# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
#MIGRATION_MODULES = {"sites": "metrica.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
#Se importa el middleware dinamico para CORS


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django_tenants.middleware.main.TenantMainMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",  
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]




# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(ROOT_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(ROOT_DIR / "metrica/static")]

# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        "DIRS": [str(APPS_DIR / "templates")],
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "metrica.utils.context_processors.settings_context",
            ],
        },
    }
]

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap5"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("mannat_themes", "test@test.com")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS


# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_REQUIRED = True
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_ADAPTER = "metrica.users.adapters.AccountAdapter"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
SOCIALACCOUNT_ADAPTER = "metrica.users.adapters.SocialAccountAdapter"

# EOSDA API CONFIG
EOSDA_BASE_URL = env.str("EOSDA_BASE_URL", default="https://api-connect.eos.com/field-management")
EOSDA_API_KEY = env.str("EOSDA_API_KEY", default="")
EOSDA_API_URL = EOSDA_BASE_URL  # Para compatibilidad con el modelo
# Your stuff...
# ------------------------------------------------------------------------------


# LEAFLET_CONFIG = {
#     'DEFAULT_CENTER': (4.6097, -74.0817),  # Latitud y longitud inicial (ej: Bogotá, Colombia)
#     'DEFAULT_ZOOM': 12,
#     'MIN_ZOOM': 3,
#     'MAX_ZOOM': 18,
# }


from datetime import timedelta

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=160),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}


MIDDLEWARE.insert(1, "django.middleware.common.CommonMiddleware")


# LOGGING para mostrar todos los logs en consola
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        '': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
from .logging_eosda import LOGGING as LOGGING_EOSDA
LOGGING['handlers']['file'] = LOGGING_EOSDA['handlers']['file']
LOGGING['loggers']['eosda'] = LOGGING_EOSDA['loggers']['eosda']
LOGGING['loggers']['eosda']['level'] = 'DEBUG'
LOGGING['loggers']['eosda']['handlers'] = ['console', 'file']
LOGGING['loggers']['eosda']['propagate'] = False


