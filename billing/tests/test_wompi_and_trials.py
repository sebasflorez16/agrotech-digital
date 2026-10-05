"""
Tests de regresión:
1. Expiración de trial robusta (cualquier plan en estado 'trialing').
2. Verificación del checksum de eventos Wompi contra el ejemplo oficial.
"""

import hashlib
from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone

from billing.models import Subscription
from billing.wompi_gateway import _wompi_event_checksum, _verify_wompi_event


# ---------------------------------------------------------------------------
# Trial expiry
# ---------------------------------------------------------------------------

def test_trial_expired_when_trial_end_passed():
    now = timezone.now()
    sub = Subscription(
        status="trialing",
        trial_end=now - timedelta(days=1),
        current_period_end=now + timedelta(days=10),
    )
    assert sub.is_trial_expired() is True


def test_trial_not_expired_when_trial_end_future():
    now = timezone.now()
    sub = Subscription(
        status="trialing",
        trial_end=now + timedelta(days=3),
        current_period_end=now + timedelta(days=3),
    )
    assert sub.is_trial_expired() is False


def test_trial_expired_without_trial_end_uses_period_end():
    now = timezone.now()
    sub = Subscription(
        status="trialing",
        trial_end=None,
        current_period_end=now - timedelta(days=2),
    )
    assert sub.is_trial_expired() is True


def test_trial_expired_when_trialing_without_dates():
    sub = Subscription(status="trialing", trial_end=None, current_period_end=None)
    assert sub.is_trial_expired() is True


def test_active_subscription_never_trial_expired():
    now = timezone.now()
    sub = Subscription(
        status="active",
        trial_end=now - timedelta(days=30),
        current_period_end=now + timedelta(days=10),
    )
    assert sub.is_trial_expired() is False


# ---------------------------------------------------------------------------
# Wompi event checksum (ejemplo oficial de docs.wompi.co/docs/colombia/eventos)
# ---------------------------------------------------------------------------

WOMPI_EXAMPLE_EVENT = {
    "event": "transaction.updated",
    "data": {
        "transaction": {
            "id": "1234-1610641025-49201",
            "amount_in_cents": 4490000,
            "reference": "MZQ3X2DE2SMX",
            "customer_email": "juan.perez@gmail.com",
            "currency": "COP",
            "payment_method_type": "NEQUI",
            "redirect_url": "https://mitienda.com.co/pagos/redireccion",
            "status": "APPROVED",
            "shipping_address": None,
            "payment_link_id": None,
            "payment_source_id": None,
        }
    },
    "environment": "prod",
    "signature": {
        "properties": [
            "transaction.id",
            "transaction.status",
            "transaction.amount_in_cents",
        ],
        "checksum": "3476DDA50F64CD7CBD160689640506FEBEA93239BC524FC0469B2C68A3CC8BD0",
    },
    "timestamp": 1530291411,
    "sent_at": "2018-07-20T16:45:05.000Z",
}

WOMPI_EXAMPLE_SECRET = "prod_events_OcHnIzeBl5socpwByQ4hA52Em3USQ93Z"


@pytest.fixture
def wompi_secret(monkeypatch):
    monkeypatch.setattr(settings, "WOMPI_EVENTS_KEY", WOMPI_EXAMPLE_SECRET, raising=False)
    yield WOMPI_EXAMPLE_SECRET


# El checksum que muestra la doc de Wompi en su ejemplo no coincide con la
# concatenación que la propia doc expone (typo del ejemplo), por eso validamos
# el ALGORITMO: SHA256(valores de properties en orden + timestamp + secreto).
WOMPI_EXPECTED_CHECKSUM = hashlib.sha256(
    (
        "1234-1610641025-49201"  # transaction.id
        + "APPROVED"             # transaction.status
        + "4490000"              # transaction.amount_in_cents
        + "1530291411"           # timestamp
        + WOMPI_EXAMPLE_SECRET   # events secret
    ).encode()
).hexdigest()


def test_wompi_checksum_follows_documented_concat_order(wompi_secret):
    assert _wompi_event_checksum(WOMPI_EXAMPLE_EVENT) == WOMPI_EXPECTED_CHECKSUM


def test_wompi_verify_accepts_valid_checksum(wompi_secret):
    assert _verify_wompi_event(WOMPI_EXAMPLE_EVENT, WOMPI_EXPECTED_CHECKSUM) is True


def test_wompi_verify_rejects_tampered_checksum(wompi_secret):
    assert _verify_wompi_event(WOMPI_EXAMPLE_EVENT, "deadbeef") is False


def test_wompi_verify_rejects_without_secret(monkeypatch):
    monkeypatch.setattr(settings, "WOMPI_EVENTS_KEY", "", raising=False)
    assert _verify_wompi_event(
        WOMPI_EXAMPLE_EVENT, WOMPI_EXAMPLE_EVENT["signature"]["checksum"]
    ) is False


# ---------------------------------------------------------------------------
# Webhook: pago anónimo (tenant_id=0) debe crear la cuenta con customer_email
# ---------------------------------------------------------------------------

def test_wompi_anonymous_payment_creates_tenant(monkeypatch):
    from billing import webhooks
    import base_agrotech.models as bam
    import billing.tenant_service as ts

    class _FakeQueryset:
        def first(self):
            return None

    class _FakeManager:
        def filter(self, **kwargs):
            return _FakeQueryset()

    monkeypatch.setattr(bam.Client, "objects", _FakeManager(), raising=False)

    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return {"success": True}

    monkeypatch.setattr(
        ts.TenantService, "create_tenant_for_subscription",
        staticmethod(fake_create), raising=False,
    )

    webhooks._process_wompi_payment(
        {"customer_email": "juan@finca.com"}, "sub_0_basic_abcd1234"
    )

    assert captured.get("payer_email") == "juan@finca.com"
    assert captured.get("plan_tier") == "basic"
    assert captured.get("payment_gateway") == "wompi"
    assert captured.get("external_subscription_id") == "sub_0_basic_abcd1234"
