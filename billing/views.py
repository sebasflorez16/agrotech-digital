"""
Views y API endpoints para billing y suscripciones.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import timedelta
from .models import Plan, Subscription, Invoice, UsageMetrics, BillingEvent
from .gateways import PaymentGatewayFactory, get_gateway_for_user
from .tenant_service import TenantService
from .serializers import (
    PlanSerializer, SubscriptionSerializer, InvoiceSerializer,
    UsageMetricsSerializer, CreateSubscriptionSerializer
)
import mercadopago
import json
import logging

logger = logging.getLogger(__name__)


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
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return Subscription.objects.filter(tenant=tenant)
        return Subscription.objects.none()
    
    def list(self, request, *args, **kwargs):
        """Obtener suscripción actual del tenant."""
        tenant = getattr(request, 'tenant', None)
        
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
        serializer = CreateSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        plan_tier = serializer.validated_data['plan_tier']
        billing_cycle = serializer.validated_data.get('billing_cycle', 'monthly')
        payment_method_token = serializer.validated_data.get('payment_method_token')
        
        try:
            plan = Plan.objects.get(tier=plan_tier, is_active=True)
        except Plan.DoesNotExist:
            return Response({
                'error': 'Plan no encontrado'
            }, status=404)
        
        # Obtener gateway apropiado para el usuario
        gateway = get_gateway_for_user(request.user)
        
        # Crear suscripción en la pasarela
        result = gateway.create_subscription(
            user=request.user,
            plan=plan,
            payment_method_token=payment_method_token
        )
        
        if not result['success']:
            return Response({
                'error': result.get('error', 'Error creating subscription')
            }, status=400)
        
        # Crear suscripción en BD
        tenant = getattr(request, 'tenant', None)
        
        now = timezone.now()
        period_days = 30 if billing_cycle == 'monthly' else 365
        
        subscription = Subscription.objects.create(
            tenant=tenant,
            plan=plan,
            payment_gateway=gateway.__class__.__name__.replace('Gateway', '').lower(),
            external_subscription_id=result.get('subscription_id'),
            status='pending',  # Se actualizará con webhook
            billing_cycle=billing_cycle,
            current_period_start=now,
            current_period_end=now + timedelta(days=period_days),
        )
        
        # Registrar evento
        BillingEvent.objects.create(
            tenant=tenant,
            subscription=subscription,
            event_type='subscription.created',
            event_data={
                'plan': plan.tier,
                'billing_cycle': billing_cycle,
                'gateway': subscription.payment_gateway
            }
        )
        
        logger.info(f"Suscripción creada para tenant {tenant.schema_name}: {subscription.id}")
        
        return Response({
            'success': True,
            'subscription': SubscriptionSerializer(subscription).data,
            'checkout_url': result.get('checkout_url') or result.get('init_point'),
            'message': 'Suscripción creada exitosamente'
        }, status=status.HTTP_201_CREATED)
    
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
        tenant = getattr(request, 'tenant', None)
        
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
        tenant = getattr(request, 'tenant', None)
        new_plan_tier = request.data.get('new_plan_tier')
        
        if not new_plan_tier:
            return Response({
                'error': 'new_plan_tier es requerido'
            }, status=400)
        
        try:
            subscription = tenant.subscription
            new_plan = Plan.objects.get(tier=new_plan_tier, is_active=True)
        except Subscription.DoesNotExist:
            return Response({'error': 'No subscription found'}, status=404)
        except Plan.DoesNotExist:
            return Response({'error': 'Plan no encontrado'}, status=404)
        
        # Validar que sea upgrade
        tier_order = ['free', 'basic', 'pro', 'enterprise']
        current_tier_idx = tier_order.index(subscription.plan.tier)
        new_tier_idx = tier_order.index(new_plan.tier)
        
        if new_tier_idx <= current_tier_idx:
            return Response({
                'error': 'Usa el endpoint de downgrade para reducir tu plan'
            }, status=400)
        
        # Calcular prorrateo (simplificado - TODO: implementar lógica completa)
        old_plan = subscription.plan
        subscription.plan = new_plan
        subscription.save()
        
        # Registrar evento
        BillingEvent.objects.create(
            tenant=tenant,
            subscription=subscription,
            event_type='plan.upgraded',
            event_data={
                'from_plan': old_plan.tier,
                'to_plan': new_plan.tier,
            }
        )
        
        logger.info(f"Plan mejorado de {old_plan.tier} a {new_plan.tier} para tenant {tenant.schema_name}")
        
        return Response({
            'success': True,
            'subscription': SubscriptionSerializer(subscription).data,
            'message': f'Plan mejorado exitosamente a {new_plan.name}'
        })


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
        tenant = getattr(self.request, 'tenant', None)
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
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return UsageMetrics.objects.filter(tenant=tenant)
        return UsageMetrics.objects.none()
    
    def list(self, request, *args, **kwargs):
        """Obtener métricas del mes actual."""
        tenant = getattr(request, 'tenant', None)
        
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
        tenant = getattr(request, 'tenant', None)
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
        
        # Hectáreas
        total_ha = Parcel.objects.filter(
            is_deleted=False
        ).aggregate(total=Sum('area_hectares'))['total'] or 0
        
        metrics.hectares_used = total_ha
        
        # Usuarios
        metrics.users_count = User.objects.count()
        
        # Parcelas
        metrics.parcels_count = Parcel.objects.filter(is_deleted=False).count()
        
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
                    "message": "Has excedido el límite de requests EOSDA en 5 requests"
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
    tenant = getattr(request, 'tenant', None)
    
    if not tenant:
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
    
    # Obtener métricas actuales
    now = timezone.now()
    metrics, created = UsageMetrics.objects.get_or_create(
        tenant=tenant,
        year=now.year,
        month=now.month
    )
    
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
        
        if limit == 0:
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
            'limit': limit if limit > 0 else 'unlimited',
            'percentage': percentage,
            'status': status
        }
        
        # Agregar overage si aplica
        if used > limit > 0:
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
            'eosda_requests': 'requests EOSDA',
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
    tenant = getattr(request, 'tenant', None)
    
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
    tenant = getattr(request, 'tenant', None)
    
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
    
    # Calcular líneas de la factura
    line_items = []
    
    # Línea base del plan
    base_amount = float(plan.price_cop)
    line_items.append({
        'description': f"{plan.name} - Suscripción mensual",
        'quantity': 1,
        'unit_price': base_amount,
        'total': base_amount
    })
    
    subtotal = base_amount
    
    # Líneas de overages
    if metrics.eosda_requests_overage > 0:
        overage_cost = metrics.eosda_requests_overage * 500  # 500 COP por request
        line_items.append({
            'description': f"Requests EOSDA adicionales ({metrics.eosda_requests_overage} requests)",
            'quantity': metrics.eosda_requests_overage,
            'unit_price': 500,
            'total': overage_cost
        })
        subtotal += overage_cost
    
    # Calcular IVA (19% en Colombia)
    tax_rate = 0.19
    tax_amount = subtotal * tax_rate
    total = subtotal + tax_amount
    
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
                'limit': plan.get_limit('eosda_requests', 0),
                'overage': metrics.eosda_requests_overage
            },
            'parcels': {
                'used': metrics.parcels_count,
                'limit': plan.get_limit('parcels', 0)
            },
            'hectares': {
                'used': round(metrics.hectares_used, 2),
                'limit': plan.get_limit('hectares', 0)
            },
            'users': {
                'used': metrics.users_count,
                'limit': plan.get_limit('users', 0)
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
    tenant = getattr(request, 'tenant', None)
    
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
def create_checkout_view(request):
    """
    Crear sesión de checkout y redirigir a MercadoPago.
    
    POST /billing/api/create-checkout/
    Body: {"plan_tier": "basic", "billing_cycle": "monthly", "payer_email": "...", "tenant_name": "..."}
    
    Flujo:
    1. Recibe datos del plan y email
    2. Crea preapproval en MercadoPago
    3. Devuelve checkout_url para redirigir al usuario
    4. Cuando MercadoPago confirma pago → webhook crea el tenant automáticamente
    """
    try:
        data = json.loads(request.body)
        plan_tier = data.get('plan_tier')
        billing_cycle = data.get('billing_cycle', 'monthly')
        tenant_name = data.get('tenant_name', '')
        username = data.get('username', '')
        password = data.get('password', '')
        
        if not plan_tier:
            return JsonResponse({'error': 'plan_tier is required'}, status=400)
        
        # Obtener el plan
        try:
            plan = Plan.objects.get(tier=plan_tier, is_active=True)
        except Plan.DoesNotExist:
            return JsonResponse({'error': 'Plan no encontrado'}, status=404)
        
        # Plan gratuito: crear tenant + usuario directamente sin pasar por MercadoPago
        if plan_tier == 'free':
            payer_email = data.get('payer_email', '')
            if not tenant_name:
                tenant_name = payer_email.split('@')[0] if payer_email else 'finca_nueva'
            
            # Generar username si no se proporcionó
            if not username:
                username = payer_email.split('@')[0].replace('.', '_').replace('-', '_') if payer_email else 'admin'
            
            result = TenantService.create_tenant_for_subscription(
                tenant_name=tenant_name,
                plan_tier='free',
                payer_email=payer_email,
                payment_gateway='manual',
                username=username,
                password=password or None,
                user_name=data.get('user_name', ''),
                user_last_name=data.get('user_last_name', ''),
            )
            
            if result['success']:
                response_data = {
                    'success': True,
                    'plan': 'free',
                    'tenant_created': True,
                    'schema_name': result['schema_name'],
                    'domain': result['domain'],
                    'username': result.get('username', username),
                    'message': 'Trial gratuito activado. Tu finca está lista.',
                }
                # Incluir tokens JWT para auto-login
                if result.get('tokens'):
                    response_data['tokens'] = result['tokens']
                return JsonResponse(response_data)
            else:
                return JsonResponse({'error': result.get('error', 'Error creando tenant')}, status=500)
        
        # Calcular precio para planes pagos
        if billing_cycle == 'yearly':
            price = float(plan.price_cop) * 12 * 0.8  # 20% descuento
            frequency = 12
            frequency_type = 'months'
        else:
            price = float(plan.price_cop)
            frequency = 1
            frequency_type = 'months'
        
        # Obtener email del payer
        payer_email = data.get('payer_email', '')
        if not payer_email and request.user.is_authenticated:
            payer_email = request.user.email
        if not payer_email:
            return JsonResponse({'error': 'Se requiere un email para continuar'}, status=400)
        
        # Nombre del tenant (para crear después del pago)
        if not tenant_name:
            tenant_name = payer_email.split('@')[0]
        
        # Crear suscripción en MercadoPago
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        
        # URL base para callbacks
        site_url = getattr(settings, 'SITE_URL', 'https://agrotech-digital-production.up.railway.app')
        if 'localhost' in site_url or '127.0.0.1' in site_url:
            site_url = 'https://agrotech-digital-production.up.railway.app'
        
        # Frontend URL para redirección después del pago
        frontend_url = getattr(
            settings, 'FRONTEND_URL',
            'https://frontend-cliente-agrotech.netlify.app'
        )
        
        # external_reference incluye toda la info necesaria para crear el tenant
        # Codificar username para poder crear el usuario al confirmar pago
        ext_username = username or payer_email.split('@')[0].replace('.', '_').replace('-', '_')
        external_ref = f"plan_{plan_tier}_{billing_cycle}__email_{payer_email}__tenant_{tenant_name}__user_{ext_username}"
        
        preapproval_data = {
            'reason': f'AgroTech Digital - {plan.name}',
            'auto_recurring': {
                'frequency': frequency,
                'frequency_type': frequency_type,
                'transaction_amount': int(price),
                'currency_id': 'COP'
            },
            'back_url': f'{frontend_url}/templates/billing/success.html?plan={plan_tier}&cycle={billing_cycle}',
            'payer_email': payer_email,
            'external_reference': external_ref,
        }
        
        result = sdk.preapproval().create(preapproval_data)
        
        if result['status'] == 201:
            checkout_url = result['response'].get('init_point')
            preapproval_id = result['response'].get('id')
            
            logger.info(f"Checkout creado: {preapproval_id} para plan {plan_tier} email={payer_email}")
            
            return JsonResponse({
                'success': True,
                'checkout_url': checkout_url,
                'preapproval_id': preapproval_id,
            })
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
def confirm_payment_create_tenant(request):
    """
    Confirmar pago exitoso y crear tenant automáticamente.
    
    POST /billing/api/confirm-payment/
    Body: {
        "preapproval_id": "...",
        "plan_tier": "basic",
        "billing_cycle": "monthly",
        "payer_email": "user@example.com",
        "tenant_name": "Mi Finca"   (opcional)
    }
    
    Flujo:
    1. Verifica con MercadoPago que el preapproval esté authorized/pending
    2. Crea tenant + schema + dominio + suscripción
    3. Devuelve datos del tenant creado
    
    SEGURIDAD: Verificación doble — solo crea si MercadoPago confirma.
    Idempotente — si el tenant ya existe para ese preapproval_id, devuelve ok.
    """
    try:
        data = json.loads(request.body)
        preapproval_id = data.get('preapproval_id', '')
        plan_tier = data.get('plan_tier', 'basic')
        billing_cycle = data.get('billing_cycle', 'monthly')
        payer_email = data.get('payer_email', '')
        tenant_name = data.get('tenant_name', '')
        
        if not payer_email:
            return JsonResponse({'error': 'payer_email requerido'}, status=400)
        
        # Idempotencia: si ya existe una suscripción con ese preapproval_id, retornar ok
        if preapproval_id:
            existing = Subscription.objects.filter(
                external_subscription_id=preapproval_id
            ).select_related('tenant').first()
            
            if existing:
                return JsonResponse({
                    'success': True,
                    'already_exists': True,
                    'tenant_name': existing.tenant.name,
                    'schema_name': existing.tenant.schema_name,
                    'plan': existing.plan.tier,
                    'status': existing.status,
                })
        
        # Verificar con MercadoPago (si hay preapproval_id)
        mp_verified = False
        if preapproval_id:
            try:
                sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
                result = sdk.preapproval().get(preapproval_id)
                if result['status'] == 200:
                    mp_status = result['response'].get('status', '')
                    if mp_status in ['authorized', 'pending']:
                        mp_verified = True
                        logger.info(f"MercadoPago verificado: {preapproval_id} status={mp_status}")
                    else:
                        logger.warning(f"MercadoPago status inesperado: {mp_status} para {preapproval_id}")
            except Exception as e:
                logger.warning(f"No se pudo verificar con MercadoPago: {e}")
        
        # Generar nombre del tenant si no se proporcionó
        if not tenant_name:
            tenant_name = payer_email.split('@')[0].replace('.', '_').replace('-', '_')
        
        # Extraer username del request o del external_reference
        username = data.get('username', '')
        password = data.get('password', '')
        
        if not username:
            username = payer_email.split('@')[0].replace('.', '_').replace('-', '_')
        
        # Crear tenant + usuario con el servicio
        result = TenantService.create_tenant_for_subscription(
            tenant_name=tenant_name,
            plan_tier=plan_tier,
            billing_cycle=billing_cycle,
            payer_email=payer_email,
            external_subscription_id=preapproval_id,
            payment_gateway='mercadopago' if preapproval_id else 'manual',
            username=username,
            password=password or None,  # None = auto-generate + email
            user_name=data.get('user_name', ''),
            user_last_name=data.get('user_last_name', ''),
        )
        
        if result['success']:
            logger.info(
                f"✅ Tenant creado post-pago: {tenant_name} plan={plan_tier} "
                f"mp_verified={mp_verified} preapproval={preapproval_id}"
            )
            response_data = {
                'success': True,
                'tenant_name': result['tenant'].name,
                'schema_name': result['schema_name'],
                'domain': result['domain'],
                'plan': plan_tier,
                'status': result['status'],
                'paid_until': result['paid_until'],
                'mp_verified': mp_verified,
                'username': result.get('username', username),
            }
            # Incluir tokens JWT para auto-login
            if result.get('tokens'):
                response_data['tokens'] = result['tokens']
            return JsonResponse(response_data)
        else:
            return JsonResponse({
                'error': result.get('error', 'Error creando tenant')
            }, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.exception(f"Error en confirm_payment_create_tenant: {e}")
        return JsonResponse({'error': str(e)}, status=500)
