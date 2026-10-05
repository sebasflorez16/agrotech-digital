"""
Management command para revisar suscripciones y gestionar tenants.

Debe ejecutarse como cron job diario en producción.

Uso:
    python manage.py check_subscriptions
    python manage.py check_subscriptions --dry-run   # Solo reportar, no actuar

Reglas:
    - Trial expirado (cualquier plan en estado 'trialing') → DESACTIVAR tenant
      (datos conservados; se reactiva al pagar)
    - Plan pago >7 días vencido → DESACTIVAR tenant (datos conservados)
    - Plan pago 1-7 días vencido → marcar como past_due (período de gracia)
"""

from django.core.management.base import BaseCommand
from billing.tenant_service import TenantService
from billing.models import Subscription
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Revisar suscripciones y desactivar/eliminar tenants según reglas de negocio'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo reportar acciones sin ejecutarlas',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.NOTICE(
            f"\n{'='*60}\n"
            f"  REVISIÓN DE SUSCRIPCIONES - {timezone.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"  {'[DRY RUN - Solo reporte]' if dry_run else '[EJECUTANDO acciones]'}\n"
            f"{'='*60}\n"
        ))

        now = timezone.now()
        
        # Obtener suscripciones activas/trialing (excluyendo public)
        subscriptions = Subscription.objects.select_related(
            'tenant', 'plan'
        ).exclude(
            status__in=['canceled', 'expired']
        ).exclude(
            tenant__schema_name='public'
        )

        stats = {
            'total': 0,
            'ok': 0,
            'trials_to_delete': 0,
            'trials_deleted': 0,
            'paid_to_deactivate': 0,
            'paid_deactivated': 0,
            'past_due': 0,
            'errors': [],
        }

        for sub in subscriptions:
            stats['total'] += 1
            tenant = sub.tenant
            plan = sub.plan

            # ── TRIAL EXPIRADO (cualquier plan en estado 'trialing') ──
            # NOTA: el plan FREE permanente se crea en estado 'active' (nunca
            # 'trialing'), por lo que no entra aquí y no se desactiva el embudo.
            if sub.status == 'trialing':
                reference_end = sub.trial_end or sub.current_period_end
                if sub.is_trial_expired():
                    stats['trials_to_delete'] += 1
                    days_expired = (now - reference_end).days if reference_end else 0

                    self.stdout.write(self.style.WARNING(
                        f"  ⏳ TRIAL EXPIRADO: {tenant.name} "
                        f"(schema={tenant.schema_name}, plan={plan.name}, hace {days_expired}d)"
                    ))

                    if not dry_run:
                        result = TenantService.deactivate_tenant(
                            tenant, reason='trial_expired_cron'
                        )
                        if result['success']:
                            stats['trials_deleted'] += 1
                            self.stdout.write(self.style.SUCCESS(
                                "     → Desactivado ✓ (datos conservados)"
                            ))
                        else:
                            stats['errors'].append(f"Error desactivando {tenant.name}: {result.get('error')}")
                            self.stdout.write(self.style.ERROR(f"     → Error: {result.get('error')}"))
                    continue
                else:
                    remaining = (reference_end - now).days if reference_end else '?'
                    self.stdout.write(
                        f"  ✅ TRIAL OK: {tenant.name} ({remaining}d restantes)"
                    )
                    stats['ok'] += 1
                    continue

            # ── PLAN PAGO VENCIDO ──
            if plan.tier != 'free' and sub.current_period_end:
                if now > sub.current_period_end:
                    days_overdue = (now - sub.current_period_end).days

                    if days_overdue > 7:
                        stats['paid_to_deactivate'] += 1
                        
                        self.stdout.write(self.style.WARNING(
                            f"  ⚠️  PAGO VENCIDO ({days_overdue}d): {tenant.name} "
                            f"(schema={tenant.schema_name}, plan={plan.name})"
                        ))
                        
                        if not dry_run:
                            result = TenantService.deactivate_tenant(
                                tenant,
                                reason=f'payment_overdue_{days_overdue}d_cron'
                            )
                            if result['success']:
                                stats['paid_deactivated'] += 1
                                self.stdout.write(self.style.SUCCESS(f"     → Desactivado ✓"))
                            else:
                                stats['errors'].append(f"Error desactivando {tenant.name}: {result.get('error')}")
                                self.stdout.write(self.style.ERROR(f"     → Error: {result.get('error')}"))
                    else:
                        # Período de gracia (1-7 días)
                        if sub.status != 'past_due':
                            stats['past_due'] += 1
                            
                            self.stdout.write(self.style.WARNING(
                                f"  ⏰ GRACIA ({days_overdue}d): {tenant.name} → past_due"
                            ))
                            
                            if not dry_run:
                                sub.status = 'past_due'
                                sub.save()
                        else:
                            self.stdout.write(
                                f"  ⏰ PAST_DUE: {tenant.name} ({days_overdue}d vencido)"
                            )
                    continue

            # ── ACTIVA OK ──
            remaining = (sub.current_period_end - now).days if sub.current_period_end else '?'
            self.stdout.write(
                f"  ✅ ACTIVA: {tenant.name} (plan={plan.name}, {remaining}d restantes)"
            )
            stats['ok'] += 1

        # ── RESUMEN ──
        self.stdout.write(self.style.NOTICE(
            f"\n{'='*60}\n"
            f"  RESUMEN\n"
            f"{'='*60}"
        ))
        self.stdout.write(f"  Total revisadas: {stats['total']}")
        self.stdout.write(self.style.SUCCESS(f"  OK: {stats['ok']}"))
        
        if stats['trials_to_delete']:
            label = f"  Trials eliminados: {stats['trials_deleted']}/{stats['trials_to_delete']}"
            self.stdout.write(self.style.WARNING(label) if dry_run else self.style.SUCCESS(label))
        
        if stats['paid_to_deactivate']:
            label = f"  Pagos desactivados: {stats['paid_deactivated']}/{stats['paid_to_deactivate']}"
            self.stdout.write(self.style.WARNING(label) if dry_run else self.style.SUCCESS(label))
        
        if stats['past_due']:
            self.stdout.write(self.style.WARNING(f"  Marcados past_due: {stats['past_due']}"))
        
        if stats['errors']:
            self.stdout.write(self.style.ERROR(f"\n  ❌ ERRORES ({len(stats['errors'])}):"))
            for err in stats['errors']:
                self.stdout.write(self.style.ERROR(f"    - {err}"))
        
        self.stdout.write('')
