"""Señales para la trazabilidad de insumos en labores."""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import LaborInput

logger = logging.getLogger(__name__)


@receiver(post_save, sender=LaborInput)
def registrar_salida_insumo_labor(sender, instance, created, **kwargs):
    """Al crear un LaborInput se descuenta stock y se registra la salida."""
    if not created:
        return
    try:
        from core.traceability import TraceabilityService

        TraceabilityService.registrar_salida_insumo(
            instance.supply,
            instance.quantity,
            crop=instance.crop,
            labor=instance.labor,
            notas=(
                "Insumo aplicado en labor "
                f"{instance.labor.nombre if instance.labor else ''}".strip()
            ),
        )
    except Exception:
        logger.exception(
            "Error registrando salida de insumo para LaborInput id=%s", instance.pk
        )
