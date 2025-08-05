from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from .models import Supply, InventoryMovement

class InventoryService:
    @staticmethod
    @transaction.atomic
    def process_movement(data):
        supply = data['supply']
        movement_type = data['movement_type']
        quantity = data['quantity']
        unit_value = data.get('unit_value') or supply.unit_value
        origin_warehouse = data.get('origin_warehouse')
        destination_warehouse = data.get('destination_warehouse')

        if movement_type == 'entrada':
            supply.quantity += quantity
            supply.save()
        elif movement_type == 'salida':
            if supply.quantity < quantity:
                return {'error': 'Stock insuficiente para salida.', 'status': status.HTTP_400_BAD_REQUEST}
            supply.quantity -= quantity
            supply.save()
        elif movement_type == 'transferencia':
            if not origin_warehouse or not destination_warehouse:
                return {'error': 'Debe especificar almacén origen y destino.', 'status': status.HTTP_400_BAD_REQUEST}
            if supply.quantity < quantity:
                return {'error': 'Stock insuficiente en almacén origen.', 'status': status.HTTP_400_BAD_REQUEST}
            supply.quantity -= quantity
            supply.save()
            dest_supply, created = Supply.objects.get_or_create(
                name=supply.name,
                warehouse=destination_warehouse,
                defaults={
                    'unit_value': unit_value,
                    'quantity': 0,
                    'description': supply.description
                }
            )
            dest_supply.quantity += quantity
            dest_supply.save()
        else:
            return {'error': 'Tipo de movimiento no soportado.', 'status': status.HTTP_400_BAD_REQUEST}
        return {'success': True}
