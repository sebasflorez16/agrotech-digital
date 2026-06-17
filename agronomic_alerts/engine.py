"""
Motor de alertas agronómicas.

Reglas duras:
1. **Sin simulación.** Una alerta solo se crea cuando hay (a) un ciclo de
   cultivo activo asociado a la parcela y (b) una lectura satelital real
   de un índice relevante para ese cultivo.
2. **Crop-aware.** Para cada cultivo se monitorean únicamente los índices
   pertinentes (palma/perennes: NDMI+NDRE+EVI; herbáceos: NDVI+NDMI+SAVI).
3. **Recomendaciones contextualizadas.** El texto se compone con el cultivo
   y la etapa fenológica reales y se acompaña de la explicación de qué mide
   el índice y por qué importa para el productor.

El motor NO llama a EOSDA: recibe los valores ya calculados.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Optional

from .indices import (
    explain_index,
    filter_relevant_readings,
    por_que_importa,
    preferred_indices_for_crop,
)
from .messages import build_alert_copy
from .models import (
    AlertaOperativa,
    AlertSeverity,
    AlertType,
    SatelliteIndex,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Estructuras de entrada
# ---------------------------------------------------------------------------

@dataclass
class IndexReading:
    """Lectura de un índice satelital para una escena."""

    indice: str          # 'ndvi' | 'ndmi' | 'savi' | 'evi' | 'ndre'
    valor: float         # valor medio (o representativo) del lote/zona
    fecha_escena: date   # fecha de la imagen Sentinel-2

    # Opcionales para análisis zonal
    zona: str = ""
    estadisticas: dict = field(default_factory=dict)  # min, max, q1, q3, std...


@dataclass
class AlertOutcome:
    """Resultado de procesar una lectura."""

    alerta: Optional[AlertaOperativa]
    created: bool
    skipped_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Mapeos
# ---------------------------------------------------------------------------

_INDEX_TO_TYPE = {
    SatelliteIndex.NDVI: AlertType.VIGOR,
    SatelliteIndex.SAVI: AlertType.VIGOR,
    SatelliteIndex.EVI: AlertType.COBERTURA,
    SatelliteIndex.NDMI: AlertType.HUMEDAD,
    SatelliteIndex.NDRE: AlertType.VIGOR,  # nutricional → vigor
}

# Mapeo del `alert_level` que devuelve CropCycle.get_index_interpretation
# (`optimal` | `normal` | `warning` | `critical` | `high`) a nuestra severidad.
_CYCLE_LEVEL_TO_SEVERITY = {
    "critical": AlertSeverity.CRITICAL,
    "warning": AlertSeverity.WARNING,
    "high": AlertSeverity.WARNING,   # por encima del rango: notar, no críticar
}


# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------

class AgronomicAlertEngine:
    """
    Genera y persiste alertas agronómicas para una parcela a partir de
    lecturas reales de índices satelitales.

    Sin ciclo de cultivo activo → NO se generan alertas (el productor debe
    asignar primero el cultivo). Esto evita cualquier tipo de simulación.

    Uso típico:
        engine = AgronomicAlertEngine(parcel)
        outcomes = engine.process_readings([
            IndexReading('ndmi', 0.08, fecha_escena),
            IndexReading('ndre', 0.20, fecha_escena),
        ])
    """

    def __init__(self, parcel, *, ventana_dias_default: int = 7):
        self.parcel = parcel
        self.ventana_dias_default = ventana_dias_default
        self._crop_cycle = self._resolve_active_crop_cycle()
        self._crop_catalog = (
            getattr(self._crop_cycle, "crop_catalog", None)
            if self._crop_cycle else None
        )
        self._preferred_indices = preferred_indices_for_crop(self._crop_catalog)

    # ---- Helpers de contexto ----
    def _resolve_active_crop_cycle(self):
        """Devuelve el CropCycle activo más reciente para la parcela, o None."""
        try:
            return (
                self.parcel.crop_cycles
                .filter(status="active")
                .order_by("-planting_date")
                .first()
            )
        except Exception:  # noqa: BLE001 - lazy import, parcela en test sin relación
            logger.debug("Parcela %s sin crop_cycles relacionados.", self.parcel.pk)
            return None

    # ---- API pública ----
    def process_readings(
        self, readings: Iterable[IndexReading],
    ) -> list[AlertOutcome]:
        """Procesa lecturas. Filtra primero a las relevantes para el cultivo."""
        relevantes = filter_relevant_readings(readings, self._crop_catalog)
        if not self._crop_cycle:
            return [
                AlertOutcome(
                    alerta=None, created=False,
                    skipped_reason="parcela_sin_ciclo_de_cultivo",
                )
                for _ in readings
            ]
        return [self.process_reading(r) for r in relevantes]

    def process_reading(self, reading: IndexReading) -> AlertOutcome:
        """Procesa una lectura individual y persiste alerta si aplica."""
        indice_norm = (reading.indice or "").lower().strip()

        if indice_norm not in SatelliteIndex.values:
            return AlertOutcome(
                alerta=None, created=False,
                skipped_reason=f"indice_no_soportado:{reading.indice}",
            )
        if not self._crop_cycle:
            return AlertOutcome(
                alerta=None, created=False,
                skipped_reason="parcela_sin_ciclo_de_cultivo",
            )
        if self._preferred_indices and indice_norm not in self._preferred_indices:
            return AlertOutcome(
                alerta=None, created=False,
                skipped_reason=f"indice_no_relevante_para_cultivo:{indice_norm}",
            )

        # `get_index_interpretation` solo soporta NDVI/NDMI/SAVI hoy.
        # Para EVI/NDRE intentamos igualmente; si no hay rangos definidos
        # en la etapa fenológica, NO inventamos umbrales (no simulamos).
        return self._process_with_cycle(indice_norm, reading)

    # ---- Caso A: con CropCycle ----
    def _process_with_cycle(self, indice_norm, reading):
        cycle = self._crop_cycle
        try:
            interp = cycle.get_index_interpretation(indice_norm, reading.valor)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Fallo get_index_interpretation parcel=%s indice=%s: %s",
                self.parcel.pk, indice_norm, exc,
            )
            return AlertOutcome(
                alerta=None, created=False,
                skipped_reason=f"interpretacion_no_disponible:{indice_norm}",
            )

        level = interp.get("status")
        if level == "unknown":
            return AlertOutcome(
                alerta=None, created=False,
                skipped_reason=f"rangos_no_definidos_para_etapa:{indice_norm}",
            )

        severidad = _CYCLE_LEVEL_TO_SEVERITY.get(level)
        if severidad is None:
            # `optimal` o `normal`: lote sano, no se crea alerta.
            return AlertOutcome(
                alerta=None, created=False,
                skipped_reason=f"sin_desviacion_relevante:{level}",
            )

        stage_info = interp.get("stage") or {}
        index_info = interp.get("index") or {}
        crop_info = interp.get("crop") or {}

        tipo = _INDEX_TO_TYPE[SatelliteIndex(indice_norm)]
        copy = build_alert_copy(
            cultivo=crop_info.get("name", ""),
            etapa=stage_info.get("name", ""),
            indice=indice_norm,
            tipo=tipo,
            severidad=severidad,
            valor=reading.valor,
            optimo=index_info.get("optimal"),
            rango=index_info.get("range"),
            es_etapa_critica=stage_info.get("is_critical", False),
        )

        rango = index_info.get("range") or [None, None]
        explicacion = explain_index(indice_norm)
        contexto = {
            "cultivo": crop_info.get("name"),
            "categoria": crop_info.get("category"),
            "etapa": stage_info,
            "indice": index_info,
            "dias_desde_siembra": interp.get("days_since_planting"),
            "progreso_pct": interp.get("progress_percent"),
            "estadisticas": reading.estadisticas,
            "interpretacion_raw": interp,
            # Contexto educativo para el productor (frontend lo renderiza tal cual).
            "explicacion_indice": explicacion,
            "por_que_importa": por_que_importa(
                indice_norm,
                crop_info.get("name", ""),
                stage_info.get("name", ""),
            ),
            "indices_monitoreados": list(self._preferred_indices),
        }

        return self._persist(
            indice_norm=indice_norm,
            reading=reading,
            tipo=tipo,
            severidad=severidad,
            titulo=copy.titulo,
            causa=copy.causa,
            recomendacion=copy.recomendacion,
            ventana_dias=copy.ventana_dias,
            umbral_min=rango[0] if len(rango) > 0 else None,
            umbral_max=rango[1] if len(rango) > 1 else None,
            desviacion_pct=index_info.get("deviation_percent"),
            contexto=contexto,
        )

    # ---- Persistencia idempotente ----
    def _persist(
        self, *, indice_norm, reading, tipo, severidad,
        titulo, causa, recomendacion, ventana_dias,
        umbral_min, umbral_max, desviacion_pct, contexto,
    ):
        fingerprint = AlertaOperativa.build_fingerprint(
            parcel_id=self.parcel.pk,
            indice=indice_norm,
            tipo=tipo,
            fecha_escena=reading.fecha_escena,
            zona=reading.zona,
        )

        defaults = {
            "parcel": self.parcel,
            "crop_cycle": self._crop_cycle,
            "tipo": tipo,
            "severidad": severidad,
            "indice_afectado": indice_norm,
            "titulo": titulo[:200],
            "zona": reading.zona or "",
            "causa_probable": causa,
            "valor_observado": reading.valor,
            "valor_umbral_min": umbral_min,
            "valor_umbral_max": umbral_max,
            "desviacion_pct": desviacion_pct,
            "recomendacion": recomendacion,
            "ventana_dias": ventana_dias or self.ventana_dias_default,
            "fecha_escena_origen": reading.fecha_escena,
            "contexto": contexto,
        }

        alerta, created = AlertaOperativa.objects.get_or_create(
            fingerprint=fingerprint,
            defaults=defaults,
        )
        return AlertOutcome(alerta=alerta, created=created)
