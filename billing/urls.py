"""
URLs para el app de billing.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, webhooks

# Router para viewsets
router = DefaultRouter()
router.register(r'plans', views.PlanViewSet, basename='plan')
router.register(r'subscription', views.SubscriptionViewSet, basename='subscription')
router.register(r'invoices', views.InvoiceViewSet, basename='invoice')
router.register(r'usage', views.UsageMetricsViewSet, basename='usage')

app_name = 'billing'

urlpatterns = [
    # ============== PÁGINAS HTML ==============
    # Página de planes/pricing
    path('planes/', views.pricing_page_view, name='pricing_page'),
    
    # Checkout
    path('checkout/<str:plan_tier>/', views.checkout_page_view, name='checkout_page'),
    
    # Resultado del pago
    path('success/', views.success_page_view, name='checkout_success'),
    path('cancel/', views.cancel_page_view, name='checkout_cancel'),
    
    # Dashboard de suscripción del usuario
    path('mi-suscripcion/', views.subscription_page_view, name='subscription_page'),
    
    # ============== API ENDPOINTS ==============
    path('api/', include(router.urls)),
    
    # Dashboard de métricas
    path('api/usage/dashboard/', views.usage_dashboard_view, name='usage_dashboard'),
    path('api/usage/history/', views.usage_history_view, name='usage_history'),
    path('api/invoice/current/', views.current_invoice_preview, name='current_invoice'),
    
    # Estado de suscripción para frontend
    path('api/status/', views.subscription_status_view, name='subscription_status'),
    
    # Crear checkout (redirige a MercadoPago)
    path('api/create-checkout/', views.create_checkout_view, name='create_checkout'),
    
    # Confirmar pago y crear tenant (llamado desde success page o webhook)
    path('api/confirm-payment/', views.confirm_payment_create_tenant, name='confirm_payment'),
    
    # ============== WEBHOOKS ==============
    path('webhooks/mercadopago/', webhooks.mercadopago_webhook, name='webhook_mercadopago'),
    path('webhooks/paddle/', webhooks.paddle_webhook, name='webhook_paddle'),
]
