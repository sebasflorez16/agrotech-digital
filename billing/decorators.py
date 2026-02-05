"""
Decoradores para verificar límites específicos de recursos.

Uso en views:
    @check_hectare_limit
    def create_parcel(request):
        ...
"""

from functools import wraps
from django.http import JsonResponse
from .models import UsageMetrics
import logging

logger = logging.getLogger(__name__)


def check_hectare_limit(view_func):
    """
    Decorator para verificar límite de hectáreas antes de crear parcela.
    
    Uso:
        @check_hectare_limit
        def create_parcel(request):
            ...
    """
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        subscription = getattr(request, 'subscription', None)
        
        if not subscription:
            return JsonResponse({
                'error': 'No subscription found'
            }, status=402)
        
        # Calcular hectáreas actuales
        from parcels.models import Parcel
        from django.db.models import Sum
        
        current_ha = Parcel.objects.filter(
            is_deleted=False
        ).aggregate(
            total=Sum('area_hectares')
        )['total'] or 0
        
        # Obtener área de la nueva parcela del request
        if hasattr(request, 'data'):
            new_ha = float(request.data.get('area_hectares', 0))
        else:
            new_ha = float(request.POST.get('area_hectares', 0))
        
        total_ha = current_ha + new_ha
        
        # Verificar límite
        is_within, limit = subscription.check_limit('hectares', total_ha)
        
        if not is_within:
            return JsonResponse({
                'error': 'Límite de hectáreas excedido',
                'code': 'hectares_limit_exceeded',
                'current': float(current_ha),
                'new': float(new_ha),
                'total': float(total_ha),
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
    """
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        subscription = getattr(request, 'subscription', None)
        
        if not subscription:
            return JsonResponse({
                'error': 'No subscription found'
            }, status=402)
        
        # Obtener métricas del mes actual
        tenant = request.tenant if hasattr(request, 'tenant') else None
        if not tenant:
            # Fallback: continuar sin verificación
            logger.warning("No se pudo obtener tenant para verificar límite EOSDA")
            return view_func(request, *args, **kwargs)
        
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
        response = view_func(request, *args, **kwargs)
        
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
        subscription = getattr(request, 'subscription', None)
        
        if not subscription:
            return JsonResponse({
                'error': 'No subscription found'
            }, status=402)
        
        # Contar usuarios actuales del tenant
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        tenant = request.tenant if hasattr(request, 'tenant') else None
        if not tenant:
            return view_func(request, *args, **kwargs)
        
        current_users = User.objects.count()
        
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
