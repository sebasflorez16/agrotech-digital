"""
With these settings, tests run faster.
"""

from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# TEMPLATES
# ------------------------------------------------------------------------------
TEMPLATES[-1]["OPTIONS"]["loaders"] = [  # type: ignore[index] # noqa F405
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    )
]

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


# Cambiar temporalmente el TEST_RUNNER para usar SimpleTestRunner
TEST_RUNNER = 'config.testrunner.SimpleTestRunner'

# Forzar el uso de la base de datos de prueba limpia
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('TEST_DB_NAME', default='test_prueba2'),
        'USER': env('TEST_DB_USER', default='postgres'),
        'PASSWORD': env('TEST_DB_PASSWORD', default=''),
        'HOST': env('TEST_DB_HOST', default='localhost'),
        'PORT': env('TEST_DB_PORT', default='5432'),
    }
}

# Your stuff...
# ------------------------------------------------------------------------------
