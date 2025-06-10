from django.test.runner import DiscoverRunner
from django.core.management import call_command

class TenantMigrateSchemasTestRunner(DiscoverRunner):
    """
    Test runner que ejecuta migrate_schemas en la base de datos de test antes de correr los tests.
    Esto asegura que todos los schemas y tablas existan en la base de datos de pruebas.
    """
    def setup_databases(self, **kwargs):
        # Llama al setup original
        result = super().setup_databases(**kwargs)
        # Ejecuta migrate_schemas en la base de datos de test
        call_command('migrate_schemas', interactive=False, verbosity=1)
        return result

class SimpleTestRunner(DiscoverRunner):
    """
    Test runner que no utiliza multi-tenant para simplificar la ejecución de pruebas.
    """
    def setup_databases(self, **kwargs):
        # Llama al setup original
        return super().setup_databases(**kwargs)
