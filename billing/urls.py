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
    # API endpoints
    path('api/', include(router.urls)),
    
    # Dashboard de métricas
    path('api/usage/dashboard/', views.usage_dashboard_view, name='usage_dashboard'),
    path('api/usage/history/', views.usage_history_view, name='usage_history'),
    path('api/invoice/current/', views.current_invoice_preview, name='current_invoice'),
    
    # Webhooks (sin autenticación)
    path('webhooks/mercadopago/', webhooks.mercadopago_webhook, name='webhook_mercadopago'),
    path('webhooks/paddle/', webhooks.paddle_webhook, name='webhook_paddle'),
]
