"""
Views de autenticación para AgroTech Digital SaaS.

Endpoints:
- POST /api/auth/register/  → Registro completo (User + Tenant + Subscription)
- POST /api/auth/login/     → Login con JWT (access + refresh tokens)
- POST /api/auth/me/        → Datos del usuario autenticado
"""

import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle

from django.contrib.auth import authenticate, get_user_model
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
            logger.error(f"Error de registro: {str(e)}")
            return Response({
                'success': False,
                'error': 'Error al crear la cuenta. Por favor intenta de nuevo.',
                'detail': str(e),
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
            logger.warning(f"Intento de login fallido para: {username}")
            return Response({
                'success': False,
                'error': 'Credenciales inválidas.',
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                'success': False,
                'error': 'Esta cuenta está desactivada.',
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generar tokens
        refresh = RefreshToken.for_user(user)
        
        logger.info(f"Login exitoso: {user.username}")
        
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