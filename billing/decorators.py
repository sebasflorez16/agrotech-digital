"""
Decoradores para verificar límites específicos de recursos.

Uso en views:
    @check_hectare_limit
    def create_parcel(request):
        ...
"""

from functools import wraps
from django.http import JsonResponse
from .models import UsageMetrics, Subscription
import logging

logger = logging.getLogger(__name__)


def _calculate_geom_area_hectares(geom_data):
    """
    Calcula el área en hectáreas de un polígono GeoJSON (fórmula Shoelace).
    Devuelve 0 si el GeoJSON es inválido o no está presente.
    """
    if not geom_data or not isinstance(geom_data, dict):
        return 0

    try:
        coordinates = geom_data.get('coordinates', [[]])
        if not coordinates or not isinstance(coordinates, list) or len(coordinates) == 0:
            return 0
        coords = coordinates[0] if isinstance(coordinates[0], list) else coordinates
        if not coords or len(coords) < 3:
            return 0

        area = 0.0
        for i in range(len(coords)):
            x1, y1 = coords[i]
            x2, y2 = coords[(i + 1) % len(coords)]
            area += x1 * y2 - x2 * y1
        area_m2 = abs(area) / 2.0 * 111320 * 111320
        return area_m2 / 10000.0
    except (TypeError, ValueError, IndexError):
        return 0


