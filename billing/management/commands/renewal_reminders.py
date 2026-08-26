"""
Envía recordatorios de renovación con un link de pago (alternativa al cobro 3RI).

Mientras Wompi no tenga activado 3DS para cobro automático, este comando:
    1. Encuentra suscripciones que vencen en los próximos 3 días
       (activas, con renovación automática y SIN tarjeta guardada).
    2. Genera un link de pago de renovación (Wompi).
    3. Envía un email al cliente con el link.
    4. Marca el recordatorio como enviado (evita spam).

Debe ejecutarse como cron diario, ANTES de check_subscriptions.

Uso:
    python manage.py renewal_reminders
    python manage.py renewal_reminders --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from billing.models import Subscription
from billing.wompi_gateway import WompiGateway
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Envía recordatorios de renovación con link de pago'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo reportar, no enviar')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        horizon = now + timedelta(days=3)

        expiring = Subscription.objects.select_related('tenant', 'plan').filter(
            status='active',
            auto_renew=True,
            cancel_at_period_end=False,
            current_period_end__lte=horizon,
            current_period_end__gte=now - timedelta(days=1),
        ).exclude(payment_source_id__isnull=False).exclude(payment_source_id='')

        self.stdout.write(self.style.NOTICE(
            f"\n{'='*60}\n"
            f"  RECORDATORIOS DE RENOVACIÓN - {now.strftime('%Y-%m-%d %H:%M')}\n"
            f"  {'[DRY RUN]' if dry_run else '[EJECUTANDO]'}\n"
            f"  A punto de vencer: {expiring.count()}\n"
            f"{'='*60}"
        ))

        gateway = WompiGateway()
        sent = 0
        failed = 0

        for sub in expiring:
            payer_email = (sub.metadata or {}).get('payer_email', '')
            if not payer_email:
                self.stdout.write(self.style.WARNING(f"  ⚠️ {sub.tenant.name}: sin email (metadata.payer_email), omitido"))
                continue

            # Anti-spam: un recordatorio por día
            last = (sub.metadata or {}).get('last_renewal_reminder')
            if last and last >= now.date().isoformat():
                self.stdout.write(f"  ⏭️  {sub.tenant.name}: ya notificado hoy")
                continue

            self.stdout.write(f"\n  📧 {sub.tenant.name} — plan {sub.plan.name} (vence {sub.current_period_end.date()})")

            if dry_run:
                self.stdout.write(self.style.WARNING("     [DRY RUN] no se envía"))
                continue

            # 1. Crear link de renovación
            link = gateway.create_renewal_link(sub.tenant_id, sub.plan, payer_email)
            if not link.get('success'):
                failed += 1
                self.stdout.write(self.style.ERROR(f"     → Error creando link: {link.get('error')}"))
                continue

            # 2. Enviar email
            try:
                self._send_email(payer_email, sub.tenant.name, sub.plan.name, sub.plan.price_cop, link['checkout_url'])
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"     → Error enviando email: {e}"))
                continue

            # 3. Marcar enviado
            sub.metadata = {**(sub.metadata or {}), 'last_renewal_reminder': now.date().isoformat()}
            sub.save(update_fields=['metadata', 'updated_at'])
            sent += 1
            self.stdout.write(self.style.SUCCESS("     → Link enviado ✓"))

        self.stdout.write(self.style.NOTICE(
            f"\n{'='*60}\n"
            f"  RESUMEN: enviados={sent} · fallidos={failed}\n"
            f"{'='*60}\n"
        ))

    def _send_email(self, to_email, tenant_name, plan_name, price_cop, checkout_url):
        subject = f"Renueva tu plan de AgroTech — {plan_name}"
        text = (
            f"Hola,\n\n"
            f"Tu plan {plan_name} ({price_cop:,.0f} COP/mes) de la finca {tenant_name} "
            f"está por vencer.\n\n"
            f"Renueva ahora para no perder el acceso:\n{checkout_url}\n\n"
            f"Si ya renovaste, ignora este mensaje."
        )
        html = (
            f"<p>Hola,</p>"
            f"<p>Tu plan <strong>{plan_name}</strong> ({price_cop:,.0f} COP/mes) de la finca "
            f"<strong>{tenant_name}</strong> está por vencer.</p>"
            f"<p><a href='{checkout_url}'>Renovar mi plan</a></p>"
            f"<p>Si ya renovaste, ignora este mensaje.</p>"
        )
        email = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'contacto@agrotechcolombia.com'),
            to=[to_email],
        )
        email.attach_alternative(html, "text/html")
        email.send(fail_silently=False)
