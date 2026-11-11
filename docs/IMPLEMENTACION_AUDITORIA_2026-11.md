# Implementación de la auditoría — estado

Fecha: 2026-11-10
Alcance: backend `agrotech-digital` + frontend `../agrotech-client-frontend`

## Completado en esta iteración

### Pagos y suscripciones (P0)
- `confirm-payment` ya **no confía** en `plan_tier` ni `billing_cycle` del body:
  deriva plan, ciclo y monto del pago verificado (Wompi/MercadoPago) o de la
  intención guardada en servidor.
- Se valida el **monto en centavos** y la **moneda COP** contra el plan.
- MercadoPago solo activa con estado `authorized`; `pending` ya no da acceso.
- Wompi anual otorga **365 días** y las renovaciones usan el ciclo real
  (antes todo se extendía 30 días).
- `charge_recurring` cobra el monto correcto (mensual/anual), usa referencia
  `renew_` y bloquea el doble procesamiento con `BillingEvent`.
- `subscribe-card` (heredado, sin autenticación ni idempotencia) queda
  deshabilitado con `410 Gone`.
- Webhooks: devuelven 5xx ante error para que la pasarela reintente; la
  deduplicación se marca **después** de procesar.
- Paddle deshabilitado por defecto (`PADDLE_ENABLED=False`).
- Facturas: IVA desglosado sin duplicar el 19%; preview de factura usa el
  precio anual cuando corresponde.
- Precio anual: **20% real** sobre 12 meses (coherente con la UI).

### Billing / tenant
- Endpoints de suscripción, facturas, consumo y cancelación resuelven el
  tenant desde JWT (`Authorization: Bearer`) y no desde `request.tenant`.
- `upgrade` y `create-subscription` ya no permiten upgrades gratis: exigen
  checkout (`402 payment_required`).
- Un cliente existente que paga se actualiza en su tenant; no se crea un
  tenant duplicado.
- Si el correo ya tiene cuenta, el pago se aplica a esa cuenta y se pide
  iniciar sesión (no se emiten tokens desde `confirm-payment`).

### Registro, verificación y login
- Reenvío de verificación visible en el registro y en el login (403).
- El backend acepta email **o** username para reenviar verificación.
- El registro acepta `fbp`, `fbc`, `event_id`, `attribution` y
  `marketing_consent`.
- `CompleteRegistration` se envía a Meta CAPI con el mismo `event_id` del
  pixel.
- Copy de la oferta alineado: **plan gratis permanente** (1 parcela / 30 ha /
  5 análisis), sin prometer 14 días que el producto no entrega.

### Límites y pricing
- Resumen de parcelas lee límites reales del plan (`parcel_limit`,
  `area_limit`, `parcel_restante`) y ya no muestra 50/300 fijos.
- Pricing, plan-detail, checkout y landing alineados con la base de datos.
- Free: 1 parcela / 30 ha / 1 usuario / 5 análisis.
- Basic: 10 / 100 / 2 / 100.
- Pro: 50 / 300 / 3 / 500.
- Se eliminaron claims no sustentados (“precisión milimétrica”, “ahorra 40%”).

### Medición / Meta Ads
- Nuevo `js/meta-tracking.js`: un solo pixel, consentimiento (Ley 1581),
  UTMs/fbclid, `fbp`/`fbc` y helper de eventos.
- Pixel presente en landing, registro, login, checkout, success, pricing y
  plan-detail (antes solo en la landing).
- Nuevo `core/meta_capi.py` + variables `META_*`.
- Eventos: `PageView`, `ViewContent`, `Lead`, `CompleteRegistration`,
  `InitiateCheckout`, `Purchase`, `Subscribe`.
- `Purchase` del pixel y CAPI comparten `event_id` (`purchase_{reference}`).
- El checkout abre el widget de Wompi en el dominio canónico y conserva
  usuario/contraseña/tenant (antes redirigía a otra página que los ignoraba).

### Operación
- Sentry inicializado en producción si `SENTRY_DSN` existe.
- `/health/detailed/` valida DB, caché, EOSDA y storage.
- `ALLOWED_HOSTS` incluye subdominios de tenants.
- `CONN_MAX_AGE=60` en producción.
- `start.sh` ya no imprime credenciales; `collectstatic` falla el deploy si
  no puede completarse.
- Nuevo `python manage.py run_billing_maintenance` para cron de Railway.
- `FRONTEND_URL`/`LOGIN_REDIRECT_URL` apuntan al dominio canónico.