def check_hectare_limit(view_func):
    """
    Decorator para verificar límite de hectáreas antes de crear parcela.

    El área de la nueva parcela se calcula desde el GeoJSON del request
    (campo 'geom'), que es la fuente real de datos.

    Uso:
        @check_hectare_limit
        def create_parcel(request):
            ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from django.conf import settings

        # 🛡️ MODO DESARROLLADOR: superusuario + DEVELOPER_MODE + toggle activo = sin límites
        from config.devmode import is_dev_mode_active
        if is_dev_mode_active(request):
            logger.info(f"[check_hectare_limit] 🔓 DEVELOPER MODE: {request.user.username} sin límites de hectáreas")
            return view_func(request, *args, **kwargs)

        subscription = getattr(request, 'subscription', None)

        if not subscription:
            tenant = getattr(request, 'tenant', None)
            if tenant and tenant.schema_name != 'public':
                try:
                    subscription = tenant.subscription
                    request.subscription = subscription
                except Subscription.DoesNotExist:
                    subscription = None

        if not subscription:
            # En modo DEBUG, permitir continuar sin suscripción (desarrollo local)
            if getattr(settings, 'DEBUG', False):
                logger.warning("[check_hectare_limit] DEBUG MODE: Permitiendo acceso sin suscripción")
                return view_func(request, *args, **kwargs)

            return JsonResponse({
                'error': 'No subscription found'
            }, status=402)

        # Calcular hectáreas actuales del tenant (queryset scoped por schema)
        from parcels.models import Parcel

        current_ha = 0
        for parcel in Parcel.objects.filter(is_deleted=False):
            current_ha += parcel.area_hectares() or 0

        # Obtener área de la nueva parcela desde el GeoJSON real del request
        if hasattr(request, 'data'):
            geom_data = request.data.get('geom')
        else:
            geom_data = None
            if request.POST.get('geom'):
                import json
                try:
                    geom_data = json.loads(request.POST['geom'])
                except (ValueError, TypeError):
                    geom_data = None

        new_ha = _calculate_geom_area_hectares(geom_data)

        # Fallback: campo explícito de área si el cliente lo envía
        if new_ha == 0 and hasattr(request, 'data'):
            try:
                new_ha = float(request.data.get('area_hectares', 0))
            except (TypeError, ValueError):
                new_ha = 0

        total_ha = current_ha + new_ha

        # Verificar límite
        is_within, limit = subscription.check_limit('hectares', total_ha)

        if not is_within:
            return JsonResponse({
                'error': 'Límite de hectáreas excedido',
                'code': 'hectares_limit_exceeded',
                'current': round(float(current_ha), 2),
                'new': round(float(new_ha), 2),
                'total': round(float(total_ha), 2),
                'limit': limit,
                'plan': subscription.plan.name,
                'message': f'Tu plan {subscription.plan.name} permite hasta {limit} hectáreas. '
                           f'Actualmente tienes {current_ha:.2f} ha. '
                           f'Al agregar {new_ha:.2f} ha superarías el límite.',
                'suggestions': [
                    'Mejora a un plan superior',
                    'Elimina parcelas que ya no uses',
                    'Adquiere hectáreas adicionales'
                ],
                'upgrade_url': '/billing/upgrade/'
            }, status=403)  # Forbidden

        # Actualizar métricas
        try:
            tenant = request.tenant if hasattr(request, 'tenant') else None
            if tenant:
                metrics = UsageMetrics.get_or_create_current(tenant)
                metrics.hectares_used = total_ha
                metrics.save()
        except Exception as e:
            logger.warning(f"No se pudo actualizar métricas de hectáreas: {e}")

        return view_func(request, *args, **kwargs)

    return wrapper


def check_eosda_limit(view_func):
    """
    Decorator para rate limiting de peticiones EOSDA API.
    
    Uso:
        @check_eosda_limit
        def get_satellite_analysis(request, parcel_id):
            ...
    
    En modo DEBUG=True, permite continuar sin suscripción para desarrollo.
    """
    
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        from django.conf import settings
        
        # Soportar tanto vistas basadas en funciones como en clases
        # En FBV: args[0] es request
        # En CBV: args[0] es self, args[1] es request
        if len(args) >= 2 and hasattr(args[0], '__class__') and hasattr(args[1], 'META'):
            # Class-based view
            request = args[1]
        elif len(args) >= 1 and hasattr(args[0], 'META'):
            # Function-based view
            request = args[0]
        else:
            logger.error("[check_eosda_limit] No se pudo determinar el request")
            return JsonResponse({'error': 'Internal error'}, status=500)

        # 🛡️ MODO DESARROLLADOR: primer chequeo, antes de cualquier lógica de suscripción
        from config.devmode import is_dev_mode_active
        if is_dev_mode_active(request):
            logger.info(f"[check_eosda_limit] 🔓 DEVELOPER MODE: {request.user.username} sin límites EOSDA")
            return view_func(*args, **kwargs)
        
        # Intentar obtener subscription del request primero
        subscription = getattr(request, 'subscription', None)
        
        # Si no está en request, intentar obtenerla del tenant
        if not subscription:
            tenant = getattr(request, 'tenant', None)
            if tenant and tenant.schema_name != 'public':
                try:
                    subscription = tenant.subscription
                    # Guardarla en request para uso posterior
                    request.subscription = subscription
                except Subscription.DoesNotExist:
                    logger.warning(f"[check_eosda_limit] No subscription for tenant {tenant.schema_name}")
        
        if not subscription:
            # En modo DEBUG, permitir continuar sin suscripción (desarrollo local)
            if getattr(settings, 'DEBUG', False):
                logger.warning("[check_eosda_limit] DEBUG MODE: Permitiendo acceso sin suscripción")
                return view_func(*args, **kwargs)
            
            # En producción, devolver error más descriptivo
            return JsonResponse({
                'error': 'No subscription found',
                'code': 'no_subscription',
                'message': 'Este tenant no tiene una suscripción activa configurada. '
                           'Por favor configure una suscripción para acceder a las funciones satelitales.',
                'solution': 'Ejecute el comando: python manage.py setup_default_subscription'
            }, status=402)
        
        # Obtener métricas del mes actual
        tenant = request.tenant if hasattr(request, 'tenant') else None
        if not tenant:
            # Fallback: continuar sin verificación
            logger.warning("No se pudo obtener tenant para verificar límite EOSDA")
            return view_func(*args, **kwargs)
        
        metrics = UsageMetrics.get_or_create_current(tenant)
        
        # Verificar límite
        is_within, limit = subscription.check_limit(
            'eosda_requests',
            metrics.eosda_requests + 1  # +1 porque vamos a hacer una nueva request
        )
        
        if not is_within:
            # Calcular fecha de reset
            from django.utils import timezone
            now = timezone.now()
            next_month = now.replace(day=1) + timezone.timedelta(days=32)
            reset_date = next_month.replace(day=1)
            
            return JsonResponse({
                'error': 'Límite de análisis satelitales excedido',
                'code': 'eosda_limit_exceeded',
                'used': metrics.eosda_requests,
                'limit': limit,
                'plan': subscription.plan.name,
                'message': f'Has alcanzado el límite de {limit} análisis satelitales mensuales '
                           f'de tu plan {subscription.plan.name}.',
                'reset_date': reset_date.strftime('%Y-%m-%d'),
                'suggestions': [
                    'Mejora a un plan con más análisis incluidos',
                    'Adquiere paquetes adicionales de análisis',
                    f'Espera hasta el {reset_date.strftime("%d/%m/%Y")} para que se reinicie tu cuota'
                ],
                'upgrade_url': '/billing/upgrade/',
                'addon_url': '/billing/addons/extra-api-calls/'
            }, status=429)  # Too Many Requests
        
        # Incrementar contador DESPUÉS de ejecutar la vista exitosamente
        response = view_func(*args, **kwargs)
        
        # Solo incrementar si la request fue exitosa (2xx status code)
        if 200 <= response.status_code < 300:
            metrics.eosda_requests += 1
            metrics.save()
            
            # Calcular overages
            metrics.calculate_overages()
            
            logger.info(
                f"EOSDA request #{metrics.eosda_requests} "
                f"para tenant {tenant.schema_name} "
                f"(límite: {limit})"
            )
        
        return response
    
    return wrapper


def feature_required(feature_name):
    """
    Decorator para verificar que el plan incluya una feature específica.
    
    Uso:
        @feature_required('advanced_analytics')
        def get_advanced_report(request):
            ...
    """
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 🛡️ MODO DESARROLLADOR: bypass para superusuarios
            from config.devmode import is_dev_mode_active
            if is_dev_mode_active(request):
                logger.info(f"[feature_required] 🔓 DEVELOPER MODE: {request.user.username} — feature '{feature_name}' sin restricción")
                return view_func(request, *args, **kwargs)
            
            subscription = getattr(request, 'subscription', None)
            
            if not subscription:
                return JsonResponse({
                    'error': 'No subscription found'
                }, status=402)
            
            # Verificar si el plan incluye la feature
            features = subscription.plan.features_included
            
            if feature_name not in features:
                return JsonResponse({
                    'error': f'Feature "{feature_name}" no disponible en tu plan',
                    'code': 'feature_not_available',
                    'feature': feature_name,
                    'current_plan': subscription.plan.name,
                    'tier': subscription.plan.tier,
                    'message': f'La funcionalidad "{feature_name}" no está disponible en tu plan actual.',
                    'available_in_plans': _get_plans_with_feature(feature_name),
                    'upgrade_url': '/billing/upgrade/'
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def _get_plans_with_feature(feature_name):
    """
    Obtener lista de planes que incluyen una feature.
    
    Args:
        feature_name: Nombre de la feature
        
    Returns:
        Lista de nombres de planes
    """
    from .models import Plan
    
    plans = Plan.objects.filter(
        features_included__contains=[feature_name],
        is_active=True
    ).values_list('name', flat=True)
    
    return list(plans)


def require_feature(feature_name):
    """
    Decorator para verificar features por plan en métodos de APIView (CBV DRF).
    
    Uso:
        class CropHealthAPIView(APIView):
            @require_feature('continuous_monitoring')
            def get(self, request, parcel_id):
                ...
    
    A diferencia de @feature_required (pensado para FBV), este decorator
    recibe `self` como primer argumento y funciona con request.posicional.
    """
    from rest_framework.response import Response as DRFResponse

    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, request, *args, **kwargs):
            subscription = getattr(request, 'subscription', None)

            if not subscription:
                return DRFResponse({
                    'error': 'No tienes una suscripción activa',
                    'code': 'no_subscription',
                    'message': 'Debes tener un plan activo para acceder a esta función.',
                    'upgrade_url': '/billing/plans/'
                }, status=402)

            features = subscription.plan.features_included or []

            if feature_name not in features:
                return DRFResponse({
                    'error': f'Feature "{feature_name}" no disponible en tu plan',
                    'code': 'feature_not_available',
                    'feature': feature_name,
                    'current_plan': subscription.plan.name,
                    'tier': subscription.plan.tier,
                    'message': f'La funcionalidad "{feature_name}" está disponible en tu plan '
                               f'{_get_plans_with_feature_label(feature_name)}.',
                    'available_in_plans': _get_plans_with_feature(feature_name),
                    'upgrade_url': '/billing/upgrade/'
                }, status=403)

            return view_method(self, request, *args, **kwargs)

        return wrapper

    return decorator


def _get_plans_with_feature_label(feature_name):
    """Genera etiqueta legible de planes que incluyen una feature."""
    plans = _get_plans_with_feature(feature_name)
    if not plans:
        return "ningún plan disponible"
    if len(plans) == 1:
        return f"el plan {plans[0]}"
    return f"los planes {', '.join(plans[:-1])} y {plans[-1]}"


def users_limit_check(view_func):
    """
    Decorator para verificar límite de usuarios antes de crear uno nuevo.
    
    Uso:
        @users_limit_check
        def create_user(request):
            ...
    """
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 🛡️ MODO DESARROLLADOR: bypass para superusuarios
        from config.devmode import is_dev_mode_active
        if is_dev_mode_active(request):
            logger.info(f"[users_limit_check] 🔓 DEVELOPER MODE: {request.user.username} sin límite de usuarios")
            return view_func(request, *args, **kwargs)
        
        subscription = getattr(request, 'subscription', None)
        
        if not subscription:
            return JsonResponse({
                'error': 'No subscription found'
            }, status=402)
        
        # Contar usuarios actuales del tenant (solo los de su organización)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        tenant = request.tenant if hasattr(request, 'tenant') else None
        if not tenant:
            return view_func(request, *args, **kwargs)
        
        current_users = User.objects.filter(tenant=tenant).count()
        
        # Verificar límite
        is_within, limit = subscription.check_limit('users', current_users + 1)
        
        if not is_within:
            return JsonResponse({
                'error': 'Límite de usuarios excedido',
                'code': 'users_limit_exceeded',
                'current': current_users,
                'limit': limit,
                'plan': subscription.plan.name,
                'message': f'Tu plan {subscription.plan.name} permite hasta {limit} usuarios. '
                           f'Actualmente tienes {current_users}.',
                'upgrade_url': '/billing/upgrade/'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
