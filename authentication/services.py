"""
Servicio de registro SaaS para AgroTech Digital.
 
Maneja la creación atómica de:
1. Client (Tenant) - Schema de PostgreSQL aislado
2. Domain - Subdominio para el tenant
3. User (Admin) - Usuario administrador (is_active=False hasta verificar email)
4. Subscription - Suscripción trial automática (via signal)
5. Email de verificación enviado al correo del usuario
 
Implementa transacciones atómicas para evitar datos huérfanos.
"""
 
import re
import logging
from datetime import date, timedelta
from uuid import uuid4
 
from django.db import transaction, connection
from django.conf import settings
from django.core.mail import send_mail
from django_tenants.utils import schema_context
 
from base_agrotech.models import Client, Domain
from django.contrib.auth import get_user_model
 
User = get_user_model()
logger = logging.getLogger(__name__)


class RegistrationService:
    """
    Servicio encargado del flujo completo de registro SaaS.
    
    Uso:
        service = RegistrationService()
        result = service.register(validated_data)
    """
    
    def register(self, validated_data: dict) -> dict:
        """
        Ejecuta el registro completo de forma atómica.
        
        Args:
            validated_data: Datos validados por RegisterSerializer
            
        Returns:
            dict con tenant, user y subscription creados
            
        Raises:
            RegistrationError: Si algo falla en el proceso
        """
        try:
            with transaction.atomic():
                # 1. Crear el Tenant (Client)
                tenant = self._create_tenant(validated_data)
                
                # 2. Crear el Domain para el tenant
                domain = self._create_domain(tenant)
                
                # 3. Crear el User admin dentro del schema del tenant
                user = self._create_admin_user(tenant, validated_data)
                
                # 4. La suscripción se crea automáticamente via signal
                #    (billing.signals.create_free_subscription_for_new_tenant)
                subscription = self._get_subscription(tenant)

                # 5. Enviar email de verificación (fuera de la transacción)
                self._send_verification_email_later(user, tenant)

                logger.info(
                    f"Registro exitoso: tenant={tenant.schema_name}, "
                    f"user={user.username}, plan={subscription.plan.tier if subscription else 'N/A'} "
                    f"(pendiente verificacion email)"
                )

                return {
                    'tenant': tenant,
                    'domain': domain,
                    'user': user,
                    'subscription': subscription,
                    'requires_email_verification': True,
                }

        except Exception as e:
            logger.error(f"Error en registro: {str(e)}", exc_info=True)
            raise RegistrationError(str(e))

    def _send_verification_email_later(self, user, tenant):
        """Envía el email de verificación sin bloquear la transacción."""
        try:
            self.send_verification_email(user, tenant)
        except Exception as e:
            logger.warning(f"Fallo al enviar email de verificacion (no critico): {e}")
                
        except Exception as e:
            logger.error(f"Error en registro: {str(e)}", exc_info=True)
            raise RegistrationError(str(e))
    
    def _create_tenant(self, data: dict) -> Client:
        """Crear el tenant (Client) con schema aislado."""
        org_name = data['organization_name']
        
        # Generar schema_name seguro
        schema_name = re.sub(r'[^a-z0-9]', '_', org_name.lower())
        schema_name = re.sub(r'_+', '_', schema_name).strip('_')
        if not schema_name.startswith('tenant_'):
            schema_name = f'tenant_{schema_name}'
        
        # Asegurar unicidad
        base_schema = schema_name
        counter = 1
        while Client.objects.filter(schema_name=schema_name).exists():
            schema_name = f"{base_schema}_{counter}"
            counter += 1
        
        tenant = Client(
            schema_name=schema_name,
            name=org_name,
            paid_until=date.today() + timedelta(days=14),  # Trial 14 días
            on_trial=True,
        )
        tenant.save()  # Esto crea el schema en PostgreSQL
        
        logger.info(f"Tenant creado: {schema_name} ({org_name})")
        return tenant
    
    def _create_domain(self, tenant: Client) -> Domain:
        """Crear el domain (subdominio) para el tenant."""
        # Generar subdominio basado en schema
        subdomain = tenant.schema_name.replace('tenant_', '')
        
        # Determinar el dominio base según el entorno
        if settings.DEBUG:
            base_domain = 'localhost'
            domain_str = f"{subdomain}.{base_domain}"
        else:
            base_domain = 'agrotechcolombia.com'
            domain_str = f"{subdomain}.{base_domain}"
        
        # Asegurar unicidad del dominio
        base_domain_str = domain_str
        counter = 1
        while Domain.objects.filter(domain=domain_str).exists():
            domain_str = f"{subdomain}{counter}.{base_domain}"
            counter += 1
        
        domain = Domain.objects.create(
            domain=domain_str,
            tenant=tenant,
            is_primary=True,
        )
        
        logger.info(f"Domain creado: {domain_str} -> {tenant.schema_name}")
        return domain
    
    def _create_admin_user(self, tenant: Client, data: dict) -> User:
        """Crear el usuario administrador."""
        from uuid import uuid4

        verification_required = (
            getattr(settings, 'ACCOUNT_EMAIL_VERIFICATION', 'optional') == 'mandatory'
        )

        user = User(
            username=data['username'],
            email=data['email'],
            name=data['name'],
            last_name=data['last_name'],
            phone=data.get('phone', ''),
            is_active=not verification_required,  # Activo solo si no requiere verificacion
            email_verified=False,
            verification_token=uuid4().hex,
            is_staff=True,
            role='admin',
            tenant=tenant,
        )
        user.set_password(data['password'])
        user.save()

        logger.info(
            f"Admin user creado: {user.email} → tenant: {tenant.schema_name} "
            f"(verificacion={'requerida' if verification_required else 'opcional'})"
        )
        return user

    def send_verification_email(self, user: User, tenant: Client):
        """Envía el email de verificación al nuevo usuario."""
        frontend_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        verify_url = f"{frontend_url}/api/auth/verify-email/?token={user.verification_token}"

        subject = f"[AgroTech] Verifica tu cuenta — {tenant.name}"
        message = (
            f"Hola {user.name},\n\n"
            f"¡Bienvenido a AgroTech Digital! Tu finca '{tenant.name}' está casi lista.\n\n"
            f"Para activar tu cuenta, verifica tu correo haciendo clic aquí:\n"
            f"{verify_url}\n\n"
            f"Si no creaste esta cuenta, ignora este mensaje.\n\n"
            f"AgroTech Digital — Agricultura de precisión al alcance de tu mano."
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@agrotechcolombia.com'),
                recipient_list=[user.email],
                fail_silently=True,
            )
            logger.info(f"Email de verificacion enviado a {user.email}")
        except Exception as e:
            logger.warning(f"No se pudo enviar email de verificacion a {user.email}: {e}")

    def _get_subscription(self, tenant: Client):
        """Obtener la suscripción creada automáticamente por el signal."""
        try:
            return tenant.subscription
        except Exception:
            logger.warning(
                f"No se encontró suscripción auto-creada para {tenant.schema_name}. "
                f"Verificar que el Plan 'free' existe en la BD."
            )
            return None


class RegistrationError(Exception):
    """Error durante el proceso de registro."""
    pass
