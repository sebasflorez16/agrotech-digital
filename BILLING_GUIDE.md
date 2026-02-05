# 💳 Sistema de Suscripciones y Billing - AgroTech Digital

Sistema completo de monetización SaaS con soporte multi-gateway para Colombia e internacional.

## 📋 Tabla de Contenidos

1. [Arquitectura General](#arquitectura-general)
2. [Pasarelas de Pago](#pasarelas-de-pago)
3. [Planes Disponibles](#planes-disponibles)
4. [Setup Inicial](#setup-inicial)
5. [Configuración de Variables](#configuración-de-variables)
6. [Uso del Sistema](#uso-del-sistema)
7. [Webhooks](#webhooks)
8. [Limitación de Recursos](#limitación-de-recursos)
9. [Facturación](#facturación)
10. [Testing](#testing)

---

## 🏗️ Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                   AGROTECH DIGITAL BILLING                      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ├── COLOMBIA (COP)
                            │   └── MercadoPago
                            │       ├── Suscripciones recurrentes
                            │       ├── Fee: 3.99% + 900 COP
                            │       └── Retiro a cuenta colombiana
                            │
                            └── INTERNACIONAL (USD/EUR)
                                └── Paddle
                                    ├── Merchant of Record
                                    ├── Fee: 5% + $0.50 USD
                                    ├── Maneja compliance fiscal global
                                    └── Retiro vía Wise/Wire Transfer
```

### Componentes Principales

- **`billing/models.py`**: Modelos de Plan, Subscription, Invoice, UsageMetrics
- **`billing/gateways.py`**: Abstract PaymentGateway + Factory pattern
- **`billing/mercadopago_gateway.py`**: Integración MercadoPago
- **`billing/paddle_gateway.py`**: Integración Paddle
- **`billing/middleware.py`**: Verificación de suscripción activa
- **`billing/decorators.py`**: Límites de recursos (@check_hectare_limit, etc.)
- **`billing/views.py`**: API endpoints REST
- **`billing/webhooks.py`**: Procesamiento de notificaciones

---

## 💰 Pasarelas de Pago

### MercadoPago (Colombia)

**Ventajas:**
- ✅ Nativo en Colombia (COP)
- ✅ Suscripciones recurrentes nativas
- ✅ Retiros gratis a cuenta colombiana
- ✅ Webhooks confiables
- ✅ SDK Python oficial

**Limitaciones:**
- ❌ Solo COP (no USD/EUR)
- ❌ No óptimo para clientes internacionales

**Setup:**
1. Crear cuenta en [mercadopago.com.co](https://www.mercadopago.com.co)
2. Obtener credenciales en Dashboard → Desarrolladores
3. Configurar webhook URL: `https://tu-dominio.com/billing/webhooks/mercadopago/`

### Paddle (Internacional)

**Ventajas:**
- ✅ Merchant of Record (maneja toda la facturación)
- ✅ Compliance fiscal automático (VAT, sales tax, etc.)
- ✅ Multi-moneda (USD, EUR, GBP, etc.)
- ✅ Simplifica enormemente compliance internacional

**Limitaciones:**
- ❌ Fee más alto (5% vs 3.99%)
- ❌ No acepta COP directamente

**Setup:**
1. Crear cuenta en [paddle.com](https://www.paddle.com)
2. Configurar productos en Paddle Dashboard
3. Obtener Vendor ID y API Key
4. Configurar webhook URL: `https://tu-dominio.com/billing/webhooks/paddle/`

---

## 📊 Planes Disponibles

### FREE - Explorador
**Precio:** $0 COP/mes  
**Límites:**
- 50 hectáreas
- 1 usuario
- 20 análisis EOSDA/mes
- 3 parcelas
- 100 MB almacenamiento
- 3 meses de histórico

**Incluye:**
- Análisis NDVI básico
- Clima actual
- Mapa base satelital

### BASIC - Agricultor
**Precio:** $49,000 COP/mes (~$12 USD)  
**Límites:**
- 300 hectáreas
- 3 usuarios
- 100 análisis EOSDA/mes
- 10 parcelas
- 500 MB almacenamiento
- 12 meses de histórico

**Incluye:**
- Todos los índices (NDVI, NDMI, EVI)
- Pronóstico 7 días
- Alertas por correo
- Exportar CSV

### PRO - Empresarial
**Precio:** $149,000 COP/mes (~$37 USD)  
**Límites:**
- 1,000 hectáreas
- 10 usuarios
- 500 análisis EOSDA/mes
- 50 parcelas
- 2 GB almacenamiento
- 36 meses de histórico

**Incluye:**
- API REST ilimitada
- Reportes PDF automatizados
- Webhooks/Integraciones
- Dashboard personalizado
- Soporte prioritario 12h

### ENTERPRISE - Corporativo
**Precio:** Custom  
**Límites:**
- ♾️ Ilimitado todo

**Incluye:**
- Todo en Pro +
- Servidor dedicado
- SLA 99.9%
- Account manager
- Capacitación on-site

---

## 🚀 Setup Inicial

### 1. Instalar Dependencias

```bash
pip install mercadopago==2.2.3
pip install geoip2==4.8.0
pip install reportlab==4.2.5
```

### 2. Agregar App a INSTALLED_APPS

Ya está agregado en `config/settings/base.py`:

```python
SHARED_APPS = [
    # ...
    "billing",
]
```

### 3. Ejecutar Migraciones

```bash
python manage.py makemigrations billing
python manage.py migrate billing
```

### 4. Crear Planes Iniciales

```bash
python manage.py create_billing_plans
```

Esto creará los 4 planes (Free, Basic, Pro, Enterprise) con sus límites configurados.

### 5. Asignar Plan FREE Automáticamente

El sistema automáticamente asigna el plan FREE a nuevos tenants mediante un signal en `billing/signals.py`.

---

## ⚙️ Configuración de Variables

### Variables de Entorno (.env)

```bash
# === MercadoPago (Colombia) ===
MERCADOPAGO_ACCESS_TOKEN=APP_USR-xxxxxxxxxx
MERCADOPAGO_PUBLIC_KEY=APP_USR-xxxxxxxxxx
MERCADOPAGO_WEBHOOK_SECRET=tu_webhook_secret

# === Paddle (Internacional) ===
PADDLE_VENDOR_ID=12345
PADDLE_API_KEY=xxxxxxxxxxxxxxxx
PADDLE_PUBLIC_KEY=xxxxxxxxxxxxxxxx
PADDLE_SANDBOX=True  # False en producción

# === General ===
SITE_URL=https://agrotechcolombia.com
DEFAULT_COUNTRY=CO
```

### Railway Environment Variables

En Railway dashboard, configurar:

```
MERCADOPAGO_ACCESS_TOKEN
MERCADOPAGO_PUBLIC_KEY
PADDLE_VENDOR_ID
PADDLE_API_KEY
PADDLE_SANDBOX=False
SITE_URL=https://agrotechcolombia.com
```

---

## 💻 Uso del Sistema

### API Endpoints

#### Obtener Planes Disponibles

```bash
GET /billing/api/plans/

Response:
[
  {
    "tier": "free",
    "name": "Explorador",
    "price_cop": 0,
    "price_usd": 0,
    "limits": {
      "hectares": 50,
      "users": 1,
      "eosda_requests": 20
    },
    "features_included": [...]
  },
  ...
]
```

#### Obtener Suscripción Actual

```bash
GET /billing/api/subscription/
Headers: Authorization: Bearer <jwt_token>

Response:
{
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
  "plan": {
    "tier": "basic",
    "name": "Agricultor"
  },
  "status": "active",
  "current_period_end": "2026-03-01T00:00:00Z",
  "days_until_renewal": 25
}
```

#### Crear Suscripción

```bash
POST /billing/api/subscription/create_subscription/
Headers: Authorization: Bearer <jwt_token>
Body:
{
  "plan_tier": "basic",
  "billing_cycle": "monthly"
}

Response:
{
  "success": true,
  "checkout_url": "https://www.mercadopago.com/checkout/xxx",
  "subscription": {...}
}
```

#### Mejorar Plan (Upgrade)

```bash
POST /billing/api/subscription/upgrade/
Body:
{
  "new_plan_tier": "pro"
}
```

#### Cancelar Suscripción

```bash
POST /billing/api/subscription/cancel_subscription/
Body:
{
  "immediately": false,  # true para cancelar ahora
  "reason": "Ya no necesito el servicio"
}
```

#### Consultar Uso Actual

```bash
GET /billing/api/usage/

Response:
{
  "year": 2026,
  "month": 2,
  "hectares_used": 120.5,
  "eosda_requests": 45,
  "users_count": 2,
  "plan": {
    "name": "Agricultor",
    "limits": {
      "hectares": 300,
      "eosda_requests": 100
    }
  },
  "usage_percentages": {
    "hectares": 40.17,
    "eosda_requests": 45.0
  }
}
```

---

## 🔔 Webhooks

### MercadoPago Webhook

**URL:** `https://tu-dominio.com/billing/webhooks/mercadopago/`

**Eventos manejados:**
- `payment` → Pago procesado (éxito/fallo)
- `subscription_preapproval` → Cambio en suscripción

**Configuración en MercadoPago:**
1. Dashboard → Webhooks
2. Agregar URL
3. Seleccionar eventos: Payment, Subscription

### Paddle Webhook

**URL:** `https://tu-dominio.com/billing/webhooks/paddle/`

**Eventos manejados:**
- `subscription_created`
- `subscription_updated`
- `subscription_cancelled`
- `subscription_payment_succeeded`
- `subscription_payment_failed`

**Configuración en Paddle:**
1. Dashboard → Developer Tools → Webhooks
2. Agregar URL
3. Paddle envía todos los eventos automáticamente

---

## 🔒 Limitación de Recursos

### Middleware de Suscripción

El middleware `SubscriptionLimitMiddleware` verifica automáticamente:
- ✅ Suscripción activa
- ✅ Trial no expirado
- ✅ Estado válido

**URLs excluidas:**
- `/health/`
- `/admin/`
- `/api/auth/`
- `/billing/webhook/`

### Decoradores de Límites

#### @check_hectare_limit

Verifica límite de hectáreas antes de crear parcela:

```python
from billing.decorators import check_hectare_limit

@check_hectare_limit
def create_parcel(request):
    # Crear parcela solo si no excede límite
    ...
```

#### @check_eosda_limit

Verifica límite de peticiones EOSDA:

```python
from billing.decorators import check_eosda_limit

@check_eosda_limit
def get_satellite_analysis(request, parcel_id):
    # Ejecutar análisis solo si hay cuota disponible
    ...
```

#### @feature_required

Verifica que el plan incluya una feature:

```python
from billing.decorators import feature_required

@feature_required('advanced_analytics')
def get_advanced_report(request):
    # Solo disponible en planes Pro+
    ...
```

### Respuestas de Error

Cuando se excede un límite:

```json
HTTP 403 Forbidden
{
  "error": "Límite de hectáreas excedido",
  "code": "hectares_limit_exceeded",
  "current": 280,
  "new": 51,
  "total": 331,
  "limit": 300,
  "plan": "Agricultor",
  "message": "Tu plan Agricultor permite hasta 300 hectáreas...",
  "upgrade_url": "/billing/upgrade/"
}
```

---

## 📄 Facturación

### Facturas Automáticas

El sistema genera facturas automáticamente cuando:
- Se procesa un pago exitoso
- Se renueva una suscripción

### Factura Simple (MVP)

Inicialmente se generan facturas PDF simples con:
- Numeración consecutiva (AGRO-000001)
- IVA 19% (Colombia)
- Datos completos del tenant
- Detalles de líneas

### Facturación Electrónica DIAN (Futuro)

**¿Cuándo implementar?**
- Cuando ingresos > $100M COP/mes
- Cuando tengas 50+ clientes empresariales

**Solución recomendada:**
- Integrar con Alegra (~$50k COP/mes)
- O usar MercadoPago (facturación DIAN nativa)

---

## 🧪 Testing

### Tests Unitarios

```bash
# Correr tests de billing
pytest billing/tests/

# Con cobertura
pytest billing/ --cov=billing --cov-report=html
```

### Tests de Integración

Crear tenants de prueba:

```bash
python manage.py shell

from base_agrotech.models import Client, Domain
from billing.models import Plan, Subscription

# Crear tenant de prueba
tenant = Client.objects.create(
    schema_name='test_tenant',
    name='Test Company'
)
Domain.objects.create(
    tenant=tenant,
    domain='test.localhost',
    is_primary=True
)

# Verificar que tenga plan FREE asignado
print(tenant.subscription.plan.tier)  # 'free'
```

### Testing de Webhooks (Local)

Usar ngrok para exponer localhost:

```bash
# Terminal 1: Correr servidor
python manage.py runserver

# Terminal 2: Exponer con ngrok
ngrok http 8000

# Copiar URL de ngrok (ej: https://abc123.ngrok.io)
# Configurar en MercadoPago/Paddle:
# Webhook URL: https://abc123.ngrok.io/billing/webhooks/mercadopago/
```

---

## 📈 Métricas de Uso

El sistema rastrea automáticamente:
- Hectáreas usadas
- Peticiones EOSDA realizadas
- Número de usuarios
- Número de parcelas
- Almacenamiento

Actualización:
- En tiempo real (cada acción)
- Agregación mensual en `UsageMetrics`

---

## 🔐 Seguridad

### Validación de Webhooks

**MercadoPago:**
- Verifica header `x-signature`
- TODO: Implementar verificación completa

**Paddle:**
- Verifica firma `p_signature`
- TODO: Implementar verificación RSA con public key

### Autenticación de API

Todos los endpoints (excepto webhooks) requieren:
- JWT Token en header `Authorization: Bearer <token>`

---

## 🚀 Deployment

### Railway

1. Configurar variables de entorno
2. Las migraciones corren automáticamente
3. Ejecutar management command:

```bash
railway run python manage.py create_billing_plans
```

### Netlify (Frontend)

Configurar redirects para billing callbacks:

```toml
# netlify.toml
[[redirects]]
  from = "/billing/success"
  to = "/dashboard?payment=success"
  status = 200

[[redirects]]
  from = "/billing/cancel"
  to = "/plans?payment=canceled"
  status = 200
```

---

## 📚 Recursos Adicionales

- [Documentación MercadoPago](https://www.mercadopago.com.co/developers)
- [Documentación Paddle](https://developer.paddle.com)
- [Django Tenants](https://django-tenants.readthedocs.io/)

---

## 🆘 Troubleshooting

### "No subscription found"

Verificar que el tenant tenga suscripción:

```python
python manage.py shell
from base_agrotech.models import Client
tenant = Client.objects.get(schema_name='xxx')
print(tenant.subscription)
```

Si no existe, el signal no corrió. Crear manualmente:

```python
from billing.signals import create_free_subscription_for_new_tenant
create_free_subscription_for_new_tenant(Client, tenant, True)
```

### Webhook no se procesa

1. Verificar logs: `logs/errors.log`
2. Verificar que la URL sea accesible (no localhost)
3. Verificar firma del webhook (temporalmente desactivada para testing)

### Límites no se aplican

1. Verificar que SubscriptionLimitMiddleware esté en MIDDLEWARE
2. Verificar que los decorators estén aplicados en las vistas correctas
3. Verificar métricas: `UsageMetrics.get_or_create_current(tenant)`

---

**Desarrollado por:** AgroTech Digital  
**Versión:** 1.0.0  
**Última actualización:** Febrero 2026
