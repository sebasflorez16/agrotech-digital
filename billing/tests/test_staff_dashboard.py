"""
Tests para el Panel de Control del Operador SaaS (Staff Dashboard).

Verifica:
- El HTML del dashboard es accesible sin autenticación
- Los endpoints JSON requieren is_staff=True
- Los usuarios normales (is_staff=False) reciben 403
- Los endpoints devuelven la estructura JSON correcta
- La búsqueda de tenants funciona

EJECUTAR:
    pytest billing/tests/test_staff_dashboard.py -v
"""

import pytest
from collections import defaultdict
from unittest.mock import patch, MagicMock, PropertyMock
from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone


def _zero_agg():
    """MagicMock de aggregate que devuelve Decimal('0') para cualquier clave."""
    m = MagicMock()
    m.__getitem__ = MagicMock(return_value=Decimal("0"))
    return m

User = get_user_model()


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def _staff_user():
    """Crea un mock de usuario staff."""
    u = MagicMock(spec=User)
    u.id = 1
    u.email = "admin@agrotech.co"
    u.username = "admin"
    u.is_staff = True
    u.is_superuser = True
    u.is_active = True
    u.is_anonymous = False
    u.is_authenticated = True
    return u


def _normal_user():
    """Crea un mock de usuario normal (no staff)."""
    u = MagicMock(spec=User)
    u.id = 2
    u.email = "user@tenant.co"
    u.username = "regularuser"
    u.is_staff = False
    u.is_superuser = False
    u.is_active = True
    u.is_anonymous = False
    u.is_authenticated = True
    return u


def _make_get_request(user=None):
    """Crea una Request GET con usuario dado."""
    rf = RequestFactory()
    req = rf.get("/staff/api/metrics/")
    req.user = user or _staff_user()
    return req


# ──────────────────────────────────────────────────────────────
# UNIT TESTS — Importaciones y estructura
# ──────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestStaffViewsImport:
    """Verifica que las vistas se importan correctamente."""

    def test_views_importable(self):
        from billing.views_staff import StaffMetricsAPI, StaffTenantsAPI
        assert StaffMetricsAPI is not None
        assert StaffTenantsAPI is not None

    def test_metrics_api_has_correct_permissions(self):
        from billing.views_staff import StaffMetricsAPI
        from rest_framework.permissions import IsAdminUser
        view = StaffMetricsAPI()
        perm_classes = [type(p) for p in view.get_permissions()]
        assert IsAdminUser in perm_classes

    def test_tenants_api_has_correct_permissions(self):
        from billing.views_staff import StaffTenantsAPI
        from rest_framework.permissions import IsAdminUser
        view = StaffTenantsAPI()
        perm_classes = [type(p) for p in view.get_permissions()]
        assert IsAdminUser in perm_classes

    def test_urls_importable(self):
        from billing import urls_staff
        assert hasattr(urls_staff, "urlpatterns")
        assert len(urls_staff.urlpatterns) == 2  # solo API: metrics + tenants

    def test_urls_have_correct_names(self):
        from billing.urls_staff import urlpatterns
        names = {p.name for p in urlpatterns}
        assert "staff_metrics" in names
        assert "staff_tenants" in names
        # El HTML vive en el frontend (Netlify), no en el backend
        assert "staff_dashboard" not in names


# ──────────────────────────────────────────────────────────────
# UNIT TESTS — Permisos
# ──────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestStaffPermissions:
    """Verifica que los endpoints protegen correctamente el acceso."""

    def test_normal_user_denied_metrics(self):
        """Un usuario sin is_staff=True debe recibir 403."""
        from billing.views_staff import StaffMetricsAPI
        rf = RequestFactory()
        req = rf.get("/staff/api/metrics/")
        req.user = _normal_user()
        view = StaffMetricsAPI.as_view()
        # Parcheamos las autenticaciones para que devuelvan el usuario normal
        with patch.object(StaffMetricsAPI, "perform_authentication", return_value=None):
            response = view(req)
        assert response.status_code == 403

    def test_normal_user_denied_tenants(self):
        """Un usuario sin is_staff=True no puede ver tenants."""
        from billing.views_staff import StaffTenantsAPI
        rf = RequestFactory()
        req = rf.get("/staff/api/tenants/")
        req.user = _normal_user()
        view = StaffTenantsAPI.as_view()
        with patch.object(StaffTenantsAPI, "perform_authentication", return_value=None):
            response = view(req)
        assert response.status_code == 403

    def test_unauthenticated_denied(self):
        """Un usuario no autenticado debe recibir 401."""
        from billing.views_staff import StaffMetricsAPI
        from django.contrib.auth.models import AnonymousUser
        rf = RequestFactory()
        req = rf.get("/staff/api/metrics/")
        req.user = AnonymousUser()
        view = StaffMetricsAPI.as_view()
        with patch.object(StaffMetricsAPI, "perform_authentication", return_value=None):
            response = view(req)
        assert response.status_code in (401, 403)


