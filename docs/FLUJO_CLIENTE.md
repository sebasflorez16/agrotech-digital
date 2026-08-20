# DOCUMENTO 2 — FLUJO DE TRABAJO DEL CLIENTE EN AGROTECH

> Auditoría del flujo **real actualmente implementado**, de extremo a extremo,
> desde la perspectiva de un cliente/tenant. No describe lo que "debería"
> existir ni funcionalidades futuras.
>
> **Leyenda de estados** (usada en todo el documento):
> - ✅ **FUNCIONAL** — implementado y conectado de punta a punta.
> - ⚠️ **PARCIAL** — implementado pero incompleto, defectuoso o no conectado del todo.
> - 🧪 **SIMULADO** — devuelve datos generados en código (random/numpy), no datos reales.
> - ❌ **ROTO / NO EXISTE** — no funciona tal cual está, o no existe.
>
> Fecha de auditoría: 2026-08-14.

---

## 1. Contexto técnico general (para leer el resto)

- **Arquitectura**: Django **multi-tenant** con `django-tenants`. Cada cliente
  (tenant) vive en un **schema PostgreSQL** separado. El tenant se modela en
  `base_agrotech.Client` y el usuario en `metrica.users.User`
  (`AUTH_USER_MODEL = "users.User"`, `config/settings/base.py:253`).
- **Autenticación**: JWT (`rest_framework_simplejwt`). El token lleva `tenant_id`
  en el payload; el middleware `config/middleware.py` (`SmartTenantMiddleware`)
  resuelve el tenant a partir del **JWT** (o del header `X-Tenant-Domain`), no
  del subdominio. Sin JWT en rutas no públicas → **401**.
- **Dos frontends**: el **operativo** es el dashboard HTML servido por Django
  (`metrica/templates/parcels/parcels-dashboard.html` + JS en
  `metrica/static/js/parcels/`). Existe además un SPA React en `frontend/` cuyo
  flujo de registro está **desalineado** con el backend (ver §2).
- **EOSDA**: una sola API Key compartida por todos los tenants. El acceso se
  centraliza en `parcels/eosda_client.py`.

---

## 2. Registro e ingreso del usuario

### Registro
1. **Usuario**: rellena el formulario de registro (nombre, email, usuario,
   contraseña, **nombre de la organización**).
2. **Frontend**: envía `POST /api/auth/register/`. ⚠️ El SPA React
   (`frontend/src/api/client.js:105`, `frontend/src/pages/Register.jsx:7`)
   envía un contrato **que no coincide** con el backend: le faltan
   `organization_name` y `name`. **El registro por la UI está roto.**
3. **Backend**: `RegisterView` + `RegisterSerializer`
   (`authentication/views.py:47`, `authentication/serializers.py:21`). Valida
   email único, bloquea dominios desechables, fortaleza de contraseña, y genera
   `schema_name` desde `organization_name`. `RegistrationService.register()`
   (`authentication/services.py:40`) en una sola transacción crea: **tenant
   (Client) → Domain → usuario admin → suscripción**.
4. **Base de datos**: crea el schema del tenant (Postgres), el `Client`, el
   `Domain`, el `User` con `role='admin'` e `is_active=False` (pendiente de
   verificación), y la `Subscription` free (vía signal
   `billing/signals.py`).
5. **EOSDA**: no interviene.
6. **Caché**: no aplica.

**Verificación de email** — ⚠️ PARCIAL:
- El usuario recibe un email con token; `POST /api/auth/verify-email/?token=...`
  activa la cuenta (`authentication/views.py:150`).
- ⚠️ **Si el envío de email falla**, el error se traga en silencio
  (`authentication/services.py:89-98`, doble `except` con código muerto) y el
  usuario queda **inactivo sin forma de reenviar** (no existe endpoint de
  reenvío).

### Login — ✅ FUNCIONAL
1. **Usuario**: entra usuario/email y contraseña.
2. **Frontend**: `POST /api/auth/login/`; guarda `accessToken`/`refreshToken`/
   `userData` en `localStorage`.
