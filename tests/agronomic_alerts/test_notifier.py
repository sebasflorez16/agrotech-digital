"""Tests del notificador de alertas."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agronomic_alerts.models import AlertSeverity
from agronomic_alerts.notifier import (
    AlertNotifier,
    SEVERITY_RANK,
    default_recipients_resolver,
)


pytestmark = pytest.mark.unit


def _mock_alerta(severidad=AlertSeverity.WARNING):
    alerta = MagicMock()
    alerta.pk = 1
    alerta.severidad = severidad
    alerta.titulo = "Vigor por debajo del esperado — Arroz (Macollamiento)"
    alerta.causa_probable = "NDVI por debajo del óptimo."
    alerta.recomendacion = "Revisar el lote en 7 días."
    alerta.ventana_dias = 7
    alerta.fecha_escena_origen = date(2025, 1, 15)
    alerta.valor_observado = 0.32
    alerta.valor_umbral_min = 0.45
    alerta.valor_umbral_max = 0.75
    alerta.indice_afectado = "ndvi"
    alerta.tipo = "vigor"
    alerta.zona = ""
    alerta.contexto = {}
    alerta.parcel = SimpleNamespace(name="Lote 1", pk=1)
    alerta.get_severidad_display.return_value = "Advertencia"
    alerta.get_tipo_display.return_value = "Vigor vegetativo"
    alerta.get_indice_afectado_display.return_value = "NDVI"
    return alerta


class TestSeverityGate:
    def test_severity_rank_ordenado(self):
        assert SEVERITY_RANK[AlertSeverity.INFO] < SEVERITY_RANK[AlertSeverity.WARNING]
        assert SEVERITY_RANK[AlertSeverity.WARNING] < SEVERITY_RANK[AlertSeverity.CRITICAL]

    def test_info_se_omite_con_default(self):
        notifier = AlertNotifier()
        result = notifier.notify(_mock_alerta(severidad=AlertSeverity.INFO))
        assert result.sent == 0
        assert result.skipped == 1

    @patch("agronomic_alerts.notifier._tenant_has_email_feature", return_value=True)
    @patch("agronomic_alerts.notifier._resolve_recipients", return_value=[])
    def test_sin_destinatarios_skip(self, _res, _feat):
        notifier = AlertNotifier()
        result = notifier.notify(_mock_alerta(severidad=AlertSeverity.WARNING))
        assert result.sent == 0
        assert result.skipped == 1

    @patch("agronomic_alerts.notifier._tenant_has_email_feature", return_value=False)
    @patch("agronomic_alerts.notifier._resolve_recipients", return_value=["a@x.com"])
    def test_sin_feature_alerts_email_skip(self, _res, _feat):
        notifier = AlertNotifier()
        result = notifier.notify(_mock_alerta(severidad=AlertSeverity.WARNING))
        assert result.sent == 0
        assert result.skipped == 1


class TestRender:
    def test_render_produce_subject_y_cuerpos(self):
        notifier = AlertNotifier()
        subject, text_body, html_body = notifier._render(_mock_alerta())
        assert subject.startswith("[Alerta]") or subject.startswith("[Crítica]")
        assert "Macollamiento" in subject
        assert "NDVI" in text_body
        assert "Lote 1" in text_body
        assert "<html" in html_body.lower()
        assert "Vigor vegetativo" in html_body

    def test_render_critica_marca_prefijo(self):
        notifier = AlertNotifier()
        alerta = _mock_alerta(severidad=AlertSeverity.CRITICAL)
        subject, _, _ = notifier._render(alerta)
        assert subject.startswith("[Crítica]")


class TestSendIntegration:
    """Tests del flujo de envío con mock de get_or_create y EmailMultiAlternatives."""

    @patch("agronomic_alerts.notifier._tenant_has_email_feature", return_value=True)
    @patch("agronomic_alerts.notifier.EmailMultiAlternatives")
    @patch("agronomic_alerts.notifier._resolve_recipients", return_value=["a@x.com", "b@x.com"])
    @patch("agronomic_alerts.notifier.AlertNotification.objects")
    def test_envia_a_todos_los_destinatarios(self, notif_mgr, _res, EmailCls, _feat):
        # Cada llamada a get_or_create devuelve un mock fresco con marcar_enviada.
        notifs = [MagicMock(estado="pendiente"), MagicMock(estado="pendiente")]
        notif_mgr.get_or_create.side_effect = [(n, True) for n in notifs]
        EmailCls.return_value.send.return_value = 1

        notifier = AlertNotifier()
        result = notifier.notify(_mock_alerta(severidad=AlertSeverity.WARNING))

        assert result.sent == 2
        for n in notifs:
            n.marcar_enviada.assert_called_once()

    @patch("agronomic_alerts.notifier._tenant_has_email_feature", return_value=True)
    @patch("agronomic_alerts.notifier.EmailMultiAlternatives")
    @patch("agronomic_alerts.notifier._resolve_recipients", return_value=["a@x.com"])
    @patch("agronomic_alerts.notifier.AlertNotification.objects")
    def test_skip_si_ya_fue_enviada(self, notif_mgr, _res, EmailCls, _feat):
        n = MagicMock()
        n.estado = "enviada"
        notif_mgr.get_or_create.return_value = (n, False)

        notifier = AlertNotifier()
        result = notifier.notify(_mock_alerta(severidad=AlertSeverity.WARNING))

        assert result.sent == 0
        assert result.skipped == 1
        EmailCls.return_value.send.assert_not_called()

    @patch("agronomic_alerts.notifier._tenant_has_email_feature", return_value=True)
    @patch("agronomic_alerts.notifier.EmailMultiAlternatives")
    @patch("agronomic_alerts.notifier._resolve_recipients", return_value=["a@x.com"])
    @patch("agronomic_alerts.notifier.AlertNotification.objects")
    def test_marca_fallida_en_error_smtp(self, notif_mgr, _res, EmailCls, _feat):
        n = MagicMock(estado="pendiente")
        notif_mgr.get_or_create.return_value = (n, True)
        EmailCls.return_value.send.side_effect = RuntimeError("smtp down")

        notifier = AlertNotifier()
        result = notifier.notify(_mock_alerta(severidad=AlertSeverity.WARNING))

        assert result.failed == 1
        assert result.sent == 0
        n.marcar_fallida.assert_called_once()
