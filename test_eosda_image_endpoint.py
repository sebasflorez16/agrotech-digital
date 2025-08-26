#!/usr/bin/env python3
"""
Script para probar el endpoint EOSDA Image directamente
"""
import requests
import json
import sys

def test_eosda_image_endpoint():
    """Probar el endpoint /api/parcels/eosda-image/"""
    
    # URL del endpoint
    url = "http://localhost:8000/api/parcels/eosda-image/"
    
    # Datos de prueba - usando valores que aparecen en el frontend
    test_data = {
        "field_id": "test_field_123",
        "view_id": "test_view_456", 
        "type": "ndvi",
        "format": "png"
    }
    
    print(f"🧪 Probando endpoint: {url}")
    print(f"📊 Datos enviados: {json.dumps(test_data, indent=2)}")
    print("-" * 50)
    
    try:
        # Realizar la petición POST
        response = requests.post(url, json=test_data, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📊 Headers: {dict(response.headers)}")
        print(f"📊 Content-Type: {response.headers.get('content-type', 'N/A')}")
        print("-" * 50)
        
        # Imprimir contenido de la respuesta
        print("📊 Contenido de la respuesta:")
        print(response.text[:2000])  # Primeros 2000 caracteres
        
        if response.status_code == 500:
            print("\n❌ ERROR 500 detectado!")
            print("📋 Verificar logs del servidor Django para más detalles")
            
        elif response.status_code == 200:
            print("\n✅ Endpoint funcionando correctamente")
            try:
                json_data = response.json()
                print(f"📊 JSON Response: {json.dumps(json_data, indent=2)}")
            except:
                print("⚠️  No se pudo parsear como JSON")
        else:
            print(f"\n⚠️  Status Code inesperado: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión. ¿Está el servidor Django ejecutándose?")
        print("💡 Ejecutar: python manage.py runserver 8000")
        return False
    except requests.exceptions.Timeout:
        print("❌ Timeout en la petición")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Test del endpoint EOSDA Image")
    print("=" * 50)
    test_eosda_image_endpoint()
