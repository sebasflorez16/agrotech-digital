# 🔧 GUÍA: MIGRACIONES CON DJANGO-TENANTS

## ⚠️ IMPORTANTE: Django-Tenants usa comandos DIFERENTES

Con `django-tenants`, **NO se usa** `python manage.py migrate` normal.

---

## ✅ COMANDOS CORRECTOS PARA DJANGO-TENANTS

### 1. Crear migraciones (igual que Django normal)

```bash
python manage.py makemigrations billing
```

### 2. Aplicar migraciones - COMANDO ESPECIAL

```bash
# ❌ INCORRECTO (Django normal)
python manage.py migrate billing

# ✅ CORRECTO (Django-Tenants)
python manage.py migrate_schemas --shared
```

**¿Por qué `--shared`?**

En tu proyecto tienes 2 tipos de apps:

**SHARED_APPS** (compartidas entre todos los tenants):
- `billing` ← Aquí están los planes
- `authentication`
- `base_agrotech`

**TENANT_APPS** (específicas de cada tenant):
- `parcels`
- `crop`
- `labores`
- `inventario`

---

## 📋 PROCESO COMPLETO CORRECTO

### Paso 1: Verificar que billing está en SHARED_APPS

```bash
grep -A 20 "SHARED_APPS" config/settings/base.py
```

Deberías ver:
```python
SHARED_APPS = [
    'django_tenants',
    'base_agrotech',  # Modelo Client (tenant)
    'authentication',
    'billing',  # ← Aquí debe estar
    # ...
]
```

### Paso 2: Crear migraciones

```bash
python manage.py makemigrations billing
```

Output esperado:
```
Migrations for 'billing':
  billing/migrations/0001_initial.py
    - Create model Plan
    - Create model Subscription
    - Create model Invoice
    - Create model UsageMetrics
    - Create model BillingEvent
```

### Paso 3: Aplicar migraciones a SHARED schema

```bash
python manage.py migrate_schemas --shared
```

Output esperado:
```
=== Running migrate for schema public
Running migrations:
  Applying billing.0001_initial... OK
  Applying billing.0002_auto_... OK
```

### Paso 4: Verificar en PostgreSQL

```bash
python manage.py dbshell
```

```sql
-- Ver que las tablas se crearon en schema public
\dt billing_*

-- Deberías ver:
-- billing_plan
-- billing_subscription
-- billing_invoice
-- billing_usagemetrics
-- billing_billingevent
```

### Paso 5: Crear planes iniciales

```bash
python manage.py create_billing_plans
```

**Esto crea los planes en el schema `public` (compartido)**, accesible por todos los tenants.

---

## 🔍 DIFERENCIA CLAVE: SHARED vs TENANT

### SHARED_APPS (schema `public`)
```
billing_plan         ← Planes son ÚNICOS para toda la plataforma
billing_subscription ← Suscripciones están en public (vinculadas a tenant)
billing_invoice
billing_usagemetrics
billing_billingevent
```

**1 solo conjunto de planes para TODOS los tenants** ✅

### TENANT_APPS (schema `tenant_xxx`)
```
parcels_parcel       ← Cada tenant tiene SUS propias parcelas
crop_crop
labores_labor
inventario_warehouse
```

**Cada tenant tiene sus propios datos** ✅

---

## 🚨 ERRORES COMUNES Y SOLUCIONES

### Error 1: "No such table: billing_plan"

**Causa:** Ejecutaste `migrate` en lugar de `migrate_schemas --shared`

**Solución:**
```bash
python manage.py migrate_schemas --shared
```

---

### Error 2: "billing is in both SHARED_APPS and TENANT_APPS"

**Causa:** billing está duplicado en settings

**Solución:** billing debe estar SOLO en SHARED_APPS
```python
SHARED_APPS = [
    # ...
    'billing',  # ✅ Aquí
]

TENANT_APPS = [
    # ...
    # NO incluir 'billing' aquí
]
```

---

### Error 3: "Can't create subscription for tenant"

**Causa:** Tabla billing_subscription no existe

**Verificar:**
```bash
python manage.py dbshell
```

```sql
SELECT schemaname, tablename 
FROM pg_tables 
WHERE tablename LIKE 'billing_%';

-- Debe mostrar:
-- schemaname | tablename
-- public     | billing_plan
-- public     | billing_subscription
-- etc.
```

---

## 📝 RESUMEN COMANDOS DJANGO-TENANTS

```bash
# 1. Crear migraciones (igual que siempre)
python manage.py makemigrations billing

# 2. Aplicar a SHARED schema (billing, auth, base_agrotech)
python manage.py migrate_schemas --shared

# 3. Aplicar a TODOS los tenants (parcels, crop, labores, etc.)
python manage.py migrate_schemas

# 4. Aplicar solo a UN tenant específico
python manage.py migrate_schemas --tenant=finca_demo

# 5. Ver estado de migraciones
python manage.py showmigrations billing
```

---

## ✅ CHECKLIST PRE-MIGRACIÓN

Antes de ejecutar migraciones, verificar:

- [ ] billing está en SHARED_APPS (no en TENANT_APPS)
- [ ] Archivo create_billing_plans.py existe
- [ ] PostgreSQL está corriendo
- [ ] Base de datos configurada en settings
- [ ] No hay errores de sintaxis en models.py

---

## 🚀 COMANDO FINAL CORRECTO

Para aplicar migraciones de billing:

```bash
# Paso 1
python manage.py makemigrations billing

# Paso 2 - COMANDO CORRECTO
python manage.py migrate_schemas --shared

# Paso 3
python manage.py create_billing_plans
```

**NO usar** `python manage.py migrate billing` ❌

---

¿Listo para ejecutar las migraciones correctamente?