3. **Backend**: `LoginView` (`authentication/views.py:181`) devuelve
   `{tokens:{access,refresh}, user:{...}}` con `tenant_id` inyectado en el JWT.
   Access 30 min, refresh 7 días con rotación y blacklist.
4. **Base de datos**: consulta `User` por username/email.
5. **EOSDA**: no interviene.
6. **Caché**: no aplica.

- Logout, refresh y cambio de contraseña: ✅ FUNCIONAL.
- **Recuperación de contraseña ("olvidé mi contraseña"): ❌ NO EXISTE**
  (solo referencias a vistas inexistentes en `authentication/urls_pages.py`).

---

## 3. Creación y configuración del tenant

El tenant se crea por **tres vías**, una rota:

| Vía | Estado |
|---|---|
| Registro vía API (`RegistrationService._create_tenant`) | ✅ FUNCIONAL (`authentication/services.py:100`) |
| Checkout/pago (`TenantService.create_tenant_for_subscription`) | ✅ FUNCIONAL (`billing/tenant_service.py:69`) |
| Comando `python manage.py create_tenant` | ❌ ROTO (`base_agrotech/.../create_tenant.py:63` usa `description=` que no existe en el modelo, y omite `paid_until`/`on_trial` requeridos) |

Al crearse el tenant, el `Client` tiene `auto_create_schema=True`, así que se
crea el schema Postgres automáticamente. El plan **free** se asigna por signal
`billing/signals.py`; los planes pagos se crean tras verificar el pago
(MercadoPago/Wompi/Paddle).

**Configuración del tenant**: ❌ NO existe una pantalla de configuración del
tenant (nombre, logo, plan, etc.) accesible para el cliente. Solo el operador
global gestiona tenants desde el panel staff.

---

## 4. Gestión de usuarios y permisos dentro del tenant

- **Roles**: el campo `User.role` (`admin/manager/employee/accountant`) existe
  (`metrica/users/models.py:110`), pero **no se usa para autorizar nada**: todos
  los endpoints del tenant usan solo `permissions.IsAuthenticated`. ⚠️ PARCIAL.
- **Invitar usuarios: ❌ NO EXISTE** (no hay endpoint/UI).
- **Crear/editar usuarios por tenant**: ⚠️ PARCIAL y defectuoso. Existen vistas
  CRUD (`metrica/users/views.py`) con templates de un proyecto "hospital"
  heredado, y `UserCreationForm` **no setea contraseña** → el usuario creado no
  puede loguearse (`metrica/users/forms.py:13`).
- **Límite de usuarios por plan**: el decorador `users_limit_check` está
  **definido pero nunca aplicado** (`billing/decorators.py:400`). Solo una vista
  CRUD defectuosa lo consulta. ⚠️ Casi muerto.

---

## 5. Creación y gestión de parcelas/campos

### Creación — ✅ FUNCIONAL (con matices)
1. **Usuario**: dibuja un polígono en el mapa (Leaflet.Draw) y rellena el
   formulario (nombre, tipo de campo, suelo, topografía).
2. **Frontend** (`parcel.js`): convierte `[lat,lng]`→`[lng,lat]`, cierra el
   anillo, arma GeoJSON `{type:"Polygon", coordinates:[...]}` y hace
   `POST /api/parcels/parcel/`.
3. **Backend** (`ParcelViewSet.create`, `parcels/views.py:427`):
   - Límite de **parcelas** por plan → 403 `parcels_limit_exceeded`.
   - Límite de **hectáreas** por plan → 403 `hectares_limit_exceeded`.
   - Sin suscripción → 402 `no_subscription`.
   - Guarda el registro con `tenant_id`.
4. **Base de datos**: inserta `Parcel` con `geom` como **JSONField (GeoJSON)**
   (NO PostGIS; el código GIS está comentado).
5. **EOSDA**: durante `Parcel.save()` se intenta crear el campo en EOSDA
   (§6). Es **no fatal**.
6. **Caché**: no aplica.

### Listar / editar / eliminar — ✅ FUNCIONAL
- `GET /api/parcels/parcel/` (listado, envuelto en `{cesium_token, parcels}`).
- `PATCH parcel/<id>/` para editar nombre/descripción/tipo/suelo/topografía.
  ⚠️ **No se puede editar/redibujar la geometría** desde la UI.
