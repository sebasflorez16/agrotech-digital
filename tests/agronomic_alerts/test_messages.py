"""Tests unitarios del catálogo de copy de alertas."""

import pytest

from agronomic_alerts.messages import build_alert_copy, fallback_copy
from agronomic_alerts.models import AlertSeverity, AlertType


pytestmark = pytest.mark.unit


class TestBuildAlertCopy:
    def test_titulo_incluye_cultivo_y_etapa(self):
        copy = build_alert_copy(
            cultivo="Arroz", etapa="Macollamiento", indice="ndvi",
            tipo=AlertType.VIGOR, severidad=AlertSeverity.WARNING,
            valor=0.32, optimo=0.55, rango=[0.45, 0.75],
            es_etapa_critica=False,
        )
        assert "Arroz" in copy.titulo
        assert "Macollamiento" in copy.titulo
        assert copy.ventana_dias >= 1

    def test_critical_humedad_tiene_ventana_corta(self):
        copy = build_alert_copy(
            cultivo="Maíz", etapa="Floración", indice="ndmi",
            tipo=AlertType.HUMEDAD, severidad=AlertSeverity.CRITICAL,
            valor=0.02, optimo=0.25, rango=[0.15, 0.45],
            es_etapa_critica=True,
        )
        assert copy.ventana_dias <= 3  # crítico → actuar rápido
        assert "riego" in copy.recomendacion.lower() or "inspeccionar" in copy.recomendacion.lower()

    def test_etapa_critica_acorta_ventana_en_warning(self):
        normal = build_alert_copy(
            cultivo="Palma", etapa="Producción", indice="ndvi",
            tipo=AlertType.VIGOR, severidad=AlertSeverity.WARNING,
            valor=0.40, optimo=0.60, rango=[0.50, 0.80],
            es_etapa_critica=False,
        )
        critica = build_alert_copy(
            cultivo="Palma", etapa="Producción", indice="ndvi",
            tipo=AlertType.VIGOR, severidad=AlertSeverity.WARNING,
            valor=0.40, optimo=0.60, rango=[0.50, 0.80],
            es_etapa_critica=True,
        )
        assert critica.ventana_dias < normal.ventana_dias

    def test_causa_incluye_valor_y_rango(self):
        copy = build_alert_copy(
            cultivo="Arroz", etapa="Espigado", indice="ndvi",
            tipo=AlertType.VIGOR, severidad=AlertSeverity.WARNING,
            valor=0.42, optimo=0.65, rango=[0.55, 0.80],
            es_etapa_critica=False,
        )
        assert "0.42" in copy.causa
        assert "0.65" in copy.causa


class TestFallbackCopy:
    def test_fallback_copy_lanza_porque_ya_no_se_simula(self):
        """Las alertas requieren ciclo de cultivo activo; no hay fallback."""
        with pytest.raises(NotImplementedError):
            fallback_copy(
                indice="ndvi", tipo=AlertType.VIGOR,
                severidad=AlertSeverity.WARNING,
                valor=0.28, optimo_min=0.50, optimo_max=0.85,
            )
