#!/usr/bin/env python
"""Script para probar suscripciones de MercadoPago"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

import django
django.setup()

from django.conf import settings
import mercadopago

sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

# Crear una suscripcion de prueba para el Plan Agricultor (79,000 COP/mes)
preapproval_data = {
    'reason': 'AgroTech Digital - Plan Agricultor',
    'auto_recurring': {
        'frequency': 1,
        'frequency_type': 'months',
        'transaction_amount': 79000,
        'currency_id': 'COP'
    },
    'back_url': 'https://unmellifluous-benton-emotional.ngrok-free.app/billing/success/',
    'payer_email': 'juansebastianflorezescobar@gmail.com',
    'external_reference': 'test_subscription_001'
}

result = sdk.preapproval().create(preapproval_data)
print('Status:', result['status'])

if result['status'] == 201:
    response = result['response']
    print()
    print('=' * 60)
    print('SUSCRIPCION CREADA EXITOSAMENTE')
    print('=' * 60)
    print(f"ID: {response['id']}")
    print(f"Plan: Plan Agricultor - COP 79,000/mes")
    print()
    print("URL DE PAGO (abrela en el navegador):")
    print(response['init_point'])
    print()
    print("CREDENCIALES DE PRUEBA:")
    print("   Usuario: TETE6372648")
    print("   Contrasena: hUjCNax0WK")
    print('=' * 60)
else:
    print('Error:', result)