- `DELETE parcel/<id>/` → **soft delete** (`is_deleted=True`).

⚠️ **Inconsistencias**:
- El **área** se calcula con la fórmula Shoelace equirectangular (constante
  `111320`) tanto en el modelo (`parcels/models.py:31`) como en el ViewSet
  (`parcels/views.py:338`), mientras el frontend usa área **esférica** → el área
  que ve el usuario y la que usa el límite difieren.
- `Parcel.clean()` (validación de 300 ha) está **comentado**; el límite solo se
  aplica en el ViewSet.

---

## 6. Qué ocurre técnicamente al crear una parcela (EOSDA)

Dentro de `Parcel.save()` (`parcels/models.py:79-135`):

1. `full_clean()` valida campos.
2. Si `no eosda_id` y hay geometría → intenta crear el campo:
   - `POST https://api-connect.eos.com/field-management` con GeoJSON Feature,
     header `x-api-key`, **a través del cliente central** (`get_eosda_client().post`).
   - Si `200/201` → guarda `eosda_id`.
   - Si `402` (límite) o cualquier otro error, o **sin API Key** → imprime y
     **continúa**: la parcela se guarda **sin** `eosda_id`.
3. `super().save()` se ejecuta siempre.

**Estado: ⚠️ PARCIAL.**
- La parcela **siempre se guarda localmente**, sincronizada o no. El usuario ve
  un toast "guardada localmente, pero NO sincronizada" (`parcel.js:644`).
- ⚠️ La creación de campo **no se registra** como consumo: no llama a
  `client.record()`, así que **no** incrementa `eosda_requests` ni escribe
  `EosdaRequestLog` (solo consume token del rate limiter).
- ⚠️ No hay verificación de que `field-management` sea el endpoint correcto de
  creación de campo de EOSDA API Connect.
- ⚠️ Una parcela sin `eosda_id` fallará después en las funciones satelitales
  (404 "campo no encontrado").

---

## 7. Dashboard y visualización de información satelital (mapas, tiles)

**Dashboard de parcelas** (`parcels_dashboard_view` → `parcels-dashboard.html`): ✅ FUNCIONAL.

1. **Usuario**: abre el dashboard y ve el mapa, la lista de parcelas y paneles de
   análisis satelital/meteorológico.
2. **Frontend**: Leaflet con capas Esri/OSM, geocoder Nominatim (proxy),
   tabla de parcelas con acciones Ver/Editar/Eliminar, paneles "Análisis de
   Imagen Satelital", "Info Parcela", "Estado Rápido".
3. **Backend**: `GET /api/parcels/parcel/` (lista) y `summary`.
4. **Base de datos**: `Parcel`, `ParcelSceneCache`, `CropHealthStatus`.
5. **EOSDA**: no directamente en el listado (solo al solicitar análisis).
6. **Caché**: no aplica al listado.

⚠️ **Notas**:
- **Bug de render**: `loadParcels()` dibuja el polígono solo si `parcel.geometry`
  existe, pero el serializador devuelve `geom` → los polígonos probablemente no
  se dibujan al cargar la lista (`parcel.js:739` vs `serializers.py:17`).
- El texto "Visualización 3D por CesiumJS" es **residual**: la implementación
  real es Leaflet; hay código Cesium muerto (`parcel.js:855-902`).
- Hay **duplicados** de templates/JS en `staticfiles/` (copias de collectstatic);
  la fuente real es `metrica/`.

### Tiles WMTS (Render API) — ✅ FUNCIONAL
`parcels/proxy.py` proxyea `api-connect.eos.com/api/render/{scene}/{layer}/{z}/{x}/{y}?api_key=...`.
- **Cache 24 h por tile** (servidor) + `Cache-Control` de 24 h (navegador).
- Pasa por el cliente central **sin rate limiter** (`rate_limit=False`), porque
  la Render API es un producto distinto y un mapa carga decenas de tiles.
- **No** cuenta en `eosda_requests` ni en `EosdaRequestLog`.

---

