"""
Modelos de facturación y suscripciones para AgroTech Digital
"""

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from base_agrotech.models import Client
from decimal import Decimal
import uuid


class Plan(models.Model):
    """
    Planes de suscripción disponibles para el SaaS.
    
    Soporta múltiples pasarelas de pago (MercadoPago, Paddle, etc.)
    """
    
    TIER_CHOICES = [
        ('free', 'Explorador'),
        ('basic', 'Agricultor'),
        ('pro', 'Empresarial'),
        ('enterprise', 'Corporativo'),
    ]
    
    FREQUENCY_CHOICES = [
        (1, 'Mensual'),
        (3, 'Trimestral'),
        (12, 'Anual'),
    ]
    
    # Identificación
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True, db_index=True)
    name = models.CharField(max_length=100, verbose_name='Nombre del plan')
    description = models.TextField(verbose_name='Descripción')
    
    # Precios
    price_cop = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name='Precio en COP',
        help_text='Precio mensual en pesos colombianos'
    )
    price_usd = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name='Precio en USD',
        help_text='Precio mensual en dólares'
    )
    
    # Frecuencia de pago
    frequency = models.IntegerField(
        choices=FREQUENCY_CHOICES, 
        default=1,
        verbose_name='Frecuencia de cobro',
        help_text='En meses: 1=Mensual, 3=Trimestral, 12=Anual'
    )
    
    # Límites del plan (JSON para flexibilidad)
    limits = models.JSONField(
        default=dict,
        verbose_name='Límites del plan',
        help_text='Ejemplo: {"hectares": 300, "users": 3, "eosda_requests": 100, "parcels": 10, "storage_mb": 500}'
    )
    
    # Features incluidas y excluidas
    features_included = models.JSONField(
        default=list,
        verbose_name='Características incluidas',
        help_text='Lista de features disponibles en este plan'
    )
    features_excluded = models.JSONField(
        default=list,
        verbose_name='Características excluidas',
        help_text='Lista de features NO disponibles (para mostrar en comparación)'
    )
    
    # IDs en pasarelas externas
    mercadopago_plan_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name='ID del plan en MercadoPago'
    )
    paddle_product_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name='ID del producto en Paddle'
    )
    stripe_price_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name='ID del precio en Stripe (futuro)'
    )
    
    # Configuración
    is_active = models.BooleanField(
        default=True,
        verbose_name='Plan activo',
        help_text='Desactivar para ocultar de la lista de planes disponibles'
    )
    is_custom = models.BooleanField(
        default=False,
        verbose_name='Plan personalizado',
        help_text='True para planes Enterprise con pricing custom'
    )
    trial_days = models.IntegerField(
        default=14,
        verbose_name='Días de prueba',
        help_text='Período de trial gratuito en días'
    )
    
    # Orden de visualización
    sort_order = models.IntegerField(
        default=0,
        verbose_name='Orden',
        help_text='Para ordenar planes en la UI (menor primero)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'tier']
        verbose_name = 'Plan de Suscripción'
        verbose_name_plural = 'Planes de Suscripción'
        indexes = [
            models.Index(fields=['tier', 'is_active']),
            models.Index(fields=['sort_order']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.price_cop:,} COP/mes"
    
    def get_limit(self, key, default=0):
        """
        Obtener un límite específico del plan.
        
        Args:
            key: Nombre del límite ('hectares', 'users', etc.)
            default: Valor por defecto si no existe
            
        Returns:
            Valor del límite o default
        """
        return self.limits.get(key, default)
    
    def get_price(self, currency='COP'):
        """
        Obtener precio en la moneda especificada.
        
        Args:
            currency: 'COP' o 'USD'
            
        Returns:
            Precio en la moneda solicitada
        """
        if currency.upper() == 'USD':
            return self.price_usd
        return self.price_cop
    
    def get_yearly_discount(self):
        """
        Calcular descuento para pago anual (2 meses gratis).
        
        Returns:
            dict con precio anual y ahorro
        """
        monthly_price_cop = self.price_cop
        yearly_price_cop = monthly_price_cop * 10  # 12 meses - 2 gratis
        savings_cop = monthly_price_cop * 2
        
        monthly_price_usd = self.price_usd
        yearly_price_usd = monthly_price_usd * 10
        savings_usd = monthly_price_usd * 2
        
        return {
            'yearly_price_cop': yearly_price_cop,
            'savings_cop': savings_cop,
            'yearly_price_usd': yearly_price_usd,
            'savings_usd': savings_usd,
            'discount_percent': 20
        }


class Subscription(models.Model):
    """
    Suscripción activa de un tenant.
    
    Maneja múltiples pasarelas de pago (multi-gateway support).
    """
    
    STATUS_CHOICES = [
        ('trialing', 'En período de prueba'),
        ('active', 'Activa'),
        ('past_due', 'Pago vencido'),
        ('canceled', 'Cancelada'),
        ('paused', 'Pausada'),
        ('expired', 'Expirada'),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Mensual'),
        ('yearly', 'Anual'),
    ]
    
    GATEWAY_CHOICES = [
        ('mercadopago', 'MercadoPago'),
        ('paddle', 'Paddle'),
        ('stripe', 'Stripe'),
        ('manual', 'Manual'),
    ]
    
    # Identificación única
    uuid = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True,
        verbose_name='UUID'
    )
    
    # Relaciones
    tenant = models.OneToOneField(
        Client, 
        on_delete=models.CASCADE, 
        related_name='subscription',
        verbose_name='Tenant'
    )
    plan = models.ForeignKey(
        Plan, 
        on_delete=models.PROTECT,
        verbose_name='Plan'
    )
    
    # Pasarela de pago
    payment_gateway = models.CharField(
        max_length=50,
        choices=GATEWAY_CHOICES,
        default='mercadopago',
        verbose_name='Pasarela de pago',
        help_text='Gateway usado para procesar pagos'
    )
    external_subscription_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='ID externo',
        help_text='ID de la suscripción en la pasarela de pago'
    )
    
    # Estado
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='trialing',
        db_index=True,
        verbose_name='Estado'
    )
    billing_cycle = models.CharField(
        max_length=10, 
        choices=BILLING_CYCLE_CHOICES, 
        default='monthly',
        verbose_name='Ciclo de facturación'
    )
    
    # Fechas importantes
    current_period_start = models.DateTimeField(
        verbose_name='Inicio período actual'
    )
    current_period_end = models.DateTimeField(
        verbose_name='Fin período actual'
    )
    trial_end = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Fin del trial'
    )
    canceled_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Fecha de cancelación'
    )
    ended_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Fecha de finalización'
    )
    
    # Control de renovación
    cancel_at_period_end = models.BooleanField(
        default=False,
        verbose_name='Cancelar al fin del período',
        help_text='Si True, no se renovará automáticamente'
    )
    auto_renew = models.BooleanField(
        default=True,
        verbose_name='Renovación automática'
    )
    
    # Metadata adicional
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Metadata',
        help_text='Información adicional de la suscripción'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Suscripción'
        verbose_name_plural = 'Suscripciones'
        indexes = [
            models.Index(fields=['status', 'current_period_end']),
            models.Index(fields=['tenant']),
            models.Index(fields=['payment_gateway', 'external_subscription_id']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.plan.name} ({self.get_status_display()})"
    
    def is_active_or_trialing(self):
        """Verifica si la suscripción está activa o en trial."""
        return self.status in ['active', 'trialing']
    
    def is_trial_expired(self):
        """Verifica si el trial expiró."""
        if self.trial_end and self.status == 'trialing':
            return timezone.now() > self.trial_end
        return False
    
    def days_until_renewal(self):
        """Días hasta la próxima renovación."""
        if self.current_period_end:
            delta = self.current_period_end - timezone.now()
            return max(0, delta.days)
        return 0
    
    def check_limit(self, resource_type, current_value):
        """
        Verifica si se excede un límite del plan.
        
        Args:
            resource_type: 'hectares', 'users', 'eosda_requests', etc.
            current_value: valor actual del recurso
        
        Returns:
            tuple (bool, int): (is_within_limit, limit_value)
        """
        limit = self.plan.get_limit(resource_type)
        
        # Enterprise unlimited
        if limit == 'unlimited':
            return (True, float('inf'))
        
        try:
            limit_int = int(limit)
            return (current_value <= limit_int, limit_int)
        except (ValueError, TypeError):
            return (True, 0)
    
    def cancel(self, immediately=False, reason=None):
        """
        Cancelar la suscripción.
        
        Args:
            immediately: Si True, cancela de inmediato. Si False, al fin del período.
            reason: Motivo de la cancelación (opcional)
        """
        self.canceled_at = timezone.now()
        
        if immediately:
            self.status = 'canceled'
            self.ended_at = timezone.now()
            self.auto_renew = False
        else:
            self.cancel_at_period_end = True
        
        if reason:
            self.metadata['cancellation_reason'] = reason
        
        self.save()
        
        # Registrar evento
        BillingEvent.objects.create(
            tenant=self.tenant,
            subscription=self,
            event_type='subscription.canceled',
            event_data={
                'immediately': immediately,
                'reason': reason,
                'canceled_at': self.canceled_at.isoformat()
            }
        )


class UsageMetrics(models.Model):
    """
    Tracking de consumo mensual por tenant.
    
    Registra el uso de recursos para verificar límites y generar reportes.
    """
    
    tenant = models.ForeignKey(
        Client, 
        on_delete=models.CASCADE, 
        related_name='usage_metrics',
        verbose_name='Tenant'
    )
    subscription = models.ForeignKey(
        Subscription, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name='Suscripción'
    )
    
    # Período
    year = models.IntegerField(verbose_name='Año')
    month = models.IntegerField(verbose_name='Mes')
    
    # Métricas de uso
    hectares_used = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name='Hectáreas usadas'
    )
    eosda_requests = models.IntegerField(
        default=0,
        verbose_name='Peticiones EOSDA'
    )
    users_count = models.IntegerField(
        default=0,
        verbose_name='Cantidad de usuarios'
    )
    parcels_count = models.IntegerField(
        default=0,
        verbose_name='Cantidad de parcelas'
    )
    storage_mb = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name='Almacenamiento en MB'
    )
    
    # Excesos (overages)
    hectares_overage = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name='Hectáreas en exceso'
    )
    eosda_requests_overage = models.IntegerField(
        default=0,
        verbose_name='Peticiones EOSDA en exceso'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('tenant', 'year', 'month')
        ordering = ['-year', '-month']
        verbose_name = 'Métrica de Uso'
        verbose_name_plural = 'Métricas de Uso'
        indexes = [
            models.Index(fields=['tenant', 'year', 'month']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.month:02d}/{self.year}"
    
    @classmethod
    def get_or_create_current(cls, tenant):
        """
        Obtener o crear métricas del mes actual para un tenant.
        
        Args:
            tenant: Instancia de Client
            
        Returns:
            Instancia de UsageMetrics
        """
        now = timezone.now()
        metrics, created = cls.objects.get_or_create(
            tenant=tenant,
            year=now.year,
            month=now.month,
            defaults={
                'subscription': getattr(tenant, 'subscription', None)
            }
        )
        return metrics
    
    def calculate_overages(self):
        """Calcula excesos respecto al plan de la suscripción."""
        if not self.subscription:
            return
        
        plan = self.subscription.plan
        
        hectares_limit = plan.get_limit('hectares', 0)
        if hectares_limit != 'unlimited':
            self.hectares_overage = max(0, Decimal(str(self.hectares_used)) - Decimal(str(hectares_limit)))
        
        eosda_limit = plan.get_limit('eosda_requests', 0)
        if eosda_limit != 'unlimited':
            self.eosda_requests_overage = max(0, self.eosda_requests - int(eosda_limit))
        
        self.save()


class Invoice(models.Model):
    """
    Factura generada por suscripción o pago único.
    
    Soporta facturación simple (PDF) y electrónica (DIAN).
    """
    
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('open', 'Pendiente'),
        ('paid', 'Pagada'),
        ('void', 'Anulada'),
        ('uncollectible', 'Incobrable'),
    ]
    
    # Identificación
    invoice_number = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name='Número de factura'
    )
    
    # Relaciones
    tenant = models.ForeignKey(
        Client, 
        on_delete=models.CASCADE, 
        related_name='invoices',
        verbose_name='Tenant'
    )
    subscription = models.ForeignKey(
        Subscription, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='Suscripción'
    )
    
    # Montos
    subtotal = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name='Subtotal'
    )
    tax_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        verbose_name='IVA',
        help_text='IVA 19% en Colombia'
    )
    total = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name='Total'
    )
    currency = models.CharField(
        max_length=3, 
        default='COP',
        verbose_name='Moneda'
    )
    
    # Estado
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft',
        db_index=True,
        verbose_name='Estado'
    )
    
    # Fechas
    invoice_date = models.DateField(verbose_name='Fecha de factura')
    due_date = models.DateField(verbose_name='Fecha de vencimiento')
    paid_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name='Fecha de pago'
    )
    
    # IDs en pasarelas externas
    mercadopago_payment_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name='ID de pago en MercadoPago'
    )
    paddle_payment_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name='ID de pago en Paddle'
    )
    stripe_invoice_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name='ID de factura en Stripe'
    )
    
    # DIAN (Facturación electrónica - Colombia)
    dian_invoice_number = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name='Número DIAN',
        help_text='Número de factura electrónica DIAN'
    )
    dian_pdf_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name='URL PDF DIAN'
    )
    dian_xml_url = models.URLField(
        blank=True, 
        null=True,
        verbose_name='URL XML DIAN'
    )
    
    # Archivo PDF generado
    pdf_file = models.FileField(
        upload_to='invoices/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Archivo PDF'
    )
    
    # Detalles de líneas (items)
    line_items = models.JSONField(
        default=list,
        verbose_name='Líneas de factura',
        help_text='Ejemplo: [{"description": "Plan Pro", "quantity": 1, "amount": 149000}]'
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Metadata'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-invoice_date', '-created_at']
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['invoice_date']),
            models.Index(fields=['status', 'due_date']),
        ]
    
    def __str__(self):
        return f"Factura {self.invoice_number} - {self.tenant.name} - {self.total} {self.currency}"
    
    def save(self, *args, **kwargs):
        """Override save para generar número de factura y calcular IVA."""
        # Generar número de factura si no existe
        if not self.invoice_number:
            last_invoice = Invoice.objects.order_by('-id').first()
            if last_invoice and last_invoice.invoice_number:
                try:
                    last_num = int(last_invoice.invoice_number.split('-')[-1])
                    self.invoice_number = f"AGRO-{last_num + 1:06d}"
                except (ValueError, IndexError):
                    self.invoice_number = f"AGRO-{uuid.uuid4().hex[:8].upper()}"
            else:
                self.invoice_number = "AGRO-000001"
        
        # Calcular IVA (19% Colombia) si no está establecido
        if self.tax_amount == 0 and self.currency == 'COP':
            self.tax_amount = self.subtotal * Decimal('0.19')
            self.total = self.subtotal + self.tax_amount
        
        super().save(*args, **kwargs)
    
    def mark_as_paid(self, payment_method='online', payment_id=None):
        """
        Marcar factura como pagada.
        
        Args:
            payment_method: Método de pago ('mercadopago', 'paddle', etc.)
            payment_id: ID del pago en la pasarela
        """
        self.status = 'paid'
        self.paid_at = timezone.now()
        
        if payment_id:
            if payment_method == 'mercadopago':
                self.mercadopago_payment_id = payment_id
            elif payment_method == 'paddle':
                self.paddle_payment_id = payment_id
            elif payment_method == 'stripe':
                self.stripe_invoice_id = payment_id
        
        self.save()
        
        # Registrar evento
        BillingEvent.objects.create(
            tenant=self.tenant,
            subscription=self.subscription,
            event_type='invoice.paid',
            event_data={
                'invoice_number': self.invoice_number,
                'amount': float(self.total),
                'currency': self.currency,
                'payment_method': payment_method,
                'payment_id': payment_id
            }
        )


