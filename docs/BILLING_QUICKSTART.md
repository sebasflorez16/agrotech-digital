# 🚀 Quick Start - Sistema de Billing

Guía rápida para poner en marcha el sistema de suscripciones en **5 pasos**.

---

## ✅ Paso 1: Instalar Dependencias

```bash
pip install -r requirements.txt
```

Esto instalará:
- `mercadopago==2.2.3` (MercadoPago SDK)
- `geoip2==4.8.0` (Detección de país)
- `reportlab==4.2.5` (Generación de PDFs)

---

## ✅ Paso 2: Configurar Variables de Entorno

Copia el archivo de ejemplo:

```bash
cp .env.example .env
```

Edita `.env` y configura **mínimo**:

```bash
# === MERCADOPAGO (Para Colombia) ===
MERCADOPAGO_ACCESS_TOKEN=APP_USR-tu-token-aqui
MERCADOPAGO_PUBLIC_KEY=APP_USR-tu-public-key-aqui

# === PADDLE (Para Internacional) - Opcional ===
PADDLE_VENDOR_ID=12345
PADDLE_API_KEY=tu-api-key
PADDLE_SANDBOX=True  # Usar sandbox para testing

# === GENERAL ===
SITE_URL=http://localhost:8000
```

### Cómo Obtener Credenciales MercadoPago:

