"""
Cobra automáticamente las suscripciones vencidas (renovación automática).

Debe ejecutarse como cron job diario ANTES de `check_subscriptions`.

Uso:
    python manage.py charge_recurring
    python manage.py charge_recurring --dry-run   # Solo reportar, no cobrar

Flujo:
    1. Encuentra suscripciones activas con renovación automática vencidas
       (current_period_end <= hoy) y con fuente de pago tokenizada (3RI).
    2. Cobra la tarjeta con Wompi (transacción automática 3RI).
    3. Si APRUEBA → extiende el período 30 días.
    4. Si FALLA → registra el error en metadata (luego check_subscriptions
       aplica el período de gracia y desactiva).
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from billing.models import Subscription
from billing.wompi_gateway import WompiGateway
import uuid
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cobra automáticamente las suscripciones vencidas (renovación recurrente 3RI)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo reportar, no cobrar')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()

        due_subs = Subscription.objects.select_related('tenant', 'plan').filter(
            status='active',
            auto_renew=True,
            cancel_at_period_end=False,
            current_period_end__lte=now,
        ).exclude(payment_source_id__isnull=True).exclude(payment_source_id='')

        self.stdout.write(self.style.NOTICE(
            f"\n{'='*60}\n"
            f"  COBRO RECURRENTE - {now.strftime('%Y-%m-%d %H:%M')}\n"
            f"  {'[DRY RUN - Solo reporte]' if dry_run else '[EJECUTANDO cobros]'}\n"
            f"  Suscripciones a cobrar: {due_subs.count()}\n"
            f"{'='*60}"
        ))

        gateway = WompiGateway()
        charged = 0
        failed = 0

        for sub in due_subs:
            plan = sub.plan
            amount_in_cents = int(plan.price_cop * 100)
            customer_email = (sub.metadata or {}).get('payer_email', '') or sub.tenant.name
            reference = f"sub_{sub.tenant_id}_{plan.tier}_{uuid.uuid4().hex[:8]}"

            self.stdout.write(f"\n  💳 {sub.tenant.name} — plan {plan.name} "
                              f"(${plan.price_cop:,.0f} COP) · ref={reference[:20]}…")

            if dry_run:
                self.stdout.write(self.style.WARNING("     [DRY RUN] no se cobra"))
                continue

            result = gateway.charge_payment_source(
                payment_source_id=sub.payment_source_id,
                amount_in_cents=amount_in_cents,
                reference=reference,
                customer_email=customer_email,
            )

            if result.get('success') and result.get('status') == 'APPROVED':
                sub.current_period_start = now
                sub.current_period_end = now + timedelta(days=30)
                sub.status = 'active'
                sub.save(update_fields=['current_period_start', 'current_period_end', 'status', 'updated_at'])
                charged += 1
                self.stdout.write(self.style.SUCCESS(f"     → Cobrado ✓ (hasta {sub.current_period_end.date()})"))
            else:
                error = result.get('error', 'unknown')
                sub.metadata = {**(sub.metadata or {}), 'last_charge_error': error,
                                'last_charge_attempt': now.isoformat()}
                sub.save(update_fields=['metadata', 'updated_at'])
                failed += 1
                self.stdout.write(self.style.ERROR(f"     → Falló: {error}"))

        self.stdout.write(self.style.NOTICE(
            f"\n{'='*60}\n"
            f"  RESUMEN: cobrados={charged} · fallidos={failed}\n"
            f"{'='*60}\n"
        ))