# ──────────────────────────────────────────────────────────────
# UNIT TESTS — Métricas API (con mocks)
# ──────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestStaffMetricsAPIUnit:
    """Tests unitarios de StaffMetricsAPI con toda la BD mockeada."""

    def _get_mocked_response(self):
        """Llama a la vista con todos los modelos mockeados."""
        from billing.views_staff import StaffMetricsAPI
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get("/staff/api/metrics/")
        request.user = _staff_user()

        view = StaffMetricsAPI()
        view.request = Request(request)
        view.format_kwarg = None

        now = timezone.now()
        sample_events = [
            {
                "created_at": now,
                "tenant__name": "Finca Test",
                "event_type": "invoice.paid",
                "data": {"amount": 350000},
            }
        ]

        def _make_values_qs(data):
            """Devuelve un MagicMock cuyo slice devuelve un mock con .values() = data."""
            sliced = MagicMock()
            sliced.values.return_value = data
            qs = MagicMock()
            qs.__getitem__ = MagicMock(return_value=sliced)
            return qs

        with patch("billing.views_staff.Client.objects") as mc, \
             patch("billing.views_staff.Subscription.objects") as ms, \
             patch("billing.views_staff.Invoice.objects") as mi, \
             patch("billing.views_staff.BillingEvent.objects") as me, \
             patch("billing.views_staff.UsageMetrics.objects") as mu:

            # Client
            mc.exclude.return_value.count.return_value = 5
            mc.exclude.return_value.filter.return_value.count.return_value = 2

            # Subscription — 4 .filter().count() calls: active, trialing, canceled, past_due
            ms.filter.return_value.count.side_effect = [3, 1, 0, 0]
            ms.filter.return_value.aggregate.return_value = {"mrr": Decimal("1050000")}
            ms.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
                {"plan__name": "Empresarial", "plan__tier": "pro", "count": 3}
            ]

            # Invoice — aggregate puede usar clave "total" o "t"
            mi.filter.return_value.aggregate.return_value = _zero_agg()
            # Para recent_invoices: select_related().order_by()[:15].values()
            mi.select_related.return_value.order_by.return_value = _make_values_qs([])

            # BillingEvent — select_related().order_by()[:25].values()
            me.select_related.return_value.order_by.return_value = _make_values_qs(sample_events)

            # UsageMetrics — filter().select_related().order_by()[:10].values()
            mu.filter.return_value.select_related.return_value.order_by.return_value = _make_values_qs([])

            response = view.get(view.request)

        return response

    def test_returns_200(self):
        resp = self._get_mocked_response()
        assert resp.status_code == 200

    def test_has_kpis_key(self):
        resp = self._get_mocked_response()
        assert "kpis" in resp.data

    def test_kpis_has_required_fields(self):
        resp = self._get_mocked_response()
        kpis = resp.data["kpis"]
        required = [
            "total_tenants", "new_this_month", "active_subs",
            "trialing_subs", "canceled_subs", "past_due_subs",
            "mrr_cop", "revenue_this_month_cop",
        ]
        for field in required:
            assert field in kpis, f"Campo faltante en kpis: {field}"

    def test_has_revenue_history_key(self):
        resp = self._get_mocked_response()
        assert "revenue_history" in resp.data

    def test_revenue_history_has_6_months(self):
        resp = self._get_mocked_response()
        # Puede ser menos si algunos meses no tienen facturas (zeros)
        assert len(resp.data["revenue_history"]) == 6

    def test_has_by_plan_key(self):
        resp = self._get_mocked_response()
        assert "by_plan" in resp.data

    def test_has_recent_events_key(self):
        resp = self._get_mocked_response()
        assert "recent_events" in resp.data

    def test_has_top_usage_key(self):
        resp = self._get_mocked_response()
        assert "top_usage" in resp.data

    def test_has_recent_invoices_key(self):
        resp = self._get_mocked_response()
        assert "recent_invoices" in resp.data


