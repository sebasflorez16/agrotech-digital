"""
Servicio de gestión automática de tenants vinculados a suscripciones.

Responsabilidades:
- Crear tenant + schema + dominio cuando un usuario paga o inicia free trial
- Desactivar tenant cuando una suscripción paga vence sin renovar (datos conservados)
- Eliminar tenant cuando un trial gratuito expira sin conversión
- Reactivar tenant cuando un usuario renueva su pago

Reglas de negocio:
┌─────────────────────────────────────────────────────────────────┐
│  PLAN GRATUITO (free trial)                                     │
│  - Se crea tenant al registrar suscripción free                 │
│  - Si el trial expira sin upgrade → ELIMINAR tenant y schema    │
│                                                                 │
│  PLAN PAGO (basic, pro, enterprise)                             │
│  - Se crea tenant al confirmar primer pago                      │
│  - Si deja de pagar → DESACTIVAR (on_trial=False, paid_until=   │
│    fecha pasada). Los datos se conservan en la DB.              │
│  - Si renueva pago → REACTIVAR (paid_until extendida)          │
└─────────────────────────────────────────────────────────────────┘
"""

import logging
import re
import secrets
import string
from datetime import timedelta
from django.db import connection, transaction
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_exists, schema_context
from rest_framework_simplejwt.tokens import RefreshToken

from base_agrotech.models import Client, Domain
from .models import Subscription, Plan, BillingEvent

logger = logging.getLogger(__name__)
User = get_user_model()


def _generate_password(length=12):
    """Generar contraseña segura aleatoria."""
    chars = string.ascii_letters + string.digits + '!@#$%'
    return ''.join(secrets.choice(chars) for _ in range(length))


def _slugify_schema(name: str) -> str:
    """Convertir nombre a slug válido para schema PostgreSQL."""
    slug = re.sub(r'[^a-z0-9]', '_', name.lower().strip())
    slug = re.sub(r'_+', '_', slug).strip('_')
    # Schema names no pueden empezar con número
    if slug and slug[0].isdigit():
        slug = f"t_{slug}"
    return slug[:63]  # Máximo 63 chars en PostgreSQL


