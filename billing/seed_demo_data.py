"""
Seed de datos de demostración para el panel de operador.

Crea 6 tenants ficticios (empresas agro colombianas) con:
  - Suscripciones a distintos planes
  - Facturas de los últimos 6 meses
  - Eventos de facturación
  - Métricas de uso (UsageMetrics)

Uso:
    conda run -n agro-rest python -m billing.seed_demo_data
    (desde la raíz del proyecto agrotech-digital)
"""
import os
import sys
import random
from datetime import datetime, timedelta
from decimal import Decimal

# ── Bootstrap Django ──────────────────────────────────────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
import django
django.setup()

from django.utils import timezone
from django_tenants.utils import schema_context

from base_agrotech.models import Client, Domain
from billing.models import Plan, Subscription, Invoice, BillingEvent, UsageMetrics

# ── Datos ficticios ───────────────────────────────────────────────────────────
TENANTS = [
    {"schema": "haciendalaesperanza", "name": "Hacienda La Esperanza", "domain": "hacienda.localhost", "plan": "profesional"},
    {"schema": "agrofincasantacruz",  "name": "Agrofinca Santa Cruz",  "domain": "santacruz.localhost",  "plan": "empresarial"},
    {"schema": "cultivoscordillera",  "name": "Cultivos Cordillera",   "domain": "cordillera.localhost",  "plan": "profesional"},
    {"schema": "campoverde",          "name": "Campo Verde S.A.S",     "domain": "campoverde.localhost",  "plan": "starter"},
    {"schema": "agrotecsabana",       "name": "AgroTec Sabana",        "domain": "sabana.localhost",      "plan": "starter"},
    {"schema": "fincaelsol",          "name": "Finca El Sol",          "domain": "fincasol.localhost",    "plan": "empresarial", "trial": True},
]

PLAN_PRICES = {
    "starter":     {"price_cop": Decimal("99000"),  "price_usd": Decimal("25"),  "tier": "starter"},
    "profesional": {"price_cop": Decimal("249000"), "price_usd": Decimal("65"),  "tier": "profesional"},
    "empresarial": {"price_cop": Decimal("599000"), "price_usd": Decimal("150"), "tier": "empresarial"},
}

EVENT_TYPES = [
    "subscription_created",
    "payment_success",
    "payment_success",
    "payment_success",
    "login",
    "subscription_renewed",
    "payment_failed",
]

def get_or_create_plans():
    plans = {}
    for slug, p in PLAN_PRICES.items():
        limits = {
            "users": 2 if slug == "starter" else (5 if slug == "profesional" else 999),
            "parcels": 5 if slug == "starter" else (20 if slug == "profesional" else 9999),
            "hectares": 100 if slug == "starter" else (500 if slug == "profesional" else 99999),
            "eosda_requests": 50 if slug == "starter" else (200 if slug == "profesional" else 9999),
            "storage_mb": 500 if slug == "starter" else (2000 if slug == "profesional" else 99999),
        }
        plan, _ = Plan.objects.get_or_create(name=slug.capitalize(), defaults={"tier": p["tier"]})
        # Siempre actualizar precios y límites (por si existían sin datos)
        Plan.objects.filter(pk=plan.pk).update(
            tier=p["tier"],
            price_cop=p["price_cop"],
            price_usd=p["price_usd"],
            is_active=True,
            limits=limits,
        )
        plan.refresh_from_db()
        plans[slug] = plan
    return plans


