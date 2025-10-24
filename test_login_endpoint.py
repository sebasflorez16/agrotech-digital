#!/usr/bin/env python
"""
Script de prueba para verificar el endpoint de login
Ejecutar: python test_login_endpoint.py
"""

import requests
import json

# Configuración
BACKEND_URL = "https://agrotechcolombia.com"
LOGIN_ENDPOINT = f"{BACKEND_URL}/api/authentication/login/"

def test_login_endpoint():
    """Prueba el endpoint de login"""
    print("🔍 Probando endpoint de login...")
    print(f"📍 URL: {LOGIN_ENDPOINT}")
    print("-" * 60)
    
    # Datos de prueba
    payload = {
        "username": "testuser",
        "password": "testpassword"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://agrotechcolombia.netlify.app"
    }
    
    try:
        # Hacer la petición POST
        response = requests.post(
            LOGIN_ENDPOINT, 
            json=payload, 
            headers=headers,
            timeout=10
        )
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        print("-" * 60)
        
        # Verificar si la respuesta es JSON o HTML
        content_type = response.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            print("✅ Respuesta en JSON:")
            print(json.dumps(response.json(), indent=2))
        elif 'text/html' in content_type:
            print("❌ ERROR: El servidor respondió con HTML en lugar de JSON")
            print("Esto indica que la ruta no fue encontrada (404)")
            print(f"Primeras 500 caracteres de la respuesta:")
            print(response.text[:500])
        else:
            print(f"⚠️  Content-Type inesperado: {content_type}")
            print(response.text[:500])
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al conectar con el servidor: {e}")
    
    print("-" * 60)

def test_cors_preflight():
    """Prueba el preflight de CORS (OPTIONS)"""
    print("\n🔍 Probando CORS preflight (OPTIONS)...")
    print(f"📍 URL: {LOGIN_ENDPOINT}")
    print("-" * 60)
    
    headers = {
        "Origin": "https://agrotechcolombia.netlify.app",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type"
    }
    
    try:
        response = requests.options(LOGIN_ENDPOINT, headers=headers, timeout=10)
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"📋 CORS Headers:")
        for header, value in response.headers.items():
            if 'access-control' in header.lower():
                print(f"   {header}: {value}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
    
    print("-" * 60)

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 TEST DE ENDPOINT DE AUTENTICACIÓN")
    print("=" * 60)
    
    # Ejecutar pruebas
    test_login_endpoint()
    test_cors_preflight()
    
    print("\n✅ Pruebas completadas")