## 8. Flujo de búsqueda de escenas — ✅ FUNCIONAL

1. **Usuario**: selecciona una parcela y un rango de fechas; pulsa "buscar escenas".
2. **Frontend**: `GET /api/parcels/parcel/<id>/scenes/?start_date=...&end_date=...`
   (o `POST /api/parcels/eosda-scenes/`). Tiene caché de escenas en memoria
   (`window.EOSDA_SCENES_CACHE`).
3. **Backend** (`ParcelScenesByDateView` / `EosdaScenesView`):
   - `POST https://api-connect.eos.com/scene-search/for-field/{eosda_id}`.
   - Recibe `request_id` y hace **polling** (`GET .../{request_id}`) hasta 10
     intentos cada 3 s, hasta que `status != 'pending'`.
4. **Base de datos**: guarda escenas en `ParcelSceneCache` (7 días) y actualiza
   `CropHealthStatus`.
5. **EOSDA**: 1 POST + N GET de polling.
6. **Consumo/caché**: la vista `EosdaScenesView` usa `client.cached()` (cache +
   **deduplicación**): si dos usuarios piden las mismas escenas a la vez, solo
   **1** sale a EOSDA. La caché dura 6 h. Un **cache hit no consume nada**.

---

## 9. Análisis e índices disponibles (EOSDA vs backend)

**Índices que se consultan de VERDAD a EOSDA:**

| Índice | ¿Real contra EOSDA? | Dónde |
|---|---|---|
| **NDVI** | ✅ Real | imagen, escenas-analytics, histórico, analytics, ndvi_historical |
| **NDMI** | ✅ Real | imagen, water-stress, escenas-analytics, histórico, analytics |
| **EVI** | ✅ Real | imagen, escenas-analytics, histórico, analytics |
| **SAVI** | ✅ Real | imagen (`EosdaImageView`), escenas-analytics |
| **NDRE** | ✅ Real | imagen (`EosdaImageView`), escenas-analytics, analytics (gdw) |
| lai / fpar / fcover | ⚠️ Passthrough sin validar soporte | `EosdaSceneAnalyticsView` |
| B01–B12 (bandas) | ✅ Real (mt_stats) | `EosdaAdvancedStatisticsView` |

**Índices SIMULADOS (generados con numpy/random en código):**

| Índice | Dónde | Método |
|---|---|---|
| NDVI/NDMI/SAVI/NDRE | Zonificación | `np.random` + gradiente espacial (`zonification_pipeline.py:189`) |
| vv/vh/rvi (radar) | Sentinel-1 | sigma0 real extraído de productos GRD (ya no es modelo empírico) |

**Resumen EOSDA vs backend:**
- EOSDA sí soporta (a nivel de producto) muchos índices/bandas. Nuestro backend
  expone de forma real: **NDVI, NDMI, EVI, SAVI, NDRE** (imagen y escenas-analytics),
  y bandas espectrales **B01–B12** (estadística avanzada).
- **NDRE** está implementado en los flujos reales de imagen (`field-imagery/indicies`)
  y de escenas-analytics (`v1/indices/ndre`).
- **SAVI** se corrigió el mapeo "fantasma" en analytics (mt_stats); ahora SAVI y
  NDRE se consultan donde EOSDA los soporta (imagen y v1/indices).

---

## 10. Flujo de análisis históricos — ⚠️ PARCIAL

`ParcelHistoricalIndicesView` (`parcels/views.py:1844`, URL
`/api/parcels/parcel/<id>/historical-indices/`):

1. **Usuario**: pulsa "gráfico histórico".
2. **Frontend**: `historical-chart.js` grafica NDVI/NDMI/EVI con Chart.js.
3. **Backend**: para cada índice (ndvi, ndmi, evi) hace
   `POST field-analytics/trend/{eosda_id}` + polling (hasta 2 intentos).
4. **Base de datos**: guarda en caché 6 h y actualiza `CropHealthStatus`.
5. **EOSDA**: 3 POST + hasta 6 GET.
6. **Consumo/caché**: 1 operación de análisis (`historical_indices`). Cache hit = 0 consumo.

