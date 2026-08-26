"""
Corrige suscripciones cuyo plan no coincide con el plan del pago.

Los planes válidos son: free (Explorador), basic (Agricultor), pro (Empresarial).
'enterprise' (Corporativo) fue descontinuado.

La referencia del pago (external_subscription_id) tiene el formato:
    sub_<tenant_id>_<plan_tier>_<uuid>  (primer pago)

Reglas:
    - Si la suscripción tiene un plan inválido (ej. enterprise), se corrige al
      plan de la referencia; si no hay referencia, se usa 'basic'.
    - Si la referencia indica otro plan, se corrige a ese plan.

Uso:
    python manage.py fix_subscription_plans
    python manage.py fix_subscription_plans --dry-run
"""

from django.core.management.base import BaseCommand
from billing.models import Subscription, Plan
import re

VALID_TIERS = ['free', 'basic', 'pro']


class Command(BaseCommand):
    help = 'Corrige suscripciones con plan incorrecto (según la referencia del pago)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo reportar, no corregir')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        fixed = 0

        subs = Subscription.objects.select_related('tenant', 'plan').all()

        for sub in subs:
            ref = sub.external_subscription_id or ''
            m = re.search(r'sub_\d+_([a-z]+)_', ref)
            intended_tier = m.group(1) if m else None

            target = None
            if sub.plan.tier not in VALID_TIERS:
                # Plan inválido → corregir al de la referencia, o 'basic' si no hay
                target = intended_tier if intended_tier in VALID_TIERS else 'basic'
            elif intended_tier and intended_tier in VALID_TIERS and intended_tier != sub.plan.tier:
                # La referencia indica otro plan → corregir
                target = intended_tier

            if not target:
                continue

            plan = Plan.objects.filter(tier=target, is_active=True).first()
            if not plan:
                self.stdout.write(self.style.WARNING(f'⚠️ {sub.tenant.schema_name}: plan {target} no disponible'))
                continue

            self.stdout.write(f'🔧 {sub.tenant.schema_name}: {sub.plan.tier} → {target}')
            if not dry_run:
                sub.plan = plan
                sub.save(update_fields=['plan', 'updated_at'])
            fixed += 1

        self.stdout.write(self.style.SUCCESS(f'\nSuscripciones corregidas: {fixed}'))
