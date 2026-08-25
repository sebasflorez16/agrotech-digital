from django.apps import AppConfig


class LaboresConfig(AppConfig):
    name = 'labores'

    def ready(self):
        import labores.signals  # noqa: F401
