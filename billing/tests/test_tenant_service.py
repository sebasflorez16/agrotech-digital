"""
Tests para el servicio de gestión de tenants (TenantService) y endpoints billing.

Verifica el ciclo de vida completo:
- Crear tenant con suscripción free y paid
- Desactivar tenant (plan pago sin renovar)
- Eliminar tenant (trial expirado)
- Reactivar tenant
- Upgrade de suscripción
- Check masivo de suscripciones
- Endpoints create-checkout y confirm-payment

EJECUTAR:
    pytest billing/tests/test_tenant_service.py -v
    pytest billing/tests/test_tenant_service.py -v -k "unit"         # solo unitarios
    pytest billing/tests/test_tenant_service.py -v -k "integration"  # solo integración
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from datetime import date, timedelta
from django.test import TestCase, RequestFactory
from django.utils import timezone
from decimal import Decimal


# ═══════════════════════════════════════════════════════════════
#  TESTS UNITARIOS — _slugify_schema (no necesita DB)
# ═══════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestSlugifySchema:
    """Tests para la función _slugify_schema."""

    def test_simple_name(self):
        from billing.tenant_service import _slugify_schema
        assert _slugify_schema("Finca El Roble") == "finca_el_roble"

    def test_special_characters(self):
        from billing.tenant_service import _slugify_schema
        assert _slugify_schema("Mi Finca!@#$%") == "mi_finca"

    def test_starts_with_number(self):
        from billing.tenant_service import _slugify_schema
        result = _slugify_schema("123 Finca")
        assert result.startswith("t_")

    def test_empty_name(self):
        from billing.tenant_service import _slugify_schema
        assert _slugify_schema("") == ""

    def test_long_name_truncated(self):
        from billing.tenant_service import _slugify_schema
        result = _slugify_schema("a" * 100)
        assert len(result) <= 63

    def test_multiple_spaces(self):
        from billing.tenant_service import _slugify_schema
        result = _slugify_schema("Finca   El   Roble")
        assert "__" not in result

    def test_leading_trailing_spaces(self):
        from billing.tenant_service import _slugify_schema
        result = _slugify_schema("  Finca Test  ")
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_only_numbers(self):
        from billing.tenant_service import _slugify_schema
        result = _slugify_schema("12345")
        assert result.startswith("t_")


# ═══════════════════════════════════════════════════════════════
#  TESTS UNITARIOS CON DB (django_db) — Mocks parciales
#  @transaction.atomic necesita una conexión de DB activa,
#  así que usamos pytest.mark.django_db para que pytest-django
#  permita el acceso.
# ═══════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.django_db
class TestTenantServiceCreateMocked:
    """Tests para create_tenant_for_subscription con mocks sobre modelos."""

    @patch('billing.tenant_service.BillingEvent')
    @patch('billing.tenant_service.Subscription')
    @patch('billing.tenant_service.Domain')
    @patch('billing.tenant_service.Client')
    @patch('billing.tenant_service.Plan')
    def test_create_free_trial_returns_success(self, MockPlan, MockClient, MockDomain, MockSub, MockEvent):
        """Crear tenant con plan free → success=True, status=trialing."""
        from billing.tenant_service import TenantService

        mock_plan = Mock()
        mock_plan.trial_days = 14
        MockPlan.objects.get.return_value = mock_plan
        MockClient.objects.filter.return_value.exists.return_value = False

        mock_tenant = Mock()
        mock_tenant.schema_name = 'finca_test'
        MockClient.objects.get_or_create.return_value = (mock_tenant, True)
        MockDomain.objects.get_or_create.return_value = (Mock(), True)
        MockSub.objects.update_or_create.return_value = (Mock(), True)

        result = TenantService.create_tenant_for_subscription(
            tenant_name='Finca Test',
            plan_tier='free',
            payer_email='test@example.com',
        )

        assert result['success'] is True
        assert result['status'] == 'trialing'
        MockClient.objects.get_or_create.assert_called_once()
        MockDomain.objects.get_or_create.assert_called_once()
        MockSub.objects.update_or_create.assert_called_once()

    @patch('billing.tenant_service.BillingEvent')
    @patch('billing.tenant_service.Subscription')
    @patch('billing.tenant_service.Domain')
    @patch('billing.tenant_service.Client')
    @patch('billing.tenant_service.Plan')
    def test_create_paid_plan_returns_active(self, MockPlan, MockClient, MockDomain, MockSub, MockEvent):
        """Crear tenant con plan pago → status=active."""
        from billing.tenant_service import TenantService

        MockPlan.objects.get.return_value = Mock()
        MockClient.objects.filter.return_value.exists.return_value = False

        mock_tenant = Mock()
        mock_tenant.schema_name = 'finca_pro'
        MockClient.objects.get_or_create.return_value = (mock_tenant, True)
        MockDomain.objects.get_or_create.return_value = (Mock(), True)
        MockSub.objects.update_or_create.return_value = (Mock(), True)

        result = TenantService.create_tenant_for_subscription(
            tenant_name='Finca Pro',
            plan_tier='basic',
            billing_cycle='monthly',
            payer_email='pro@example.com',
            payment_gateway='mercadopago',
        )

        assert result['success'] is True
        assert result['status'] == 'active'

    @patch('billing.tenant_service.Plan')
    def test_create_with_invalid_plan_returns_error(self, MockPlan):
        """Plan inexistente → error."""
        from billing.tenant_service import TenantService
        from billing.models import Plan as RealPlan

        MockPlan.DoesNotExist = RealPlan.DoesNotExist
        MockPlan.objects.get.side_effect = RealPlan.DoesNotExist

        result = TenantService.create_tenant_for_subscription(
            tenant_name='Finca Error',
            plan_tier='nonexistent',
        )

        assert result['success'] is False
        assert 'error' in result

    @patch('billing.tenant_service.BillingEvent')
    @patch('billing.tenant_service.Subscription')
    @patch('billing.tenant_service.Domain')
    @patch('billing.tenant_service.Client')
    @patch('billing.tenant_service.Plan')
    def test_create_yearly_plan_extends_paid_until(self, MockPlan, MockClient, MockDomain, MockSub, MockEvent):
        """Plan anual → paid_until ~365 días en el futuro."""
        from billing.tenant_service import TenantService

        MockPlan.objects.get.return_value = Mock()
        MockClient.objects.filter.return_value.exists.return_value = False

        mock_tenant = Mock()
        mock_tenant.schema_name = 'finca_yearly'
        MockClient.objects.get_or_create.return_value = (mock_tenant, True)
        MockDomain.objects.get_or_create.return_value = (Mock(), True)
        MockSub.objects.update_or_create.return_value = (Mock(), True)

        result = TenantService.create_tenant_for_subscription(
            tenant_name='Finca Yearly',
            plan_tier='pro',
            billing_cycle='yearly',
        )

        assert result['success'] is True
        create_call = MockClient.objects.get_or_create.call_args
        paid_until = create_call.kwargs['defaults']['paid_until']
        days_diff = (paid_until - timezone.now().date()).days
        assert 360 <= days_diff <= 370

    @patch('billing.tenant_service.BillingEvent')
    @patch('billing.tenant_service.Subscription')
    @patch('billing.tenant_service.Domain')
    @patch('billing.tenant_service.Client')
    @patch('billing.tenant_service.Plan')
    def test_schema_collision_appends_counter(self, MockPlan, MockClient, MockDomain, MockSub, MockEvent):
        """Schema existente → agrega sufijo numérico."""
        from billing.tenant_service import TenantService

        mock_plan = Mock()
        mock_plan.trial_days = 14
        MockPlan.objects.get.return_value = mock_plan

        MockClient.objects.filter.return_value.exists.side_effect = [True, False]

        mock_tenant = Mock()
        mock_tenant.schema_name = 'finca_test_1'
        MockClient.objects.get_or_create.return_value = (mock_tenant, True)
        MockDomain.objects.get_or_create.return_value = (Mock(), True)
        MockSub.objects.update_or_create.return_value = (Mock(), True)

        result = TenantService.create_tenant_for_subscription(
            tenant_name='Finca Test',
            plan_tier='free',
        )

        assert result['success'] is True
        create_call = MockClient.objects.get_or_create.call_args
        schema = create_call.kwargs.get('schema_name') or create_call[1].get('schema_name', '')
        assert schema == 'finca_test_1'


@pytest.mark.unit
@pytest.mark.django_db
class TestTenantServiceDeactivateMocked:
    """Tests para desactivar tenants."""

    @patch('billing.tenant_service.BillingEvent')
    def test_deactivate_sets_expired(self, MockEvent):
        """Desactivar → status=expired, paid_until pasado."""
        from billing.tenant_service import TenantService

        mock_tenant = Mock()
        mock_tenant.name = 'Finca Test'
        mock_tenant.schema_name = 'finca_test'

        mock_sub = Mock()
        mock_sub.status = 'active'
        mock_sub.metadata = {}
        mock_tenant.subscription = mock_sub

        result = TenantService.deactivate_tenant(mock_tenant, reason='payment_overdue')

        assert result['success'] is True
        assert mock_sub.status == 'expired'
        assert mock_tenant.on_trial is False
        mock_sub.save.assert_called_once()
        mock_tenant.save.assert_called_once()

    def test_deactivate_no_subscription_error(self):
        """Sin suscripción → error."""
        from billing.tenant_service import TenantService
        from billing.models import Subscription

        mock_tenant = Mock()
        type(mock_tenant).subscription = PropertyMock(side_effect=Subscription.DoesNotExist)

        result = TenantService.deactivate_tenant(mock_tenant)

        assert result['success'] is False


@pytest.mark.unit
@pytest.mark.django_db
class TestTenantServiceDeleteMocked:
    """Tests para eliminar tenants."""

    @patch('billing.tenant_service.schema_exists')
    @patch('billing.tenant_service.connection')
    @patch('billing.tenant_service.Subscription')
    @patch('billing.tenant_service.BillingEvent')
    @patch('billing.tenant_service.Domain')
    def test_delete_drops_schema(self, MockDomain, MockEvent, MockSubscription, mock_conn, mock_schema_exists):
        """Eliminar → DROP SCHEMA + delete records."""
        from billing.tenant_service import TenantService

        mock_tenant = Mock()
        mock_tenant.name = 'Trial Expirado'
        mock_tenant.schema_name = 'trial_expirado'
        mock_schema_exists.return_value = True

        mock_sub = Mock()
        mock_sub.status = 'trialing'
        mock_sub.metadata = {}
        mock_sub.delete.return_value = None
        mock_tenant.subscription = mock_sub

        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        # Mock Domain.objects.filter to return a proper queryset mock
        mock_domain_qs = MagicMock()
        mock_domain_qs.delete.return_value = (1, {'base_agrotech.Domain': 1})
        MockDomain.objects.filter.return_value = mock_domain_qs

        # Mock BillingEvent.objects.filter
        mock_event_qs = MagicMock()
        mock_event_qs.delete.return_value = (0, {})
        MockEvent.objects.filter.return_value = mock_event_qs

        # Mock Subscription.objects.filter
        mock_sub_qs = MagicMock()
        mock_sub_qs.delete.return_value = (1, {'billing.Subscription': 1})
        MockSubscription.objects.filter.return_value = mock_sub_qs

        result = TenantService.delete_tenant(mock_tenant, reason='trial_expired')

        assert result['success'] is True
        mock_cursor.execute.assert_called()
        mock_tenant.delete.assert_called_once()


@pytest.mark.unit
@pytest.mark.django_db
class TestTenantServiceReactivateMocked:
    """Tests para reactivar tenants."""

    @patch('billing.tenant_service.BillingEvent')
    def test_reactivate_restores_active(self, MockEvent):
        """Reactivar → status=active, paid_until futuro."""
        from billing.tenant_service import TenantService

        mock_tenant = Mock()
        mock_tenant.name = 'Finca Reactivada'
        mock_tenant.schema_name = 'finca_reactivada'

        mock_sub = Mock()
        mock_sub.status = 'expired'
        mock_sub.plan.tier = 'basic'
        mock_sub.metadata = {'deactivated_at': '2024-01-01'}
        mock_tenant.subscription = mock_sub

        result = TenantService.reactivate_tenant(
            mock_tenant,
            billing_cycle='monthly',
            external_subscription_id='new_sub_123',
        )

        assert result['success'] is True
        assert mock_sub.status == 'active'
        mock_sub.save.assert_called_once()
        mock_tenant.save.assert_called_once()
        assert mock_tenant.paid_until > timezone.now().date()

    def test_reactivate_no_subscription_error(self):
        """Sin suscripción → error."""
        from billing.tenant_service import TenantService
        from billing.models import Subscription

        mock_tenant = Mock()
        type(mock_tenant).subscription = PropertyMock(side_effect=Subscription.DoesNotExist)

        result = TenantService.reactivate_tenant(mock_tenant)

        assert result['success'] is False


@pytest.mark.unit
@pytest.mark.django_db
class TestTenantServiceUpgradeMocked:
    """Tests para upgrade de plan."""

    @patch('billing.tenant_service.BillingEvent')
    @patch('billing.tenant_service.Plan')
    def test_upgrade_changes_plan(self, MockPlan, MockEvent):
        """Upgrade → nuevo plan asignado."""
        from billing.tenant_service import TenantService

        new_plan = Mock()
        new_plan.tier = 'pro'
        MockPlan.objects.get.return_value = new_plan

        mock_tenant = Mock()
        mock_tenant.name = 'Finca Upgrade'
        mock_tenant.schema_name = 'finca_upgrade'

        old_plan = Mock()
        old_plan.tier = 'basic'

        mock_sub = Mock()
        mock_sub.plan = old_plan
        mock_sub.status = 'active'
        mock_sub.billing_cycle = 'monthly'
        mock_sub.metadata = {}
        mock_tenant.subscription = mock_sub

        result = TenantService.upgrade_subscription(
            mock_tenant,
            new_plan_tier='pro',
        )

        assert result['success'] is True
        assert mock_sub.plan == new_plan
        mock_sub.save.assert_called_once()

    @patch('billing.tenant_service.Plan')
    def test_upgrade_invalid_plan_error(self, MockPlan):
        """Upgrade a plan inexistente → error."""
        from billing.tenant_service import TenantService
        from billing.models import Plan as RealPlan

        MockPlan.DoesNotExist = RealPlan.DoesNotExist
        MockPlan.objects.get.side_effect = RealPlan.DoesNotExist

        mock_tenant = Mock()
        mock_sub = Mock()
        mock_sub.status = 'active'
        mock_sub.metadata = {}
        mock_tenant.subscription = mock_sub

        result = TenantService.upgrade_subscription(mock_tenant, new_plan_tier='nonexistent')

        assert result['success'] is False


# ═══════════════════════════════════════════════════════════════
#  TESTS check_all_subscriptions
# ═══════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.django_db
class TestCheckAllSubscriptions:
    """Tests para check_all_subscriptions."""

    @patch('billing.tenant_service.Subscription')
    def test_no_subscriptions_returns_zeros(self, MockSub):
        """Sin suscripciones activas → contadores en 0."""
        from billing.tenant_service import TenantService

        MockSub.objects.select_related.return_value.exclude.return_value.exclude.return_value = []

        result = TenantService.check_all_subscriptions()

        assert result['checked'] == 0
        assert result['trials_deleted'] == 0
        assert result['paid_deactivated'] == 0

    @patch('billing.tenant_service.TenantService.delete_tenant')
    @patch('billing.tenant_service.Subscription')
    def test_expired_trial_gets_deleted(self, MockSub, mock_delete):
        """Trial expirado → se elimina."""
        from billing.tenant_service import TenantService

        mock_tenant = Mock()
        mock_tenant.paid_until = (timezone.now() - timedelta(days=1)).date()
        mock_tenant.name = 'Trial Test'

        mock_sub = Mock()
        mock_sub.id = 1
        mock_sub.status = 'trialing'
        mock_sub.plan.tier = 'free'
        mock_sub.tenant = mock_tenant
        mock_sub.trial_end = timezone.now() - timedelta(days=1)
        mock_sub.current_period_end = timezone.now() - timedelta(days=1)

        MockSub.objects.select_related.return_value.exclude.return_value.exclude.return_value = [mock_sub]
        mock_delete.return_value = {'success': True}

        result = TenantService.check_all_subscriptions()

        assert result['checked'] == 1
        assert result['trials_deleted'] == 1
        mock_delete.assert_called_once()

    @patch('billing.tenant_service.TenantService.deactivate_tenant')
    @patch('billing.tenant_service.Subscription')
    def test_overdue_paid_gets_deactivated(self, MockSub, mock_deactivate):
        """Plan pago con >7 días vencido → se desactiva."""
        from billing.tenant_service import TenantService

        mock_tenant = Mock()
        mock_tenant.paid_until = (timezone.now() - timedelta(days=10)).date()
        mock_tenant.name = 'Paid Test'

        mock_sub = Mock()
        mock_sub.id = 2
        mock_sub.status = 'active'
        mock_sub.plan.tier = 'basic'
        mock_sub.tenant = mock_tenant
        mock_sub.trial_end = None
        mock_sub.current_period_end = timezone.now() - timedelta(days=10)

        MockSub.objects.select_related.return_value.exclude.return_value.exclude.return_value = [mock_sub]
        mock_deactivate.return_value = {'success': True}

        result = TenantService.check_all_subscriptions()

        assert result['checked'] == 1
        assert result['paid_deactivated'] == 1
        mock_deactivate.assert_called_once()

    @patch('billing.tenant_service.BillingEvent')
    @patch('billing.tenant_service.Subscription')
    def test_grace_period_marks_past_due(self, MockSub, MockEvent):
        """Plan pago 1-7 días vencido → marca past_due."""
        from billing.tenant_service import TenantService

        mock_tenant = Mock()
        mock_tenant.paid_until = (timezone.now() - timedelta(days=3)).date()
        mock_tenant.name = 'Grace Test'

        mock_sub = Mock()
        mock_sub.id = 3
        mock_sub.status = 'active'
        mock_sub.plan.tier = 'basic'
        mock_sub.tenant = mock_tenant
        mock_sub.trial_end = None
        mock_sub.current_period_end = timezone.now() - timedelta(days=3)

        MockSub.objects.select_related.return_value.exclude.return_value.exclude.return_value = [mock_sub]

        result = TenantService.check_all_subscriptions()

        assert result['checked'] == 1
        assert result['marked_past_due'] == 1
        assert mock_sub.status == 'past_due'
        mock_sub.save.assert_called()


# ═══════════════════════════════════════════════════════════════
#  TESTS DE VIEWS — Endpoints API
# ═══════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestCreateCheckoutEndpoint:
    """Tests para el endpoint /billing/api/create-checkout/."""

    def test_get_returns_405(self):
        """GET → 405."""
        from billing.views import create_checkout_view

        factory = RequestFactory()
        request = factory.get('/billing/api/create-checkout/')
        response = create_checkout_view(request)
        assert response.status_code == 405

    def test_missing_plan_tier_returns_400(self):
        """Sin plan_tier → 400."""
        from billing.views import create_checkout_view

        factory = RequestFactory()
        request = factory.post(
            '/billing/api/create-checkout/',
            data=json.dumps({'billing_cycle': 'monthly'}),
            content_type='application/json',
        )
        response = create_checkout_view(request)
        assert response.status_code == 400

    @pytest.mark.django_db
    @patch('billing.views.TenantService')
    @patch('billing.views.Plan')
    def test_free_plan_creates_tenant(self, MockPlan, MockTenantService):
        """plan_tier=free → crea tenant directamente, success=True."""
        from billing.views import create_checkout_view

        factory = RequestFactory()
        request = factory.post(
            '/billing/api/create-checkout/',
            data=json.dumps({
                'plan_tier': 'free',
                'billing_cycle': 'monthly',
                'payer_email': 'test@example.com',
                'tenant_name': 'Mi Finca Test',
            }),
            content_type='application/json',
        )

        mock_plan = Mock()
        mock_plan.tier = 'free'
        MockPlan.objects.get.return_value = mock_plan

        MockTenantService.create_tenant_for_subscription.return_value = {
            'success': True,
            'schema_name': 'mi_finca_test',
            'domain': 'mi_finca_test.agrotechcolombia.com',
            'status': 'trialing',
        }

        response = create_checkout_view(request)
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['success'] is True
        assert data['tenant_created'] is True
        assert data['schema_name'] == 'mi_finca_test'

    @pytest.mark.django_db
    @patch('billing.views.Plan')
    def test_nonexistent_plan_returns_404(self, MockPlan):
        """Plan inexistente → 404."""
        from billing.views import create_checkout_view
        from billing.models import Plan as RealPlan

        factory = RequestFactory()
        request = factory.post(
            '/billing/api/create-checkout/',
            data=json.dumps({
                'plan_tier': 'nonexistent',
                'billing_cycle': 'monthly',
                'payer_email': 'test@example.com',
            }),
            content_type='application/json',
        )

        MockPlan.DoesNotExist = RealPlan.DoesNotExist
        MockPlan.objects.get.side_effect = RealPlan.DoesNotExist

        response = create_checkout_view(request)
        assert response.status_code == 404


@pytest.mark.unit
class TestConfirmPaymentEndpoint:
    """Tests para el endpoint /billing/api/confirm-payment/."""

    def test_get_returns_405(self):
        """GET → 405."""
        from billing.views import confirm_payment_create_tenant

        factory = RequestFactory()
        request = factory.get('/billing/api/confirm-payment/')
        response = confirm_payment_create_tenant(request)
        assert response.status_code == 405

    def test_missing_email_returns_400(self):
        """Sin payer_email → 400."""
        from billing.views import confirm_payment_create_tenant

        factory = RequestFactory()
        request = factory.post(
            '/billing/api/confirm-payment/',
            data=json.dumps({
                'preapproval_id': 'abc123',
                'plan_tier': 'basic',
            }),
            content_type='application/json',
        )
        response = confirm_payment_create_tenant(request)
        assert response.status_code == 400

    @pytest.mark.django_db
    @patch('billing.views.Subscription')
    def test_existing_subscription_returns_ok(self, MockSub):
        """Suscripción ya existente → success + already_exists."""
        from billing.views import confirm_payment_create_tenant

        factory = RequestFactory()
        request = factory.post(
            '/billing/api/confirm-payment/',
            data=json.dumps({
                'preapproval_id': 'existing_sub_123',
                'plan_tier': 'basic',
                'billing_cycle': 'monthly',
                'payer_email': 'user@test.com',
            }),
            content_type='application/json',
        )

        mock_sub = Mock()
        mock_sub.tenant.name = 'Finca Existente'
        mock_sub.tenant.schema_name = 'finca_existente'
        mock_sub.status = 'active'
        mock_sub.plan.tier = 'basic'
        MockSub.objects.filter.return_value.select_related.return_value.first.return_value = mock_sub

        response = confirm_payment_create_tenant(request)
        data = json.loads(response.content)

        assert response.status_code == 200
        assert data['success'] is True
        assert data['already_exists'] is True
        assert data['schema_name'] == 'finca_existente'


# ═══════════════════════════════════════════════════════════════
#  TESTS DE MANAGEMENT COMMAND
# ═══════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.django_db
class TestCheckSubscriptionsCommand:
    """Tests para el management command check_subscriptions."""

    @patch('billing.management.commands.check_subscriptions.TenantService')
    def test_command_runs_without_error(self, MockTenantService):
        """El command debe ejecutarse sin errores."""
        from django.core.management import call_command
        from io import StringIO

        MockTenantService.check_all_subscriptions.return_value = {
            'checked': 0,
            'trials_deleted': 0,
            'paid_deactivated': 0,
            'marked_past_due': 0,
            'errors': [],
        }

        out = StringIO()
        call_command('check_subscriptions', stdout=out)
        output = out.getvalue()
        assert len(output) > 0

    @patch('billing.management.commands.check_subscriptions.TenantService')
    def test_dry_run_mode(self, MockTenantService):
        """--dry-run debe indicar modo simulación."""
        from django.core.management import call_command
        from io import StringIO

        MockTenantService.check_all_subscriptions.return_value = {
            'checked': 2,
            'trials_deleted': 1,
            'paid_deactivated': 1,
            'marked_past_due': 0,
            'errors': [],
        }

        out = StringIO()
        call_command('check_subscriptions', '--dry-run', stdout=out)
        output = out.getvalue()
        # Debe ejecutarse sin error y producir algún output
        assert len(output) > 0


# ═══════════════════════════════════════════════════════════════
#  TESTS DE INTEGRACIÓN — DB real PostgreSQL + django-tenants
# ═══════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.tenant
@pytest.mark.django_db(transaction=True)
class TestTenantLifecycleIntegration:
    """
    Tests de integración que crean tenants reales en PostgreSQL.

    NOTA: Crean schemas reales y pueden ser lentos (~5s cada uno).
    """

    @classmethod
    def _ensure_plans(cls):
        """Asegurar que existen planes de prueba en la DB."""
        from billing.models import Plan
        Plan.objects.get_or_create(
            tier='free',
            defaults={
                'name': 'Explorador Test',
                'description': 'Plan free para tests',
                'price_cop': Decimal('0.00'),
                'price_usd': Decimal('0.00'),
                'limits': {'hectares': 50, 'users': 1, 'parcels': 3, 'eosda_requests': 10},
                'features_included': ['basic_analytics'],
                'features_excluded': ['advanced_analytics', 'api_access'],
                'trial_days': 14,
                'is_active': True,
            },
        )
        Plan.objects.get_or_create(
            tier='basic',
            defaults={
                'name': 'Agricultor Test',
                'description': 'Plan basic para tests',
                'price_cop': Decimal('79000.00'),
                'price_usd': Decimal('20.00'),
                'limits': {'hectares': 300, 'users': 3, 'parcels': 10, 'eosda_requests': 100},
                'features_included': ['basic_analytics', 'weather_forecast'],
                'features_excluded': ['api_access'],
                'trial_days': 14,
                'is_active': True,
            },
        )

    @staticmethod
    def _cleanup(schema_name):
        """Limpiar tenant de test de la DB."""
        from base_agrotech.models import Client, Domain
        from billing.models import Subscription, BillingEvent
        from django.db import connection
        from django_tenants.utils import schema_exists

        try:
            tenant = Client.objects.filter(schema_name=schema_name).first()
            if tenant:
                BillingEvent.objects.filter(tenant=tenant).delete()
                Subscription.objects.filter(tenant=tenant).delete()
                Domain.objects.filter(tenant=tenant).delete()
                if schema_exists(schema_name):
                    with connection.cursor() as cursor:
                        cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
                tenant.delete()
        except Exception:
            pass

    def test_free_trial_create_and_delete(self):
        """Ciclo completo: crear trial → verificar → eliminar."""
        from billing.tenant_service import TenantService
        from base_agrotech.models import Client
        from billing.models import Subscription

        self._ensure_plans()
        schema = 'test_int_free_trial'
        self._cleanup(schema)

        try:
            # Crear
            result = TenantService.create_tenant_for_subscription(
                tenant_name='Test Integration Free',
                schema_name=schema,
                plan_tier='free',
                payer_email='intfree@test.com',
            )
            assert result['success'] is True
            assert result['status'] == 'trialing'

            # Verificar en DB
            tenant = Client.objects.get(schema_name=schema)
            assert tenant.on_trial is True
            sub = Subscription.objects.get(tenant=tenant)
            assert sub.status == 'trialing'
            assert sub.plan.tier == 'free'

            # Eliminar
            del_result = TenantService.delete_tenant(tenant, reason='test')
            assert del_result['success'] is True
            assert not Client.objects.filter(schema_name=schema).exists()

        finally:
            self._cleanup(schema)

    def test_paid_plan_create_deactivate_reactivate(self):
        """Ciclo completo: crear pago → desactivar → reactivar."""
        from billing.tenant_service import TenantService
        from base_agrotech.models import Client
        from billing.models import Subscription
        from django_tenants.utils import schema_exists

        self._ensure_plans()
        schema = 'test_int_paid_life'
        self._cleanup(schema)

        try:
            # Crear
            result = TenantService.create_tenant_for_subscription(
                tenant_name='Test Integration Paid',
                schema_name=schema,
                plan_tier='basic',
                billing_cycle='monthly',
                payer_email='intpaid@test.com',
                payment_gateway='manual',
            )
            assert result['success'] is True
            assert result['status'] == 'active'

            tenant = Client.objects.get(schema_name=schema)
            assert tenant.on_trial is False

            # Desactivar
            deact = TenantService.deactivate_tenant(tenant, reason='test_overdue')
            assert deact['success'] is True
            tenant.refresh_from_db()
            sub = Subscription.objects.get(tenant=tenant)
            assert sub.status == 'expired'
            assert tenant.paid_until < timezone.now().date()
            assert schema_exists(schema), "Schema debe existir tras desactivación"

            # Reactivar
            react = TenantService.reactivate_tenant(tenant, billing_cycle='monthly')
            assert react['success'] is True
            tenant.refresh_from_db()
            sub.refresh_from_db()
            assert sub.status == 'active'
            assert tenant.paid_until > timezone.now().date()

        finally:
            self._cleanup(schema)

    def test_duplicate_name_different_schemas(self):
        """Dos tenants con mismo nombre → schemas distintos."""
        from billing.tenant_service import TenantService
        from base_agrotech.models import Client

        self._ensure_plans()
        s1 = s2 = None

        try:
            r1 = TenantService.create_tenant_for_subscription(
                tenant_name='Finca Dup Int',
                plan_tier='free',
                payer_email='dup1@test.com',
            )
            assert r1['success'] is True
            s1 = r1['schema_name']

            r2 = TenantService.create_tenant_for_subscription(
                tenant_name='Finca Dup Int',
                plan_tier='free',
                payer_email='dup2@test.com',
            )
            assert r2['success'] is True
            s2 = r2['schema_name']

            assert s1 != s2
        finally:
            if s1:
                self._cleanup(s1)
            if s2:
                self._cleanup(s2)
