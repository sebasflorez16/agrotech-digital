"""Señales para la trazabilidad de insumos en cultivos."""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CropInput

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CropInput)
def registrar_salida_insumo_crop(sender, instance, created, **kwargs):
    """Al crear un CropInput se descuenta stock y se registra la salida."""
    if not created:
        return
    try:
        from core.traceability import TraceabilityService

        TraceabilityService.registrar_salida_insumo(
            instance.supply,
            instance.quantity,
            crop=instance.crop,
            notas=(
                "Aplicación de insumo al cultivo "
                f"{instance.crop.name if instance.crop else ''}".strip()
            ),
        )
    except Exception:
        logger.exception(
            "Error registrando salida de insumo para CropInput id=%s", instance.pk
        )
