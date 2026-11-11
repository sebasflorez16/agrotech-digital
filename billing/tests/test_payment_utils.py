from datetime import timedelta
from decimal import Decimal

from django.test import SimpleTestCase
from django.utils import timezone

from billing.models import Plan
from billing.payment_utils import (
    build_wompi_reference,
    normalize_cycle,
    parse_mercadopago_reference,
    parse_wompi_reference,
    period_end,
    plan_amount_cents,
)


class PaymentUtilsTest(SimpleTestCase):
    def test_normalize_cycle_rejects_unknown_values(self):
        self.assertEqual(normalize_cycle('YEARLY'), 'yearly')
        self.assertEqual(normalize_cycle('monthly'), 'monthly')
        self.assertEqual(normalize_cycle('weekly'), 'monthly')
        self.assertEqual(normalize_cycle(None), 'monthly')

    def test_parse_new_wompi_reference(self):
        ref = build_wompi_reference(42, 'pro', 'yearly')
        parsed = parse_wompi_reference(ref)
        self.assertEqual(parsed['tenant_id'], 42)
        self.assertEqual(parsed['plan_tier'], 'pro')
        self.assertEqual(parsed['cycle'], 'yearly')

    def test_parse_legacy_wompi_reference_defaults_to_monthly(self):
        parsed = parse_wompi_reference('sub_7_basic_abcd1234')
        self.assertEqual(parsed['tenant_id'], 7)
        self.assertEqual(parsed['plan_tier'], 'basic')
        self.assertEqual(parsed['cycle'], 'monthly')

    def test_plan_amounts_are_monthly_and_yearly_20_percent(self):
        plan = Plan(tier='basic', name='Agricultor', price_cop=Decimal('79000.00'), price_usd=Decimal('20.00'))
        self.assertEqual(plan_amount_cents(plan, 'monthly'), 7_900_000)
        self.assertEqual(plan_amount_cents(plan, 'yearly'), 75_840_000)

    def test_period_end_uses_cycle_days(self):
        start = timezone.now()
        self.assertEqual(period_end(start, 'monthly') - start, timedelta(days=30))
        self.assertEqual(period_end(start, 'yearly') - start, timedelta(days=365))

    def test_parse_mercadopago_reference(self):
        ref = 'plan_pro_yearly__email_user%40test.com__tenant_Finca__user_juan'
        parsed = parse_mercadopago_reference(ref)
        self.assertEqual(parsed['plan_tier'], 'pro')
        self.assertEqual(parsed['cycle'], 'yearly')
        self.assertEqual(parsed['tenant_name'], 'Finca')
        self.assertEqual(parsed['username'], 'juan')