class TenantService:
    """Servicio centralizado para crear, desactivar, reactivar y eliminar tenants."""

    # ──────────────────────────────────────────────
    #  CREAR TENANT
    # ──────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def create_tenant_for_subscription(
        tenant_name: str,
        schema_name: str | None = None,
        domain_name: str | None = None,
        plan_tier: str = 'free',
        billing_cycle: str = 'monthly',
        payer_email: str = '',
        external_subscription_id: str | None = None,
        payment_gateway: str = 'manual',
        # Parámetros para crear usuario admin
        username: str | None = None,
        password: str | None = None,
        user_name: str = '',
        user_last_name: str = '',
    ) -> dict:
        """
        Crear un nuevo tenant con su suscripción asociada.

        Args:
            tenant_name: Nombre legible del tenant (ej: "Finca El Roble")
            schema_name: Nombre del schema PostgreSQL (auto-generado si None)
            domain_name: Subdominio (auto-generado si None)
            plan_tier: Tier del plan ('free', 'basic', 'pro', 'enterprise')
            billing_cycle: 'monthly' o 'yearly'
            payer_email: Email del pagador
            external_subscription_id: ID de suscripción en pasarela de pago
            payment_gateway: 'mercadopago', 'paddle', 'manual'

        Returns:
            dict con tenant, subscription, domain y status info
        """
        # ── VALIDACIÓN DE DUPLICADOS ──
        # Impedir que un mismo email cree múltiples tenants
        if payer_email:
            existing_subs = Subscription.objects.filter(
                metadata__payer_email=payer_email,
                status__in=['active', 'trialing'],
            ).select_related('tenant')

            if existing_subs.exists():
                existing = existing_subs.first()
                logger.warning(
                    f"⚠️ Intento de crear tenant duplicado con email={payer_email}. "
                    f"Ya existe: {existing.tenant.name} (schema={existing.tenant.schema_name})"
                )
                return {
                    'success': False,
                    'error': (
                        f'Ya tienes un espacio de trabajo activo: "{existing.tenant.name}". '
                        f'No puedes crear otro con el mismo correo electrónico. '
                        f'Si necesitas acceder a tu cuenta, inicia sesión.'
                    ),
                    'existing_tenant': existing.tenant.name,
                    'existing_schema': existing.tenant.schema_name,
                }

        # 1. Generar schema_name si no se provee
        if not schema_name:
            schema_name = _slugify_schema(tenant_name)

        # Evitar colisión con schemas existentes — en lugar de agregar sufijo,
        # rechazar si ya existe un tenant con ese nombre exacto
        if Client.objects.filter(schema_name=schema_name).exists():
            existing_tenant = Client.objects.get(schema_name=schema_name)
            logger.warning(
                f"⚠️ Schema '{schema_name}' ya existe para tenant '{existing_tenant.name}'"
            )
            return {
                'success': False,
                'error': (
                    f'Ya existe un espacio de trabajo con el nombre "{tenant_name}". '
                    f'Usa un nombre diferente o inicia sesión en tu cuenta existente.'
                ),
                'existing_tenant': existing_tenant.name,
                'existing_schema': schema_name,
            }

        # 2. Obtener plan
        try:
            plan = Plan.objects.get(tier=plan_tier, is_active=True)
        except Plan.DoesNotExist:
            logger.error(f"Plan '{plan_tier}' no encontrado o inactivo")
            return {'success': False, 'error': f"Plan '{plan_tier}' no disponible"}

        # 3. Calcular fechas según tipo de plan
        now = timezone.now()

        if plan_tier == 'free':
            # Trial gratuito
            trial_days = plan.trial_days or 14
            paid_until = (now + timedelta(days=trial_days)).date()
            status = 'trialing'
            trial_end = now + timedelta(days=trial_days)
            period_end = trial_end
        else:
            # Plan pago — periodo según ciclo
            if billing_cycle == 'yearly':
                period_days = 365
            else:
                period_days = 30
            paid_until = (now + timedelta(days=period_days)).date()
            status = 'active'
            trial_end = None
            period_end = now + timedelta(days=period_days)

        # 4. Crear o recuperar Client (tenant)
        if not domain_name:
            domain_name = f"{schema_name}.agrotechcolombia.com"

        tenant, tenant_created = Client.objects.get_or_create(
            schema_name=schema_name,
            defaults={
                'name': tenant_name,
                'paid_until': paid_until,
                'on_trial': (plan_tier == 'free'),
            },
        )
        if not tenant_created:
            # Tenant ya existía — actualizar datos
            tenant.name = tenant_name
            tenant.paid_until = paid_until
            tenant.on_trial = (plan_tier == 'free')
            tenant.save()

        # 5. Crear dominio si no existe
        Domain.objects.get_or_create(
            domain=domain_name,
            defaults={
                'tenant': tenant,
                'is_primary': True,
            },
        )

        # 6. Crear o actualizar suscripción
        subscription, sub_created = Subscription.objects.update_or_create(
            tenant=tenant,
            defaults={
                'plan': plan,
                'payment_gateway': payment_gateway,
                'external_subscription_id': external_subscription_id or '',
                'status': status,
                'billing_cycle': billing_cycle,
                'current_period_start': now,
                'current_period_end': period_end,
                'trial_end': trial_end,
                'auto_renew': (plan_tier != 'free'),
                'metadata': {
                    'payer_email': payer_email,
                    'created_via': 'tenant_service',
                },
            },
        )

        # 7. Registrar evento
        event_type = 'trial.started' if plan_tier == 'free' else 'subscription.created'
        BillingEvent.objects.create(
            tenant=tenant,
            subscription=subscription,
            event_type=event_type,
            event_data={
                'plan': plan_tier,
                'billing_cycle': billing_cycle,
                'payer_email': payer_email,
                'schema_name': schema_name,
                'domain': domain_name,
                'external_subscription_id': external_subscription_id or '',
            },
        )

        # 8. Crear usuario admin dentro del schema del tenant
        user = None
        tokens = None
        auto_generated_password = False

        if username and payer_email:
            # Si no se provee password, generar uno automáticamente
            if not password:
                password = _generate_password()
                auto_generated_password = True

            with schema_context(schema_name):
                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': payer_email,
                        'name': user_name or tenant_name,
                        'last_name': user_last_name or '',
                        'is_active': True,
                        'is_staff': True,
                        'role': 'admin',
                    },
                )
                if user_created:
                    user.set_password(password)
                    user.save()
                    logger.info(f"Admin user creado: {username} en schema {schema_name}")
                else:
                    logger.info(f"Admin user ya existía: {username} en schema {schema_name}")
                    auto_generated_password = False  # No devolver password de usuario existente

            # Generar JWT tokens para auto-login
            try:
                refresh = RefreshToken.for_user(user)
                tokens = {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                }
            except Exception as e:
                logger.warning(f"No se pudieron generar tokens JWT: {e}")

            # Enviar email de bienvenida
            TenantService._send_welcome_email(
                email=payer_email,
                username=username,
                password=password if auto_generated_password else None,
                tenant_name=tenant_name,
                plan_tier=plan_tier,
            )

        logger.info(
            f"✅ Tenant creado: {tenant_name} (schema={schema_name}) "
            f"plan={plan_tier} status={status} user={username or 'N/A'}"
        )

        return {
            'success': True,
            'tenant': tenant,
            'subscription': subscription,
            'schema_name': schema_name,
            'domain': domain_name,
            'status': status,
            'paid_until': paid_until.isoformat(),
            'user': user,
            'tokens': tokens,
            'username': username,
        }

    # ──────────────────────────────────────────────
    #  EMAIL DE BIENVENIDA
    # ──────────────────────────────────────────────

    @staticmethod
    def _send_welcome_email(
        email: str,
        username: str,
        password: str | None,
        tenant_name: str,
        plan_tier: str,
    ):
        """Enviar email de bienvenida con credenciales de acceso."""
        try:
            frontend_url = getattr(
                settings, 'FRONTEND_URL',
                'https://frontend-cliente-agrotech.netlify.app'
            )
            login_url = f"{frontend_url}/templates/authentication/login.html"

            plan_names = {
                'free': 'Explorador (Trial 14 días)',
                'basic': 'Agricultor',
                'pro': 'Empresarial',
                'enterprise': 'Enterprise',
            }
            plan_display = plan_names.get(plan_tier, plan_tier)

            # Construir mensaje
            subject = f"🌱 Bienvenido a AgroTech Digital - Tu cuenta está lista"

            password_section = ""
            if password:
                password_section = f"""
Tu contraseña temporal: {password}
⚠️ Te recomendamos cambiarla después de iniciar sesión.
"""
            else:
                password_section = """
Usa la contraseña que configuraste durante el registro.
"""

            message = f"""
¡Hola {username}!

¡Bienvenido a AgroTech Digital! Tu espacio de trabajo "{tenant_name}" está listo.

═══════════════════════════════════════
  DATOS DE ACCESO
═══════════════════════════════════════

🔗 Iniciar sesión: {login_url}
👤 Usuario: {username}
📧 Email: {email}
{password_section}
📋 Plan: {plan_display}
🏡 Finca/Empresa: {tenant_name}

═══════════════════════════════════════
  PRÓXIMOS PASOS
═══════════════════════════════════════

1. Inicia sesión en la plataforma
2. Configura tus parcelas y cultivos
3. Ejecuta tu primer análisis satelital NDVI

Si tienes alguna pregunta, contáctanos en info@agrotechdigital.com

¡Éxito con tus cultivos! 🌾
El equipo de AgroTech Digital
"""

            html_message = f"""
<div style="font-family: 'Inter', -apple-system, sans-serif; max-width: 600px; margin: 0 auto; background: #f8f9fa;">
    <div style="background: linear-gradient(135deg, #2FB344 0%, #1a7a2e 100%); padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 800;">🌱 AgroTech Digital</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0; font-size: 16px;">Tu cuenta está lista</p>
    </div>

    <div style="background: white; padding: 30px; border-radius: 0 0 12px 12px;">
        <h2 style="color: #1a1a1a; margin: 0 0 20px;">¡Hola {username}!</h2>
        <p style="color: #4a4a4a; line-height: 1.6;">
            Tu espacio de trabajo <strong>"{tenant_name}"</strong> ha sido creado exitosamente.
        </p>

        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 24px; margin: 24px 0;">
            <h3 style="color: #166534; margin: 0 0 16px; font-size: 16px;">🔐 Datos de acceso</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="color: #6b7280; padding: 6px 0;">Usuario:</td><td style="font-weight: 600; color: #1a1a1a;">{username}</td></tr>
                <tr><td style="color: #6b7280; padding: 6px 0;">Email:</td><td style="font-weight: 600; color: #1a1a1a;">{email}</td></tr>
                <tr><td style="color: #6b7280; padding: 6px 0;">Plan:</td><td style="font-weight: 600; color: #1a1a1a;">{plan_display}</td></tr>
                {"<tr><td style='color: #6b7280; padding: 6px 0;'>Contraseña:</td><td style='font-weight: 600; color: #dc2626;'>" + password + "</td></tr>" if password else ""}
            </table>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{login_url}" style="display: inline-block; background: linear-gradient(135deg, #2FB344, #1a7a2e); color: white; text-decoration: none; padding: 14px 36px; border-radius: 50px; font-weight: 700; font-size: 16px;">
                Iniciar Sesión →
            </a>
        </div>

        <div style="border-top: 1px solid #e5e7eb; padding-top: 20px; margin-top: 24px;">
            <h3 style="color: #1a1a1a; font-size: 15px; margin: 0 0 12px;">📋 Próximos pasos</h3>
            <ol style="color: #4a4a4a; line-height: 2; padding-left: 20px; margin: 0;">
                <li>Inicia sesión en la plataforma</li>
                <li>Configura tus parcelas y cultivos</li>
                <li>Ejecuta tu primer análisis satelital NDVI</li>
            </ol>
        </div>
    </div>

    <div style="text-align: center; padding: 20px; color: #9ca3af; font-size: 13px;">
        <p>AgroTech Digital — Agricultura de Precisión</p>
        <p>info@agrotechdigital.com</p>
    </div>
</div>
"""

            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@agrotechdigital.com'),
                recipient_list=[email],
                html_message=html_message,
                fail_silently=True,
            )
            logger.info(f"📧 Email de bienvenida enviado a {email}")

        except Exception as e:
            # No bloquear el flujo si el email falla
            logger.warning(f"No se pudo enviar email de bienvenida a {email}: {e}")

    # ──────────────────────────────────────────────
    #  DESACTIVAR TENANT (plan pago sin renovar)
    # ──────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def deactivate_tenant(tenant: Client, reason: str = 'payment_overdue') -> dict:
        """
        Desactivar un tenant sin eliminar sus datos.

        Se usa cuando un plan pago vence sin renovación.
        El schema y datos se conservan en la DB para posible reactivación.

        Args:
            tenant: Instancia de Client
            reason: Motivo de la desactivación

        Returns:
            dict con resultado
        """
        try:
            subscription = tenant.subscription
        except Subscription.DoesNotExist:
            return {'success': False, 'error': 'No subscription found'}

        # Marcar suscripción como expirada
        old_status = subscription.status
        subscription.status = 'expired'
        subscription.ended_at = timezone.now()
        subscription.auto_renew = False
        subscription.metadata['deactivation_reason'] = reason
        subscription.metadata['deactivated_at'] = timezone.now().isoformat()
        subscription.metadata['previous_status'] = old_status
        subscription.save()

        # Marcar tenant como no pagado (paid_until en el pasado)
        tenant.paid_until = (timezone.now() - timedelta(days=1)).date()
        tenant.on_trial = False
        tenant.save()

        # Registrar evento
        BillingEvent.objects.create(
            tenant=tenant,
            subscription=subscription,
            event_type='tenant.deactivated',
            event_data={
                'reason': reason,
                'previous_status': old_status,
                'schema_name': tenant.schema_name,
            },
        )

        logger.warning(
            f"⚠️ Tenant desactivado: {tenant.name} (schema={tenant.schema_name}) "
            f"razón={reason}"
        )

        return {
            'success': True,
            'tenant_name': tenant.name,
            'schema_name': tenant.schema_name,
            'action': 'deactivated',
            'reason': reason,
        }

    # ──────────────────────────────────────────────
    #  ELIMINAR TENANT (trial gratuito expirado)
    # ──────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def delete_tenant(tenant: Client, reason: str = 'trial_expired') -> dict:
        """
        Eliminar completamente un tenant y su schema.

        Se usa cuando un trial gratuito expira sin conversión a plan pago.
        ¡DESTRUCTIVO! Elimina el schema PostgreSQL y todos los datos.

        Args:
            tenant: Instancia de Client
            reason: Motivo de la eliminación

        Returns:
            dict con resultado
        """
        schema_name = tenant.schema_name
        tenant_name = tenant.name

        # Seguridad: nunca eliminar el schema 'public'
        if schema_name == 'public':
            logger.error("❌ Intento de eliminar schema 'public' — RECHAZADO")
            return {'success': False, 'error': 'Cannot delete public schema'}

        # Registrar evento ANTES de eliminar (para logs)
        try:
            subscription = tenant.subscription
            BillingEvent.objects.create(
                tenant=tenant,
                subscription=subscription,
                event_type='tenant.deleted',
                event_data={
                    'reason': reason,
                    'schema_name': schema_name,
                    'tenant_name': tenant_name,
                    'plan': subscription.plan.tier,
                },
            )
        except Subscription.DoesNotExist:
            pass

        # Eliminar dominios
        Domain.objects.filter(tenant=tenant).delete()

        # Eliminar suscripción (CASCADE debería hacerlo, pero explícito)
        Subscription.objects.filter(tenant=tenant).delete()

        # Eliminar el tenant (esto NO elimina el schema automáticamente)
        tenant.delete()

        # Eliminar schema de PostgreSQL
        try:
            with connection.cursor() as cursor:
                # Usar quote_ident para prevenir SQL injection
                cursor.execute(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                    [schema_name]
                )
                if cursor.fetchone():
                    cursor.execute(f'DROP SCHEMA "{schema_name}" CASCADE')
                    logger.info(f"🗑️ Schema '{schema_name}' eliminado de PostgreSQL")
                else:
                    logger.info(f"Schema '{schema_name}' no existía en PostgreSQL")
        except Exception as e:
            logger.error(f"Error eliminando schema '{schema_name}': {e}")
            # No hacemos rollback — el tenant ya fue eliminado de la tabla

        logger.warning(
            f"🗑️ Tenant eliminado: {tenant_name} (schema={schema_name}) "
            f"razón={reason}"
        )

        return {
            'success': True,
            'tenant_name': tenant_name,
            'schema_name': schema_name,
            'action': 'deleted',
            'reason': reason,
        }

    # ──────────────────────────────────────────────
    #  REACTIVAR TENANT (renueva pago)
    # ──────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def reactivate_tenant(
        tenant: Client,
        plan_tier: str | None = None,
        billing_cycle: str = 'monthly',
        external_subscription_id: str | None = None,
        payment_gateway: str = 'mercadopago',
    ) -> dict:
        """
        Reactivar un tenant que fue desactivado por falta de pago.

        Args:
            tenant: Instancia de Client
            plan_tier: Nuevo plan (None = mismo plan anterior)
            billing_cycle: Ciclo de facturación
            external_subscription_id: ID de suscripción en pasarela
            payment_gateway: Pasarela usada

        Returns:
            dict con resultado
        """
        try:
            subscription = tenant.subscription
        except Subscription.DoesNotExist:
            return {'success': False, 'error': 'No subscription found to reactivate'}

        # Determinar plan
        if plan_tier:
            try:
                new_plan = Plan.objects.get(tier=plan_tier, is_active=True)
            except Plan.DoesNotExist:
                return {'success': False, 'error': f"Plan '{plan_tier}' not found"}
        else:
            new_plan = subscription.plan

        # Calcular nuevo período
        now = timezone.now()
        period_days = 365 if billing_cycle == 'yearly' else 30

        # Actualizar suscripción
        subscription.plan = new_plan
        subscription.status = 'active'
        subscription.billing_cycle = billing_cycle
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=period_days)
        subscription.ended_at = None
        subscription.canceled_at = None
        subscription.auto_renew = True
        subscription.cancel_at_period_end = False
        if external_subscription_id:
            subscription.external_subscription_id = external_subscription_id
        if payment_gateway:
            subscription.payment_gateway = payment_gateway
        subscription.metadata['reactivated_at'] = now.isoformat()
        subscription.save()

        # Actualizar tenant
        tenant.paid_until = (now + timedelta(days=period_days)).date()
        tenant.on_trial = False
        tenant.save()

        # Registrar evento
        BillingEvent.objects.create(
            tenant=tenant,
            subscription=subscription,
            event_type='tenant.reactivated',
            event_data={
                'plan': new_plan.tier,
                'billing_cycle': billing_cycle,
                'schema_name': tenant.schema_name,
            },
        )

        logger.info(
            f"✅ Tenant reactivado: {tenant.name} (schema={tenant.schema_name}) "
            f"plan={new_plan.tier}"
        )

        return {
            'success': True,
            'tenant_name': tenant.name,
            'schema_name': tenant.schema_name,
            'action': 'reactivated',
            'plan': new_plan.tier,
            'paid_until': tenant.paid_until.isoformat(),
        }

    # ──────────────────────────────────────────────
    #  UPGRADE DE PLAN (free → pago, o pago → pago superior)
    # ──────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def upgrade_subscription(
        tenant: Client,
        new_plan_tier: str,
        billing_cycle: str = 'monthly',
        external_subscription_id: str | None = None,
        payment_gateway: str = 'mercadopago',
        payer_email: str = '',
    ) -> dict:
        """
        Upgrade de plan para un tenant existente.

        Args:
            tenant: Instancia de Client
            new_plan_tier: Tier del nuevo plan
            billing_cycle: Ciclo de facturación
            external_subscription_id: ID externo
            payment_gateway: Pasarela
            payer_email: Email del pagador

        Returns:
            dict con resultado
        """
        try:
            subscription = tenant.subscription
        except Subscription.DoesNotExist:
            return {'success': False, 'error': 'No subscription found'}

        try:
            new_plan = Plan.objects.get(tier=new_plan_tier, is_active=True)
        except Plan.DoesNotExist:
            return {'success': False, 'error': f"Plan '{new_plan_tier}' not found"}

        old_plan = subscription.plan.tier
        now = timezone.now()
        period_days = 365 if billing_cycle == 'yearly' else 30

        # Actualizar suscripción
        subscription.plan = new_plan
        subscription.status = 'active'
        subscription.billing_cycle = billing_cycle
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=period_days)
        subscription.trial_end = None  # Ya no está en trial
        subscription.auto_renew = True
        subscription.cancel_at_period_end = False
        if external_subscription_id:
            subscription.external_subscription_id = external_subscription_id
        if payment_gateway:
            subscription.payment_gateway = payment_gateway
        if payer_email:
            subscription.metadata['payer_email'] = payer_email
        subscription.metadata['upgraded_at'] = now.isoformat()
        subscription.metadata['upgraded_from'] = old_plan
        subscription.save()

        # Actualizar tenant
        tenant.paid_until = (now + timedelta(days=period_days)).date()
        tenant.on_trial = False
        tenant.save()

        # Registrar evento
        BillingEvent.objects.create(
            tenant=tenant,
            subscription=subscription,
            event_type='subscription.upgraded',
            event_data={
                'from_plan': old_plan,
                'to_plan': new_plan_tier,
                'billing_cycle': billing_cycle,
                'payer_email': payer_email,
            },
        )

        logger.info(
            f"⬆️ Upgrade: {tenant.name} {old_plan} → {new_plan_tier} "
            f"(cycle={billing_cycle})"
        )

        return {
            'success': True,
            'tenant_name': tenant.name,
            'action': 'upgraded',
            'from_plan': old_plan,
            'to_plan': new_plan_tier,
            'paid_until': tenant.paid_until.isoformat(),
        }

    # ──────────────────────────────────────────────
    #  PROCESO BATCH: revisar todas las suscripciones
    # ──────────────────────────────────────────────

    @classmethod
    def check_all_subscriptions(cls) -> dict:
        """
        Revisar TODAS las suscripciones y aplicar reglas de negocio.

        Debe ejecutarse como cron job diario.

        Reglas:
        1. Trial gratuito expirado → ELIMINAR tenant
        2. Plan pago expirado (>7 días de gracia) → DESACTIVAR tenant
        3. Plan pago en gracia (1-7 días vencido) → marcar past_due

        Returns:
            dict con resumen de acciones tomadas
        """
        now = timezone.now()
        results = {
            'checked': 0,
            'trials_deleted': 0,
            'paid_deactivated': 0,
            'marked_past_due': 0,
            'errors': [],
        }

        subscriptions = Subscription.objects.select_related(
            'tenant', 'plan'
        ).exclude(
            status__in=['canceled', 'expired']
        ).exclude(
            tenant__schema_name='public'
        )

        for sub in subscriptions:
            results['checked'] += 1

            try:
                # ── Trial gratuito expirado ──
                if sub.plan.tier == 'free' and sub.status == 'trialing':
                    if sub.trial_end and now > sub.trial_end:
                        result = cls.delete_tenant(
                            sub.tenant,
                            reason='trial_expired_no_conversion'
                        )
                        if result['success']:
                            results['trials_deleted'] += 1
                            logger.info(
                                f"🗑️ Trial expirado eliminado: {sub.tenant.name}"
                            )
                        else:
                            results['errors'].append(
                                f"Error eliminando trial {sub.tenant.name}: {result.get('error')}"
                            )
                        continue

                # ── Plan pago vencido ──
                if sub.plan.tier != 'free' and sub.current_period_end:
                    if now > sub.current_period_end:
                        days_overdue = (now - sub.current_period_end).days

                        if days_overdue > 7:
                            # Más de 7 días → desactivar
                            result = cls.deactivate_tenant(
                                sub.tenant,
                                reason=f'payment_overdue_{days_overdue}_days'
                            )
                            if result['success']:
                                results['paid_deactivated'] += 1
                            else:
                                results['errors'].append(
                                    f"Error desactivando {sub.tenant.name}: {result.get('error')}"
                                )
                        elif sub.status != 'past_due':
                            # 1-7 días → período de gracia, marcar past_due
                            sub.status = 'past_due'
                            sub.save()
                            results['marked_past_due'] += 1

                            BillingEvent.objects.create(
                                tenant=sub.tenant,
                                subscription=sub,
                                event_type='subscription.past_due',
                                event_data={
                                    'days_overdue': days_overdue,
                                    'period_end': sub.current_period_end.isoformat(),
                                },
                            )
                            logger.warning(
                                f"⏰ Pago vencido ({days_overdue}d): {sub.tenant.name}"
                            )

            except Exception as e:
                results['errors'].append(f"Error procesando {sub.id}: {str(e)}")
                logger.exception(f"Error en check_all_subscriptions para sub {sub.id}")

        logger.info(
            f"📊 Check subscriptions: {results['checked']} revisadas, "
            f"{results['trials_deleted']} trials eliminados, "
            f"{results['paid_deactivated']} pagos desactivados, "
            f"{results['marked_past_due']} marcados past_due"
        )

        return results
