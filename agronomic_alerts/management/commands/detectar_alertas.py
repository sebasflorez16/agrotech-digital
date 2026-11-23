"""
Management command: detectar_alertas

Dispara el motor agronómico para las parcelas activas de los tenants con
'monitoreo continuo' (Pro+), usando índices REALES de Sentinel-2
(Planetary Computer). NO depende de EOSDA.

Se ejecuta por evento o cron:

    python manage.py detectar_alertas
    python manage.py detectar_alertas --tenant finca_demo
    python manage.py detectar_alertas --tenant finca_demo --parcel 42
    python manage.py detectar_alertas --dry-run
    python manage.py detectar_alertas --no-notify
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context

from agronomic_alerts.engine import AgronomicAlertEngine, IndexReading
from agronomic_alerts.notifier import AlertNotifier
from base_agrotech.models import Client
from billing.models import Subscription
from parcels.models import Parcel

logger = logging.getLogger(__name__)

S2_INDICES = ("ndvi", "ndmi", "savi", "ndre")


# ---------------------------------------------------------------------------
# Lecturas desde Sentinel-2 (real, sin EOSDA)
# ---------------------------------------------------------------------------

def _fetch_s2_readings(parcel, days: int) -> list[IndexReading]:
    """Lecturas del último scene Sentinel-2 utilizable (píxeles válidos)."""
    from parcels.sentinel2 import _find_scene_and_arrays, get_index_analysis

    scene, arrays = _find_scene_and_arrays(
        parcel.geom, str(date.today()), mask_clouds=True
    )
    if not scene or not arrays:
        return []

    try:
        scene_date = datetime.strptime(str(scene.get("date"))[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        scene_date = date.today()

    # No generar alertas con una escena demasiado vieja.
    if (date.today() - scene_date).days > days:
        return []

    stats = get_index_analysis(parcel.geom, str(date.today()), arrays=arrays) or {}
    readings = []
    for idx in S2_INDICES:
        s = stats.get(idx)
        if s and s.get("mean") is not None:
            readings.append(IndexReading(
                indice=idx,
                valor=float(s["mean"]),
                fecha_escena=scene_date,
            ))
    return readings


# ---------------------------------------------------------------------------
# Procesamiento por parcela
# ---------------------------------------------------------------------------

def _process_parcel(parcel, days: int, dry_run: bool, notify: bool,
                    notifier: AlertNotifier, tenant=None) -> dict:
    """Procesa una parcela y devuelve un resumen."""
    summary = {
        "parcel_id": parcel.pk, "parcel": parcel.name,
        "readings": 0, "created": 0, "skipped": 0,
        "notified": 0, "errors": [],
    }
    if not parcel.geom:
        summary["errors"].append("parcela sin geometría")
        return summary

    try:
        readings = _fetch_s2_readings(parcel, days)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Sentinel-2 falló para parcela %s: %s", parcel.pk, exc)
        summary["errors"].append(f"sentinel2: {exc}")
        return summary

    summary["readings"] = len(readings)
    if not readings:
        return summary

    if dry_run:
        summary["skipped"] = len(readings)
        return summary

    engine = AgronomicAlertEngine(parcel)
    outcomes = engine.process_readings(readings)
    created_alerts = [o.alerta for o in outcomes if o.created and o.alerta is not None]
    summary["created"] = len(created_alerts)
    summary["skipped"] = sum(1 for o in outcomes if not o.created)

    if notify and created_alerts:
        try:
            result = notifier.notify_many(created_alerts)
            summary["notified"] = result.sent
            if result.errors:
                summary["errors"].extend([str(e) for e in result.errors])
        except Exception as exc:  # noqa: BLE001
            logger.exception("Notifier falló para parcela %s: %s", parcel.pk, exc)
            summary["errors"].append(f"notifier: {exc}")

    return summary


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Detecta alertas agronómicas con índices Sentinel-2 reales (plan Pro+)."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", help="Schema del tenant a procesar (default: todos).")
        parser.add_argument("--parcel", type=int, help="ID de parcela específica.")
        parser.add_argument("--days", type=int, default=14, help="Antigüedad máxima de la escena (días).")
        parser.add_argument("--dry-run", action="store_true", help="No persiste ni notifica.")
        parser.add_argument("--no-notify", action="store_true", help="Persiste pero no envía correos.")

    def handle(self, *args, **opts):
        tenant_arg = opts.get("tenant")
        parcel_id = opts.get("parcel")
        days = opts["days"]
        dry_run = opts["dry_run"]
        notify = not opts["no_notify"]

        tenants = self._select_tenants(tenant_arg)
        if not tenants:
            raise CommandError("No se encontraron tenants para procesar.")

        # Suscripciones (schema público) para filtrar solo Pro/Enterprise.
        subs = {
            s.tenant_id: s
            for s in Subscription.objects
            .filter(tenant_id__in=[t.id for t in tenants])
            .select_related("plan")
        }

        notifier = AlertNotifier()
        total = {"parcels": 0, "alerts": 0, "notified": 0, "errors": 0, "skipped_tenants": 0}

        for tenant in tenants:
            sub = subs.get(tenant.id)
            features = (sub.plan.features_included if sub and sub.plan else []) or []
            if "continuous_monitoring" not in features:
                total["skipped_tenants"] += 1
                self.stdout.write(
                    f"\n→ Tenant: {tenant.schema_name} ({tenant.name}) "
                    f"— sin monitoreo continuo (omitido)"
                )
                continue

            self.stdout.write(self.style.MIGRATE_HEADING(
                f"\n→ Tenant: {tenant.schema_name} ({tenant.name})"
            ))
            with schema_context(tenant.schema_name):
                parcels_qs = Parcel.objects.filter(
                    is_deleted=False, state=True, crop_cycles__status="active"
                ).distinct()
                if parcel_id:
                    parcels_qs = parcels_qs.filter(pk=parcel_id)

                for parcel in parcels_qs.iterator():
                    summary = _process_parcel(parcel, days, dry_run, notify, notifier, tenant)
                    total["parcels"] += 1
                    total["alerts"] += summary["created"]
                    total["notified"] += summary["notified"]
                    total["errors"] += len(summary["errors"])
                    self._print_parcel_summary(summary, dry_run)

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Procesadas {total['parcels']} parcelas · "
            f"{total['alerts']} alertas creadas · "
            f"{total['notified']} notificaciones enviadas · "
            f"{total['errors']} errores · "
            f"{total['skipped_tenants']} tenants sin monitoreo"
        ))

    # ---- Helpers ----
    def _select_tenants(self, tenant_arg):
        qs = Client.objects.exclude(schema_name="public")
        if tenant_arg:
            qs = qs.filter(schema_name=tenant_arg)
        return list(qs)

    def _print_parcel_summary(self, summary, dry_run):
        prefix = "  ·"
        mode = " [DRY-RUN]" if dry_run else ""
        msg = (
            f"{prefix} {summary['parcel']} (id={summary['parcel_id']}){mode}: "
            f"{summary['readings']} lecturas, "
            f"{summary['created']} alertas, "
            f"{summary['notified']} notificadas"
        )
        if summary["errors"]:
            self.stdout.write(self.style.WARNING(msg + f" | errores: {summary['errors']}"))
        elif summary["created"]:
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            self.stdout.write(msg)