⚠️ **Problema crítico**: cuando EOSDA falla o la tarea no termina, el backend
genera **datos aleatorios de prueba** (`_generate_test_data`, `random.random()`)
**sin marcar que son falsos**, y además **actualiza la salud del cultivo** con
esos datos simulados (`views.py:1997→2051`). El gráfico histórico puede mostrar
valores inventados como si fueran reales.

---

## 11. Otras funcionalidades existentes

| Funcionalidad | Endpoint | Dato | Estado |
|---|---|---|---|
| Pronóstico del clima | `/parcel/<id>/weather-forecast/` | Open-Meteo real (16 días), plan-gated | ✅ FUNCIONAL |
| Comparativa NDVI-clima | `/parcel/<id>/ndvi-weather-comparison/` | Open-Meteo Archive real + **fallback sintético**; NO devuelve NDVI pese al nombre | ⚠️ PARCIAL |
| Elevación/topografía | `/parcel/<id>/elevation/` | Open-Meteo Elevation real + heatmap PNG | ✅ FUNCIONAL |
| Radar Sentinel-1 | `/parcel/<id>/radar/` | Monitoreo radar REAL (GRD VV+VH): serie temporal, cambio → "requiere revisión". Sin datos → "no disponible" | ✅ FUNCIONAL (extracción real pendiente de validar contra proveedor) |
| Fusión multi-fuente | `/parcel/<id>/fusion-assessment/` | Óptico real-condicional + radar semi-simulado; **clima nunca se alimenta** | ⚠️ PARCIAL |
| Salud del cultivo | `/parcel/<id>/health/` | Deriva de EOSDA, pero puede contaminarse con fallback sintético | ⚠️ PARCIAL |
| Zonificación (precisión) | `/parcel-zonifications/`, `/parcel-zones/` | **100 % sintético** (numpy + KMeans) | 🧪 SIMULADO |
| Ciclos de cultivo | `/api/crop/cycles/...` | CRUD + interpretación por etapa fenológica (sin datos satelitales propios) | ✅ FUNCIONAL |
| Reporte PDF ejecutivo | `/parcel/<id>/report/` | ReportLab real, plan-gated (`pdf_reports`) | ✅ FUNCIONAL |

---

## 12. Caché: cuándo el cliente NO paga una request

Regla general: **solo se consume lo que sale de verdad a EOSDA**.

| Escenario | ¿Llama a EOSDA? | ¿Token rate limiter? | ¿+1 `eosda_requests`? | ¿Fila en log? |
|---|---|---|---|---|
| Análisis nuevo (cache miss) | Sí | Sí (1 por HTTP) | Sí (1 por análisis) | Sí |
| Mismo análisis repetido (cache hit) | No | No | No | No |
| Tiles ya cacheados | No | No | No | No |
| Creación de campo (parcela) | Sí (1 POST) | Sí | **No** | **No** |

**Tiempos de caché actuales:**
- Escenas: 6 h (`eosda_scenes_*`).
- Imagen generada (request_id): 30 min; imagen descargada: 1 h.
- Analytics por escena: 2 h.
- Estadística avanzada: 1 h (tarea) / 24 h (resultado).
- Histórico: 6 h.
- Tiles: 24 h (servidor + navegador).
- Elevación: 30 días.

---

## 13. Registro del consumo (las 3 capas)

(Conserva la observación de la auditoría anterior.)

1. **Rate limiter global** — cuenta **cada HTTP** a EOSDA. Límite **8/min**,
   **global** (una sola API Key). No es por tenant.
2. **Cuota mensual por tenant** (`UsageMetrics.eosda_requests`) — cuenta **cada
   operación de análisis (1 por invocación de endpoint de análisis EOSDA)**. Se
   incrementa solo en `EosdaClient.record()`. Una imagen completa (generar +
   descargar) cuenta 2 (`image` + `image_result`). No equivale a la facturación
   comercial de EOSDA (pendiente de confirmar con el proveedor).
3. **Registro de auditoría** (`EosdaRequestLog`, schema `public`) — 1 fila por
   cada `record()` (misma granularidad que `eosda_requests`), con tenant,
   usuario, parcela, operación, índice, fecha y `source` (`eosda`/`cache`).

