# 🔧 INSTRUCCIONES PARA SOLUCIONAR ERROR 402/503 EN EOSDA

## Problema Identificado
El error 402 "Payment Required" NO viene de EOSDA, sino del sistema interno de billing de AgroTech. 
El decorador `@check_eosda_limit` verifica si existe una suscripción activa para el tenant, y si no la encuentra, devuelve error 402.

## Cambios Realizados

### 1. Decorador `billing/decorators.py`
- Modificado para permitir acceso en modo DEBUG=True sin suscripción
- Agregado mensaje de error más descriptivo

### 2. Middleware `billing/middleware.py`
- Modificado para permitir acceso en modo DEBUG=True sin suscripción

### 3. Comando `billing/management/commands/setup_dev_subscription.py`
- Creado para configurar suscripción de desarrollo con límites altos

### 4. `manage.py`
- Cambiado para usar `config.settings.local` por defecto (DEBUG=True)

---

## PASOS PARA EJECUTAR CUANDO VUELVAS

### Paso 1: Detener el servidor actual (si está corriendo)
```bash
# Ctrl+C en el terminal donde corre el servidor
```

### Paso 2: Ejecutar el comando de setup
```bash
cd /Users/sebasflorez16/Documents/Agrotech/agrotech-digital
python manage.py setup_dev_subscription
```

### Paso 3: Reiniciar el servidor
```bash
python manage.py runserver 0.0.0.0:8000
```

### Paso 4: Probar en el frontend
- Ir a la página de parcelas
- Seleccionar una parcela
- Buscar escenas satelitales
- Debería funcionar sin error 402

---

## SI HAY ERRORES

### Error "No module named 'billing'"
El servidor no está usando la configuración correcta. Ejecutar:
```bash
export DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py setup_dev_subscription
```

### Error de base de datos
Asegurarse que PostgreSQL esté corriendo:
```bash
brew services start postgresql
# o
pg_ctl -D /opt/homebrew/var/postgresql@14 start
```

### Error "Plan matching query does not exist"
Ejecutar primero:
```bash
python manage.py seed_plans
python manage.py setup_dev_subscription
```

---

## Resumen de Límites Configurados
- Hectáreas: 999,999 (ilimitado para pruebas)
- Requests EOSDA: 99,999/mes
- Parcelas: 9,999
- Usuarios: 999

---

## Archivos Modificados
1. `/billing/decorators.py` - Tolerancia en DEBUG mode
2. `/billing/middleware.py` - Tolerancia en DEBUG mode  
3. `/billing/management/commands/setup_dev_subscription.py` - Nuevo comando
4. `/manage.py` - Default a config.settings.local

Fecha: 11 de febrero de 2026
