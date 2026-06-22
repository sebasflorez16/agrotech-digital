"""
Views de autenticación para AgroTech Digital SaaS.

Endpoints:
- POST /api/auth/register/          → Registro completo (User + Tenant + Subscription)
- POST /api/auth/login/             → Login con JWT (access + refresh tokens)
- GET  /api/auth/me/                → Datos del usuario autenticado
- POST /api/auth/logout/            → Cerrar sesión (invalida refresh token)
- POST /api/auth/password/change/   → Cambiar contraseña
- PATCH /api/auth/profile/          → Actualizar perfil del usuario
"""

import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle

from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer
from .services import RegistrationService, RegistrationError

User = get_user_model()
logger = logging.getLogger(__name__)


# ── Throttles personalizados ────────────────────────────────────────────────

class RegisterThrottle(AnonRateThrottle):
    """Limitar intentos de registro: 5 por hora por IP."""
    rate = '5/hour'


class LoginThrottle(AnonRateThrottle):
    """Limitar intentos de login: 10 por minuto por IP."""
    rate = '10/min'


# ── Views ────────────────────────────────────────────────────────────────────

class RegisterView(APIView):
    """
    Registro de nuevos usuarios SaaS.
    
    POST /api/auth/register/
    
    Body:
    {
        "email": "admin@finca.com",
        "username": "juanperez",
        "password": "MiPassword123!",
        "password_confirm": "MiPassword123!",
        "name": "Juan",
        "last_name": "Pérez",
        "phone": "+573001234567",
        "organization_name": "Finca El Roble",
        "plan_tier": "free"
    }
    
    Response 201:
    {
        "success": true,
        "message": "Cuenta creada exitosamente",
        "data": {
            "user": { ... },
            "tenant": { ... },
            "subscription": { ... },
            "tokens": { "access": "...", "refresh": "..." }
        }
    }
    """
    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Ejecutar registro atómico
            service = RegistrationService()
            result = service.register(serializer.validated_data)
            
            tenant = result['tenant']
            user = result['user']
            subscription = result.get('subscription')
            domain = result['domain']
            
            # Generar tokens JWT para auto-login
            refresh = RefreshToken.for_user(user)
            
            # Construir respuesta
            response_data = {
                'success': True,
                'message': 'Cuenta creada exitosamente. ¡Bienvenido a AgroTech Digital!',
                'data': {
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'name': user.name,
                        'last_name': user.last_name,
                        'role': user.role,
                    },
                    'tenant': {
                        'id': tenant.id,
                        'name': tenant.name,
                        'schema_name': tenant.schema_name,
                        'domain': domain.domain,
                        'on_trial': tenant.on_trial,
                        'paid_until': str(tenant.paid_until),
                    },
                    'subscription': {
                        'plan': subscription.plan.tier if subscription else 'free',
                        'plan_name': subscription.plan.name if subscription else 'Explorador',
                        'status': subscription.status if subscription else 'trialing',
                        'trial_end': subscription.trial_end.isoformat() if subscription and subscription.trial_end else None,
                        'current_period_end': subscription.current_period_end.isoformat() if subscription else None,
                    } if subscription else None,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    },
                }
            }
            
            logger.info(f"Registro exitoso: {user.username} -> {tenant.schema_name}")
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except RegistrationError as e:
            # Log detallado para administradores (sin exponer al usuario)
            logger.error(f"Error de registro: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': 'Error al crear la cuenta. Por favor intenta de nuevo.',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            logger.exception(f"Error inesperado en registro: {str(e)}")
            return Response({
                'success': False,
                'error': 'Error interno del servidor.',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(APIView):
    """
    Login con JWT.
    
    POST /api/auth/login/
    
    Body:
    {
        "username": "juanperez",   (o email)
        "password": "MiPassword123!"
    }
    
    Response 200:
    {
        "success": true,
        "tokens": { "access": "...", "refresh": "..." },
        "user": { ... }
    }
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]
    
    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        
        if not username or not password:
            return Response({
                'success': False,
                'error': 'Se requieren usuario/email y contraseña.',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Permitir login con email o username
        user = authenticate(username=username, password=password)
        
        # Si falla con username, intentar con email
        if user is None and '@' in username:
            try:
                user_obj = User.objects.get(email__iexact=username)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user is None:
            # Log con hash para no exponer emails en logs
            import hashlib
            username_hash = hashlib.sha256(username.encode()).hexdigest()[:16]
            ip = request.META.get('REMOTE_ADDR', 'unknown')
            logger.warning(f"Intento de login fallido desde IP: {ip} (hash: {username_hash})")
            return Response({
                'success': False,
                'error': 'Credenciales inválidas.',
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                'success': False,
                'error': 'Esta cuenta está desactivada.',
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generar tokens con tenant_id en el payload (sin fallback: si no existe, no se incluye)
        refresh = RefreshToken.for_user(user)
        if hasattr(user, 'tenant_id') and user.tenant_id:
            refresh['tenant_id'] = user.tenant_id
            refresh.access_token['tenant_id'] = user.tenant_id
        
        logger.info(f"Login exitoso: {user.username} (tenant_id={getattr(user, 'tenant_id', 'N/A')})")
        
        return Response({
            'success': True,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'name': user.name,
                'last_name': user.last_name,
                'role': user.role,
                'is_superuser': user.is_superuser,
            },
        })


class MeView(APIView):
    """
    Obtener datos del usuario autenticado y su suscripción.
    
    GET /api/auth/me/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        tenant = getattr(request, 'tenant', None)
        
        data = {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'name': user.name,
                'last_name': user.last_name,
                'phone': user.phone,
                'role': user.role,
                'image': user.image.url if user.image else None,
            },
        }
        
        # Agregar info del tenant si existe
        if tenant and tenant.schema_name != 'public':
            data['tenant'] = {
                'id': tenant.id,
                'name': tenant.name,
                'schema_name': tenant.schema_name,
                'on_trial': tenant.on_trial,
                'paid_until': str(tenant.paid_until),
            }
            
            # Agregar info de suscripción
            try:
                sub = tenant.subscription
                data['subscription'] = {
                    'plan': sub.plan.tier,
                    'plan_name': sub.plan.name,
                    'status': sub.status,
                    'trial_end': sub.trial_end.isoformat() if sub.trial_end else None,
                    'current_period_end': sub.current_period_end.isoformat(),
                    'days_until_renewal': sub.days_until_renewal(),
                    'is_active': sub.is_active_or_trialing(),
                }
            except Exception:
                data['subscription'] = None
        
        return Response(data)


# ── Logout ────────────────────────────────────────────────────────────────────

class LogoutView(APIView):
    """
    Cerrar sesion: invalida refresh token y access token JWT.

    POST /api/auth/logout/

    Body:
    {
        "refresh": "<refresh_token>"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        errors = []
        
        # 1. Invalidar refresh token
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info(f"Refresh token invalidado para {request.user.username}")
            except Exception as e:
                logger.error(f"Error invalidando refresh token: {e}")
                errors.append('refresh_invalidation_failed')
        
        # 2. Invalidar access token actual
        try:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                access_token_str = auth_header.split(' ')[1]
                from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
                outstanding = OutstandingToken.objects.filter(
                    token=access_token_str
                ).first()
                if outstanding:
                    BlacklistedToken.objects.get_or_create(token=outstanding)
                    logger.info(f"Access token invalidado para {request.user.username}")
        except Exception as e:
            logger.error(f"Error invalidando access token: {e}")
            errors.append('access_invalidation_failed')
        
        if errors:
            return Response({
                'success': True,
                'message': 'Sesion cerrada parcialmente.',
                'warnings': errors,
            }, status=status.HTTP_200_OK)
        
        return Response(
            {'success': True, 'message': 'Sesion cerrada correctamente'},
            status=status.HTTP_200_OK
        )


# ── Cambio de contraseña ───────────────────────────────────────────────────────

class PasswordChangeThrottle(AnonRateThrottle):
    """Maximo 5 cambios de password por hora por usuario."""
    rate = '5/hour'
    
    def get_cache_key(self, request, view):
        return f"password_change_{request.user.id}"


class PasswordChangeView(APIView):
    """
    Cambiar la contrasena del usuario autenticado.

    POST /api/auth/password/change/

    Body:
    {
        "current_password": "...",
        "new_password": "...",
        "confirm_password": "..."
    }
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [PasswordChangeThrottle]

    def post(self, request):
        user = request.user
        current_password = request.data.get('current_password', '').strip()
        new_password = request.data.get('new_password', '').strip()
        confirm_password = request.data.get('confirm_password', '').strip()

        if not current_password or not new_password or not confirm_password:
            return Response(
                {'error': 'Todos los campos son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(current_password):
            return Response(
                {'error': 'La contraseña actual es incorrecta'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_password:
            return Response(
                {'error': 'La nueva contraseña y su confirmación no coinciden'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 8:
            return Response(
                {'error': 'La nueva contraseña debe tener al menos 8 caracteres'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password == current_password:
            return Response(
                {'error': 'La nueva contraseña debe ser diferente a la actual'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()
        logger.info(f"Contraseña cambiada para usuario: {user.username}")

        # Generar nuevos tokens para que el usuario no pierda la sesión
        refresh = RefreshToken.for_user(user)
        return Response({
            'success': True,
            'message': 'Contraseña actualizada correctamente',
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
        })


# ── Actualizar perfil ─────────────────────────────────────────────────────────

class DeveloperModeActivateView(APIView):
    """
    Activar modo desarrollador para el usuario autenticado.
    Solo disponible si el usuario es superusuario.
    
    POST /api/auth/devmode/activate/
    
    Body:
    {
        "pin": "dev2026agro"
    }
    
    Response 200:
    {
        "success": true,
        "dev_mode": true,
        "message": "🔓 Modo desarrollador activado."
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # Solo superusuarios pueden activar dev mode
        if not user.is_superuser:
            logger.warning(f"DevMode: acceso denegado para {user.username} (no superuser)")
            return Response({
                'success': False,
                'error': 'Acceso denegado. Solo administradores del sistema.',
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Validar PIN
        pin = request.data.get('pin', '').strip()
        expected_pin = getattr(settings, 'DEVELOPER_PIN', '')
        
        if not expected_pin:
            return Response({
                'success': False,
                'error': 'DEVELOPER_PIN no está configurado en el servidor.',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if pin != expected_pin:
            logger.warning(f"DevMode: PIN inválido para {user.username}")
            return Response({
                'success': False,
                'error': 'PIN de desarrollador incorrecto.',
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Guardar flag en caché para que middleware/decorators la detecten
        from config.devmode import set_dev_mode
        set_dev_mode(user.id, True)
        
        logger.info(f"🔓 DevMode activado para superuser: {user.username}")
        
        return Response({
            'success': True,
            'dev_mode': True,
            'message': '🔓 Modo desarrollador activado. Sin límites de suscripción.',
            'user': {
                'id': user.id,
                'username': user.username,
                'is_superuser': user.is_superuser,
            }
        })


class DeveloperModeDeactivateView(APIView):
    """
    Desactivar modo desarrollador.
    
    POST /api/auth/devmode/deactivate/
    
    Response 200:
    {
        "success": true,
        "dev_mode": false,
        "message": "🔒 Modo desarrollador desactivado."
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if not user.is_superuser:
            return Response({
                'success': False,
                'error': 'Acceso denegado.',
            }, status=status.HTTP_403_FORBIDDEN)
        
        from config.devmode import set_dev_mode
        set_dev_mode(user.id, False)
        
        logger.info(f"🔒 DevMode desactivado para superuser: {user.username}")
        
        return Response({
            'success': True,
            'dev_mode': False,
            'message': '🔒 Modo desarrollador desactivado. Límites de suscripción restaurados.',
        })


class DeveloperModeStatusView(APIView):
    """
    Consultar estado del modo desarrollador.
    
    GET /api/auth/devmode/status/
    
    Response 200:
    {
        "dev_mode": true,
        "user": "admin",
        "is_superuser": true
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from config.devmode import is_dev_mode_active
        dev_mode = is_dev_mode_active(request)
        
        return Response({
            'dev_mode': dev_mode,
            'user': request.user.username if dev_mode else None,
            'is_superuser': request.user.is_superuser,
        })


class ProfileUpdateView(APIView):
    """
    Actualizar el perfil del usuario autenticado.

    PATCH /api/auth/profile/

    Body (todos los campos son opcionales):
    {
        "name": "...",
        "last_name": "...",
        "phone": "...",
        "address": "...",
        "job_title": "...",
        "description": "..."
    }
    """
    permission_classes = [IsAuthenticated]
    UPDATABLE_FIELDS = ['name', 'last_name', 'phone', 'address', 'job_title', 'description']

    def patch(self, request):
        user = request.user
        updated_fields = []

        for field in self.UPDATABLE_FIELDS:
            if field in request.data:
                value = request.data[field]
                setattr(user, field, value)
                updated_fields.append(field)

        if not updated_fields:
            return Response(
                {'error': 'No se proporcionaron campos para actualizar'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.save(update_fields=updated_fields)
        logger.info(f"Perfil actualizado para usuario: {user.username} — campos: {updated_fields}")

        return Response({
            'success': True,
            'message': f'Perfil actualizado correctamente',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'name': user.name,
                'last_name': user.last_name,
                'phone': user.phone,
                'job_title': user.job_title,
                'description': user.description,
            },
        })