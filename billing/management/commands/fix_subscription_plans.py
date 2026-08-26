"""
Corrige suscripciones cuyo plan no coincide con el plan del pago.

La referencia del pago (external_subscription_id) tiene el formato:
    sub_<tenant_id>_<plan_tier>_<uuid>  (primer pago)
    renew_<tenant_id>_<uuid>            (renovación)

Si el plan actual no coincide con el plan_tier de la referencia, se corrige.

Uso:
    python manage.py fix_subscription_plans
    python manage.py fix_subscription_plans --dry-run
"""

from django.core.management.base import BaseCommand
from billing.models import Subscription, Plan
import re


class Command(BaseCommand):
    help = 'Corrige suscripciones con plan incorrecto (según la referencia del pago)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo reportar, no corregir')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        fixed = 0

        subs = Subscription.objects.filter(
            payment_gateway='wompi',
        ).exclude(external_subscription_id__isnull=True).exclude(external_subscription_id='')

        for sub in subs:
            ref = sub.external_subscription_id
            m = re.search(r'sub_\d+_([a-z]+)_', ref)
            if not m:
                continue
            intended_tier = m.group(1)
            if sub.plan.tier == intended_tier:
                continue

            plan = Plan.objects.filter(tier=intended_tier, is_active=True).first()
            if not plan:
                self.stdout.write(self.style.WARNING(f'⚠️ {sub.tenant.schema_name}: plan {intended_tier} no disponible'))
                continue

            self.stdout.write(f'🔧 {sub.tenant.schema_name}: {sub.plan.tier} → {intended_tier}')
            if not dry_run:
                sub.plan = plan
                sub.save(update_fields=['plan', 'updated_at'])
            fixed += 1

        self.stdout.write(self.style.SUCCESS(f'\nSuscripciones corregidas: {fixed}'))
