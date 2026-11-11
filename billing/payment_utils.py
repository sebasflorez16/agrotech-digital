"""Utilidades compartidas para checkout, referencias y períodos de pago.

Este módulo centraliza la lógica que NO debe depender de datos enviados por el
cliente: montos, ciclos, referencias firmadas e intenciones de checkout.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.core.cache import cache
from django.utils import timezone

MONTHLY_DAYS = 30
YEARLY_DAYS = 365
VALID_CYCLES = ('monthly', 'yearly')
INTENT_TTL = 60 * 60  # 1 hora


def normalize_cycle(value: Optional[str]) -> str:
    """Devuelve un ciclo válido; cualquier valor extraño cae a mensual."""
    value = (value or '').strip().lower()
    return value if value in VALID_CYCLES else 'monthly'


def period_days(cycle: str) -> int:
    """Días que otorga cada ciclo de facturación."""
    return YEARLY_DAYS if normalize_cycle(cycle) == 'yearly' else MONTHLY_DAYS


def period_end(start, cycle: str):
    """Fecha de fin de período para un ciclo."""
    return start + timedelta(days=period_days(cycle))


def plan_amount_cents(plan, cycle: str) -> int:
    """Monto a cobrar en centavos de COP según plan y ciclo.

    La fuente de verdad es el plan en base de datos. El precio anual usa el
    mismo cálculo que la UI y MercadoPago (20% de descuento real).
    """
    cycle = normalize_cycle(cycle)
    if cycle == 'yearly':
        amount = plan.get_yearly_discount()['yearly_price_cop']
    else:
        amount = plan.price_cop
    return int(round(float(Decimal(str(amount))) * 100))


def build_wompi_reference(tenant_id: int, plan_tier: str, cycle: str) -> str:
    """Referencia de Wompi que incluye plan, ciclo y tenant.

    Formato: ``sub_{tenant_id}_{tier}_{cycle}_{random}``.
    El ciclo viaja firmado dentro de la referencia para que el webhook no
    dependa únicamente de la caché (que puede perderse).
    """
    import uuid

    return f"sub_{int(tenant_id)}_{plan_tier}_{normalize_cycle(cycle)}_{uuid.uuid4().hex[:8]}"


def parse_wompi_reference(reference: str) -> dict:
    """Extrae tenant, plan y ciclo de una referencia de Wompi.

    Soporta el formato nuevo (con ciclo) y el formato anterior sin ciclo
    (se asume mensual para no romper pagos en curso).
    """
    parts = (reference or '').split('_')
    if len(parts) < 4 or parts[0] != 'sub':
        return {}
    try:
        tenant_id = int(parts[1])
    except (TypeError, ValueError):
        return {}

    plan_tier = parts[2]
    # Formato nuevo: sub_{tenant}_{tier}_{cycle}_{random} → 5 partes.
    # Formato viejo: sub_{tenant}_{tier}_{random} → 4 partes (mensual).
    if len(parts) >= 5 and parts[3] in VALID_CYCLES:
        cycle = parts[3]
    else:
        cycle = 'monthly'

    return {
        'tenant_id': tenant_id,
        'plan_tier': plan_tier,
        'cycle': cycle,
    }


def save_checkout_intent(reference: str, payload: dict) -> None:
    """Guarda la intención de checkout asociada a una referencia."""
    try:
        cache.set(f"wompi_intent:{reference}", payload, INTENT_TTL)
    except Exception:
        # La caché no debe romper el checkout; el webhook tiene la referencia
        # firmada como respaldo.
        pass


def get_checkout_intent(reference: str) -> dict:
    """Recupera la intención de checkout; devuelve {} si no existe."""
    try:
        return cache.get(f"wompi_intent:{reference}") or {}
    except Exception:
        return {}


def parse_mercadopago_reference(external_reference: str) -> dict:
    """Extrae plan, ciclo, email y tenant de un external_reference de MP.

    Formato histórico:
        plan_{tier}_{cycle}__email_{email}__tenant_{name}__user_{username}
    """
    result = {}
    for part in (external_reference or '').split('__'):
        if part.startswith('plan_'):
            bits = part[len('plan_'):].split('_')
            if len(bits) >= 2:
                result['plan_tier'] = bits[0]
                result['cycle'] = normalize_cycle(bits[1])
        elif part.startswith('email_'):
            result['payer_email'] = part[len('email_'):]
        elif part.startswith('tenant_'):
            result['tenant_name'] = part[len('tenant_'):]
        elif part.startswith('user_'):
            result['username'] = part[len('user_'):]
    return result


def sanitize_external_reference_part(value: str) -> str:
    """Evita inyección de separadores en external_reference de MercadoPago."""
    return (
        (value or '')
        .replace('__', ' ')
        .replace('plan_', 'plan ')
        .replace('email_', 'email ')
        .replace('tenant_', 'tenant ')
        .replace('user_', 'user ')
        .strip()
    )


def subscription_is_current(subscription) -> bool:
    """True si la suscripción sigue vigente (activa o trial no vencido)."""
    if subscription is None:
        return False
    if not subscription.is_active_or_trialing():
        return False
    return not subscription.is_trial_expired()


def add_billing_days(base, cycle: str):
    """Extiende un período desde ``base`` (o ahora si ya venció)."""
    now = timezone.now()
    start = base if base and base > now else now
    return start + timedelta(days=period_days(cycle))
