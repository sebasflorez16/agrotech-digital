"""
Sistema de alertas y notificaciones para billing.

Envía notificaciones cuando:
- Se alcanza el 80% del límite de un recurso
- Se alcanza el 90% del límite
- Se excede el 100% del límite
- Se genera un overage
"""

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class BillingAlertManager:
    """
    Gestor de alertas de billing.
    
    Envía notificaciones por email cuando se alcanzan umbrales de uso.
    """
    
    THRESHOLDS = {
        'warning': 80,   # 80% del límite
        'danger': 90,    # 90% del límite
        'exceeded': 100  # 100% o más
    }
    
    def __init__(self, metrics):
        """
        Args:
            metrics: Instancia de UsageMetrics
        """
        self.metrics = metrics
        self.tenant = metrics.tenant
        self.subscription = metrics.subscription
        self.plan = self.subscription.plan if self.subscription else None
        
    def check_and_send_alerts(self):
        """
        Verifica todos los recursos y envía alertas si es necesario.
        
        Returns:
            list: Lista de alertas enviadas
        """
        if not self.plan:
            logger.warning(f"No plan found for tenant {self.tenant.name}")
            return []
        
        alerts_sent = []
        
        # Verificar cada recurso
        resources = {
            'eosda_requests': {
                'name': 'Requests EOSDA',
                'current': self.metrics.eosda_requests,
                'limit': self.plan.get_limit('eosda_requests', 0),
                'unit': 'requests'
            },
            'parcels': {
                'name': 'Parcelas',
                'current': self.metrics.parcels_count,
                'limit': self.plan.get_limit('parcels', 0),
                'unit': 'parcelas'
            },
            'hectares': {
                'name': 'Hectáreas',
                'current': float(self.metrics.hectares_used),
                'limit': self.plan.get_limit('hectares', 0),
                'unit': 'hectáreas'
            },
            'users': {
                'name': 'Usuarios',
                'current': self.metrics.users_count,
                'limit': self.plan.get_limit('users', 0),
                'unit': 'usuarios'
            }
        }
        
        for resource_key, resource_data in resources.items():
            alert = self._check_resource_threshold(resource_key, resource_data)
            if alert:
                alerts_sent.append(alert)
        
        return alerts_sent
    
    def _check_resource_threshold(self, resource_key, resource_data):
        """
        Verifica si un recurso ha alcanzado un umbral y envía alerta.
        
        Args:
            resource_key: Clave del recurso (ej: 'eosda_requests')
            resource_data: Dict con name, current, limit, unit
            
        Returns:
            dict: Alerta enviada o None
        """
        current = resource_data['current']
        limit = resource_data['limit']
        name = resource_data['name']
        unit = resource_data['unit']
        
        if limit == 0 or limit == 'unlimited':
            return None
        
        # Calcular porcentaje
        percentage = (current / limit) * 100
        
        # Determinar nivel de alerta
        alert_level = None
        if percentage >= self.THRESHOLDS['exceeded']:
            alert_level = 'exceeded'
        elif percentage >= self.THRESHOLDS['danger']:
            alert_level = 'danger'
        elif percentage >= self.THRESHOLDS['warning']:
            alert_level = 'warning'
        
        if not alert_level:
            return None
        
        # Verificar si ya se envió esta alerta
        if self._was_alert_sent_recently(resource_key, alert_level):
            logger.info(f"Alert for {resource_key} at {alert_level} already sent recently")
            return None
        
        # Construir mensaje
        alert_data = {
            'tenant': self.tenant.name,
            'resource': name,
            'resource_key': resource_key,
            'current': current,
            'limit': limit,
            'percentage': round(percentage, 2),
            'unit': unit,
            'level': alert_level,
            'period': f"{self.metrics.year}-{self.metrics.month:02d}"
        }
        
        # Enviar email
        self._send_alert_email(alert_data)
        
        # Registrar en BillingEvent
        self._log_alert_event(alert_data)
        
        return alert_data
    
    def _send_alert_email(self, alert_data):
        """
        Envía email de alerta.
        
        Args:
            alert_data: Dict con información de la alerta
        """
        subject = self._build_email_subject(alert_data)
        message = self._build_email_message(alert_data)
        
        # Obtener emails de usuarios del tenant
        recipient_emails = self._get_recipient_emails()
        
        if not recipient_emails:
            logger.warning(f"No recipients found for tenant {self.tenant.name}")
            return
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_emails,
                fail_silently=False
            )
            logger.info(f"Alert email sent to {recipient_emails} for {alert_data['resource']}")
        except Exception as e:
            logger.error(f"Failed to send alert email: {str(e)}")
    
    def _build_email_subject(self, alert_data):
        """Construye el asunto del email."""
        level_text = {
            'warning': '⚠️ Advertencia',
            'danger': '🔴 Alerta Crítica',
            'exceeded': '🚫 Límite Excedido'
        }
        
        return f"{level_text[alert_data['level']]}: {alert_data['resource']} - AgroTech Digital"
    
    def _build_email_message(self, alert_data):
        """Construye el mensaje del email."""
        level_messages = {
            'warning': f"Estás usando el {alert_data['percentage']}% de tus {alert_data['resource']} permitidos.",
            'danger': f"¡ATENCIÓN! Estás usando el {alert_data['percentage']}% de tus {alert_data['resource']} permitidos.",
            'exceeded': f"Has excedido el límite de {alert_data['resource']}."
        }
        
        message = f"""
Hola,

{level_messages[alert_data['level']]}

Detalles de uso:
- Recurso: {alert_data['resource']}
- Uso actual: {alert_data['current']} {alert_data['unit']}
- Límite del plan: {alert_data['limit']} {alert_data['unit']}
- Porcentaje usado: {alert_data['percentage']}%
- Período: {alert_data['period']}

"""
        
        if alert_data['level'] == 'exceeded':
            overage = alert_data['current'] - alert_data['limit']
            overage_cost = overage * 500 if alert_data['resource_key'] == 'eosda_requests' else 0
            
            message += f"""
⚠️ IMPORTANTE: Has excedido tu límite en {overage} {alert_data['unit']}.

"""
            if overage_cost > 0:
                message += f"""Esto generará un cargo adicional de {overage_cost:,} COP en tu próxima factura.

"""
            
            message += f"""Recomendaciones:
1. Considera mejorar tu plan para obtener más {alert_data['resource']}
2. Revisa tu uso actual en el dashboard
3. Contacta a soporte si necesitas asistencia

"""
        elif alert_data['level'] == 'danger':
            message += f"""Recomendaciones:
1. Monitorea tu uso regularmente
2. Considera mejorar tu plan antes de alcanzar el límite
3. Planifica tus actividades para optimizar el uso de recursos

"""
        else:
            message += f"""Recomendación: Monitorea tu uso para evitar cargos adicionales.

"""
        
        message += f"""Puedes revisar tu uso actual en: {getattr(settings, 'FRONTEND_URL', 'https://app.agrotech.com')}/dashboard/usage

Saludos,
Equipo AgroTech Digital
        """
        
        return message
    
    def _get_recipient_emails(self):
        """
        Obtiene los emails de los usuarios del tenant para enviar alertas.
        
        Returns:
            list: Lista de emails
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Por ahora, obtener todos los usuarios del tenant
        # TODO: Filtrar por rol (admin, owner) o preferencias de notificación
        emails = []
        
        try:
            # Cambiar al schema del tenant
            from django.db import connection
            connection.set_tenant(self.tenant)
            
            users = User.objects.filter(is_active=True).exclude(email='')
            emails = [user.email for user in users if user.email]
            
            # Volver al schema público
            connection.set_schema_to_public()
        except Exception as e:
            logger.error(f"Error getting recipient emails: {str(e)}")
        
        return emails
    
    def _log_alert_event(self, alert_data):
        """
        Registra la alerta en BillingEvent.
        
        Args:
            alert_data: Dict con información de la alerta
        """
        from billing.models import BillingEvent
        
        try:
            BillingEvent.objects.create(
                tenant=self.tenant,
                event_type='alert',
                event_data={
                    'resource': alert_data['resource_key'],
                    'level': alert_data['level'],
                    'current': alert_data['current'],
                    'limit': alert_data['limit'],
                    'percentage': alert_data['percentage'],
                    'period': alert_data['period'],
                    'message': f"Alert {alert_data['level']} for {alert_data['resource']}: {alert_data['percentage']}%"
                }
            )
        except Exception as e:
            logger.error(f"Error logging alert event: {str(e)}")
    
    def _was_alert_sent_recently(self, resource_key, alert_level):
        """
        Verifica si ya se envió esta alerta recientemente (últimas 24 horas).
        
        Args:
            resource_key: Clave del recurso
            alert_level: Nivel de alerta
            
        Returns:
            bool: True si ya se envió
        """
        from billing.models import BillingEvent
        from datetime import timedelta
        
        recent_threshold = timezone.now() - timedelta(hours=24)
        
        recent_alerts = BillingEvent.objects.filter(
            tenant=self.tenant,
            event_type='alert',
            event_data__resource=resource_key,
            event_data__level=alert_level,
            created_at__gte=recent_threshold
        ).exists()
        
        return recent_alerts


def check_all_tenants_usage():
    """
    Función para ejecutar periódicamente (cron/celery).
    
    Verifica el uso de todos los tenants y envía alertas necesarias.
    """
    from base_agrotech.models import Client
    from billing.models import UsageMetrics
    from django.utils import timezone
    
    now = timezone.now()
    alerts_summary = []
    
    for tenant in Client.objects.all():
        try:
            # Obtener métricas del mes actual
            metrics = UsageMetrics.objects.filter(
                tenant=tenant,
                year=now.year,
                month=now.month
            ).first()
            
            if not metrics:
                continue
            
            # Actualizar métricas
            metrics.update_from_tenant()
            
            # Verificar y enviar alertas
            alert_manager = BillingAlertManager(metrics)
            alerts = alert_manager.check_and_send_alerts()
            
            if alerts:
                alerts_summary.append({
                    'tenant': tenant.name,
                    'alerts': alerts
                })
                
        except Exception as e:
            logger.error(f"Error checking alerts for tenant {tenant.name}: {str(e)}")
    
    return alerts_summary
