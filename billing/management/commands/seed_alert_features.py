"""
Sembrar las features de la suite de Alertas Agronómicas en los planes existentes.

Idempotente: solo agrega las claves que faltan, nunca elimina ni reescribe lo ya
configurado por el equipo de producto.

Mapeo de features → planes (alineado con `PROPUESTA_PRICING_AJUSTADO.md`):

    BASIC         (tier=basic)        : agronomic_alerts
    PRO           (tier=pro)          : agronomic_alerts, alerts_email,
                                        historico_180d, pdf_premium,
                                        zonificacion_3, comparador_temporada
    ENTERPRISE    (tier=enterprise)   : todas las anteriores +
                                        zonificacion_16, webhook_api,
                                        historico_completo

Uso:
    python manage.py seed_alert_features
    python manage.py seed_alert_features --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from billing.models import Plan


FEATURES_POR_TIER = {
    "basic": [
        "agronomic_alerts",
    ],
    "pro": [
        "agronomic_alerts",
        "alerts_email",
        "historico_180d",
        "pdf_premium",
        "zonificacion_3",
        "comparador_temporada",
    ],
    "enterprise": [
        "agronomic_alerts",
        "alerts_email",
        "historico_180d",
        "historico_completo",
        "pdf_premium",
        "zonificacion_3",
        "zonificacion_16",
        "comparador_temporada",
        "webhook_api",
    ],
}


class Command(BaseCommand):
    help = "Siembra features de alertas agronómicas en planes existentes."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="No persiste cambios.")

    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]
        changed = 0
        for plan in Plan.objects.all():
            wanted = FEATURES_POR_TIER.get(plan.tier, [])
            if not wanted:
                continue

            current = list(plan.features_included or [])
            new_keys = [k for k in wanted if k not in current]
            if not new_keys:
                self.stdout.write(f"  · {plan.name} ({plan.tier}): sin cambios")
                continue

            updated = current + new_keys
            self.stdout.write(self.style.MIGRATE_HEADING(
                f"→ {plan.name} ({plan.tier}): +{new_keys}"
            ))
            if not dry_run:
                plan.features_included = updated
                plan.save(update_fields=["features_included", "updated_at"])
                changed += 1

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: nada se persistió."))
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ {changed} planes actualizados."))