**Exposición al cliente**:
- El cliente **sí puede ver su consumo agregado** (eosda_requests, parcelas,
  hectáreas, usuarios, %) vía `GET /billing/api/usage/dashboard/` y
  `/billing/api/usage/history/`.
- ⚠️ Pero el dashboard de uso está **roto**: `usage_dashboard_view` referencia
  `User` sin definir → `NameError`/500 (`billing/views.py:608`); el historial y
  la factura tienen **formato desalineado** con el JS (`billing-liquid.js`).
- El **detalle** por request (`EosdaRequestLog`) **no está expuesto al cliente**
  (solo en Django admin y en el panel staff).

**Panel staff/operador** (global): ✅ FUNCIONAL. Ve consumo agregado por tenant,
totales de `eosda_requests`, y puede suspender/reactivar/cambiar plan
(`billing/views_staff.py`).

---

## 14. Cuota y límites alcanzados

El backend emite respuestas ricas (con `code`, `upgrade_url`, sugerencias), pero
el frontend del cliente casi no las consume.

| Código | HTTP | Contexto |
|---|---|---|
| `no_subscription` | 402 | sin suscripción activa (middleware / crear parcela) |
| `subscription_inactive` / `trial_expired` | 402 | suscripción pausada / trial vencido |
| `hectares_limit_exceeded` | 403 | exceder hectáreas del plan |
| `parcels_limit_exceeded` | 403 | exceder número de parcelas |
| `eosda_limit_exceeded` | 429 | exceder cuota mensual de análisis EOSDA |
| `index_not_available` | 403 | índice no incluido en el plan (imagen) |
| `weather_not_available` | 403 | clima no incluido en el plan |
| `feature_not_available` | 403 | feature no incluida (reportes, monitoreo) |
| `SATELITAL_LIMIT_EXCEEDED` | 402 | **EOSDA upstream** devolvió 402 (límite del plan EOSDA) |
| `SATELITAL_FIELD_NOT_FOUND` | 404 | el campo no existe en EOSDA |

⚠️ **Frontend**: solo maneja específicamente el 402/404 de escenas y el
403/402 del reporte. Los demás (429 `eosda_limit_exceeded`, `hectares/parcels
_limit_exceeded`, `no_subscription`, `weather/index_not_available`) caen a
toasts/alertas **genéricos sin botón de upgrade**.

---

## 15. Errores de EOSDA, 429 y timeouts

**Backend**:
- El cliente central **no reintenta** las llamadas (1 intento por HTTP).
- El rate limiter **encola** hasta 60 s; si se agota → lanza `EosdaRateLimitError`
  (subclase de `RequestException`), capturado como error sin reintento.
- El **polling** de tareas asíncronas está **acotado** (10/5/2 intentos). No es
  retry de errores, es espera de tarea legítima.

**Frontend**:
- ⚠️ **No hay manejo específico de 429, 500, 502 ni timeout**. Caen al catch
  genérico. No hay reintento automático con backoff.
- Solo existe: refresh de token en 401 (con flag anti-bucle), debounce del botón
  Stats (<1.5 s), y polling de imagen con intervalo creciente.
- Maneja 402/404 de escenas satelitales con toast + `mailto:admin`.

---

## 16. Generación y consulta de resultados (reportes, descargas)

- **Reporte PDF** (`CropCycleReportView`, `parcels/report_views.py`): ✅ FUNCIONAL.
  Genera PDF real con **ReportLab** (A4). Plan-gated (`pdf_reports`). Botón
  `downloadCropReport()` en el frontend descarga el blob y maneja 403/402.
- ⚠️ **Advertencia de veracidad**: el pie del PDF afirma que "los índices
  provienen de datos reales (Sentinel-2/EOSDA)" (`report_views.py:334`), lo cual
  puede ser **falso** si la salud fue poblada con el fallback sintético del
  histórico (§10).
- No hay otras descargas (CSV/Excel/GeoJSON) implementadas para el cliente.

---

## 17. Qué puede y qué NO puede hacer el cliente (hoy)

