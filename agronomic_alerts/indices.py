"""
Catálogo de índices satelitales y reglas por cultivo.

Objetivo: el productor entiende **qué mide cada índice** y **por qué importa**
en su cultivo, sin jerga académica. La lógica del motor consulta este módulo
para decidir qué índices monitorear según el cultivo asignado.

Convención de claves de índice: minúscula (ndvi, ndmi, savi, evi, ndre).
"""

from __future__ import annotations

from typing import Iterable


# ---------------------------------------------------------------------------
# 1. Diccionario explicativo (lenguaje productor)
# ---------------------------------------------------------------------------
# `que_mide` se muestra al productor cuando recibe la alerta.
# `como_se_lee` ayuda a interpretar valores altos/bajos.
INDEX_EXPLAINER: dict[str, dict[str, str]] = {
    "ndvi": {
        "nombre_corto": "NDVI",
        "nombre_largo": "Índice de Verdor",
        "que_mide": (
            "Qué tan verde y activa está la masa foliar del lote. "
            "Es el termómetro del vigor vegetativo."
        ),
        "como_se_lee": (
            "Valores bajos indican suelo descubierto, plantas estresadas o "
            "muy poco desarrollo. Valores altos indican cultivo denso y sano."
        ),
        "limitaciones": (
            "Se satura en cultivos muy frondosos (palma adulta, caña): "
            "deja de distinguir diferencias finas. Por eso en perennes se "
            "usa NDRE/EVI en su lugar."
        ),
    },
    "ndmi": {
        "nombre_corto": "NDMI",
        "nombre_largo": "Índice de Humedad",
        "que_mide": (
            "Cuánta agua hay en las hojas del cultivo. Es el termómetro del "
            "estrés hídrico ANTES de que la planta se marchite a la vista."
        ),
        "como_se_lee": (
            "Valores bajos = la planta está perdiendo agua, posible riego "
            "insuficiente o sequía. Valores altos = humedad foliar adecuada."
        ),
        "limitaciones": (
            "Sensible a nubes altas; cruzar con NDVI/NDRE para confirmar "
            "que la caída es estrés y no efecto atmosférico."
        ),
    },
    "savi": {
        "nombre_corto": "SAVI",
        "nombre_largo": "NDVI ajustado al suelo",
        "que_mide": (
            "Vigor del cultivo descontando el efecto del suelo desnudo. "
            "Útil en etapas tempranas donde el lote aún no está cubierto."
        ),
        "como_se_lee": (
            "Similar a NDVI pero más realista en cultivos jóvenes o de "
            "baja cobertura. Bajo = cultivo poco desarrollado para la fecha."
        ),
        "limitaciones": (
            "En cobertura plena se comporta como NDVI."
        ),
    },
    "evi": {
        "nombre_corto": "EVI",
        "nombre_largo": "Índice de Vegetación Mejorado",
        "que_mide": (
            "Cobertura y densidad del dosel en cultivos muy frondosos. "
            "Detecta zonas con menos hojas dentro de lotes verdes."
        ),
        "como_se_lee": (
            "Bajo en zonas del lote = posibles claros, palmas faltantes, "
            "daño por viento, raleos, ataque de plagas defoliadoras."
        ),
        "limitaciones": (
            "Requiere bandas azul/rojo/infrarrojo; menos preciso bajo "
            "nubosidad alta."
        ),
    },
    "ndre": {
        "nombre_corto": "NDRE",
        "nombre_largo": "Índice del Red-Edge",
        "que_mide": (
            "Estado nutricional (nitrógeno) y clorofila en cultivos perennes "
            "y de hoja densa. Es el indicador profesional para palma, caña, "
            "café y frutales en producción."
        ),
        "como_se_lee": (
            "Bajo = deficiencia de nitrógeno o clorosis. Alto = nutrición "
            "balanceada. Reacciona ANTES que NDVI a problemas nutricionales."
        ),
        "limitaciones": (
            "Necesita banda Red-Edge (Sentinel-2 la trae nativa)."
        ),
    },
}


