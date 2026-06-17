"""
Tests unitarios del motor `AgronomicAlertEngine`.

Estos tests NO tocan la base de datos: usan mocks para `Parcel`,
`CropCycle` y para el manager de `AlertaOperativa`. Validan la
lógica de decisión (qué crea, qué descarta, idempotencia).

Los tests con base de datos real van en `tests/agronomic_alerts/
test_engine_integration.py` (Sprint 2).
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agronomic_alerts.engine import (
    AgronomicAlertEngine,
    IndexReading,
)
from agronomic_alerts.models import (
    AlertaOperativa,
    AlertSeverity,
    AlertType,
)


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_parcel(pk=1, with_active_cycle=None):
    parcel = MagicMock(name="Parcel")
    parcel.pk = pk
    parcel.id = pk

    qs = MagicMock(name="CropCycleQuerySet")
    if with_active_cycle is not None:
        qs.filter.return_value.order_by.return_value.first.return_value = with_active_cycle
    else:
        qs.filter.return_value.order_by.return_value.first.return_value = None
    parcel.crop_cycles = qs
    return parcel


def _mock_crop_cycle(*, status_level, stage_name="Macollamiento",
                     crop_name="Arroz", crop_category="cereals",
                     optimal=0.55, rango=(0.40, 0.75),
                     deviation_pct=35.0, is_critical=False):
    """Devuelve un CropCycle cuyo get_index_interpretation retorna un dict fijo."""
    cycle = MagicMock(name="CropCycle")
    cycle.pk = 99
    cycle.crop_catalog = SimpleNamespace(name=crop_name, category=crop_category)

    interp = {
        "status": status_level,
        "message": "msg",
        "stage": {
            "name": stage_name,
            "day_start": 30, "day_end": 60,
            "is_critical": is_critical,
            "water_need": 4,
        },
        "index": {
            "type": "ndvi",
            "value": 0.30,
            "optimal": optimal,
            "range": list(rango),
            "deviation_percent": deviation_pct,
        },
        "crop": {"name": crop_name, "category": "cereals"},
        "days_since_planting": 45,
        "progress_percent": 40,
    }
    cycle.get_index_interpretation.return_value = interp
    return cycle


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEngineConCropCycle:
    @patch.object(AlertaOperativa.objects, "get_or_create")
    def test_critical_crea_alerta_con_severidad_critical(self, get_or_create):
        get_or_create.return_value = (MagicMock(spec=AlertaOperativa), True)

        cycle = _mock_crop_cycle(status_level="critical", is_critical=True)
        parcel = _mock_parcel(with_active_cycle=cycle)
        engine = AgronomicAlertEngine(parcel)

        outcome = engine.process_reading(IndexReading(
            indice="ndvi", valor=0.20, fecha_escena=date(2025, 1, 15),
        ))

        assert outcome.created is True
        kwargs = get_or_create.call_args.kwargs
        defaults = kwargs["defaults"]
        assert defaults["severidad"] == AlertSeverity.CRITICAL
        assert defaults["tipo"] == AlertType.VIGOR
        assert defaults["indice_afectado"] == "ndvi"
        assert defaults["parcel"] is parcel
        assert defaults["crop_cycle"] is cycle
        assert defaults["fecha_escena_origen"] == date(2025, 1, 15)
        assert "fingerprint" in kwargs

    @patch.object(AlertaOperativa.objects, "get_or_create")
    def test_optimal_no_crea_alerta(self, get_or_create):
        cycle = _mock_crop_cycle(status_level="optimal")
        parcel = _mock_parcel(with_active_cycle=cycle)
        engine = AgronomicAlertEngine(parcel)

        outcome = engine.process_reading(IndexReading(
            indice="ndvi", valor=0.55, fecha_escena=date(2025, 1, 15),
        ))

        assert outcome.created is False
        assert outcome.alerta is None
        get_or_create.assert_not_called()

    @patch.object(AlertaOperativa.objects, "get_or_create")
    def test_ndmi_mapea_a_humedad(self, get_or_create):
        get_or_create.return_value = (MagicMock(spec=AlertaOperativa), True)
        cycle = _mock_crop_cycle(status_level="warning")
        parcel = _mock_parcel(with_active_cycle=cycle)
        engine = AgronomicAlertEngine(parcel)

        engine.process_reading(IndexReading(
            indice="ndmi", valor=0.10, fecha_escena=date(2025, 1, 20),
        ))

        defaults = get_or_create.call_args.kwargs["defaults"]
        assert defaults["tipo"] == AlertType.HUMEDAD


class TestEngineSinCropCycle:
    """Sin ciclo de cultivo asignado, el motor NO genera alertas (no se simula)."""

    @patch.object(AlertaOperativa.objects, "get_or_create")
    def test_sin_ciclo_no_crea_alerta(self, get_or_create):
        parcel = _mock_parcel(with_active_cycle=None)
        engine = AgronomicAlertEngine(parcel)

        outcome = engine.process_reading(IndexReading(
            indice="ndvi", valor=0.15, fecha_escena=date(2025, 1, 10),
        ))

        assert outcome.created is False
        assert outcome.alerta is None
        assert outcome.skipped_reason == "parcela_sin_ciclo_de_cultivo"
        get_or_create.assert_not_called()

    @patch.object(AlertaOperativa.objects, "get_or_create")
    def test_sin_ciclo_lote_de_lecturas_no_genera_nada(self, get_or_create):
        parcel = _mock_parcel(with_active_cycle=None)
        engine = AgronomicAlertEngine(parcel)

        outcomes = engine.process_readings([
            IndexReading(indice="ndvi", valor=0.15, fecha_escena=date(2025, 1, 10)),
            IndexReading(indice="ndmi", valor=0.05, fecha_escena=date(2025, 1, 10)),
        ])

        assert all(o.created is False for o in outcomes)
        assert all(o.skipped_reason == "parcela_sin_ciclo_de_cultivo" for o in outcomes)
        get_or_create.assert_not_called()


class TestEngineCropAware:
    """Los índices monitoreados dependen del cultivo (palma vs herbáceos)."""

    @patch.object(AlertaOperativa.objects, "get_or_create")
    def test_evi_no_se_genera_para_cereales(self, get_or_create):
        cycle = _mock_crop_cycle(
            status_level="critical", crop_name="Arroz", crop_category="cereals",
        )
        parcel = _mock_parcel(with_active_cycle=cycle)
        engine = AgronomicAlertEngine(parcel)

        outcome = engine.process_reading(IndexReading(
            indice="evi", valor=0.10, fecha_escena=date(2025, 2, 1),
        ))

        assert outcome.created is False
        assert "indice_no_relevante_para_cultivo" in (outcome.skipped_reason or "")
        get_or_create.assert_not_called()

    @patch.object(AlertaOperativa.objects, "get_or_create")
    def test_ndvi_no_se_genera_para_palma(self, get_or_create):
        cycle = _mock_crop_cycle(
            status_level="critical",
            crop_name="Palma de Aceite", crop_category="oilseeds",
        )
        parcel = _mock_parcel(with_active_cycle=cycle)
        engine = AgronomicAlertEngine(parcel)

        outcome = engine.process_reading(IndexReading(
            indice="ndvi", valor=0.30, fecha_escena=date(2025, 2, 1),
        ))

        assert outcome.created is False
        assert "indice_no_relevante_para_cultivo" in (outcome.skipped_reason or "")
        get_or_create.assert_not_called()


class TestIdempotencia:
    def test_fingerprint_es_determinista(self):
        f1 = AlertaOperativa.build_fingerprint(
            parcel_id=10, indice="ndvi", tipo=AlertType.VIGOR,
            fecha_escena=date(2025, 1, 15), zona="norte",
        )
        f2 = AlertaOperativa.build_fingerprint(
            parcel_id=10, indice="ndvi", tipo=AlertType.VIGOR,
            fecha_escena=date(2025, 1, 15), zona="NORTE",
        )
        # Misma información → mismo fingerprint (case-insensitive en zona)
        assert f1 == f2

    def test_fingerprint_cambia_con_fecha(self):
        f1 = AlertaOperativa.build_fingerprint(
            parcel_id=10, indice="ndvi", tipo=AlertType.VIGOR,
            fecha_escena=date(2025, 1, 15),
        )
        f2 = AlertaOperativa.build_fingerprint(
            parcel_id=10, indice="ndvi", tipo=AlertType.VIGOR,
            fecha_escena=date(2025, 1, 16),
        )
        assert f1 != f2

    def test_fingerprint_cambia_con_parcela(self):
        f1 = AlertaOperativa.build_fingerprint(
            parcel_id=10, indice="ndvi", tipo=AlertType.VIGOR,
            fecha_escena=date(2025, 1, 15),
        )
        f2 = AlertaOperativa.build_fingerprint(
            parcel_id=11, indice="ndvi", tipo=AlertType.VIGOR,
            fecha_escena=date(2025, 1, 15),
        )
        assert f1 != f2


class TestProcessReadings:
    @patch.object(AlertaOperativa.objects, "get_or_create")
    def test_procesa_multiples_lecturas_en_un_call(self, get_or_create):
        get_or_create.return_value = (MagicMock(spec=AlertaOperativa), True)
        # Con ciclo de cultivo activo: lecturas críticas → alertas; óptima → no.
        cycle_critico = _mock_crop_cycle(status_level="critical")
        parcel = _mock_parcel(with_active_cycle=cycle_critico)

        # `process_readings` invoca a `process_reading` por cada lectura.
        # Configuramos el side_effect del CropCycle: dos críticos y un óptimo.
        def _interp_side_effect(indice, valor):
            level = "critical" if valor < 0.40 else "optimal"
            return {
                "status": level,
                "stage": {"name": "Macollamiento", "is_critical": False,
                          "day_start": 30, "day_end": 60, "water_need": 4},
                "index": {"type": indice, "value": valor,
                          "optimal": 0.55, "range": [0.40, 0.75],
                          "deviation_percent": 50.0},
                "crop": {"name": "Arroz", "category": "cereals"},
                "days_since_planting": 45, "progress_percent": 40,
            }
        cycle_critico.get_index_interpretation.side_effect = _interp_side_effect

        engine = AgronomicAlertEngine(parcel)
        outcomes = engine.process_readings([
            IndexReading("ndvi", 0.15, date(2025, 1, 1)),
            IndexReading("ndmi", 0.02, date(2025, 1, 1)),
            IndexReading("ndvi", 0.70, date(2025, 1, 1)),  # óptimo, no genera
        ])

        creadas = [o for o in outcomes if o.created]
        descartadas = [o for o in outcomes if not o.created]
        assert len(creadas) == 2
        assert len(descartadas) == 1