**Puede (conectado de punta a punta):**
- Registrarse (backend) y hacer login/logout (JWT).
- Crear parcelas dibujando el polígono (con límites de parcelas/hectáreas).
- Listar/editar (campos básicos)/eliminar (soft) parcelas.
- Buscar escenas satelitales y verlas.
- Generar imágenes NDVI/NDMI/EVI/SAVI y verlas como tiles.
- Ver analíticas por escena (NDVI/NDMI/EVI reales; lai/fpar/fcover passthrough).
- Ver pronóstico del clima (Open-Meteo) y elevación.
- Ver gráfico histórico (⚠️ puede ser sintético sin avisar).
- Descargar reporte PDF ejecutivo.
- Ver su consumo agregado (⚠️ dashboard de uso actualmente roto).

**NO puede (hoy):**
- Registrarse desde la UI (frontend desalineado) ni recuperar contraseña.
- Invitar/crear usuarios correctamente dentro del tenant (roto).
- Editar/redibujar la geometría de una parcela.
- Ver el **detalle** de su consumo EOSDA por request.
- Ver una página de "Mi Suscripción" funcional (endpoints inexistentes).
- Confiar en que la fusión/zonificación muestran datos reales (la zonificación
  es sintética y la fusión es parcial; el radar ya usa datos reales).

---

## 18. Observaciones conservadas de la auditoría anterior (consumo)

Se mantienen las conclusiones del documento `docs/EOSDA_CONSUMO.md`:
- El **consumo HTTP real** (rate limiter 8/min global) ≠ **cuota interna por
  tenant** (`eosda_requests`, 1 por invocación de endpoint de análisis) ≠
  **registro de auditoría** (`EosdaRequestLog`).
- Una operación de análisis (1 invocación de endpoint) puede hacer varias
  llamadas HTTP (POST + polling), pero solo suma **1** a la cuota y **1** fila
  al log.
- Un **cache hit** no consume nada.
- El contador interno **no** se asume igual a la facturación comercial de EOSDA.

---

## 19. Funcionalidades confirmadas (✅)

- Login/logout/refresh/cambio de contraseña (JWT).
- Registro backend con creación automática de tenant + verificación de email.
- Creación de tenant por registro y por checkout/pago (MercadoPago/Wompi/Paddle).
- Creación de parcelas (dibujo Leaflet) con límites de parcelas y hectáreas.
- Soft delete y listado de parcelas.
- Búsqueda de escenas con polling y caché/dedup.
- Imágenes NDVI/NDMI/EVI/SAVI (flujo imagen) + tiles WMTS con caché 24 h.
- Analíticas por escena (NDVI/NDMI/EVI reales).
- Pronóstico del clima (Open-Meteo) y elevación (Open-Meteo).
- Reporte PDF (ReportLab).
- Ciclos de cultivo (CRUD + interpretación).
- Rate limiter global 8/min, registro `EosdaRequestLog` y `UsageMetrics`.
- Panel staff/operador (métricas, tenants, consumo, acciones).

## 20. Funcionalidades parciales (⚠️)

- Verificación de email sin reenvío (errores de envío tragados).
- Roles de usuario sin enforcement; CRUD de usuarios defectuoso.
- Límite de usuarios por plan (decorador muerto).
- Creación de campo EOSDA en `Parcel.save()` (no fatal, sin registro, endpoint no verificado).
- Fusión multi-fuente (clima nunca alimentado).
- Salud del cultivo (puede contaminarse con fallback sintético).
- Gráfico histórico (fallback aleatorio silencioso).
- Comparativa NDVI-clima (no devuelve NDVI real).
- Exposición del consumo al cliente (dashboard de uso roto).
- Manejo de errores de límite en el frontend (solo 402/404/403 de reporte).

## 21. Funcionalidades pendientes o inexistentes (❌)

- Registro funcional desde la UI (React desalineado con backend).
- Recuperación de contraseña.
- Invitación de usuarios.
- Gestión/configuración del tenant por el cliente.
- Edición de geometría de parcela.
- Detalle de consumo EOSDA para el cliente.
- Página "Mi Suscripción" funcional.
- Carga de GeoJSON / creación de parcela por archivo.
- Descargas CSV/Excel/GeoJSON.