## Verificación ejecutada (local, Postgres real)

- Integrado sobre la `main` de producción (`3155a6f`), no sobre una base vieja.
- `python manage.py check`: sin errores.
- `manage.py check --deploy`: sin hallazgos (salvo el secreto dummy usado en local).
- **199 tests** de billing + autenticación: OK.
- **22 tests** de radar: OK.
- **3 tests** de aislamiento multi-tenant: OK.
- **69 tests** de users/crop/agrotech alerts: OK.
- **21 tests** de modelos de parcelas + validación EODSA: OK.
- `node --check` de todo el JS modificado y de los scripts inline: OK.
- Validación de assets locales del funnel: 0 faltantes, 0 IDs duplicados.

Se corrigió durante la verificación un bug real del parser de referencias
Wompi: el formato nuevo `sub_tenant_tier_yearly_uuid` se interpretaba como
mensual, por lo que un pago anual habría otorgado 30 días. Ahora hay test de
regresión.

## Cómo desplegar

```bash
# Backend
python manage.py create_billing_plans   # sincroniza precios/límites
python manage.py migrate_schemas --shared
python manage.py migrate_schemas
python manage.py collectstatic --noinput

# Tests (en entorno con Postgres/Redis)
pytest billing/tests/test_payment_utils.py
pytest billing/tests/test_wompi_and_trials.py
pytest billing/tests/test_tenant_service.py
```

Variables nuevas en producción:

```
META_PIXEL_ID=1521929183273863
META_CAPI_ACCESS_TOKEN=...
META_CAPI_ENABLED=True
META_CAPI_TEST_EVENT_CODE=   # solo pruebas
FRONTEND_URL=https://agrotechcolombia.com
SENTRY_DSN=...
```

Cron sugerido en Railway (cada hora):

```
python manage.py run_billing_maintenance
```

## Importación de lotes (nuevo)

- Endpoint: `POST /api/parcels/parcel/import/` (multipart, campo `file`).
- Formatos: GeoJSON/JSON, KML, KMZ, Shapefile `.zip`, GPX y GeoPackage.
- Normaliza a EPSG:4326, valida polígonos y reproyecta si el archivo trae CRS.
- Si el archivo tiene varios lotes, crea una parcela por lote.
- Respeta límites de parcelas y hectáreas del plan (atómico: si no cabe, no crea ninguna).
- La sincronización con EOSDA se dispara desde el frontend en segundo plano.
- Tests: `parcels/tests/test_importers.py` (8 pruebas).

## Email transaccional (bloqueador operativo)

Railway **bloquea SMTP saliente** (puerto 587): `smtp.gmail.com` devuelve
`Network is unreachable`. Por eso se implementó `core/email_backends.py`, que
envía por la API HTTPS de Resend.

Para activarlo:

1. Crear cuenta en https://resend.com.
2. Agregar el dominio `agrotechcolombia.com` y crear los registros DNS
   (SPF/DKIM) en Netlify.
3. Generar un API key.
4. En Railway (servicio `agrotech-digital`, environment `production`):
   ```
   RESEND_API_KEY=re_...
   DEFAULT_FROM_EMAIL=AgroTech Digital <noreply@agrotechcolombia.com>
   ```
5. Redeploy y probar registro, reenvío de verificación y recuperación de
   contraseña.

Mientras no exista `RESEND_API_KEY`, los correos fallan y el registro sigue
funcionando (verificación opcional), pero no hay recuperación de contraseña
ni recibos por email.

## Pendiente (siguientes fases)

1. Ejecutar la matriz E2E en staging con Wompi sandbox.
2. Configurar `META_CAPI_ACCESS_TOKEN` y validar eventos en Test Events.
3. Configurar Resend y verificar entrega en Gmail/Outlook.
4. Implementar/decidir trial real de 14 días (hoy es freemium puro).
5. Límites faltantes: storage, clima basic/full, tiles WMTS.
6. Enviar `Contact` (WhatsApp) y `AddPaymentInfo` a Meta.
7. Monitoreo de capacidad EOSDA (cola/worker) y pruebas de carga.
8. Backups automáticos + restore drill.
9. Optimización de imágenes/fuentes y Lighthouse móvil.
10. Campaña Meta Ads: ver `docs/META_ADS_LAUNCH_CHECKLIST.md`.
