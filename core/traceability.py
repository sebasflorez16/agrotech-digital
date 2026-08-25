"""
Capa de trazabilidad central.

Conecta el inventario con cultivos y labores: cuando se aplica un insumo
(CropInput / LaborInput) se descuenta stock y se deja un movimiento de
salida enlazado al destino (cultivo/labor).

Es ADITIVA: no modifica modelos existentes; solo coordina el flujo entre
ellos a través de los nuevos campos opcionales de InventoryMovement.
"""
import logging

from django.db import transaction

logger = logging.getLogger(__name__)


class TraceabilityService:
    """Coordina la trazabilidad entre inventario, cultivos y labores."""

    @staticmethod
    @transaction.atomic
    def registrar_salida_insumo(supply, quantity, *, crop=None, labor=None, notas=None):
        """Descuenta stock y registra un movimiento de salida de inventario.

        Devuelve (movement, error). Si no hay supply o cantidad, no hace nada
        y devuelve (None, None).
        """
        from django.contrib.contenttypes.models import ContentType

        from inventario.models import InventoryMovement

        if not supply:
            return None, None

        qty = float(quantity or 0)
        if qty <= 0:
            return None, None

        stock = float(supply.quantity or 0)
        if stock < qty:
            logger.warning(
                "Stock insuficiente al aplicar insumo: %s (stock=%s, requerido=%s)",
                supply.name, stock, qty,
            )
            return None, "Stock insuficiente"

        supply.quantity = stock - qty
        supply.save(update_fields=["quantity", "updated"])

        movement = InventoryMovement.objects.create(
            tenant_id=supply.tenant_id,
            content_type=ContentType.objects.get_for_model(supply),
            object_id=supply.pk,
            movement_type="salida",
            quantity=qty,
            unit_value=supply.unit_value,
            crop=crop,
            labor=labor,
            notes=notas or "Salida automática por aplicación de insumo",
        )
        logger.info(
            "Movimiento de salida registrado: %s -> %s (%s)",
            supply.name, crop or labor, qty,
        )
        return movement, None

    @staticmethod
    def calcular_costo_labor(labor):
        """Costo total de una labor = insumos + maquinaria + mano de obra."""
        return labor.calcular_costo_total() or 0