## 22. Problemas e inconsistencias encontradas

1. **Frontend de registro desalineado** con el backend (falta `organization_name`).
2. **Usuarios creados sin contraseña** (`UserCreationForm` sin `set_password`).
3. **Comando `create_tenant` roto** (`description=` inexistente, faltan campos).
4. **`setup_railway`** crea la tabla Client por SQL crudo con columnas distintas
   al modelo (`description` sí, `paid_until`/`on_trial` no).
5. **`usage_dashboard_view` con `NameError`** (referencia `User` sin definir).
6. **Mismatch de formatos** entre `usage_history_view`/`current_invoice_preview`
   y `billing-liquid.js` (gráfico y factura rotos).
7. **Endpoints inexistentes** que el frontend llama (`/billing/api/my-subscription/`,
   `/billing/api/cancel-subscription/`).
8. **Contaminación de datos reales con sintéticos**: histórico→salud→reporte PDF
   afirma "datos reales" cuando puede ser aleatorio.
9. **SAVI "fantasma"** en analytics (mapeado pero filtrado).
10. **Cálculo de área inconsistente** (Shoelace equirectangular vs esférica en UI).
11. **Bug de render de polígonos** en la lista (`geometry` vs `geom`).
12. **Código muerto con datos aleatorios** en `metereological.py` (4 funciones
    no conectadas).
13. **`users_limit_check` y `check_hectare_limit`** definidos pero nunca aplicados.
14. **`EOSDAMetricsViewSet`** (`parcels/metrics_views.py`) no registrado en ningún
    router (código muerto).

## 23. Riesgos técnicos relevantes

- **Cobro basado en datos potencialmente falsos**: el reporte PDF y la salud del
  cultivo pueden mostrar índices sintéticos como si fueran reales, sin indicarlo.
- **Registro frágil**: si falla el email, el usuario queda inactivo sin reenvío.
- **Cuota EOSDA global compartida**: una sola API Key; el rate limiter 8/min es
  la única barrera. Los tiles van sin rate limiter (podrían, en teoría, consumir
  la cuota de la Render API por separado).
- **Parcela sin `eosda_id`**: se guarda "rota" para funciones satelitales; no hay
  reintento de sincronización desde la UI.
- **Caché no tena-sensible en escenas**: la clave de escenas no incluye rango de
  fechas en `EosdaScenesView` (usa ventana fija de 90 días), mientras
  `ParcelScenesByDateView` sí la incluye.
- **Fallo de resolución de tenant**: la resolución depende del JWT; si el token
  no lleva `tenant_id` correcto, el middleware devuelve 401.
- **Drift de migraciones**: `Subscription.payment_gateway` tiene la opción
  `wompi` sin migrar (preexistente).

## 24. Archivos/módulos principales involucrados

| Área | Archivos clave |
|---|---|
| Autenticación | `authentication/views.py`, `serializers.py`, `services.py`, `urls.py` |
| Usuarios | `metrica/users/models.py`, `views.py`, `forms.py` |
| Tenants | `base_agrotech/models.py`, `config/middleware.py` |
| Parcelas | `parcels/models.py`, `serializers.py`, `views.py`, `routers.py`, `urls.py` |
| Dashboard/Frontend | `metrica/templates/parcels/parcels-dashboard.html`, `metrica/static/js/parcels/parcel.js` (+ `layers.js`, `analytics-cientifico.js`, `historical-chart.js`, `meteorological-analysis.js`, `elevation.js`, `crop-cycles.js`) |
| EOSDA | `parcels/eosda_client.py`, `eosda_rate_limiter.py`, `analytics_views.py`, `metereological.py`, `proxy.py`, `elevation.py`, `sentinel1.py`, `fusion_engine.py`, `zonification_pipeline.py`, `zone_views.py`, `report_views.py` |
| Billing/cuotas | `billing/models.py`, `decorators.py`, `middleware.py`, `views.py`, `views_staff.py`, `tenant_service.py`, `admin.py` |
| Config | `config/settings/base.py`, `config/urls.py`, `config/public_urls.py`, `config/middleware.py` |
