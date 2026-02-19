"""
seed_crop_types.py - Siembra CropType + CropCatalog en TODOS los schemas de tenants.

Por que es necesario:
    crop esta en SHARED_APPS y TENANT_APPS: sus tablas existen en cada schema de
    tenant, NO en el schema public. Sin este iterador, el seedeo quedaba en public
    y los usuarios veian dropdowns vacios en el modal de Cultivos y en Parcelas.

Uso:
    python manage.py seed_crop_types
    python manage.py seed_crop_types --schema=finca_demo
"""
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context, get_tenant_model
from crop.models import CropType, CropCatalog

CROP_TYPES = [
    {"name": "Maiz",               "description": "Zea mays - cereal de grano grueso, ciclo 90-120 dias"},
    {"name": "Arroz",              "description": "Oryza sativa - cereal semiacuatico, ciclo 100-130 dias"},
    {"name": "Sorgo",              "description": "Sorghum bicolor - tolerante a sequia, ciclo 90-110 dias"},
    {"name": "Soja",               "description": "Glycine max - oleaginosa leguminosa, ciclo 90-120 dias"},
    {"name": "Frijol",             "description": "Phaseolus vulgaris - leguminosa de grano, ciclo 60-90 dias"},
    {"name": "Papa",               "description": "Solanum tuberosum - tuberculo andino, ciclo 90-150 dias"},
    {"name": "Cafe Arabica",       "description": "Coffea arabica - cultivo industrial perenne, ciclo 8-9 meses"},
    {"name": "Cana de Azucar",     "description": "Saccharum officinarum - industrial, ciclo 12-18 meses"},
    {"name": "Palma de Aceite",    "description": "Elaeis guineensis - oleaginosa perenne, 25+ anos"},
    {"name": "Algodon",            "description": "Gossypium hirsutum - fibra industrial, ciclo 150-180 dias"},
    {"name": "Pastura Brachiaria", "description": "Brachiaria spp. - forraje tropical perenne"},
    {"name": "Pastura Kikuyo",     "description": "Cenchrus clandestinus - forraje de clima frio perenne"},
    {"name": "Yuca",               "description": "Manihot esculenta - tuberculo tropical, ciclo 8-18 meses"},
    {"name": "Platano",            "description": "Musa paradisiaca - fruta tropical perenne"},
    {"name": "Cacao",              "description": "Theobroma cacao - arbol tropical, 20+ anos"},
    {"name": "Aguacate",           "description": "Persea americana - frutal tropical, 15+ anos"},
    {"name": "Banano",             "description": "Musa acuminata - frutal tropical, ciclo 9-12 meses"},
    {"name": "Tomate",             "description": "Solanum lycopersicum - hortaliza, ciclo 90-120 dias"},
    {"name": "Cebolla",            "description": "Allium cepa - bulbo, ciclo 90-120 dias"},
    {"name": "Girasol",            "description": "Helianthus annuus - oleaginosa, ciclo 90-130 dias"},
]

