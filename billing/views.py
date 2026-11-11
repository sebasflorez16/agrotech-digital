"""
Views y API endpoints para billing y suscripciones.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import AnonRateThrottle
from django.utils import timezone
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.cache import cache
from datetime import timedelta
from functools import wraps
from .models import Plan, Subscription, Invoice, UsageMetrics, BillingEvent
from .gateways import PaymentGatewayFactory, get_gateway_for_user
from .tenant_service import TenantService
from .payment_utils import (
    build_wompi_reference,
    get_checkout_intent,
    normalize_cycle,
    parse_mercadopago_reference,
    parse_wompi_reference,
    plan_amount_cents,
    sanitize_external_reference_part,
    save_checkout_intent,
)
from .serializers import (
    PlanSerializer, SubscriptionSerializer, InvoiceSerializer,
    UsageMetricsSerializer, CreateSubscriptionSerializer
)
import mercadopago
import json
import logging
from .access import is_unlimited_user

logger = logging.getLogger(__name__)


class CheckoutRateThrottle(AnonRateThrottle):
    """
    Rate limiting para endpoints de checkout y confirmación de pago.
    Límite: 10 intentos por hora por IP.
    Previene abuso de la API de MercadoPago y creación masiva de tenants.
    """
    rate = '10/hour'
    scope = 'checkout'


def _tenant_from_jwt_header(request):
    """Resuelve el tenant desde el header Authorization (JWT).

    Las rutas de billing corren en schema public y varias son vistas Django
    planas (no DRF), así que `request.user` puede ser anónimo aunque el
    frontend envíe un Bearer token. Sin esta resolución, un cliente existente
    que intente mejorar su plan se trataría como tenant_id=0 y podría generar
    un tenant duplicado.
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return None
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        from django.db import connection
        from base_agrotech.models import Client

        token = AccessToken(auth_header.split(' ', 1)[1])
        tenant_id = token.get('tenant_id')
        if not tenant_id:
            return None
        connection.set_schema_to_public()
        tenant = Client.objects.filter(id=tenant_id).first()
        if tenant and tenant.schema_name != 'public':
            return tenant
    except Exception as exc:
        logger.debug(f"_tenant_from_jwt_header: no se pudo resolver tenant: {exc}")
    return None


def resolve_tenant_for_request(request):
    """
    Resuelve el tenant para un request autenticado de forma segura.
    
    1. Intenta desde request.user.tenant_id → busca Client con raw SQL en public
    2. Intenta desde el JWT del header Authorization (vistas Django planas)
    3. Fallback a request.tenant (resuelto por middleware)
    4. Retorna None si no se encuentra
    
    NOTA: No usar getattr(request.user, 'tenant', None) directamente
    porque Django ForeignKey lanza DoesNotExist si el Client no se
    encuentra en el search_path del schema actual (ej: schema 'prueba'
    no tiene la tabla django_tenants_client).
    """
    # 1. Intentar desde el FK del user
    if hasattr(request, 'user') and request.user.is_authenticated:
        tenant_id = getattr(request.user, 'tenant_id', None)
        if tenant_id:
            try:
                from base_agrotech.models import Client
                # Usar query directa al schema public para evitar
                # problemas con el search_path del tenant actual
                tenant = Client.objects.using('default').raw(
                    'SELECT * FROM public.base_agrotech_client WHERE id = %s',
                    [tenant_id]
                )
                tenant_list = list(tenant)
                if tenant_list:
                    return tenant_list[0]
            except Exception as exc:
                logger.debug(f"resolve_tenant_for_request: raw query failed: {exc}")
                # Fallback: intentar con ORM normal por si funciona
                try:
                    return Client.objects.get(id=tenant_id)
                except Exception:
                    pass

    # 2. JWT del header (billing corre en public y puede ser vista plana)
    tenant = _tenant_from_jwt_header(request)
    if tenant:
        return tenant
    
    # 3. Fallback a request.tenant (resuelto por SmartTenantMiddleware)
    tenant = getattr(request, 'tenant', None)
    if tenant and tenant.schema_name != 'public':
        return tenant
    
    return None


def rate_limit(scope, limit=10, window=3600):
    """Rate limit simple por IP para vistas Django planas.

    El decorador `@throttle_classes` de DRF no se ejecuta en funciones Django
    normales, por lo que esos endpoints quedaban sin protección real.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            ip = (
                request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                or request.META.get('REMOTE_ADDR', 'unknown')
            )
            key = f"rate_limit:{scope}:{ip}"
            try:
                current = int(cache.get(key, 0) or 0)
                if current >= limit:
                    return JsonResponse({
                        'error': 'Demasiados intentos. Espera unos minutos e intenta de nuevo.',
                        'code': 'rate_limited',
                    }, status=429)
                cache.set(key, current + 1, window)
            except Exception:
                # Si la caché falla, no bloquear el checkout.
                pass
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar planes disponibles.
    
    Endpoints:
    - GET /api/billing/plans/ - Listar todos los planes activos
    - GET /api/billing/plans/{tier}/ - Detalle de un plan específico
    """
    
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]  # Los planes son públicos
    lookup_field = 'tier'
    
    def get_queryset(self):
        """Ordenar planes por sort_order."""
        return Plan.objects.filter(is_active=True).order_by('sort_order')
    
    @action(detail=True, methods=['get'])
    def pricing(self, request, tier=None):
        """
        Obtener pricing detallado de un plan incluyendo descuentos anuales.
        
        GET /api/billing/plans/{tier}/pricing/
        """
        plan = self.get_object()
        
        yearly_discount = plan.get_yearly_discount()
        
        return Response({
            'plan': PlanSerializer(plan).data,
            'monthly': {
                'cop': float(plan.price_cop),
                'usd': float(plan.price_usd),
                'frequency': 'monthly'
            },
            'yearly': {
                'cop': float(yearly_discount['yearly_price_cop']),
                'usd': float(yearly_discount['yearly_price_usd']),
                'savings_cop': float(yearly_discount['savings_cop']),
                'savings_usd': float(yearly_discount['savings_usd']),
                'discount_percent': yearly_discount['discount_percent'],
                'frequency': 'yearly'
            }
        })


