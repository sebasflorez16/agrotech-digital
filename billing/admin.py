"""
Admin de Django para billing.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Plan, Subscription, Invoice, UsageMetrics, BillingEvent


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Admin para planes de suscripción."""
    
    list_display = [
        'name', 'tier', 'price_cop_display', 'price_usd_display',
        'frequency_display', 'is_active', 'is_custom', 'sort_order'
    ]
    list_filter = ['tier', 'is_active', 'is_custom', 'frequency']
    search_fields = ['name', 'tier', 'description']
    ordering = ['sort_order', 'tier']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('tier', 'name', 'description', 'sort_order')
        }),
        ('Precios', {
            'fields': ('price_cop', 'price_usd', 'frequency')
        }),
        ('Límites y Features', {
            'fields': ('limits', 'features_included', 'features_excluded')
        }),
        ('IDs de Pasarelas', {
            'fields': ('mercadopago_plan_id', 'paddle_product_id', 'stripe_price_id'),
            'classes': ('collapse',)
        }),
        ('Configuración', {
            'fields': ('is_active', 'is_custom', 'trial_days')
        }),
    )
    
    def price_cop_display(self, obj):
        return f"${obj.price_cop:,.0f} COP"
    price_cop_display.short_description = 'Precio COP'
    
    def price_usd_display(self, obj):
        return f"${obj.price_usd:,.2f} USD"
    price_usd_display.short_description = 'Precio USD'
    
    def frequency_display(self, obj):
        return f"{obj.frequency} {'mes' if obj.frequency == 1 else 'meses'}"
    frequency_display.short_description = 'Frecuencia'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin para suscripciones."""
    
    list_display = [
        'tenant', 'plan', 'status_badge', 'payment_gateway',
        'current_period_end', 'auto_renew', 'created_at'
    ]
    list_filter = ['status', 'payment_gateway', 'billing_cycle', 'auto_renew']
    search_fields = ['tenant__name', 'tenant__schema_name', 'external_subscription_id']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Tenant y Plan', {
            'fields': ('tenant', 'plan')
        }),
        ('Pasarela de Pago', {
            'fields': ('payment_gateway', 'external_subscription_id')
        }),
        ('Estado', {
            'fields': ('status', 'billing_cycle', 'auto_renew', 'cancel_at_period_end')
        }),
        ('Fechas', {
            'fields': (
                'current_period_start', 'current_period_end',
                'trial_end', 'canceled_at', 'ended_at'
            )
        }),
        ('Metadata', {
            'fields': ('uuid', 'metadata', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'trialing': 'blue',
            'past_due': 'orange',
            'canceled': 'red',
            'expired': 'gray',
            'paused': 'yellow'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin para facturas."""
    
    list_display = [
        'invoice_number', 'tenant', 'total_display', 'currency',
        'status_badge', 'invoice_date', 'paid_at'
    ]
    list_filter = ['status', 'currency', 'invoice_date']
    search_fields = ['invoice_number', 'tenant__name', 'mercadopago_payment_id', 'paddle_payment_id']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']
    date_hierarchy = 'invoice_date'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('invoice_number', 'tenant', 'subscription')
        }),
        ('Montos', {
            'fields': ('subtotal', 'tax_amount', 'total', 'currency')
        }),
        ('Estado y Fechas', {
            'fields': ('status', 'invoice_date', 'due_date', 'paid_at')
        }),
        ('IDs de Pasarelas', {
            'fields': ('mercadopago_payment_id', 'paddle_payment_id', 'stripe_invoice_id'),
            'classes': ('collapse',)
        }),
        ('DIAN (Facturación Electrónica)', {
            'fields': ('dian_invoice_number', 'dian_pdf_url', 'dian_xml_url'),
            'classes': ('collapse',)
        }),
        ('Detalles', {
            'fields': ('line_items', 'pdf_file', 'metadata'),
            'classes': ('collapse',)
        }),
    )
    
    def total_display(self, obj):
        return f"${obj.total:,.2f}"
    total_display.short_description = 'Total'
    
    def status_badge(self, obj):
        colors = {
            'paid': 'green',
            'open': 'blue',
            'draft': 'gray',
            'void': 'red',
            'uncollectible': 'darkred'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(UsageMetrics)
class UsageMetricsAdmin(admin.ModelAdmin):
    """Admin para métricas de uso."""
    
    list_display = [
        'tenant', 'period', 'hectares_used', 'eosda_requests',
        'users_count', 'parcels_count', 'has_overages'
    ]
    list_filter = ['year', 'month']
    search_fields = ['tenant__name', 'tenant__schema_name']
    readonly_fields = ['created_at', 'updated_at']
    
    def period(self, obj):
        return f"{obj.month:02d}/{obj.year}"
    period.short_description = 'Período'
    
    def has_overages(self, obj):
        if obj.hectares_overage > 0 or obj.eosda_requests_overage > 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠ Sí</span>'
            )
        return format_html('<span style="color: green;">✓ No</span>')
    has_overages.short_description = 'Excesos'


@admin.register(BillingEvent)
class BillingEventAdmin(admin.ModelAdmin):
    """Admin para eventos de facturación."""
    
    list_display = [
        'created_at', 'tenant', 'event_type_badge', 'subscription'
    ]
    list_filter = ['event_type', 'created_at']
    search_fields = ['tenant__name', 'external_event_id']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def event_type_badge(self, obj):
        colors = {
            'subscription.created': 'green',
            'subscription.canceled': 'red',
            'invoice.paid': 'blue',
            'invoice.payment_failed': 'orange',
            'plan.upgraded': 'purple',
            'trial.started': 'cyan',
            'trial.ended': 'gray'
        }
        color = colors.get(obj.event_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_event_type_display()
        )
    event_type_badge.short_description = 'Evento'