class BillingEvent(models.Model):
    """
    Audit log de eventos de facturación.
    
    Registra todos los cambios importantes para debugging y compliance.
    """
    
    EVENT_TYPES = [
        ('subscription.created', 'Suscripción creada'),
        ('subscription.updated', 'Suscripción actualizada'),
        ('subscription.canceled', 'Suscripción cancelada'),
        ('subscription.renewed', 'Suscripción renovada'),
        ('invoice.created', 'Factura creada'),
        ('invoice.paid', 'Factura pagada'),
        ('invoice.payment_failed', 'Pago fallido'),
        ('plan.upgraded', 'Plan mejorado'),
        ('plan.downgraded', 'Plan reducido'),
        ('usage.exceeded', 'Límite excedido'),
        ('trial.started', 'Trial iniciado'),
        ('trial.ended', 'Trial finalizado'),
        ('alert', 'Alerta de uso'),
    ]
    
    # Relaciones
    tenant = models.ForeignKey(
        Client, 
        on_delete=models.CASCADE, 
        related_name='billing_events',
        verbose_name='Tenant'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Suscripción'
    )
    
    # Evento
    event_type = models.CharField(
        max_length=50, 
        choices=EVENT_TYPES,
        db_index=True,
        verbose_name='Tipo de evento'
    )
    event_data = models.JSONField(
        default=dict,
        verbose_name='Datos del evento'
    )
    
    # IDs externos (para webhooks)
    external_event_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name='ID externo del evento'
    )
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Evento de Facturación'
        verbose_name_plural = 'Eventos de Facturación'
        indexes = [
            models.Index(fields=['tenant', 'event_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.get_event_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