CATALOG_DATA = [
    {"name": "Maiz", "scientific_name": "Zea mays", "family": "Poaceae",
     "category": "cereals", "description": "Cereal de gran importancia economica en Colombia.",
     "cycle_days_min": 100, "cycle_days_max": 150, "temp_min": 18.0, "temp_max": 35.0,
     "rainfall_min": 500.0, "rainfall_max": 1200.0},
    {"name": "Arroz", "scientific_name": "Oryza sativa", "family": "Poaceae",
     "category": "cereals", "description": "Principal cereal alimenticio de Colombia.",
     "cycle_days_min": 100, "cycle_days_max": 130, "temp_min": 20.0, "temp_max": 38.0,
     "rainfall_min": 1000.0, "rainfall_max": 2000.0},
    {"name": "Sorgo", "scientific_name": "Sorghum bicolor", "family": "Poaceae",
     "category": "cereals", "description": "Cereal resistente a sequia, alimentacion y forraje.",
     "cycle_days_min": 90, "cycle_days_max": 120, "temp_min": 20.0, "temp_max": 38.0,
     "rainfall_min": 400.0, "rainfall_max": 1000.0},
    {"name": "Soja", "scientific_name": "Glycine max", "family": "Fabaceae",
     "category": "legumes", "description": "Principal oleaginosa-proteaginosa de Colombia.",
     "cycle_days_min": 90, "cycle_days_max": 130, "temp_min": 15.0, "temp_max": 32.0,
     "rainfall_min": 500.0, "rainfall_max": 1200.0},
    {"name": "Frijol", "scientific_name": "Phaseolus vulgaris", "family": "Fabaceae",
     "category": "legumes", "description": "Leguminosa fundamental en la dieta colombiana.",
     "cycle_days_min": 60, "cycle_days_max": 90, "temp_min": 15.0, "temp_max": 27.0,
     "rainfall_min": 300.0, "rainfall_max": 800.0},
    {"name": "Papa", "scientific_name": "Solanum tuberosum", "family": "Solanaceae",
     "category": "tubers", "description": "Principal tuberculo andino, base alimentaria en zonas frias.",
     "cycle_days_min": 90, "cycle_days_max": 150, "temp_min": 7.0, "temp_max": 20.0,
     "rainfall_min": 600.0, "rainfall_max": 1200.0},
    {"name": "Cafe Arabica", "scientific_name": "Coffea arabica", "family": "Rubiaceae",
     "category": "industrial", "description": "Cultivo insignia de Colombia, reconocido mundialmente.",
     "cycle_days_min": 240, "cycle_days_max": 300, "temp_min": 17.0, "temp_max": 23.0,
     "rainfall_min": 1600.0, "rainfall_max": 2200.0},
    {"name": "Cana de Azucar", "scientific_name": "Saccharum officinarum", "family": "Poaceae",
     "category": "industrial", "description": "Principal cultivo azucarero de Colombia.",
     "cycle_days_min": 360, "cycle_days_max": 548, "temp_min": 20.0, "temp_max": 35.0,
     "rainfall_min": 1000.0, "rainfall_max": 1800.0},
    {"name": "Palma de Aceite", "scientific_name": "Elaeis guineensis", "family": "Arecaceae",
     "category": "oilseeds", "description": "Mayor oleaginosa por produccion en Colombia.",
     "cycle_days_min": 365, "cycle_days_max": 730, "temp_min": 22.0, "temp_max": 33.0,
     "rainfall_min": 1500.0, "rainfall_max": 3000.0},
    {"name": "Yuca", "scientific_name": "Manihot esculenta", "family": "Euphorbiaceae",
     "category": "tubers", "description": "Tuberculo tropical de alta resistencia a sequia.",
     "cycle_days_min": 240, "cycle_days_max": 548, "temp_min": 20.0, "temp_max": 35.0,
     "rainfall_min": 400.0, "rainfall_max": 2000.0},
    {"name": "Platano", "scientific_name": "Musa paradisiaca", "family": "Musaceae",
     "category": "fruits", "description": "Frutal tropical de ciclo permanente en Colombia.",
     "cycle_days_min": 270, "cycle_days_max": 365, "temp_min": 18.0, "temp_max": 35.0,
     "rainfall_min": 1000.0, "rainfall_max": 3000.0},
    {"name": "Cacao", "scientific_name": "Theobroma cacao", "family": "Malvaceae",
     "category": "industrial", "description": "Cultivo tropical de alto valor en Colombia.",
     "cycle_days_min": 150, "cycle_days_max": 180, "temp_min": 18.0, "temp_max": 32.0,
     "rainfall_min": 1500.0, "rainfall_max": 3500.0},
    {"name": "Aguacate", "scientific_name": "Persea americana", "family": "Lauraceae",
     "category": "fruits", "description": "Frutal tropical con gran crecimiento en exportaciones colombianas.",
     "cycle_days_min": 180, "cycle_days_max": 365, "temp_min": 15.0, "temp_max": 28.0,
     "rainfall_min": 1000.0, "rainfall_max": 2000.0},
    {"name": "Tomate", "scientific_name": "Solanum lycopersicum", "family": "Solanaceae",
     "category": "vegetables", "description": "Hortaliza de alto consumo, cultivo intensivo en Colombia.",
     "cycle_days_min": 90, "cycle_days_max": 120, "temp_min": 15.0, "temp_max": 30.0,
     "rainfall_min": 400.0, "rainfall_max": 800.0},
    {"name": "Cebolla", "scientific_name": "Allium cepa", "family": "Alliaceae",
     "category": "vegetables", "description": "Hortaliza de bulbo ampliamente cultivada en Colombia.",
     "cycle_days_min": 90, "cycle_days_max": 120, "temp_min": 13.0, "temp_max": 24.0,
     "rainfall_min": 350.0, "rainfall_max": 700.0},
    {"name": "Girasol", "scientific_name": "Helianthus annuus", "family": "Asteraceae",
     "category": "oilseeds", "description": "Oleaginosa de ciclo corto adaptada a Colombia.",
     "cycle_days_min": 90, "cycle_days_max": 130, "temp_min": 16.0, "temp_max": 30.0,
     "rainfall_min": 400.0, "rainfall_max": 900.0},
]


def _seed_types(stdout):
    created = 0
    for ct in CROP_TYPES:
        _obj, was_created = CropType.objects.get_or_create(
            name=ct["name"], defaults={"description": ct["description"]}
        )
        if was_created:
            created += 1
    stdout.write(f"    CropType: {created} nuevos / {len(CROP_TYPES) - created} ya existian")


def _seed_catalog(stdout):
    created = 0
    for data in CATALOG_DATA:
        _obj, was_created = CropCatalog.objects.get_or_create(
            name=data["name"],
            defaults={k: v for k, v in data.items() if k != "name"},
        )
        if was_created:
            created += 1
    stdout.write(f"    CropCatalog: {created} nuevos / {len(CATALOG_DATA) - created} ya existian")


class Command(BaseCommand):
    help = "Siembra CropType + CropCatalog en todos los schemas de tenants (idempotente)"

    def add_arguments(self, parser):
        parser.add_argument("--schema", type=str, default=None,
                            help="Siembra solo en este schema (omitir = todos)")

    def handle(self, *args, **options):
        TenantModel = get_tenant_model()
        target = options.get("schema")
        tenants = (TenantModel.objects.filter(schema_name=target)
                   if target else TenantModel.objects.all())

        total = tenants.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No se encontraron tenants."))
            return

        self.stdout.write(self.style.SUCCESS(f"Sembrando datos en {total} schema(s)..."))
        errors = 0
        for tenant in tenants:
            self.stdout.write(f"  Schema: {tenant.schema_name}")
            try:
                with schema_context(tenant.schema_name):
                    _seed_types(self.stdout)
                    _seed_catalog(self.stdout)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  ERROR en {tenant.schema_name}: {exc}"))
                errors += 1

        if errors:
            self.stdout.write(self.style.WARNING(f"Completado con {errors} error(es)."))
        else:
            self.stdout.write(self.style.SUCCESS("seed_crop_types completado sin errores."))
