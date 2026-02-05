"""
Serializers para el app de billing.
"""

from rest_framework import serializers
from .models import Plan, Subscription, Invoice, UsageMetrics, BillingEvent


class PlanSerializer(serializers.ModelSerializer):
    """Serializer para planes de suscripción."""
    
    yearly_discount = serializers.SerializerMethodField()
    
    class Meta:
        model = Plan
        fields = [
            'tier', 'name', 'description',
            'price_cop', 'price_usd', 'frequency',
            'limits', 'features_included', 'features_excluded',
            'is_custom', 'trial_days', 'yearly_discount'
        ]
    
    def get_yearly_discount(self, obj):
        """Calcular descuento anual."""
        return obj.get_yearly_discount()


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer para suscripciones."""
    
    plan_details = PlanSerializer(source='plan', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'uuid', 'tenant_name', 'plan', 'plan_details',
            'payment_gateway', 'status', 'billing_cycle',
            'current_period_start', 'current_period_end',
            'trial_end', 'canceled_at', 'ended_at',
            'cancel_at_period_end', 'auto_renew',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer para facturas."""
    
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'tenant_name',
            'subscription', 'subtotal', 'tax_amount', 'total', 'currency',
            'status', 'invoice_date', 'due_date', 'paid_at',
            'line_items', 'pdf_file', 'dian_pdf_url',
            'created_at'
        ]
        read_only_fields = ['id', 'invoice_number', 'created_at']


class UsageMetricsSerializer(serializers.ModelSerializer):
    """Serializer para métricas de uso."""
    
    class Meta:
        model = UsageMetrics
        fields = [
            'year', 'month', 'hectares_used', 'eosda_requests',
            'users_count', 'parcels_count', 'storage_mb',
            'hectares_overage', 'eosda_requests_overage',
            'created_at', 'updated_at'
        ]


class BillingEventSerializer(serializers.ModelSerializer):
    """Serializer para eventos de facturación."""
    
    class Meta:
        model = BillingEvent
        fields = ['event_type', 'event_data', 'created_at']


class CreateSubscriptionSerializer(serializers.Serializer):
    """Serializer para crear suscripción."""
    
    plan_tier = serializers.ChoiceField(
        choices=['free', 'basic', 'pro', 'enterprise']
    )
    billing_cycle = serializers.ChoiceField(
        choices=['monthly', 'yearly'],
        default='monthly'
    )
    payment_method_token = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Token del método de pago (si aplica)'
    )
