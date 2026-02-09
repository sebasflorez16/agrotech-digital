"""
Serializers para autenticación y registro.

Implementa validaciones estrictas de seguridad para el flujo de registro SaaS:
- Validación de email único
- Validación de nombre de organización (tenant)
- Sanitización de inputs
- Password strength validation
"""

import re
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from base_agrotech.models import Client, Domain

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """
    Serializer para registro de nuevos usuarios SaaS.
    
    Crea: User (admin del tenant) + Client (tenant) + Domain + Subscription (trial)
    
    Validaciones:
    - Email único en todo el sistema
    - Username único y seguro (alfanumérico + guiones)
    - Contraseña fuerte (Django validators)
    - Nombre de organización único (se convierte en schema)
    - Plan seleccionado debe existir y estar activo
    """
    
    # Datos del usuario
    email = serializers.EmailField(
        required=True,
        help_text='Email del administrador de la cuenta'
    )
    username = serializers.CharField(
        min_length=3,
        max_length=30,
        required=True,
        help_text='Nombre de usuario (alfanumérico, guiones y guiones bajos)'
    )
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        required=True,
        style={'input_type': 'password'},
        help_text='Contraseña (mín. 8 caracteres, debe incluir mayúsculas, números y especiales)'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='Confirmar contraseña'
    )
    
    # Datos personales
    name = serializers.CharField(
        max_length=100,
        required=True,
        help_text='Nombres del usuario'
    )
    last_name = serializers.CharField(
        max_length=100,
        required=True,
        help_text='Apellidos del usuario'
    )
    phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text='Teléfono de contacto'
    )
    
    # Datos de la organización (tenant)
    organization_name = serializers.CharField(
        min_length=3,
        max_length=80,
        required=True,
        help_text='Nombre de la finca, empresa u organización'
    )
    
    # Plan seleccionado
    plan_tier = serializers.CharField(
        required=False,
        default='free',
        help_text='Tier del plan: free, basic, pro, enterprise'
    )
    
    def validate_email(self, value):
        """Validar que el email sea único en todo el sistema."""
        email = value.lower().strip()
        
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                'Ya existe una cuenta con este correo electrónico.'
            )
        
        # Bloquear dominios de email temporales/desechables
        disposable_domains = [
            'tempmail.com', 'throwaway.com', 'guerrillamail.com',
            'mailinator.com', 'yopmail.com', 'sharklasers.com',
            'guerrillamail.info', 'grr.la', 'guerrillamail.biz',
            'guerrillamail.de', 'guerrillamail.net', 'guerrillamailblock.com',
            'trashmail.com', 'trashmail.me', 'trashmail.net',
            'dispostable.com', 'maildrop.cc', '10minutemail.com',
        ]
        domain = email.split('@')[1]
        if domain in disposable_domains:
            raise serializers.ValidationError(
                'No se permiten correos electrónicos temporales.'
            )
        
        return email
    
    def validate_username(self, value):
        """Validar username: alfanumérico + guiones, único."""
        username = value.lower().strip()
        
        # Solo alfanumérico, guiones y guiones bajos
        if not re.match(r'^[a-z0-9][a-z0-9_-]*[a-z0-9]$', username):
            raise serializers.ValidationError(
                'El nombre de usuario solo puede contener letras, números, '
                'guiones y guiones bajos. Debe empezar y terminar con alfanumérico.'
            )
        
        # Palabras reservadas
        reserved = [
            'admin', 'root', 'system', 'api', 'www', 'mail', 'ftp',
            'public', 'static', 'media', 'billing', 'support', 'help',
            'agrotech', 'agrotechdigital', 'test', 'demo', 'null',
            'undefined', 'localhost', 'health',
        ]
        if username in reserved:
            raise serializers.ValidationError(
                'Este nombre de usuario está reservado.'
            )
        
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError(
                'Este nombre de usuario ya está en uso.'
            )
        
        return username
    
    def validate_password(self, value):
        """Validar fortaleza de contraseña usando Django validators."""
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate_organization_name(self, value):
        """Validar nombre de organización y generar schema_name."""
        name = value.strip()
        
        if len(name) < 3:
            raise serializers.ValidationError(
                'El nombre de la organización debe tener al menos 3 caracteres.'
            )
        
        # Generar schema_name a partir del nombre
        schema_name = re.sub(r'[^a-z0-9]', '_', name.lower())
        schema_name = re.sub(r'_+', '_', schema_name).strip('_')
        
        # Prefijo para evitar conflictos con schemas internos de PostgreSQL
        if not schema_name.startswith('tenant_'):
            schema_name = f'tenant_{schema_name}'
        
        # Verificar que el schema no exista
        if Client.objects.filter(schema_name=schema_name).exists():
            raise serializers.ValidationError(
                'Ya existe una organización con un nombre similar. '
                'Por favor elige otro nombre.'
            )
        
        return name
    
    def validate_plan_tier(self, value):
        """Validar que el plan exista y esté activo."""
        from billing.models import Plan
        
        tier = value.lower().strip()
        valid_tiers = ['free', 'basic', 'pro', 'enterprise']
        
        if tier not in valid_tiers:
            raise serializers.ValidationError(
                f'Plan no válido. Opciones: {", ".join(valid_tiers)}'
            )
        
        if not Plan.objects.filter(tier=tier, is_active=True).exists():
            # Si el plan no existe, defaultear a free
            return 'free'
        
        return tier
    
    def validate(self, data):
        """Validaciones cruzadas."""
        # Confirmar contraseñas
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': 'Las contraseñas no coinciden.'
            })
        
        return data


class LoginResponseSerializer(serializers.Serializer):
    """Serializer para la respuesta de login."""
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = serializers.DictField()
    tenant = serializers.DictField()
    subscription = serializers.DictField()
