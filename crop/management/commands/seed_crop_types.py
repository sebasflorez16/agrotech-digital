"""
Comando para poblar la tabla CropType con los 12 cultivos principales de Colombia.
Idempotente: usa get_or_create, puede correr múltiples veces sin duplicar datos.
"""
from django.core.management.base import BaseCommand
from crop.models import CropType

CROP_TYPES = [
    {"name": "Maíz",              "description": "Zea mays — cereal de grano grueso, ciclo 90–120 días"},
    {"name": "Arroz",             "description": "Oryza sativa — cereal semiacuático, ciclo 100–130 días"},
    {"name": "Sorgo",             "description": "Sorghum bicolor — cereal tolerante a sequía, ciclo 90–110 días"},
    {"name": "Soja",              "description": "Glycine max — oleaginosa leguminosa, ciclo 90–120 días"},
    {"name": "Frijol",            "description": "Phaseolus vulgaris — leguminosa de grano, ciclo 60–90 días"},
    {"name": "Papa",              "description": "Solanum tuberosum — tubérculo andino, ciclo 90–150 días"},
    {"name": "Café Arábica",      "description": "Coffea arabica — cultivo industrial perenne, ciclo 8–9 meses"},
    {"name": "Caña de Azúcar",    "description": "Saccharum officinarum — cultivo industrial, ciclo 12–18 meses"},
    {"name": "Palma de Aceite",   "description": "Elaeis guineensis — oleaginosa perenne, ciclo productivo 25+ años"},
    {"name": "Algodón",           "description": "Gossypium hirsutum — fibra industrial, ciclo 150–180 días"},
    {"name": "Pastura Brachiaria","description": "Brachiaria spp. — forraje tropical perenne"},
    {"name": "Pastura Kikuyo",    "description": "Cenchrus clandestinus — forraje de clima frío perenne"},
]


class Command(BaseCommand):
    help = "Pobla CropType con los 12 cultivos principales (idempotente)"

    def handle(self, *args, **options):
        created_count = 0
        for ct in CROP_TYPES:
            obj, created = CropType.objects.get_or_create(
                name=ct["name"],
                defaults={"description": ct["description"]},
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✅ Creado: {obj.name}"))
            else:
                self.stdout.write(f"  ⏭  Ya existe: {obj.name}")
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ seed_crop_types completado — {created_count} nuevos, "
                f"{len(CROP_TYPES) - created_count} ya existían."
            )
        )
