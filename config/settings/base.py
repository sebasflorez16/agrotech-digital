"""
Base settings to build other settings files upon.
"""
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


DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': "agrotech",
        'USER': "postgres",
        'PASSWORD': "guibsonsid.16",
        'HOST': "localhost",
        'PORT': "5432",
    }
}

# Propia de la documentacion de django-tenants para manejar datos geoespaciales en PostgreSQL 
ORIGINAL_BACKEND = "django.contrib.gis.db.backends.postgis"


# El ATOMIC_REQUESTS si esta activo ayuda a que dentro de las peticiones si ocurre un error durante la misma, todos los cambios que se hicieron en la base de datos se revertiran.
DATABASES["default"]["ATOMIC_REQUESTS"] = True


DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"




# Cesium Token
import os
CESIUM_ACCESS_TOKEN = os.getenv('CESIUM_ACCESS_TOKEN', 'TU_CESIUM_ACCESS_TOKEN')


#OpenWeather API
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', 'TU_WEATHER_API_KEY') #es un valor por defecto que se usa solo si no encuentra la variable de entorno. Este valor por defecto es un placeholder — útil para que el proyecto no falle localmente si no hay .env cargado.  

#SENTINEL_NDVI_WMTS
SENTINEL_NDVI_WMTS = os.getenv('SENTINEL_NDVI_WMTS') #es un valor por defecto que se usa solo si no encuentra la variable de entorno. Este valor por defecto es un placeholder — útil para que el proyecto no falle localmente si no hay .env cargado.
SENTINEL_NDMI_WMTS = os.getenv('SENTINEL_NDMI_WMTS')


# SENTINEL_API_KEY
SENTINEL_API_KEY = os.getenv('SENTINEL_API_KEY', 'TU_SENTINEL_API_KEY')


# SENTINEL_CONFIGURATION_ID
SENTINEL_CONFIGURATION_ID = os.getenv('SENTINEL_CONFIGURATION_ID', 'TU_CONFIGURATION_ID')


# APPS
# ------------------------------------------------------------------------------
# SHARED_APPS: aplicaciones que se comparten entre todos los tenants
SHARED_APPS = [
    'django_tenants',
    'rest_framework',
    "corsheaders",
    'django.contrib.contenttypes',
    "django.contrib.auth",
    'django.contrib.gis',
    'rest_framework_gis',
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.forms",
    "base_agrotech", 
    "RRHH",
    "fields",
    "parcels",
    
    # Aplicaciones de terceros
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_browser_reload",
    "leaflet",
    
    # Tus aplicaciones locales que deben ser accesibles por todos los tenants
    "metrica.users.apps.UsersConfig",  
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
    "fields",
    "parcels",
]

# Combina las aplicaciones compartidas y específicas de los tenants
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]


CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://prueba.localhost:3000",
    "http://prueba.localhost:8000",
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://[a-z0-9\-]+\\.localhost:3000$",
    r"^http://[a-z0-9\-]+\\.localhost:8000$",
]


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

# Your stuff...
# ------------------------------------------------------------------------------


LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (4.6097, -74.0817),  # Latitud y longitud inicial (ej: Bogotá, Colombia)
    'DEFAULT_ZOOM': 12,
    'MIN_ZOOM': 3,
    'MAX_ZOOM': 18,
}


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


