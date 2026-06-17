"""Tests del extractor de lecturas desde la respuesta de EOSDA Statistics."""

from datetime import date

import pytest

from agronomic_alerts.management.commands.detectar_alertas import (
    _extract_latest_reading,
)


pytestmark = pytest.mark.unit


class TestExtractLatestReading:
    def test_payload_vacio(self):
        assert _extract_latest_reading(None) is None
        assert _extract_latest_reading({}) is None
        assert _extract_latest_reading({"data": []}) is None

    def test_toma_la_fecha_mas_reciente(self):
        payload = {
            "data": [
                {"date": "2025-01-10", "mean": 0.45, "cloud": 5},
                {"date": "2025-01-20", "mean": 0.55, "cloud": 8},
                {"date": "2025-01-15", "mean": 0.50, "cloud": 12},
            ]
        }
        fecha, valor = _extract_latest_reading(payload)
        assert fecha == date(2025, 1, 20)
        assert valor == pytest.approx(0.55)

    def test_filtra_escenas_con_nubes_altas(self):
        payload = {
            "data": [
                {"date": "2025-01-20", "mean": 0.60, "cloud": 80},  # descartar
                {"date": "2025-01-10", "mean": 0.50, "cloud": 10},  # ok
            ]
        }
        fecha, valor = _extract_latest_reading(payload)
        assert fecha == date(2025, 1, 10)
        assert valor == pytest.approx(0.50)

    def test_acepta_formato_alternativo_average(self):
        payload = {
            "data": [
                {"date": "2025-02-01", "average": 0.32},
            ]
        }
        fecha, valor = _extract_latest_reading(payload)
        assert fecha == date(2025, 2, 1)
        assert valor == pytest.approx(0.32)

    def test_descarta_items_sin_fecha_o_valor(self):
        payload = {
            "data": [
                {"date": "2025-02-01"},                # sin valor
                {"mean": 0.5},                          # sin fecha
                {"date": "bad-date", "mean": 0.5},      # fecha inválida
                {"date": "2025-02-10", "mean": 0.40},   # ok
            ]
        }
        fecha, _ = _extract_latest_reading(payload)
        assert fecha == date(2025, 2, 10)