# ──────────────────────────────────────────────────────────────
# UNIT TESTS — Tenants API (con mocks)
# ──────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestStaffTenantsAPIUnit:
    """Tests unitarios de StaffTenantsAPI con BD mockeada."""

    def _get_response(self, search=""):
        from billing.views_staff import StaffTenantsAPI
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        url = f"/staff/api/tenants/?search={search}" if search else "/staff/api/tenants/"
        request = factory.get(url)
        request.user = _staff_user()

        drf_request = Request(request)
        view = StaffTenantsAPI()
        view.request = drf_request
        view.format_kwarg = None

        now = timezone.now()

        # Tenant mock
        mock_plan = MagicMock()
        mock_plan.name = "Empresarial"
        mock_plan.tier = "pro"

        mock_sub = MagicMock()
        mock_sub.plan = mock_plan
        mock_sub.status = "active"
        mock_sub.payment_gateway = "mercadopago"

        mock_tenant = MagicMock()
        mock_tenant.id = 1
        mock_tenant.name = "Finca Los Andes"
        mock_tenant.schema_name = "finca_los_andes"
        mock_tenant.created_on = now
        mock_tenant.paid_until = now.date()

        # Simular que tiene 'subscription' como atributo
        type(mock_tenant).subscription = PropertyMock(return_value=mock_sub)

        mock_qs = MagicMock()
        mock_qs.__iter__ = MagicMock(return_value=iter([mock_tenant]))

        with patch("billing.views_staff.Client.objects") as mc, \
             patch("billing.views_staff.UsageMetrics.objects") as mu:

            mc.exclude.return_value.prefetch_related.return_value.order_by.return_value = mock_qs
            mc.exclude.return_value.prefetch_related.return_value.order_by.return_value.filter.return_value = mock_qs
            mu.filter.return_value.select_related.return_value.first.return_value = None

            response = view.get(view.request)

        return response

    def test_returns_200(self):
        assert self._get_response().status_code == 200

    def test_returns_tenants_key(self):
        resp = self._get_response()
        assert "tenants" in resp.data

    def test_returns_total_key(self):
        resp = self._get_response()
        assert "total" in resp.data

    def test_tenant_has_required_fields(self):
        resp = self._get_response()
        if resp.data["tenants"]:
            tenant = resp.data["tenants"][0]
            required = ["id", "name", "schema", "plan", "tier", "status", "eosda_requests"]
            for f in required:
                assert f in tenant, f"Campo faltante en tenant: {f}"


# ──────────────────────────────────────────────────────────────
# UNIT TESTS — Helper _month_range
# ──────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestMonthRangeHelper:
    """Tests para la función helper _month_range."""

    def test_returns_tuple_of_two(self):
        from billing.views_staff import _month_range
        result = _month_range(2024, 3)
        assert len(result) == 2

    def test_start_is_first_day(self):
        from billing.views_staff import _month_range
        start, end = _month_range(2024, 3)
        assert start.day == 1
        assert start.month == 3
        assert start.year == 2024

    def test_end_is_last_day_of_month(self):
        from billing.views_staff import _month_range
        start, end = _month_range(2024, 2)  # Febrero 2024 (bisiesto)
        assert end.day == 29
        assert end.month == 2

    def test_end_is_last_day_non_leap(self):
        from billing.views_staff import _month_range
        _, end = _month_range(2023, 2)  # Febrero 2023 (no bisiesto)
        assert end.day == 28

    def test_december_last_day(self):
        from billing.views_staff import _month_range
        _, end = _month_range(2024, 12)
        assert end.day == 31

    def test_dates_are_timezone_aware(self):
        from billing.views_staff import _month_range
        import django.utils.timezone as tz
        start, end = _month_range(2024, 6)
        assert tz.is_aware(start)
        assert tz.is_aware(end)

    def test_start_before_end(self):
        from billing.views_staff import _month_range
        start, end = _month_range(2024, 6)
        assert start < end
