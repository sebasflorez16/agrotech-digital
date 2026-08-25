from django.apps import AppConfig


class CropConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crop'

    def ready(self):
        import crop.signals  # noqa: F401
