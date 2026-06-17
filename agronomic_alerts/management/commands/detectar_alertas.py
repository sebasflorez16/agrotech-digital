"""
Management command: detectar_alertas

Dispara el motor agronómico para todas las parcelas activas de cada tenant
(o las filtradas por flags) y envía notificaciones por correo.

Se diseña para ejecutarse POR EVENTO (cuando hay una nueva escena Sentinel-2
útil), no como un cron diario rígido. En la práctica:

    # Procesar todo
    python manage.py detectar_alertas

    # Procesar un tenant específico
    python manage.py detectar_alertas --tenant finca_demo

    # Procesar una parcela específica (uso típico desde un webhook EOSDA)
    python manage.py detectar_alertas --tenant finca_demo --parcel 42

    # Modo prueba sin persistir ni enviar
    python manage.py detectar_alertas --dry-run

    # Persistir pero no enviar correo
    python manage.py detectar_alertas --no-notify
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_tenants.utils import schema_context

from agronomic_alerts.engine import AgronomicAlertEngine, IndexReading
from agronomic_alerts.notifier import AlertNotifier
from base_agrotech.models import Client
from parcels.models import Parcel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Extracción de lecturas desde la respuesta de EOSDA
# ---------------------------------------------------------------------------

def _extract_latest_reading(stats_payload: dict) -> tuple[date, float] | None:
    """
    Intenta extraer la (fecha, valor medio) más reciente de la respuesta
    de Statistics API, defensivo frente a diferentes formatos.
    """
    if not stats_payload:
        return None

    # Formato típico: {'data': [{'date': 'YYYY-MM-DD', 'mean': 0.45, 'cloud': 12.3}, ...]}
    data = stats_payload.get("data") if isinstance(stats_payload, dict) else None
    if not data:
        # Algunas variantes devuelven 'result' o ya la lista directa.
        data = stats_payload.get("result") if isinstance(stats_payload, dict) else stats_payload
    if not isinstance(data, list) or not data:
        return None

    # Ordenar por fecha desc, filtrar nubosidad si está disponible (<20%).
    cleaned = []
    for item in data:
        if not isinstance(item, dict):
            continue
        fecha_raw = item.get("date") or item.get("fecha")
        try:
            if isinstance(fecha_raw, str):
                fecha = datetime.strptime(fecha_raw[:10], "%Y-%m-%d").date()
            elif isinstance(fecha_raw, date):
                fecha = fecha_raw
            else:
                continue
        except (TypeError, ValueError):
            continue

        valor = item.get("mean")
        if valor is None:
            valor = item.get("average") or item.get("avg")
        try:
            valor = float(valor)
        except (TypeError, ValueError):
            continue

        nubes = item.get("cloud") or item.get("clouds") or item.get("cloud_cover")
        try:
            nubes_pct = float(nubes) if nubes is not None else None
        except (TypeError, ValueError):
            nubes_pct = None

        # Filtrar escenas con >20% nubes (ya pedido por el cliente).
        if nubes_pct is not None and nubes_pct > 20:
            continue

        cleaned.append((fecha, valor))

    if not cleaned:
        return None

    cleaned.sort(key=lambda x: x[0], reverse=True)
    return cleaned[0]


# ---------------------------------------------------------------------------
# Procesamiento por parcela
# ---------------------------------------------------------------------------

def _process_parcel(parcel, days: int, dry_run: bool, notify: bool, notifier: AlertNotifier) -> dict:
    """Procesa una parcela y devuelve un resumen."""
    summary = {
        "parcel_id": parcel.pk, "parcel": parcel.name,
        "readings": 0, "created": 0, "skipped": 0,
        "notified": 0, "errors": [],
    }
    if not parcel.geom:
        summary["errors"].append("parcela sin geometría")
        return summary

    fecha_fin = date.today()
    fecha_inicio = fecha_fin - timedelta(days=days)

    try:
        from parcels.eosda_optimized_service import get_eosda_service
        service = get_eosda_service()
        stats = service.obtener_multi_indice(
            geometria=parcel.geom,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            indices=["NDVI", "NDMI", "SAVI", "EVI"],
            parcela_id=parcel.pk,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("EOSDA falló para parcela %s: %s", parcel.pk, exc)
        summary["errors"].append(f"eosda: {exc}")
        return summary

    readings: list[IndexReading] = []
    for indice in ("NDVI", "NDMI", "SAVI", "EVI"):
        payload = stats.get(indice) if stats else None
        latest = _extract_latest_reading(payload) if payload else None
        if latest is None:
            continue
        fecha_escena, valor = latest
        readings.append(IndexReading(
            indice=indice.lower(),
            valor=valor,
            fecha_escena=fecha_escena,
        ))

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
    help = "Detecta y persiste alertas agronómicas por evento de nueva escena satelital."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", help="Schema del tenant a procesar (default: todos).")
        parser.add_argument("--parcel", type=int, help="ID de parcela específica.")
        parser.add_argument("--days", type=int, default=14, help="Ventana de búsqueda (días).")
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

        notifier = AlertNotifier()
        total = {"parcels": 0, "alerts": 0, "notified": 0, "errors": 0}

        for tenant in tenants:
            self.stdout.write(self.style.MIGRATE_HEADING(
                f"\n→ Tenant: {tenant.schema_name} ({tenant.name})"
            ))
            with schema_context(tenant.schema_name):
                parcels_qs = Parcel.objects.filter(is_deleted=False, state=True)
                if parcel_id:
                    parcels_qs = parcels_qs.filter(pk=parcel_id)

                for parcel in parcels_qs.iterator():
                    summary = _process_parcel(parcel, days, dry_run, notify, notifier)
                    total["parcels"] += 1
                    total["alerts"] += summary["created"]
                    total["notified"] += summary["notified"]
                    total["errors"] += len(summary["errors"])
                    self._print_parcel_summary(summary, dry_run)

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Procesadas {total['parcels']} parcelas · "
            f"{total['alerts']} alertas creadas · "
            f"{total['notified']} notificaciones enviadas · "
            f"{total['errors']} errores"
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