class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar suscripciones.
    
    Endpoints:
    - GET /api/billing/subscription/ - Obtener suscripción actual
    - POST /api/billing/subscription/create/ - Crear nueva suscripción
    - POST /api/billing/subscription/cancel/ - Cancelar suscripción
    - POST /api/billing/subscription/upgrade/ - Mejorar plan
    """
    
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Solo la suscripción del tenant actual."""
        tenant = resolve_tenant_for_request(self.request)
        if tenant:
            return Subscription.objects.filter(tenant=tenant)
        return Subscription.objects.none()
    
    def list(self, request, *args, **kwargs):
        """Obtener suscripción actual del tenant."""
        tenant = resolve_tenant_for_request(request)
        
        if not tenant:
            return Response({
                'error': 'No tenant found'
            }, status=400)
        
        try:
            subscription = tenant.subscription
            serializer = self.get_serializer(subscription)
            
            # Agregar información adicional
            data = serializer.data
            data['days_until_renewal'] = subscription.days_until_renewal()
            data['is_trial_expired'] = subscription.is_trial_expired()
            
            return Response(data)
        
        except Subscription.DoesNotExist:
            return Response({
                'error': 'No subscription found',
                'message': 'Este tenant no tiene suscripción activa'
            }, status=404)
    
    @action(detail=False, methods=['post'])
    def create_subscription(self, request):
        """
        Crear nueva suscripción.
        
        POST /api/billing/subscription/create/
        Body:
            {
                "plan_tier": "basic",
                "billing_cycle": "monthly",
                "payment_method_token": "tok_xxx" (opcional)
            }
        """
        # La creación de suscripciones SIEMPRE debe pasar por el checkout
        # verificado de la pasarela. Este endpoint permitía crear una
        # suscripción sin pago y con estado inválido ('pending').
        plan_tier = (request.data.get('plan_tier') or '').strip()
        billing_cycle = normalize_cycle(request.data.get('billing_cycle'))
        if not plan_tier:
            return Response({'error': 'plan_tier es requerido'}, status=400)
        if not Plan.objects.filter(tier=plan_tier, is_active=True).exists():
            return Response({'error': 'Plan no encontrado'}, status=404)
        return Response({
            'error': 'Usa el checkout para activar o cambiar de plan.',
            'code': 'use_checkout',
            'checkout_url': f'/billing/checkout/{plan_tier}/?cycle={billing_cycle}',
        }, status=402)
    
    @action(detail=False, methods=['post'])
    def cancel_subscription(self, request):
        """
        Cancelar suscripción actual.
        
        POST /api/billing/subscription/cancel/
        Body:
            {
                "immediately": false,  # true para cancelar inmediatamente
                "reason": "Ya no necesito el servicio"  # opcional
            }
        """
        tenant = resolve_tenant_for_request(request)
        if not tenant:
            return Response({'error': 'No tenant found'}, status=400)
        
        try:
            subscription = tenant.subscription
        except Subscription.DoesNotExist:
            return Response({
                'error': 'No subscription found'
            }, status=404)
        
        immediately = request.data.get('immediately', False)
        reason = request.data.get('reason')
        
        # Cancelar en la pasarela
        if subscription.external_subscription_id:
            gateway = PaymentGatewayFactory.create(subscription.payment_gateway)
            gateway_result = gateway.cancel_subscription(subscription.external_subscription_id)
            
            if not gateway_result.get('success'):
                logger.warning(
                    f"Error cancelando suscripción en {subscription.payment_gateway}: "
                    f"{gateway_result.get('error')}"
                )
        
        # Cancelar en BD
        subscription.cancel(immediately=immediately, reason=reason)
        
        message = (
            'Suscripción cancelada inmediatamente' 
            if immediately 
            else f'Suscripción se cancelará el {subscription.current_period_end.strftime("%d/%m/%Y")}'
        )
        
        return Response({
            'success': True,
            'subscription': SubscriptionSerializer(subscription).data,
            'message': message
        })
    
    @action(detail=False, methods=['post'])
    def upgrade(self, request):
        """
        Mejorar plan de suscripción.
        
        POST /api/billing/subscription/upgrade/
        Body:
            {
                "new_plan_tier": "pro"
            }
        """
        tenant = resolve_tenant_for_request(request)
        new_plan_tier = (request.data.get('new_plan_tier') or '').strip()
        billing_cycle = normalize_cycle(request.data.get('billing_cycle'))

        if not tenant:
            return Response({'error': 'No tenant found'}, status=400)
        if not new_plan_tier:
            return Response({'error': 'new_plan_tier es requerido'}, status=400)
        if not Plan.objects.filter(tier=new_plan_tier, is_active=True).exists():
            return Response({'error': 'Plan no encontrado'}, status=404)

        # Un upgrade NUNCA puede ser gratis. Se debe pagar por el checkout
        # verificado de la pasarela; el webhook aplica el cambio.
        return Response({
            'error': 'Para cambiar de plan debes completar el pago.',
            'code': 'payment_required',
            'checkout_url': f'/billing/checkout/{new_plan_tier}/?cycle={billing_cycle}',
        }, status=402)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar facturas.
    
    Endpoints:
    - GET /api/billing/invoices/ - Listar facturas del tenant
    - GET /api/billing/invoices/{id}/ - Detalle de factura
    """
    
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Solo facturas del tenant actual."""
        tenant = resolve_tenant_for_request(self.request)
        if tenant:
            return Invoice.objects.filter(tenant=tenant)
        return Invoice.objects.none()


class UsageMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar métricas de uso.
    
    Endpoints:
    - GET /api/billing/usage/ - Métricas actuales
    - GET /api/billing/usage/history/ - Histórico de métricas
    """
    
    serializer_class = UsageMetricsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Solo métricas del tenant actual."""
        tenant = resolve_tenant_for_request(self.request)
        if tenant:
            return UsageMetrics.objects.filter(tenant=tenant)
        return UsageMetrics.objects.none()
    
    def list(self, request, *args, **kwargs):
        """Obtener métricas del mes actual."""
        tenant = resolve_tenant_for_request(request)
        
        if not tenant:
            return Response({'error': 'No tenant found'}, status=400)
        
        # Métricas del mes actual
        metrics = UsageMetrics.get_or_create_current(tenant)
        
        # Actualizar métricas en tiempo real
        self._update_current_metrics(tenant, metrics)
        
        serializer = self.get_serializer(metrics)
        data = serializer.data
        
        # Agregar información del plan y límites
        try:
            subscription = tenant.subscription
            data['plan'] = {
                'name': subscription.plan.name,
                'tier': subscription.plan.tier,
                'limits': subscription.plan.limits
            }
            
            # Calcular porcentajes de uso
            data['usage_percentages'] = {
                'hectares': self._calculate_percentage(
                    metrics.hectares_used,
                    subscription.plan.get_limit('hectares')
                ),
                'eosda_requests': self._calculate_percentage(
                    metrics.eosda_requests,
                    subscription.plan.get_limit('eosda_requests')
                ),
                'users': self._calculate_percentage(
                    metrics.users_count,
                    subscription.plan.get_limit('users')
                ),
            }
        except Subscription.DoesNotExist:
            pass
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """
        Obtener histórico de métricas.
        
        GET /api/billing/usage/history/?months=6
        """
        tenant = resolve_tenant_for_request(request)
        if not tenant:
            return Response({'error': 'No tenant found'}, status=400)
        months = int(request.query_params.get('months', 6))
        
        metrics = UsageMetrics.objects.filter(
            tenant=tenant
        ).order_by('-year', '-month')[:months]
        
        serializer = self.get_serializer(metrics, many=True)
        
        return Response(serializer.data)
    
    def _update_current_metrics(self, tenant, metrics):
        """Actualizar métricas con datos actuales."""
        from parcels.models import Parcel
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Hectáreas y parcelas (Parcel es app de tenant → requiere schema_context)
        from django_tenants.utils import schema_context

        total_ha = 0
        with schema_context(tenant.schema_name):
            for parcel in Parcel.objects.filter(is_deleted=False):
                total_ha += parcel.area_hectares() or 0
            parcels_count = Parcel.objects.filter(is_deleted=False).count()
        metrics.hectares_used = total_ha
        metrics.parcels_count = parcels_count

        # Usuarios (aislados por tenant; User es app compartida)
        metrics.users_count = User.objects.filter(is_active=True, tenant_id=tenant.id).count()

        metrics.save()
        metrics.calculate_overages()
    
    def _calculate_percentage(self, current, limit):
        """Calcular porcentaje de uso."""
        if limit == 'unlimited' or limit == 0:
            return 0
        
        try:
            limit_num = float(limit)
            current_num = float(current)
            return round((current_num / limit_num) * 100, 2)
        except (ValueError, ZeroDivisionError):
            return 0


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usage_dashboard_view(request):
    """
    Dashboard de métricas de uso para el cliente actual.
    
    GET /api/billing/usage/dashboard/
    
    Retorna:
        {
            "subscription": {
                "plan_name": "Plan Agricultor",
                "plan_tier": "basic",
                "status": "active",
                "billing_cycle": "monthly",
                "current_period_start": "2026-02-05",
                "current_period_end": "2026-03-05",
                "days_remaining": 28
            },
            "current_usage": {
                "period": "2026-02",
                "eosda_requests": {
                    "used": 105,
                    "limit": 100,
                    "percentage": 105.0,
                    "overage": 5,
                    "status": "exceeded"
                },
                "parcels": {
                    "used": 5,
                    "limit": 10,
                    "percentage": 50.0,
                    "status": "ok"
                },
                "hectares": {
                    "used": 120.5,
                    "limit": 300,
                    "percentage": 40.17,
                    "status": "ok"
                },
                "users": {
                    "used": 2,
                    "limit": 3,
                    "percentage": 66.67,
                    "status": "warning"
                }
            },
            "alerts": [
                {
                    "type": "error",
                    "resource": "eosda_requests",
                    "message": "Has excedido el límite de análisis satelitales en 5 análisis"
                },
                {
                    "type": "warning",
                    "resource": "users",
                    "message": "Estás usando el 66.67% de tus usuarios permitidos"
                }
            ],
            "billing_preview": {
                "base_cost": 79000,
                "overage_cost": 2500,
                "total_cost": 81500,
                "currency": "COP"
            }
        }
    """
    # Resolver tenant de forma segura (evita DoesNotExist en FK cross-schema)
    tenant = resolve_tenant_for_request(request)
    
    if not tenant or tenant.schema_name == 'public':
        return Response({
            'error': 'No tenant found',
            'message': 'Usuario no asociado a ningún tenant'
        }, status=400)
    
    try:
        subscription = tenant.subscription
    except Subscription.DoesNotExist:
        return Response({
            'error': 'No subscription found',
            'message': 'Este tenant no tiene suscripción activa'
        }, status=404)
    
    # Obtener metricas actuales
    now = timezone.now()
    metrics, created = UsageMetrics.objects.get_or_create(
        tenant=tenant,
        year=now.year,
        month=now.month
    )

    # Refrescar desde datos reales (parcelas, hectareas, usuarios)
    from parcels.models import Parcel
    from django.contrib.auth import get_user_model
    from django_tenants.utils import schema_context
    User = get_user_model()

    total_ha = 0
    with schema_context(tenant.schema_name):
        for parcel in Parcel.objects.filter(is_deleted=False):
            total_ha += parcel.area_hectares() or 0
        parcels_count = Parcel.objects.filter(is_deleted=False).count()
    metrics.hectares_used = total_ha
    metrics.parcels_count = parcels_count
    metrics.users_count = User.objects.filter(is_active=True, tenant_id=tenant.id).count()
    metrics.save()
    
    # Calcular overages
    metrics.calculate_overages()
    
    # Construir respuesta
    plan = subscription.plan
    
    # Información de suscripción
    subscription_data = {
        'plan_name': plan.name,
        'plan_tier': plan.tier,
        'status': subscription.status,
        'billing_cycle': subscription.billing_cycle,
        'current_period_start': subscription.current_period_start.strftime('%Y-%m-%d'),
        'current_period_end': subscription.current_period_end.strftime('%Y-%m-%d'),
        'days_remaining': subscription.days_until_renewal()
    }
    
    # Métricas de uso
    def get_resource_usage(used, limit_key, resource_name):
        """Helper para calcular métricas de un recurso."""
        limit = plan.get_limit(limit_key, 0)
        # Los planes "ilimitados" usan un sentinel grande (>= 9999). Tratarlo como ilimitado.
        is_unlimited = (limit is None) or (limit == 0) or (limit >= 9999)

        if is_unlimited:
            limit = 0
            percentage = 0
            status = 'unlimited'
        else:
            percentage = round((used / limit) * 100, 2) if limit > 0 else 0

            if percentage >= 100:
                status = 'exceeded'
            elif percentage >= 80:
                status = 'warning'
            else:
                status = 'ok'

        result = {
            'used': used,
            'limit': 'unlimited' if is_unlimited else limit,
            'percentage': percentage,
            'status': status
        }

        # Agregar overage si aplica
        if (not is_unlimited) and used > limit > 0:
            result['overage'] = used - limit

        return result
    
    current_usage = {
        'period': f"{now.year}-{now.month:02d}",
        'eosda_requests': get_resource_usage(
            metrics.eosda_requests, 
            'eosda_requests', 
            'Requests EOSDA'
        ),
        'parcels': get_resource_usage(
            metrics.parcels_count, 
            'parcels', 
            'Parcelas'
        ),
        'hectares': get_resource_usage(
            round(metrics.hectares_used, 2), 
            'hectares', 
            'Hectáreas'
        ),
        'users': get_resource_usage(
            metrics.users_count, 
            'users', 
            'Usuarios'
        )
    }
    
    # Generar alertas
    alerts = []
    
    for resource_key, resource_data in current_usage.items():
        if resource_key == 'period':
            continue
            
        status = resource_data['status']
        used = resource_data['used']
        limit = resource_data['limit']
        percentage = resource_data['percentage']
        
        resource_names = {
            'eosda_requests': 'análisis satelitales',
            'parcels': 'parcelas',
            'hectares': 'hectáreas',
            'users': 'usuarios'
        }
        
        resource_name = resource_names.get(resource_key, resource_key)
        
        if status == 'exceeded':
            overage = resource_data.get('overage', 0)
            alerts.append({
                'type': 'error',
                'resource': resource_key,
                'message': f"Has excedido el límite de {resource_name} en {overage} unidades"
            })
        elif status == 'warning':
            alerts.append({
                'type': 'warning',
                'resource': resource_key,
                'message': f"Estás usando el {percentage}% de tus {resource_name} permitidos"
            })
    
    # Preview de facturación
    base_cost = plan.price_cop
    overage_cost = 0
    
    # Calcular costo de overages (500 COP por request EOSDA extra)
    if metrics.eosda_requests_overage > 0:
        overage_cost = metrics.eosda_requests_overage * 500
    
    total_cost = base_cost + overage_cost
    
    billing_preview = {
        'base_cost': float(base_cost),
        'overage_cost': overage_cost,
        'total_cost': float(total_cost),
        'currency': 'COP',
        'overage_details': {
            'eosda_requests_extra': metrics.eosda_requests_overage,
            'cost_per_request': 500
        } if overage_cost > 0 else None
    }
    
    return Response({
        'subscription': subscription_data,
        'current_usage': current_usage,
        'alerts': alerts,
        'billing_preview': billing_preview
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usage_history_view(request):
    """
    Historial de métricas de uso por mes.
    
    GET /api/billing/usage/history/?months=6
    
    Retorna hasta 12 meses de historial.
    """
    tenant = resolve_tenant_for_request(request)
    
    if not tenant:
        return Response({
            'error': 'No tenant found'
        }, status=400)
    
    # Número de meses a retornar (máx 12)
    months = min(int(request.query_params.get('months', 6)), 12)
    
    # Obtener métricas históricas
    metrics_list = UsageMetrics.objects.filter(
        tenant=tenant
    ).order_by('-year', '-month')[:months]
    
    history = []
    for metrics in metrics_list:
        history.append({
            'period': f"{metrics.year}-{metrics.month:02d}",
            'eosda_requests': metrics.eosda_requests,
            'eosda_requests_overage': metrics.eosda_requests_overage,
            'parcels': metrics.parcels_count,
            'hectares': round(metrics.hectares_used, 2),
            'users': metrics.users_count
        })
    
    return Response({
        'tenant_name': tenant.name,
        'history': history
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_invoice_preview(request):
    """
    Preview de la factura del período actual.
    
    GET /api/billing/invoice/current/
    
    Retorna un preview de la factura que se generará al final del período,
    incluyendo el costo base del plan y los overages actuales.
    """
    tenant = resolve_tenant_for_request(request)
    
    if not tenant:
        return Response({
            'error': 'No tenant found'
        }, status=400)
    
    try:
        subscription = tenant.subscription
    except Subscription.DoesNotExist:
        return Response({
            'error': 'No subscription found'
        }, status=404)
    
    # Obtener métricas actuales
    now = timezone.now()
    metrics, created = UsageMetrics.objects.get_or_create(
        tenant=tenant,
        year=now.year,
        month=now.month
    )
    
    metrics.calculate_overages()
    
    plan = subscription.plan
    
    # Calcular líneas de la factura. Los precios del plan son IVA incluido,
    # por lo que se desglosa la base gravable y el impuesto sin sumar 19% extra.
    tax_rate = 0.19
    line_items = []

    is_yearly = subscription.billing_cycle == 'yearly'
    period_label = 'anual' if is_yearly else 'mensual'
    gross_base = float(
        plan.get_yearly_discount()['yearly_price_cop'] if is_yearly else plan.price_cop
    )
    base_amount = round(gross_base / (1 + tax_rate), 2)
    line_items.append({
        'description': f"{plan.name} - Suscripción {period_label}",
        'quantity': 1,
        'unit_price': base_amount,
        'total': base_amount
    })

    gross_total = gross_base

    # Líneas de overages (también IVA incluido)
    if metrics.eosda_requests_overage > 0:
        gross_overage = metrics.eosda_requests_overage * 500
        overage_net = round(gross_overage / (1 + tax_rate), 2)
        line_items.append({
            'description': f"Análisis satelitales adicionales ({metrics.eosda_requests_overage} análisis)",
            'quantity': metrics.eosda_requests_overage,
            'unit_price': round(overage_net / metrics.eosda_requests_overage, 2),
            'total': overage_net
        })
        gross_total += gross_overage

    subtotal = round(gross_total / (1 + tax_rate), 2)
    tax_amount = round(gross_total - subtotal, 2)
    total = round(gross_total, 2)
    
    # Construir response
    return Response({
        'tenant': tenant.name,
        'period': {
            'start': subscription.current_period_start.strftime('%Y-%m-%d'),
            'end': subscription.current_period_end.strftime('%Y-%m-%d'),
            'days_remaining': subscription.days_until_renewal()
        },
        'plan': {
            'name': plan.name,
            'tier': plan.tier
        },
        'usage_summary': {
            'eosda_requests': {
                'used': metrics.eosda_requests,
                'limit': 'unlimited' if is_unlimited_user(request.user) else plan.get_limit('eosda_requests', 0),
                'overage': metrics.eosda_requests_overage
            },
            'parcels': {
                'used': metrics.parcels_count,
                'limit': 'unlimited' if is_unlimited_user(request.user) else plan.get_limit('parcels', 0)
            },
            'hectares': {
                'used': round(metrics.hectares_used, 2),
                'limit': 'unlimited' if is_unlimited_user(request.user) else plan.get_limit('hectares', 0)
            },
            'users': {
                'used': metrics.users_count,
                'limit': 'unlimited' if is_unlimited_user(request.user) else plan.get_limit('users', 0)
            }
        },
        'invoice_preview': {
            'line_items': line_items,
            'subtotal': round(subtotal, 2),
            'tax_amount': round(tax_amount, 2),
            'tax_rate': tax_rate,
            'total': round(total, 2),
            'currency': 'COP',
            'status': 'preview',
            'notes': [
                'Esta es una previsualización',
                'La factura final se generará al fin del período',
                f"Fecha de generación estimada: {subscription.current_period_end.strftime('%d/%m/%Y')}"
            ]
        }
    })


# ==========================================
# CHECKOUT SUCCESS/CANCEL VIEWS
# ==========================================

@api_view(['GET'])
@permission_classes([AllowAny])
def checkout_success_view(request):
    """
    Página de éxito después de completar el checkout.
    
    GET /billing/success/?session_id=xxx
    
    Esta página se muestra después de que el usuario completa el pago
    en MercadoPago o Paddle. Los webhooks actualizarán la suscripción.
    """
    session_id = request.GET.get('session_id')
    collection_id = request.GET.get('collection_id')  # MercadoPago
    external_reference = request.GET.get('external_reference')  # MercadoPago
    
    logger.info(f"Checkout success: session={session_id}, collection={collection_id}, ref={external_reference}")
    
    return Response({
        'status': 'success',
        'message': '¡Pago procesado exitosamente!',
        'details': {
            'title': 'Bienvenido a AgroTech Digital',
            'description': 'Tu suscripción está siendo activada. En unos segundos tendrás acceso a todas las funcionalidades.',
            'next_steps': [
                'Revisa tu correo electrónico para la confirmación',
                'Tu suscripción estará activa en menos de 1 minuto',
                'Accede al dashboard para comenzar a usar la plataforma'
            ]
        },
        'redirect_url': '/dashboard/',
        'check_status_url': '/billing/api/status/'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def checkout_cancel_view(request):
    """
    Página de cancelación de checkout.
    
    GET /billing/cancel/
    
    Se muestra cuando el usuario cancela el proceso de pago.
    """
    reason = request.GET.get('reason', 'user_cancelled')
    
    return Response({
        'status': 'cancelled',
        'message': 'Proceso de pago cancelado',
        'reason': reason,
        'details': {
            'title': 'Pago no completado',
            'description': 'Has cancelado el proceso de pago. No se realizó ningún cargo.',
            'options': [
                'Puedes intentar nuevamente cuando quieras',
                'Tu plan actual permanece sin cambios',
                'Contacta soporte si tuviste algún problema'
            ]
        },
        'retry_url': '/pricing/',
        'support_url': '/support/'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_status_view(request):
    """
    Estado actual de la suscripción para polling desde el frontend.
    
    GET /billing/api/status/
    
    El frontend puede llamar a este endpoint periódicamente para verificar
    si la suscripción se activó después del checkout.
    """
    tenant = resolve_tenant_for_request(request)
    
    if not tenant:
        return Response({
            'error': 'No tenant found'
        }, status=400)
    
    try:
        subscription = tenant.subscription
        
        # Obtener métricas actuales
        metrics = UsageMetrics.get_or_create_current(tenant)
        
        return Response({
            'has_subscription': True,
            'status': subscription.status,
            'is_active': subscription.status in ['active', 'trialing'],
            'plan': {
                'name': subscription.plan.name,
                'tier': subscription.plan.tier,
                'price_cop': float(subscription.plan.price_cop),
                'price_usd': float(subscription.plan.price_usd)
            },
            'billing_cycle': subscription.billing_cycle,
            'current_period': {
                'start': subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                'end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                'days_remaining': subscription.days_until_renewal()
            },
            'trial': {
                'is_trial': subscription.status == 'trialing',
                'trial_end': subscription.trial_end.isoformat() if subscription.trial_end else None,
                'is_expired': subscription.is_trial_expired()
            },
            'limits': {
                'hectares': {
                    'used': round(metrics.hectares_used, 2),
                    'limit': subscription.plan.get_limit('hectares'),
                    'percentage': round((metrics.hectares_used / max(subscription.plan.get_limit('hectares') or 1, 1)) * 100, 1)
                },
                'eosda_requests': {
                    'used': metrics.eosda_requests,
                    'limit': subscription.plan.get_limit('eosda_requests'),
                    'percentage': round((metrics.eosda_requests / max(subscription.plan.get_limit('eosda_requests') or 1, 1)) * 100, 1)
                },
                'users': {
                    'used': metrics.users_count,
                    'limit': subscription.plan.get_limit('users'),
                    'percentage': round((metrics.users_count / max(subscription.plan.get_limit('users') or 1, 1)) * 100, 1)
                },
                'parcels': {
                    'used': metrics.parcels_count,
                    'limit': subscription.plan.get_limit('parcels'),
                    'percentage': round((metrics.parcels_count / max(subscription.plan.get_limit('parcels') or 1, 1)) * 100, 1)
                }
            },
            'payment_gateway': subscription.payment_gateway,
            'auto_renew': subscription.auto_renew,
            'cancel_at_period_end': subscription.cancel_at_period_end
        })
    
    except Subscription.DoesNotExist:
        return Response({
            'has_subscription': False,
            'status': 'none',
            'is_active': False,
            'message': 'No tienes una suscripción activa',
            'upgrade_url': '/pricing/'
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_subscription_view(request):
    """
    Vista "Mi Suscripción" con estructura plana para el frontend.

    GET /billing/api/my-subscription/
    """
    tenant = resolve_tenant_for_request(request)
    if not tenant:
        return Response({'error': 'No tenant found'}, status=400)

    try:
        subscription = tenant.subscription
    except Subscription.DoesNotExist:
        return Response({'has_subscription': False, 'plan_tier': 'free'}, status=200)

    plan = subscription.plan
    metrics = UsageMetrics.get_or_create_current(tenant)

    invoices = list(
        Invoice.objects.filter(tenant=tenant).order_by('-created_at')[:6]
        .values('created_at', 'total', 'status')
    )
    invoices_data = [
        {
            'date': inv['created_at'].date().isoformat() if inv['created_at'] else None,
            'amount': float(inv['total']),
            'status': inv['status'],
        }
        for inv in invoices
    ]

    from .access import is_unlimited_user
    unlimited = is_unlimited_user(request.user)
    limits = (
        {'hectares': 'unlimited', 'eosda_requests': 'unlimited',
         'users': 'unlimited', 'parcels': 'unlimited'}
        if unlimited else
        {'hectares': plan.get_limit('hectares'),
         'eosda_requests': plan.get_limit('eosda_requests'),
         'users': plan.get_limit('users'),
         'parcels': plan.get_limit('parcels')}
    )

    return Response({
        'has_subscription': True,
        'plan_tier': plan.tier,
        'plan_name': plan.name,
        'status': subscription.status,
        'billing_cycle': subscription.billing_cycle,
        'price_cop': float(plan.price_cop),
        'start_date': subscription.current_period_start.strftime('%Y-%m-%d') if subscription.current_period_start else None,
        'next_billing_date': subscription.current_period_end.strftime('%Y-%m-%d') if subscription.current_period_end else None,
        'days_until_renewal': subscription.days_until_renewal(),
        'subscription_id': subscription.external_subscription_id or str(subscription.uuid),
        'mp_preapproval_id': subscription.external_subscription_id,
        'auto_renew': subscription.auto_renew,
        'cancel_at_period_end': subscription.cancel_at_period_end,
        'unlimited': unlimited,
        'limits': limits,
        'usage': {
            'hectares': round(metrics.hectares_used, 2),
            'eosda_requests': metrics.eosda_requests,
            'users': metrics.users_count,
            'parcels': metrics.parcels_count,
        },
        'invoices': invoices_data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_my_subscription_view(request):
    """
    Cancela la suscripción actual del tenant.

    POST /billing/api/cancel-subscription/
    """
    tenant = resolve_tenant_for_request(request)
    if not tenant:
        return Response({'error': 'No tenant found'}, status=400)

    try:
        subscription = tenant.subscription
    except Subscription.DoesNotExist:
        return Response({'error': 'No subscription found'}, status=404)

    immediately = bool(request.data.get('immediately', False))
    reason = request.data.get('reason')

    try:
        if subscription.external_subscription_id:
            gateway = PaymentGatewayFactory.create(subscription.payment_gateway)
            gateway.cancel_subscription(subscription.external_subscription_id)
    except Exception as e:
        logger.warning(f"Error cancelando suscripción en pasarela: {e}")

    subscription.cancel(immediately=immediately, reason=reason)
    return Response({
        'success': True,
        'message': 'Suscripción cancelada.'
    })


# =============================================================================
# VISTAS DE PÁGINAS HTML
# =============================================================================

def pricing_page_view(request):
    """
    Página de planes y precios.
    
    GET /billing/planes/
    """
    return render(request, 'billing/pricing.html')


def checkout_page_view(request, plan_tier):
    """
    Página de checkout para un plan específico.
    
    GET /billing/checkout/<plan_tier>/
    """
    plan = get_object_or_404(Plan, tier=plan_tier, is_active=True)
    billing_cycle = request.GET.get('cycle', 'monthly')
    
    return render(request, 'billing/checkout.html', {
        'plan': plan,
        'billing_cycle': billing_cycle
    })


def success_page_view(request):
    """
    Página de éxito después del pago.
    
    GET /billing/success/
    """
    return render(request, 'billing/success.html')


def cancel_page_view(request):
    """
    Página de cancelación de pago.
    
    GET /billing/cancel/
    """
    return render(request, 'billing/cancel.html')


@login_required
def subscription_page_view(request):
    """
    Dashboard de suscripción del usuario.
    
    GET /billing/mi-suscripcion/
    """
    return render(request, 'billing/subscription.html')


@csrf_exempt
@require_http_methods(["POST"])
@rate_limit('checkout_create', 20, 3600)
def create_checkout_view(request):
    """
    Crear sesion de checkout y redirigir a la pasarela de pago.

    POST /billing/api/create-checkout/
    Body: {
        "plan_tier": "basic",
        "billing_cycle": "monthly",
        "payer_email": "...",
        "tenant_name": "...",
        "gateway": "mercadopago|wompi"  (opcional, default: mercadopago)
    }

    Flujo MercadoPago:
    1. Crea preapproval en MercadoPago
    2. Devuelve checkout_url para redirigir

    Flujo Wompi:
    1. Crea payment link en Wompi
    2. Devuelve checkout_url (hosted por Wompi)
    3. Wompi envia webhook al confirmar pago → activa suscripcion
    """
    try:
        data = json.loads(request.body)
        plan_tier = (data.get('plan_tier') or '').strip()
        gateway = (data.get('gateway') or 'mercadopago').strip().lower()
        billing_cycle = normalize_cycle(data.get('billing_cycle'))
        tenant_name = (data.get('tenant_name') or '').strip()
        username = (data.get('username') or '').strip()
        password = data.get('password', '')

        if gateway not in ('wompi', 'mercadopago'):
            return JsonResponse({'error': 'Pasarela no soportada'}, status=400)

        if not plan_tier:
            return JsonResponse({'error': 'plan_tier is required'}, status=400)

        try:
            plan = Plan.objects.get(tier=plan_tier, is_active=True)
        except Plan.DoesNotExist:
            return JsonResponse({'error': 'Plan no encontrado'}, status=404)

        payer_email = data.get('payer_email', '')
        if not payer_email and request.user.is_authenticated:
            payer_email = request.user.email
        if not payer_email:
            return JsonResponse({'error': 'Se requiere un email para continuar'}, status=400)

        if not tenant_name:
            tenant_name = payer_email.split('@')[0]

        if not username:
            username = payer_email.split('@')[0].replace('.', '_').replace('-', '_')

        # ── Plan gratuito ──────────────────────────────────────────
        if plan_tier == 'free':
            result = TenantService.create_tenant_for_subscription(
                tenant_name=tenant_name, plan_tier='free', payer_email=payer_email,
                payment_gateway='manual', username=username, password=password or None,
                user_name=data.get('user_name', ''), user_last_name=data.get('user_last_name', ''),
            )
            if result['success']:
                response_data = {
                    'success': True, 'plan': 'free', 'tenant_created': True,
                    'schema_name': result['schema_name'], 'domain': result['domain'],
                    'username': result.get('username', username),
                    'message': 'Cuenta creada. Revisa tu correo para verificarla.',
                    'requires_email_verification': result.get('requires_email_verification', False),
                }
                if result.get('tokens'):
                    response_data['tokens'] = result['tokens']
                return JsonResponse(response_data)
            else:
                error_status = 409 if result.get('existing_tenant') else 500
                return JsonResponse({'error': result.get('error', 'Error creando tenant')}, status=error_status)

        # ── WOMPI ──────────────────────────────────────────────────
        # Ya NO se generan Payment Links: no conservan nuestra `reference` y el
        # webhook no puede asociar el pago a la cuenta. Redirigimos al checkout
        # con Widget de Wompi (que envía reference + firma de integridad).
        if gateway == 'wompi':
            base = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
            base = base or request.build_absolute_uri('/').rstrip('/')
            return JsonResponse({
                'success': True,
                'gateway': 'wompi',
                'widget': True,
                'checkout_url': f"{base}/billing/checkout/{plan.tier}/?cycle={billing_cycle}",
            })

        # ── MERCADOPAGO (default) ──────────────────────────────────
        if billing_cycle == 'yearly':
            price = float(plan.get_yearly_discount()['yearly_price_cop'])
            frequency = 12
            frequency_type = 'months'
        else:
            price = float(plan.price_cop)
            frequency = 1
            frequency_type = 'months'

        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

        site_url = getattr(settings, 'SITE_URL', 'https://agrotech-digital-production.up.railway.app')
        if 'localhost' in site_url or '127.0.0.1' in site_url:
            site_url = 'https://agrotech-digital-production.up.railway.app'

        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://frontend-cliente-agrotech.netlify.app')
        ext_username = username or payer_email.split('@')[0].replace('.', '_').replace('-', '_')
        external_ref = (
            f"plan_{plan_tier}_{billing_cycle}"
            f"__email_{sanitize_external_reference_part(payer_email)}"
            f"__tenant_{sanitize_external_reference_part(tenant_name)}"
            f"__user_{sanitize_external_reference_part(ext_username)}"
        )

        preapproval_data = {
            'reason': f'AgroTech Digital - {plan.name}',
            'auto_recurring': {
                'frequency': frequency, 'frequency_type': frequency_type,
                'transaction_amount': int(price), 'currency_id': 'COP'
            },
            'back_url': f'{frontend_url}/templates/billing/success.html?plan={plan_tier}&cycle={billing_cycle}',
            'payer_email': payer_email,
            'external_reference': external_ref,
        }

        result = sdk.preapproval().create(preapproval_data)

        if result['status'] == 201:
            checkout_url = result['response'].get('init_point')
            preapproval_id = result['response'].get('id')
            save_checkout_intent(preapproval_id, {
                'gateway': 'mercadopago',
                'plan_tier': plan.tier,
                'billing_cycle': billing_cycle,
                'payer_email': payer_email,
                'tenant_name': tenant_name,
                'username': ext_username,
                'amount_cop': price,
                'external_reference': external_ref,
            })
            logger.info(f"Checkout creado: {preapproval_id} para plan {plan_tier}")
            return JsonResponse({'success': True, 'checkout_url': checkout_url, 'preapproval_id': preapproval_id})
        else:
            logger.error(f"Error creando checkout: {result}")
            return JsonResponse({
                'error': result.get('response', {}).get('message', 'Error creando checkout')
            }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.exception(f"Error en create_checkout: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@rate_limit('wompi_params', 20, 3600)
def wompi_checkout_params(request):
    """
    Devuelve los parámetros para abrir el Widget / Web Checkout de Wompi.

    La firma de integridad se genera SIEMPRE en el servidor (nunca exponer el
    secreto de integridad). Wompi exige un `reference` único por transacción y
    la firma SHA256(reference + amount_in_cents + currency + integrity_secret).

    POST /billing/api/wompi/checkout-params/
    Body: { plan_tier, billing_cycle, payer_email }
    """
    from .wompi_gateway import _integrity_signature

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    plan_tier = (data.get('plan_tier') or '').strip()
    billing_cycle = normalize_cycle(data.get('billing_cycle'))
    payer_email = (data.get('payer_email') or '').strip()

    if not plan_tier:
        return JsonResponse({'error': 'plan_tier is required'}, status=400)
    if plan_tier == 'free':
        return JsonResponse({'error': 'El plan gratuito no requiere pago.'}, status=400)

    # Si el cliente ya inició sesión, usar su email y su tenant (upgrade real).
    existing_tenant = resolve_tenant_for_request(request)
    if not payer_email and existing_tenant:
        if request.user.is_authenticated:
            payer_email = (request.user.email or '').strip()
        else:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            owner = User.objects.filter(tenant_id=existing_tenant.id).order_by('id').first()
            payer_email = (owner.email or '').strip() if owner else ''
    if not payer_email or '@' not in payer_email:
        return JsonResponse({'error': 'Se requiere un correo electrónico válido para continuar.'}, status=400)

    try:
        plan = Plan.objects.get(tier=plan_tier, is_active=True)
    except Plan.DoesNotExist:
        return JsonResponse({'error': 'Plan no encontrado'}, status=404)

    public_key = (getattr(settings, 'WOMPI_PUBLIC_KEY', '') or '').strip()
    integrity_key = (getattr(settings, 'WOMPI_INTEGRITY_KEY', '') or '').strip()
    if not public_key or not integrity_key:
        logger.error("[WOMPI] Faltan WOMPI_PUBLIC_KEY / WOMPI_INTEGRITY_KEY")
        return JsonResponse(
            {'error': 'La pasarela de pago no está configurada. Contacta a soporte.'},
            status=503,
        )

    amount_in_cents = plan_amount_cents(plan, billing_cycle)

    tenant_id = existing_tenant.id if existing_tenant else 0
    reference = build_wompi_reference(tenant_id, plan.tier, billing_cycle)

    base_url = (
        (getattr(settings, 'FRONTEND_URL', '') or '').rstrip('/')
        or (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
    )
    redirect_url = f"{base_url}/templates/billing/success.html?plan={plan.tier}&cycle={billing_cycle}&ref={reference}"

    signature = _integrity_signature(reference, amount_in_cents, 'COP')

    local = payer_email.split('@')[0]
    # La contraseña se guarda solo en caché de servidor y por 1 hora. Se usa
    # para que el webhook cree la cuenta con la clave elegida por el usuario
    # aunque la página de éxito no llegue a llamar a confirm-payment.
    checkout_password = (data.get('password') or '').strip()
    save_checkout_intent(reference, {
        'payer_email': payer_email,
        'tenant_id': tenant_id,
        'tenant_name': (data.get('tenant_name') or (existing_tenant.name if existing_tenant else local)).strip(),
        'username': (data.get('username') or local.replace('.', '_').replace('-', '_')).strip(),
        'password': checkout_password if len(checkout_password) >= 8 else '',
        'plan_tier': plan.tier,
        'billing_cycle': billing_cycle,
        'amount_in_cents': amount_in_cents,
        'currency': 'COP',
        'fbp': (data.get('fbp') or '').strip(),
        'fbc': (data.get('fbc') or '').strip(),
        'marketing_consent': bool(data.get('marketing_consent')),
    })

    logger.info(f"[WOMPI] Checkout params: plan={plan.tier} cycle={billing_cycle} ref={reference}")
    return JsonResponse({
        'success': True,
        'gateway': 'wompi',
        'public_key': public_key,
        'currency': 'COP',
        'amount_in_cents': amount_in_cents,
        'reference': reference,
        'signature_integrity': signature,
        'redirect_url': redirect_url,
        'customer_email': payer_email,
    })


@csrf_exempt
@require_http_methods(["POST"])
@rate_limit('confirm_payment', 30, 3600)
def confirm_payment_create_tenant(request):
    """Confirma un pago ya verificado y activa/crea el tenant.

    Regla de oro: el plan, el ciclo y el monto SIEMPRE se derivan de la
    pasarela o de la intención firmada en servidor; nunca del body. Esto evita
    pagar Básico y activar Pro, o pagar mensual y recibir anual.

    POST /billing/api/confirm-payment/
    """
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    gateway = (data.get('gateway') or 'mercadopago').strip().lower()
    if gateway not in ('wompi', 'mercadopago'):
        return JsonResponse({'error': 'Pasarela no soportada'}, status=400)

    preapproval_id = (data.get('preapproval_id') or '').strip()
    reference = (data.get('reference') or '').strip()
    body_plan = (data.get('plan_tier') or '').strip()
    body_cycle = normalize_cycle(data.get('billing_cycle'))
    payer_email = (data.get('payer_email') or '').strip()
    tenant_name = (data.get('tenant_name') or '').strip()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    existing_tenant = resolve_tenant_for_request(request)

    verified_plan_tier = ''
    verified_cycle = body_cycle
    verified_amount_cents = None
    verified_currency = 'COP'
    external_id = ''
    payment_verified = False

    # ── Verificación Wompi ──────────────────────────────────────────────────
    if gateway == 'wompi':
        if not reference:
            return JsonResponse({'error': 'Se requiere la referencia del pago.'}, status=402)
        from .wompi_gateway import WompiGateway

        check = WompiGateway().get_transaction_status(reference)
        if (
            not check.get('success')
            or check.get('status') != 'APPROVED'
            or (check.get('reference') and check.get('reference') != reference)
        ):
            logger.warning(
                f"[SECURITY] Wompi no aprobado: ref={reference} check={check} "
                f"ip={request.META.get('REMOTE_ADDR')}"
            )
            return JsonResponse(
                {'error': 'El pago no fue confirmado por Wompi.'},
                status=402,
            )

        parsed = parse_wompi_reference(reference)
        intent = get_checkout_intent(reference)
        verified_plan_tier = (
            intent.get('plan_tier') or parsed.get('plan_tier') or body_plan
        )
        verified_cycle = normalize_cycle(
            intent.get('billing_cycle') or parsed.get('cycle') or body_cycle
        )
        verified_amount_cents = check.get('amount_in_cents')
        verified_currency = (check.get('currency') or intent.get('currency') or 'COP')
        payer_email = (
            check.get('customer_email') or intent.get('payer_email') or payer_email
        )
        tenant_name = intent.get('tenant_name') or tenant_name
        username = intent.get('username') or username
        password = password or intent.get('password') or ''
        external_id = reference
        payment_verified = True

    # ── Verificación MercadoPago ────────────────────────────────────────────
    else:
        if not preapproval_id:
            return JsonResponse({'error': 'Se requiere el ID de preaprobación.'}, status=402)
        try:
            sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
            result = sdk.preapproval().get(preapproval_id)
        except Exception as exc:
            logger.warning(f"[SECURITY] No se pudo verificar MercadoPago {preapproval_id}: {exc}")
            return JsonResponse({'error': 'No se pudo verificar el pago.'}, status=402)

        if result.get('status') != 200:
            return JsonResponse({'error': 'No se pudo verificar el pago.'}, status=402)

        mp = result.get('response') or {}
        mp_status = (mp.get('status') or '').lower()
        if mp_status != 'authorized':
            # pending/failure: NUNCA otorgar acceso antes de autorización.
            logger.warning(
                f"[SECURITY] MercadoPago no autorizado: {preapproval_id} status={mp_status}"
            )
            return JsonResponse(
                {'error': 'El pago aún no está autorizado por MercadoPago.'},
                status=402,
            )

        parsed = parse_mercadopago_reference(mp.get('external_reference', ''))
        intent = get_checkout_intent(preapproval_id)
        verified_plan_tier = intent.get('plan_tier') or parsed.get('plan_tier') or body_plan
        verified_cycle = normalize_cycle(
            intent.get('billing_cycle') or parsed.get('cycle') or body_cycle
        )
        payer_email = (mp.get('payer_email') or intent.get('payer_email') or payer_email).strip()
        tenant_name = intent.get('tenant_name') or parsed.get('tenant_name') or tenant_name
        username = intent.get('username') or parsed.get('username') or username
        auto = mp.get('auto_recurring') or {}
        try:
            verified_amount_cents = int(round(float(auto.get('transaction_amount') or 0) * 100))
        except (TypeError, ValueError):
            verified_amount_cents = None
        verified_currency = (auto.get('currency_id') or 'COP').upper()
        external_id = preapproval_id
        payment_verified = True

    if not payment_verified:
        return JsonResponse({'error': 'Pago no verificado.'}, status=402)
    if not payer_email:
        return JsonResponse({'error': 'No se pudo obtener el email del pagador.'}, status=400)
    if verified_plan_tier == 'free':
        return JsonResponse(
            {'error': 'El plan gratuito se activa desde create-checkout, no desde confirm-payment.'},
            status=400,
        )

    try:
        plan = Plan.objects.get(tier=verified_plan_tier, is_active=True)
    except Plan.DoesNotExist:
        return JsonResponse({'error': 'El plan pagado no está disponible.'}, status=409)

    expected_cents = plan_amount_cents(plan, verified_cycle)
    if verified_amount_cents is not None and int(verified_amount_cents) != expected_cents:
        logger.error(
            f"[SECURITY] Monto no coincide: gateway={gateway} ref={external_id} "
            f"recibido={verified_amount_cents} esperado={expected_cents} "
            f"plan={verified_plan_tier} cycle={verified_cycle}"
        )
        return JsonResponse(
            {'error': 'El monto pagado no corresponde al plan seleccionado.'},
            status=402,
        )
    if verified_currency and verified_currency.upper() != 'COP':
        return JsonResponse({'error': 'La moneda del pago no es COP.'}, status=402)

    if body_plan and body_plan != verified_plan_tier:
        logger.warning(
            f"[SECURITY] El cliente intentó confirmar plan={body_plan} pero pagó "
            f"plan={verified_plan_tier} ref={external_id}. Se usa el plan pagado."
        )

    # ── Idempotencia ────────────────────────────────────────────────────────
    existing = Subscription.objects.filter(
        external_subscription_id=external_id
    ).select_related('tenant', 'plan').first()
    if existing:
        existing_amount = (
            plan_amount_cents(existing.plan, existing.billing_cycle) / 100
            if existing.plan_id else None
        )
        return JsonResponse({
            'success': True,
            'already_exists': True,
            'tenant_name': existing.tenant.name,
            'schema_name': existing.tenant.schema_name,
            'plan': existing.plan.tier if existing.plan_id else verified_plan_tier,
            'status': existing.status,
            'amount_cop': existing_amount,
            'payment_verified': True,
        })

    # ── Cliente existente: upgrade, no crear tenant duplicado ───────────────
    if existing_tenant:
        result = TenantService.upgrade_subscription(
            tenant=existing_tenant,
            new_plan_tier=verified_plan_tier,
            billing_cycle=verified_cycle,
            external_subscription_id=external_id,
            payment_gateway=gateway,
            payer_email=payer_email,
        )
        if not result.get('success'):
            return JsonResponse({'error': result.get('error', 'No se pudo aplicar el plan.')}, status=409)
        domain_obj = existing_tenant.domains.filter(is_primary=True).first() or existing_tenant.domains.first()
        return JsonResponse({
            'success': True,
            'already_exists': True,
            'tenant_name': existing_tenant.name,
            'schema_name': existing_tenant.schema_name,
            'domain': domain_obj.domain if domain_obj else '',
            'plan': verified_plan_tier,
            'status': 'active',
            'paid_until': result.get('paid_until'),
            'amount_cop': round(expected_cents / 100, 2),
            'gateway': gateway,
            'payment_verified': True,
            'username': username,
        })

    # Si el email ya pertenece a una cuenta, no crear un segundo tenant.
    from django.contrib.auth import get_user_model
    from base_agrotech.models import Client as TenantModel

    User = get_user_model()
    existing_user = User.objects.filter(
        email__iexact=payer_email,
        tenant_id__isnull=False,
    ).first()
    if existing_user:
        existing_account_tenant = TenantModel.objects.filter(id=existing_user.tenant_id).first()
        if existing_account_tenant:
            # El pago fue verificado con el email de una cuenta existente.
            # Aplicamos el plan a esa cuenta en lugar de dejar el pago sin
            # efecto o crear un tenant duplicado. El usuario entra con su
            # login habitual (no emitimos tokens desde aquí).
            result = TenantService.upgrade_subscription(
                tenant=existing_account_tenant,
                new_plan_tier=verified_plan_tier,
                billing_cycle=verified_cycle,
                external_subscription_id=external_id,
                payment_gateway=gateway,
                payer_email=payer_email,
            )
            if result.get('success'):
                domain_obj = (
                    existing_account_tenant.domains.filter(is_primary=True).first()
                    or existing_account_tenant.domains.first()
                )
                return JsonResponse({
                    'success': True,
                    'already_exists': True,
                    'requires_login': True,
                    'tenant_name': existing_account_tenant.name,
                    'schema_name': existing_account_tenant.schema_name,
                    'domain': domain_obj.domain if domain_obj else '',
                    'plan': verified_plan_tier,
                    'status': 'active',
                    'paid_until': result.get('paid_until'),
                    'amount_cop': round(expected_cents / 100, 2),
                    'gateway': gateway,
                    'payment_verified': True,
                    'username': existing_user.username,
                })
        return JsonResponse({
            'error': 'Este correo ya tiene una cuenta. Inicia sesión para ver tu plan.',
            'code': 'account_exists',
            'existing_tenant': existing_account_tenant.name if existing_account_tenant else '',
        }, status=409)

    if not tenant_name:
        tenant_name = payer_email.split('@')[0].replace('.', '_').replace('-', '_')
    if not username:
        username = payer_email.split('@')[0].replace('.', '_').replace('-', '_')

    result = TenantService.create_tenant_for_subscription(
        tenant_name=tenant_name,
        plan_tier=verified_plan_tier,
        billing_cycle=verified_cycle,
        payer_email=payer_email,
        external_subscription_id=external_id,
        payment_gateway=gateway,
        username=username,
        password=password or None,
        user_name=data.get('user_name', ''),
        user_last_name=data.get('user_last_name', ''),
    )

    if result['success']:
        logger.info(
            f"✅ Tenant creado post-pago: {tenant_name} plan={verified_plan_tier} "
            f"cycle={verified_cycle} gateway={gateway} external_id={external_id}"
        )
        response_data = {
            'success': True,
            'tenant_name': result['tenant'].name,
            'schema_name': result['schema_name'],
            'domain': result['domain'],
            'plan': verified_plan_tier,
            'status': result['status'],
            'paid_until': result['paid_until'],
            'amount_cop': round(expected_cents / 100, 2),
            'gateway': gateway,
            'payment_verified': True,
            'username': result.get('username', username),
        }
        if result.get('tokens'):
            response_data['tokens'] = result['tokens']
        return JsonResponse(response_data)

    error_status = 409 if result.get('existing_tenant') else 500
    return JsonResponse({
        'error': result.get('error', 'Error creando tenant'),
        'existing_tenant': result.get('existing_tenant', ''),
        'existing_schema': result.get('existing_schema', ''),
    }, status=error_status)


@csrf_exempt
@require_http_methods(["POST"])
def subscribe_with_card(request):
    """Suscripción con tarjeta tokenizada (pago recurrente automático 3RI).

    POST /billing/api/subscribe-card/
    Body: { "card_token", "plan_tier", "billing_cycle", "payer_email",
            "tenant_name", "username", "password", "user_name", "user_last_name" }

    Flujo:
      1. Tokeniza la tarjeta (fuente de pago con 3DS).
      2. Cobra el primer mes con la fuente (3RI).
      3. Crea tenant + usuario + suscripción.
      4. Guarda payment_source_id para que el cron cobre los siguientes meses.
    """
    # Endpoint heredado sin autenticación, sin idempotencia y con cobro
    # mensual que podía otorgar un año. Se desactiva hasta implementarlo con
    # un token de checkout firmado y verificación de monto.
    logger.warning(
        f"[SECURITY] subscribe-card bloqueado (endpoint heredado) "
        f"ip={request.META.get('REMOTE_ADDR')}"
    )
    return JsonResponse({
        'error': 'Este endpoint está deshabilitado. Usa el checkout de Wompi.',
        'code': 'endpoint_disabled',
    }, status=410)
