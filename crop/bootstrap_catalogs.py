from __future__ import annotations

from crop.models import CropType, CropVariety


DEFAULT_CROP_TYPES = [
    ("Arroz", "Cereal base para sistemas de riego y secano."),
    ("Maiz", "Cereal de ciclo corto a medio, grano y forraje."),
    ("Cafe", "Cultivo perenne de zonas andinas."),
    ("Cacao", "Cultivo perenne tropical de alto valor."),
    ("Papa", "Tuberculo de clima frio."),
    ("Frijol", "Leguminosa para rotacion y fijacion de nitrogeno."),
]

DEFAULT_VARIETIES_BY_TYPE = {
    "Arroz": [
        ("Fedearroz 67", 125),
        ("Fedearroz 2000", 130),
        ("Fedearroz 174", 120),
        ("ICA V-305", 120),
    ],
    "Maiz": [
        ("Pioneer 30F35", 140),
        ("ICA V-109", 130),
        ("H-108", 135),
    ],
    "Cafe": [
        ("Castillo", 540),
        ("Cenicafe 1", 540),
        ("Caturra", 510),
    ],
    "Cacao": [
        ("CCN-51", 900),
        ("TSH-565", 920),
        ("ICS-95", 950),
    ],
    "Papa": [
        ("Diacol Capiro", 150),
        ("Pastusa Suprema", 165),
    ],
    "Frijol": [
        ("ICA Cerinza", 105),
        ("Calima", 110),
    ],
}

DEFAULT_LABOR_TYPES = [
    ("Preparacion de suelo", "Labores de acondicionamiento y alistamiento del terreno."),
    ("Siembra", "Establecimiento del cultivo en campo."),
    ("Riego", "Aplicacion de agua de acuerdo con etapa fenologica."),
    ("Fertilizacion", "Nutricion del cultivo segun plan NPK."),
    ("Control fitosanitario", "Manejo de plagas, enfermedades y malezas."),
    ("Monitoreo", "Inspeccion y registro de estado del cultivo."),
    ("Cosecha", "Recoleccion del producto en punto optimo."),
    ("Postcosecha", "Manejo posterior a la cosecha y alistamiento."),
]


def ensure_crop_catalog_defaults(tenant_id=None) -> None:
    if tenant_id is None:
        if CropType.objects.exists() and CropVariety.objects.exists():
            return
    else:
        if CropType.objects.filter(tenant_id=tenant_id).exists() and CropVariety.objects.filter(tenant_id=tenant_id).exists():
            return

    for type_name, type_desc in DEFAULT_CROP_TYPES:
        crop_type, _ = CropType.objects.get_or_create(
            name=type_name,
            tenant_id=tenant_id,
            defaults={"description": type_desc, "tenant_id": tenant_id},
        )

        for variety_name, cycle_days in DEFAULT_VARIETIES_BY_TYPE.get(type_name, []):
            CropVariety.objects.get_or_create(
                name=variety_name,
                crop_type=crop_type,
                tenant_id=tenant_id,
                defaults={
                    "cycle_days": cycle_days,
                    "description": f"Variedad recomendada para {type_name.lower()}.",
                    "tenant_id": tenant_id,
                },
            )


def ensure_labor_type_defaults(tenant_id=None) -> None:
    from labores.models import LaborType

    if tenant_id is None:
        if LaborType.objects.exists():
            return
    else:
        if LaborType.objects.filter(tenant_id=tenant_id).exists():
            return

    for nombre, descripcion in DEFAULT_LABOR_TYPES:
        LaborType.objects.get_or_create(
            nombre=nombre,
            tenant_id=tenant_id,
            defaults={"descripcion": descripcion, "tenant_id": tenant_id},
        )


def ensure_core_agro_defaults(tenant_id=None) -> None:
    ensure_crop_catalog_defaults(tenant_id=tenant_id)
    ensure_labor_type_defaults(tenant_id=tenant_id)
