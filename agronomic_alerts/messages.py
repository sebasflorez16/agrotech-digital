"""
Catálogo de copy (textos) para alertas agronómicas.

Aquí se define el QUÉ-decir, separado del CUÁNDO-decirlo (`engine.py`).
Permite refinar mensajes sin tocar la lógica.

Los textos están pensados para productores en Colombia:
- Lenguaje directo y operativo (no académico).
- Causa probable explicada en una línea.
- Recomendación con acción concreta y ventana temporal.
"""

from dataclasses import dataclass

from .indices import explain_index, por_que_importa
from .models import AlertSeverity, AlertType


@dataclass
class AlertCopy:
    titulo: str
    causa: str
    recomendacion: str
    ventana_dias: int


# ---------------------------------------------------------------------------
# Plantillas por (tipo, severidad)
# ---------------------------------------------------------------------------

_TEMPLATES = {
    # ---- HUMEDAD (NDMI) ----
    (AlertType.HUMEDAD, AlertSeverity.CRITICAL): {
        "titulo": "Estrés hídrico severo detectado",
        "causa": (
            "El NDMI cayó muy por debajo del rango esperado, indicando que el "
            "cultivo tiene poca agua disponible en hojas y suelo superficial."
        ),
        "recomendacion": (
            "Inspeccionar el lote en campo en las próximas 48 horas. Si se "
            "confirma déficit, aplicar riego de emergencia y revisar el "
            "sistema (presión, fugas, cobertura)."
        ),
        "ventana_dias": 2,
    },
    (AlertType.HUMEDAD, AlertSeverity.WARNING): {
        "titulo": "Indicios de estrés hídrico",
        "causa": (
            "El NDMI está por debajo del óptimo. Es una señal temprana de que "
            "el cultivo está empezando a perder humedad."
        ),
        "recomendacion": (
            "Programar un recorrido en los próximos 5 días, revisar humedad "
            "del suelo y ajustar el plan de riego."
        ),
        "ventana_dias": 5,
    },

    # ---- VIGOR (NDVI / SAVI) ----
    (AlertType.VIGOR, AlertSeverity.CRITICAL): {
        "titulo": "Vigor del cultivo muy bajo",
        "causa": (
            "El NDVI/SAVI está muy por debajo de lo esperado para esta etapa. "
            "Posibles causas: estrés hídrico, deficiencia de nutrientes, "
            "presencia de plagas o enfermedades, o falla de siembra."
        ),
        "recomendacion": (
            "Inspección urgente en campo (48-72 h). Tomar muestras de hojas, "
            "verificar nutrición (N principalmente) y descartar plagas. "
            "Documentar con foto la zona afectada."
        ),
        "ventana_dias": 3,
    },
    (AlertType.VIGOR, AlertSeverity.WARNING): {
        "titulo": "Vigor por debajo del esperado",
        "causa": (
            "El NDVI/SAVI está por debajo del rango óptimo de la etapa actual. "
            "Puede deberse a estrés hídrico leve, nutrición incompleta o "
            "comienzo de presión de plagas."
        ),
        "recomendacion": (
            "Revisar el lote en los próximos 7 días. Verificar plan de "
            "fertilización y monitorear plagas en zonas más afectadas."
        ),
        "ventana_dias": 7,
    },

    # ---- COBERTURA (EVI) ----
    (AlertType.COBERTURA, AlertSeverity.CRITICAL): {
        "titulo": "Cobertura vegetal muy baja",
        "causa": (
            "El EVI muestra cobertura muy reducida frente a lo esperado. "
            "Posibles causas: fallas de germinación, daño por viento/lluvia, "
            "ataque temprano de plagas."
        ),
        "recomendacion": (
            "Inspección urgente. Evaluar resiembra parcial si la falla es "
            "localizada y se está en ventana de re-siembra."
        ),
        "ventana_dias": 3,
    },
    (AlertType.COBERTURA, AlertSeverity.WARNING): {
        "titulo": "Cobertura vegetal por debajo del esperado",
        "causa": (
            "El EVI está por debajo del rango esperado. Cobertura vegetal "
            "menor a la deseada para la etapa."
        ),
        "recomendacion": (
            "Recorrer el lote en los próximos 7 días y verificar estado "
            "general de las plantas y densidad efectiva."
        ),
        "ventana_dias": 7,
    },

    # ---- ANOMALÍA / GENÉRICO ----
    (AlertType.ANOMALIA, AlertSeverity.WARNING): {
        "titulo": "Anomalía detectada en el lote",
        "causa": "Variación significativa respecto al patrón esperado.",
        "recomendacion": "Revisar el lote y registrar observaciones.",
        "ventana_dias": 7,
    },
}


# ---------------------------------------------------------------------------
# Builders públicos
# ---------------------------------------------------------------------------

def build_alert_copy(
    *,
    cultivo: str,
    etapa: str,
    indice: str,
    tipo: AlertType,
    severidad: AlertSeverity,
    valor: float,
    optimo,
    rango,
    es_etapa_critica: bool,
) -> AlertCopy:
    """Construye el copy de una alerta cuando SÍ hay CropCycle/etapa."""
    base = _TEMPLATES.get((tipo, severidad)) or _TEMPLATES[(AlertType.ANOMALIA, AlertSeverity.WARNING)]

    titulo = base["titulo"]
    if cultivo:
        titulo = f"{titulo} — {cultivo}"
    if etapa:
        titulo = f"{titulo} ({etapa})"

    causa = base["causa"]
    contexto_extra = []
    if etapa:
        contexto_extra.append(f"Etapa actual: {etapa}.")
    if optimo is not None and rango:
        try:
            contexto_extra.append(
                f"Valor medido: {valor:.2f} | óptimo ~{optimo:.2f} "
                f"(rango {rango[0]:.2f}-{rango[1]:.2f})."
            )
        except (TypeError, ValueError, IndexError):
            pass
    if es_etapa_critica:
        contexto_extra.append("Etapa crítica: los problemas ahora afectan más al rendimiento.")
    if contexto_extra:
        causa = causa + " " + " ".join(contexto_extra)

    recomendacion = base["recomendacion"]
    ventana = base["ventana_dias"]
    if es_etapa_critica and severidad == AlertSeverity.WARNING:
        ventana = max(2, ventana - 2)  # actuar más rápido en etapa crítica

    # Enriquecemos la causa con la explicación del índice en lenguaje productor,
    # para que la alerta sea autoexplicativa (no asumimos que se sabe qué es NDMI).
    explicacion = explain_index(indice)
    if explicacion.get("que_mide"):
        causa += (
            f" ({explicacion['nombre_corto']}: {explicacion['que_mide']})"
        )
    porque = por_que_importa(indice, cultivo, etapa)
    if porque:
        recomendacion = f"{recomendacion} {porque}"

    return AlertCopy(
        titulo=titulo,
        causa=causa,
        recomendacion=recomendacion,
        ventana_dias=ventana,
    )


def fallback_copy(*_args, **_kwargs) -> AlertCopy:  # pragma: no cover - removido
    """Compatibilidad: este motor ya NO usa fallbacks genéricos.

    Las alertas solo se generan con ciclo de cultivo activo y lecturas reales.
    """
    raise NotImplementedError(
        "fallback_copy fue eliminado: las alertas requieren un ciclo de cultivo "
        "activo y datos satelitales reales. No se simulan alertas."
    )