def create_tenant(info, plans):
    schema = info["schema"]
    name = info["name"]
    domain_str = info["domain"]
    plan_slug = info["plan"]
    is_trial = info.get("trial", False)
    now = timezone.now()

    # ── Crear tenant ─────────────────────────────────────────────
    if Client.objects.filter(schema_name=schema).exists():
        tenant = Client.objects.get(schema_name=schema)
        print(f"  ⚠️  [{name}] ya existe, actualizando datos")
    else:
        tenant = Client(
            schema_name=schema,
            name=name,
            paid_until=now + timedelta(days=30),
            on_trial=is_trial,
        )
        tenant.save()  # django-tenants crea el schema automáticamente
        print(f"  ✅ [{name}] schema creado")

    # ── Dominio ───────────────────────────────────────────────────
    Domain.objects.get_or_create(
        domain=domain_str,
        defaults={"tenant": tenant, "is_primary": True},
    )

    # ── Plan & Suscripción ────────────────────────────────────────
    plan = plans[plan_slug]
    status = "trialing" if is_trial else "active"
    sub, created = Subscription.objects.get_or_create(
        tenant=tenant,
        defaults={
            "plan": plan,
            "status": status,
            "payment_gateway": random.choice(["wompi", "stripe"]),
            "current_period_start": now - timedelta(days=random.randint(5, 25)),
            "current_period_end": now + timedelta(days=random.randint(5, 30)),
            "trial_end": (now + timedelta(days=14)) if is_trial else None,
        },
    )
    if not created:
        sub.plan = plan
        sub.status = status
        sub.save()

    # ── Facturas (últimos 6 meses) ────────────────────────────────
    for i in range(6, -1, -1):
        inv_date = (now - timedelta(days=i * 30)).date()
        inv_paid = now - timedelta(days=i * 30 - 2)
        subtotal = (plan.price_cop * Decimal(str(round(random.uniform(0.9, 1.1), 4)))).quantize(Decimal("1"))
        total = (subtotal * Decimal("1.19")).quantize(Decimal("1"))
        inv, _ = Invoice.objects.get_or_create(
            tenant=tenant,
            invoice_number=f"INV-{schema[:6].upper()}-{inv_date.strftime('%Y%m')}-{i:02d}",
            defaults={
                "subscription": sub,
                "subtotal": subtotal,
                "total": total,
                "currency": "COP",
                "status": "paid" if i > 0 else random.choice(["paid", "pending"]),
                "invoice_date": inv_date,
                "paid_at": inv_paid if i > 0 else None,
                "due_date": inv_date + timedelta(days=5),
            },
        )

    # ── Eventos de facturación ─────────────────────────────────────
    existing_events = BillingEvent.objects.filter(tenant=tenant).count()
    if existing_events == 0:
        for i in range(random.randint(4, 8)):
            et = random.choice(EVENT_TYPES)
            ev = BillingEvent.objects.create(
                tenant=tenant,
                subscription=sub,
                event_type=et,
                event_data={"description": f"{et.replace('_', ' ').capitalize()} para {name}"},
            )
            # Retroceder la fecha (auto_now_add requiere .update() directo)
            past_dt = now - timedelta(days=random.randint(0, 60), hours=random.randint(0, 23))
            BillingEvent.objects.filter(pk=ev.pk).update(created_at=past_dt)

    # ── Métricas de uso (mes actual y 2 anteriores) ───────────────
    for delta_m in range(3):
        m = now.month - delta_m
        y = now.year
        if m <= 0:
            m += 12
            y -= 1
        UsageMetrics.objects.get_or_create(
            tenant=tenant,
            year=y,
            month=m,
            defaults={
                "subscription": sub,
                "eosda_requests": random.randint(10, 180),
                "hectares_used": Decimal(str(random.uniform(20, 400))).quantize(Decimal("0.01")),
                "parcels_count": random.randint(2, 18),
                "users_count": random.randint(1, 6),
                "storage_mb": random.randint(50, 900),
            },
        )

    print(f"  📊 [{name}] plan={plan_slug.upper()} status={status}")


def run():
    print("\n🌱 Creando datos de demostración para el panel de operador...\n")
    plans = get_or_create_plans()
    print(f"✅ Planes verificados: {list(plans.keys())}\n")

    for info in TENANTS:
        try:
            create_tenant(info, plans)
        except Exception as exc:
            print(f"  ❌ Error en {info['name']}: {exc}")

    total_tenants = Client.objects.exclude(schema_name="public").count()
    total_invoices = Invoice.objects.count()
    total_events = BillingEvent.objects.count()
    print(f"""
╔══════════════════════════════════════════════╗
║  Seed completado                             ║
╠══════════════════════════════════════════════╣
║  Tenants:  {total_tenants:<35}║
║  Facturas: {total_invoices:<35}║
║  Eventos:  {total_events:<35}║
╚══════════════════════════════════════════════╝
Abre http://localhost:8080/staff y verifica los datos.
""")


if __name__ == "__main__":
    run()