# ---------------------------------------------------------------------------
# 2. Índices recomendados por categoría de cultivo
# ---------------------------------------------------------------------------
# Convención profesional usada en agricultura de precisión:
#  - Cereales/leguminosas/hortalizas: NDVI + NDMI + SAVI (vigor, agua, suelo).
#  - Palma de aceite, caña, café, cítricos y frutales perennes: NDMI + NDRE + EVI
#    (NDVI satura y deja de ser informativo; NDRE detecta deficiencias antes).
#  - Pastos/forrajes: NDVI + NDMI (manejo de pastoreo y agua).
PREFERRED_INDICES_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "cereals":     ("ndvi", "ndmi", "savi"),
    "legumes":     ("ndvi", "ndmi", "savi"),
    "vegetables":  ("ndvi", "ndmi", "savi"),
    "tubers":      ("ndvi", "ndmi", "savi"),
    "fruits":      ("ndmi", "ndre", "evi"),
    "industrial":  ("ndmi", "ndre", "evi"),
    "oilseeds":    ("ndmi", "ndre", "evi"),  # palma, soja perenne, etc.
    "forage":      ("ndvi", "ndmi"),
    "other":       ("ndvi", "ndmi", "savi"),
}

# Overrides por nombre exacto del cultivo (CropCatalog.name).
# Útil para casos atípicos dentro de la misma categoría.
PREFERRED_INDICES_BY_NAME: dict[str, tuple[str, ...]] = {
    "palma de aceite":   ("ndmi", "ndre", "evi"),
    "caña de azúcar":    ("ndmi", "ndre", "evi"),
    "cana de azucar":    ("ndmi", "ndre", "evi"),
    "café":              ("ndmi", "ndre", "evi"),
    "cafe":              ("ndmi", "ndre", "evi"),
    "cacao":             ("ndmi", "ndre", "evi"),
    "aguacate":          ("ndmi", "ndre", "evi"),
    "banano":            ("ndmi", "ndre", "evi"),
    "plátano":           ("ndmi", "ndre", "evi"),
    "platano":           ("ndmi", "ndre", "evi"),
}


def preferred_indices_for_crop(crop_catalog) -> tuple[str, ...]:
    """
    Devuelve los índices que tienen sentido monitorear para este cultivo.

    Si no hay catálogo (parcela sin ciclo), retorna tupla vacía → el motor
    NO genera alertas (no se simula).
    """
    if not crop_catalog:
        return ()
    name_key = (getattr(crop_catalog, "name", "") or "").strip().lower()
    if name_key in PREFERRED_INDICES_BY_NAME:
        return PREFERRED_INDICES_BY_NAME[name_key]
    category = (getattr(crop_catalog, "category", "") or "").strip().lower()
    return PREFERRED_INDICES_BY_CATEGORY.get(category, PREFERRED_INDICES_BY_CATEGORY["other"])


def explain_index(indice: str) -> dict[str, str]:
    """Devuelve la ficha explicativa del índice en lenguaje productor."""
    return INDEX_EXPLAINER.get((indice or "").lower(), {
        "nombre_corto": (indice or "").upper(),
        "nombre_largo": "",
        "que_mide": "",
        "como_se_lee": "",
        "limitaciones": "",
    })


def por_que_importa(indice: str, cultivo_nombre: str, etapa_nombre: str) -> str:
    """
    Frase corta y operativa: por qué este índice importa para ESTE cultivo
    en ESTA etapa fenológica.
    """
    idx = (indice or "").lower()
    cultivo = (cultivo_nombre or "tu cultivo").strip()
    etapa = (etapa_nombre or "").strip()
    cabeza = f"En {cultivo}" + (f" durante {etapa}" if etapa else "") + ", "

    if idx == "ndmi":
        return cabeza + (
            "el agua disponible determina llenado de grano/fruto. Una caída "
            "sostenida adelanta el riego: cuesta menos prevenir que recuperar."
        )
    if idx == "ndvi":
        return cabeza + (
            "el vigor es proxy directo del rendimiento. Caídas anuncian "
            "estrés nutricional, hídrico o presión de plagas."
        )
    if idx == "savi":
        return cabeza + (
            "el suelo aún se ve entre plantas: SAVI evita confundir 'cultivo "
            "bajo' con 'lote vacío'."
        )
    if idx == "evi":
        return cabeza + (
            "el dosel ya es denso y NDVI se satura. EVI detecta claros, "
            "palmas faltantes y daño por viento/plagas defoliadoras."
        )
    if idx == "ndre":
        return cabeza + (
            "el NDRE refleja nitrógeno y clorofila antes que el ojo humano. "
            "Permite ajustar fertilización ANTES de perder rendimiento."
        )
    return cabeza + "este índice ayuda a monitorear el estado del lote."


def filter_relevant_readings(readings: Iterable, crop_catalog) -> list:
    """
    Filtra lecturas dejando solo las relevantes para el cultivo.
    Sin cultivo → lista vacía (no se simula nada).
    """
    preferred = set(preferred_indices_for_crop(crop_catalog))
    if not preferred:
        return []
    return [r for r in readings if (getattr(r, "indice", "") or "").lower() in preferred]
