#!/usr/bin/env python3
"""
Script de emergencia para configurar variables de entorno de Railway
Ejecuta antes de que Django cargue para asegurar que DATABASE_URL esté disponible
"""

import os
import sys

def setup_railway_environment():
    """Configurar variables de entorno críticas para Railway"""
    
    print("🔧 RAILWAY ENV SETUP - Configurando variables de entorno...")
    
    # Variables críticas que deben estar disponibles
    critical_vars = [
        'DATABASE_URL',
        'DJANGO_SECRET_KEY', 
        'PORT'
    ]
    
    missing_vars = []
    
    for var in critical_vars:
        value = os.environ.get(var)
        if value:
            if var == 'DATABASE_URL':
                print(f"✅ {var}: {value[:50]}...")
            else:
                print(f"✅ {var}: configurado")
        else:
            missing_vars.append(var)
            print(f"❌ {var}: NO CONFIGURADO")
    
    # Configurar PORT por defecto si no existe
    if 'PORT' not in os.environ:
        os.environ['PORT'] = '8080'
        print("⚙️ PORT configurado por defecto: 8080")
    
    # Asegurar DJANGO_SETTINGS_MODULE
    if 'DJANGO_SETTINGS_MODULE' not in os.environ:
        os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.production'
        print("⚙️ DJANGO_SETTINGS_MODULE configurado: config.settings.production")
    
    # Si falta DATABASE_URL, intentar detectar Railway
    if 'DATABASE_URL' not in os.environ:
        print("🚨 DATABASE_URL no encontrado!")
        
        # Verificar si estamos en Railway
        railway_vars = ['RAILWAY_ENVIRONMENT', 'RAILWAY_PROJECT_ID', 'RAILWAY_SERVICE_ID']
        is_railway = any(os.environ.get(var) for var in railway_vars)
        
        if is_railway:
            print("🚂 Detectado entorno Railway pero DATABASE_URL faltante")
            print("💡 Posibles causas:")
            print("   - Base de datos no conectada al servicio")
            print("   - Variables de entorno no configuradas")
            print("   - Problema temporal de Railway")
            
            # Lista todas las variables que empiecen con DATABASE o POSTGRES
            db_vars = {k: v for k, v in os.environ.items() 
                      if k.startswith(('DATABASE', 'POSTGRES', 'DB_'))}
            
            if db_vars:
                print("🔍 Variables de BD encontradas:")
                for k, v in db_vars.items():
                    print(f"   {k}: {v[:50]}...")
            else:
                print("❌ No se encontraron variables de base de datos")
        else:
            print("🏠 Entorno local detectado")
    
    print(f"📊 Variables críticas configuradas: {len(critical_vars) - len(missing_vars)}/{len(critical_vars)}")
    
    if missing_vars:
        print(f"⚠️ Variables faltantes: {', '.join(missing_vars)}")
        return False
    
    print("✅ Configuración de entorno completada")
    return True

if __name__ == "__main__":
    success = setup_railway_environment()
    sys.exit(0 if success else 1)
