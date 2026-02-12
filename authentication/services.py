"""
Servicio de registro SaaS para AgroTech Digital.

Maneja la creación atómica de:
1. Client (Tenant) - Schema de PostgreSQL aislado
2. Domain - Subdominio para el tenant
3. User (Admin) - Usuario administrador del tenant
4. Subscription - Suscripción trial automática (via signal)

Implementa transacciones atómicas para evitar datos huérfanos.
"""

import re
import logging
from datetime import date, timedelta

from django.db import transaction, connection
from django.conf import settings
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
                
                logger.info(
                    f"Registro exitoso: tenant={tenant.schema_name}, "
                    f"user={user.username}, plan={subscription.plan.tier if subscription else 'N/A'}"
                )
                
                return {
                    'tenant': tenant,
                    'domain': domain,
                    'user': user,
                    'subscription': subscription,
                }
                
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
        """Crear el usuario administrador y asignarlo al tenant."""
        # Users es shared_app, se crea en schema public
        # El campo user.tenant vincula al usuario con su organización
        user = User(
            username=data['username'],
            email=data['email'],
            name=data['name'],
            last_name=data['last_name'],
            phone=data.get('phone', ''),
            is_active=True,
            is_staff=True,  # Admin del tenant
            role='admin',
            tenant=tenant,  # Vincular usuario con su organización
        )
        user.set_password(data['password'])
        user.save()
        
        logger.info(f"Admin user creado: {user.email} → tenant: {tenant.schema_name}")
        return user
    
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
