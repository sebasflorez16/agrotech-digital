#!/usr/bin/env python3
"""
Script de prueba para verificar que el endpoint de analíticas científicas funcione correctamente
con el sistema multi-tenant.
"""

import os
import sys
import django
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

try:
    django.setup()
except Exception as e:
    print(f"Error al configurar Django: {e}")
    sys.exit(1)

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from parcels.analytics_views import EOSDAAnalyticsAPIView

def test_analytics_endpoint():
    print("🧪 Probando endpoint de analíticas científicas...")
    
    # Crear factory para requests
    factory = RequestFactory()
    
    # Crear un usuario de prueba
    User = get_user_model()
    user = User.objects.first()  # Usar el primer usuario disponible
    
    if not user:
        print("❌ No hay usuarios en la base de datos")
        return False
    
    # Crear request de prueba
    request = factory.get('/api/parcels/eosda-analytics/?view_id=S2/18/N/ZK/2025/8/2/0&scene_date=2025-08-02')
    request.user = user
    
    # Probar la vista
    view = EOSDAAnalyticsAPIView()
    view.request = request
    
    try:
        response = view.get(request)
        print(f"✅ Endpoint responde correctamente: status {response.status_code}")
        if hasattr(response, 'data'):
            print(f"   Datos disponibles: {list(response.data.keys()) if response.data else 'vacío'}")
        return True
    except Exception as e:
        print(f"❌ Error en endpoint: {e}")
        return False

def test_urls_resolution():
    print("🧪 Probando resolución de URLs...")
    
    from django.urls import reverse, NoReverseMatch
    
    try:
        url = reverse('parcels:eosda_analytics')
        print(f"✅ URL resuelta correctamente: {url}")
        return True
    except NoReverseMatch as e:
        print(f"❌ Error resolviendo URL: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Iniciando pruebas del sistema de analíticas científicas")
    print("=" * 60)
    
    # Verificar configuración Django
    print(f"Django configurado: {django.get_version()}")
    print(f"Settings module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    
    # Ejecutar pruebas
    url_test = test_urls_resolution()
    endpoint_test = test_analytics_endpoint()
    
    print("=" * 60)
    if url_test and endpoint_test:
        print("🎉 Todas las pruebas pasaron exitosamente")
        print("💡 El endpoint debería funcionar correctamente en el frontend")
    else:
        print("❌ Algunas pruebas fallaron")
        print("🔧 Revisa la configuración antes de probar en el frontend")