1. Ir a [mercadopago.com.co](https://www.mercadopago.com.co)
2. Registrarse / Iniciar sesión
3. Ir a **Tu negocio → Configuración → Desarrolladores**
4. Copiar `Access Token` y `Public Key`
5. Para testing, usa las credenciales de **TEST**
6. Para producción, usa las de **PRODUCCIÓN**

### Cómo Obtener Credenciales Paddle:

1. Ir a [paddle.com](https://www.paddle.com)
2. Registrarse
3. Dashboard → Developer Tools → Authentication
4. Copiar Vendor ID y API Key
5. Activar Sandbox Mode para testing

---

## ✅ Paso 3: Ejecutar Migraciones

```bash
python manage.py makemigrations billing
python manage.py migrate billing
```

Esto creará las tablas:
- `billing_plan`
- `billing_subscription`
- `billing_invoice`
- `billing_usagemetrics`
- `billing_billingevent`

---

## ✅ Paso 4: Crear Planes Iniciales

```bash
python manage.py create_billing_plans
```

**Output esperado:**

```
✓ Plan "Explorador" creado
✓ Plan "Agricultor" creado
✓ Plan "Empresarial" creado
✓ Plan "Corporativo" creado

✓ Proceso completado: 4 creados, 0 actualizados

============================================================
PLANES CONFIGURADOS:
============================================================

FREE         | Explorador      | COP $         0 | USD $  0.00
BASIC        | Agricultor      | COP $    49,000 | USD $ 12.00
PRO          | Empresarial     | COP $   149,000 | USD $ 37.00
ENTERPRISE   | Corporativo     | COP $         0 | USD $  0.00
============================================================
```

---

## ✅ Paso 5: Verificar Funcionamiento

### Opción A: Admin Django

```bash
python manage.py runserver
```

Ir a: `http://localhost:8000/admin/billing/`

Deberías ver:
- ✅ 4 planes creados
- ✅ Sección de Billing en el admin

### Opción B: API REST

```bash
# Obtener planes disponibles
curl http://localhost:8000/billing/api/plans/

# Respuesta esperada:
[
  {
    "tier": "free",
    "name": "Explorador",
    "price_cop": 0,
    "price_usd": 0,
    ...
  },
  ...
]
```

### Opción C: Crear Tenant de Prueba

```bash
python manage.py shell
```

```python
from base_agrotech.models import Client, Domain

# Crear tenant
tenant = Client.objects.create(
    schema_name='demo',
    name='Demo Company'
)

# Crear dominio
Domain.objects.create(
    tenant=tenant,
    domain='demo.localhost',
    is_primary=True
)

# Verificar que tenga plan FREE asignado automáticamente
print(tenant.subscription.plan.tier)  # Debería mostrar: 'free'
print(tenant.subscription.status)     # Debería mostrar: 'trialing'
```

**✅ Si ves 'free' y 'trialing', el sistema funciona correctamente!**

---

## 🔧 Configuración de Webhooks (Producción)

### Para MercadoPago:

1. Dashboard MercadoPago → Webhooks
2. Agregar nueva URL webhook:
   ```
   https://tu-dominio.com/billing/webhooks/mercadopago/
   ```
3. Seleccionar eventos:
   - ✅ Payment
   - ✅ Subscription

### Para Paddle:

1. Paddle Dashboard → Developer Tools → Webhooks
2. Agregar webhook URL:
   ```
   https://tu-dominio.com/billing/webhooks/paddle/
   ```
3. Paddle enviará todos los eventos automáticamente

---

## 📊 Endpoints Disponibles

```bash
# Ver planes
GET /billing/api/plans/

# Ver mi suscripción
GET /billing/api/subscription/
Headers: Authorization: Bearer <jwt_token>

# Crear suscripción
POST /billing/api/subscription/create_subscription/
Body: {"plan_tier": "basic", "billing_cycle": "monthly"}

# Mejorar plan
POST /billing/api/subscription/upgrade/
Body: {"new_plan_tier": "pro"}

# Cancelar
POST /billing/api/subscription/cancel_subscription/
Body: {"immediately": false}

# Ver uso actual
GET /billing/api/usage/

# Ver facturas
GET /billing/api/invoices/
```

---

## 🧪 Testing Local

### Simular Webhook de MercadoPago:

```bash
curl -X POST http://localhost:8000/billing/webhooks/mercadopago/ \
  -H "Content-Type: application/json" \
  -d '{
    "type": "payment",
    "data": {
      "id": "12345"
    }
  }'
```

### Usar ngrok para Exponer Localhost:

```bash
# Terminal 1
python manage.py runserver

# Terminal 2
ngrok http 8000

# Usar URL de ngrok en MercadoPago/Paddle
# Ejemplo: https://abc123.ngrok.io/billing/webhooks/mercadopago/
```

---

## 🚨 Troubleshooting

### Error: "No subscription found"

**Causa:** El tenant no tiene suscripción asignada.

**Solución:**

```python
from billing.signals import create_free_subscription_for_new_tenant
from base_agrotech.models import Client

tenant = Client.objects.get(schema_name='xxx')
create_free_subscription_for_new_tenant(Client, tenant, True)
```

### Error: "MERCADOPAGO_ACCESS_TOKEN not configured"

**Causa:** Variables de entorno no cargadas.

**Solución:**

1. Verificar que `.env` existe
2. Verificar que `DJANGO_READ_DOT_ENV_FILE=True` en `.env`
3. Reiniciar servidor Django

### Error al crear planes: "Duplicate entry"

**Causa:** Ya existen planes con esos tiers.

**Solución:**

```bash
# Re-ejecutar command (actualiza planes existentes)
python manage.py create_billing_plans
```

O eliminar y recrear:

```python
from billing.models import Plan
Plan.objects.all().delete()
```

Luego volver a ejecutar `create_billing_plans`.

---

## 📝 Próximos Pasos

1. **Configurar MercadoPago:**
   - Obtener credenciales de producción
   - Configurar webhook en producción
   - Probar flujo completo de pago

2. **Configurar Paddle (opcional):**
   - Crear productos en Paddle Dashboard
   - Obtener Product IDs
   - Actualizar planes con `paddle_product_id`

3. **Aplicar Decoradores de Límites:**
   ```python
   # En parcels/views.py
   from billing.decorators import check_hectare_limit, check_eosda_limit
   
   @check_hectare_limit
   def create_parcel(request):
       ...
   
   # En parcels/analytics_views.py
   @check_eosda_limit
   def get_satellite_analysis(request, parcel_id):
       ...
   ```

4. **Configurar Email Notifications:**
   - Trial expirando (7 días, 1 día)
   - Pago exitoso
   - Pago fallido
   - Suscripción cancelada

5. **Dashboard Frontend:**
   - Página de planes (pricing table)
   - Dashboard de billing del usuario
   - Gráficos de uso de recursos

---

## 📚 Documentación Completa

Ver [BILLING_GUIDE.md](./BILLING_GUIDE.md) para documentación exhaustiva.

---

**✅ Sistema listo para usar!**

Para cualquier duda, revisar logs en `logs/errors.log` o ejecutar:

```bash
python manage.py shell
from billing.models import *
```
