# Plan maestro — Auditoría, corrección y lanzamiento con Meta Ads

**Proyecto:** AgroTech Digital (Django multi-tenant + frontend estático en Netlify)
**Repos:**
- Backend: `agrotech-digital/` (este repo)
- Frontend real: `../agrotech-client-frontend/` (repo hermano, NO el `frontend-react-backup/`)

**Fecha:** 2026-11-10
**Estado:** plan para aprobación. No lanzar campañas pagas hasta cerrar las fases 0–5.
**Objetivo:** vender planes de monitoreo satelital agrotech con un funnel medible, confiable y sin fugas de dinero ni de acceso.

---

## 0. Resumen ejecutivo

La plataforma tiene piezas sólidas (multi-tenant, cuotas, caché EOSDA, reportes), pero **hoy no está lista para recibir tráfico pago**. Los bloqueadores no son cosméticos: afectan directamente la conversión, el cobro y la capacidad de medir.

### Bloqueadores P0 confirmados

| # | Bloqueador | Impacto comercial | Evidencia |
|---|---|---|---|
| 1 | **Meta Ads no puede optimizar**: el pixel solo dispara `PageView` en la landing. `/register`, checkout y pago no tienen eventos. GA4 está en placeholder y no hay CAPI. | Se paga por clics sin saber qué anuncio registra, activa o paga. Imposible escalar. | `../agrotech-client-frontend/index.html:14-15`; `js/analytics.js:14`; `templates/authentication/register.html` (sin `fbq`); `templates/billing/success.html` (sin pixel) |
| 2 | **Oferta inconsistente**: la web promete “14 días de prueba”, pero el registro crea un plan free permanente (1 parcela / 30 ha / 5 análisis). Además, pricing, plan-detail y fallbacks muestran límites distintos entre sí. | El cliente compra una promesa que el producto no cumple; aumenta el reembolso, el reclamo y el CAC. | `../agrotech-client-frontend/index.html:447`; `register.html:6`; `billing/signals.py:39-51`; `billing/management/commands/create_billing_plans.py:32-38`; `templates/billing/plan-detail.html:77-126`; `templates/billing/pricing.html:184-209` |
| 3 | **Seguridad de pagos**: `confirm-payment` acepta `plan_tier` y `billing_cycle` desde el cliente y solo verifica que “exista un pago aprobado”; MercadoPago acepta `pending` como pago válido. | Un usuario puede pagar Básico y activar Pro, o pagar mensual y recibir anual. Fuga directa de ingresos. | `billing/views.py:1485-1586`; `billing/mercadopago_gateway.py:369` |
| 4 | **Cobro anual incorrecto**: Wompi cobra 10 meses, pero el webhook otorga 30 días y fuerza `billing_cycle="monthly"`. Las renovaciones siempre suman 30 días. | El cliente anual recibe 1 mes, no 12. Reclamos y pérdida de confianza. | `billing/views.py:1410-1414`; `billing/webhooks.py:346-348,254` |
| 5 | **Autoservicio de suscripción roto**: `/billing/` corre siempre en schema público y varias vistas usan `request.tenant` en vez de resolver el tenant del JWT. | El cliente no puede ver su plan, factura, consumo ni cancelar. El dashboard queda con datos falsos o vacíos. | `config/middleware.py:66-77`; `billing/views.py:995-1003,1068-1081,1137-1144`; `resolve_tenant_for_request` solo se usa en `usage_dashboard` |
| 6 | **Operación incompleta**: no hay worker/cron para renovaciones, dunning, expiración de trial ni alertas; no hay Sentry inicializado; `/health/` no valida DB/Redis; no hay backups automáticos. | Las suscripciones pagas pueden quedar `active` para siempre sin renovar, y una caída no se detecta. | `railway.toml`; `start.sh`; `config/health_checks.py` sin rutas; sin `sentry_sdk.init`; `billing/middleware.py:89-119` |

### Veredicto

- **No lanzar Meta Ads de compra directa hoy.**
- **Sí se puede lanzar en 7–10 días** una campaña de **captación de leads** (WhatsApp / informe satelital gratis) si se cierran primero las fases 0–2.
- **La venta autoservicio** debe esperar a que estén cerradas las fases 3–5 (registro, límites y pagos).

---

## 1. Método de auditoría

### Enfoques
1. **Auditoría de código y configuración** (backend + frontend real).
2. **Auditoría funcional E2E** en staging con cuentas y tarjetas de prueba.
3. **Auditoría de experiencia** en móvil y desktop, con usuarios reales o heurística.
4. **Auditoría de medición**: pixel, CAPI, GA4, UTMs y eventos de negocio.
5. **Auditoría de seguridad y abuso**: pagos, límites, tenants, endpoints públicos.
6. **Auditoría de operación**: deploy, backups, cron, monitoreo, capacidad EOSDA.

### Reglas
- **Nunca** probar pagos reales ni romper datos de producción. Todo en staging con Wompi sandbox y tarjetas de prueba.
- Cada hallazgo debe tener: severidad, evidencia (`archivo:línea`), reproducción, impacto y criterio de aceptación.
- Cada fase termina con un **gate**: si no pasa, no se avanza.
- Los documentos viejos de `docs/` no son fuente de verdad; el código y las pruebas sí.

### Roles sugeridos
- **Dev full-stack** (backend + frontend): correcciones.
- **QA/PM**: guiones de prueba, evidencias, gates.
- **Growth/Meta Ads**: campañas, creativos, medición.
- **Negocio**: precios, oferta, presupuesto, decisiones.

---

## 2. Mapa del funnel actual (lo que realmente existe)

```
Landing agrotechcolombia.com
   └─ CTA /register
        └─ templates/authentication/register.html + js/register.js
             └─ POST /api/auth/register/  (crea tenant + usuario inactivo + plan free)
                  └─ email de verificación (SMTP real, sin fallback)
                       └─ GET /api/auth/verify-email/?token=...
                            └─ redirect FRONTEND_URL/login?verified=true
                                 └─ /login + js/login-liquid.js
                                      └─ POST /api/auth/login/ (JWT con tenant_id)
                                           └─ /templates/dashboard.html
                                                └─ parcelas, cultivos, análisis, facturación

Planes pagos:
/billing/planes → /billing/checkout/<tier> (frontend)
   └─ POST /billing/api/create-checkout/ (Wompi widget)
        └─ pago en Wompi
             ├─ webhook /billing/webhooks/wompi/  → activa tenant/suscripción
             └─ /templates/billing/success.html → POST /billing/api/confirm-payment/
```

**Puntos frágiles del mapa:**
- El registro no devuelve tokens; el usuario depende 100% del email.
- El pago depende de dos caminos que pueden competir (webhook + confirm-payment) sin idempotencia robusta.
- El plan free es permanente; el trial de 14 días no existe técnicamente.
- La facturación vive en schema público; el tenant del JWT no se resuelve en varias vistas.
- No hay eventos de negocio enviados a Meta.

---

## 3. Fases de ejecución

> Cada fase incluye: objetivo, auditoría, correcciones, pruebas y gate.
> Los tiempos son estimados para 1 dev + 1 QA/PM; el negocio y marketing entran en paralelo.

---

### FASE 0 — Preparación, staging y línea base
**Duración:** 1–2 días
**Objetivo:** poder probar sin riesgo y medir el estado inicial.

#### Auditoría
- [ ] Inventario de entornos, dominios, variables y servicios (Railway, Netlify, Wompi, SMTP, EOSDA, Meta).
- [ ] Confirmar que existe staging reproducible (o crearlo).
- [ ] Verificar backups de producción y hacer un restore de prueba.
- [ ] Congelar campañas pagas hasta el gate de Fase 5.
- [ ] Recolectar línea base: usuarios, tenants, suscripciones, ingresos, conversión actual, errores.

#### Correcciones / preparación
- [ ] Crear entorno staging con `DEBUG=False` y copia anonimizada de datos.
- [ ] Configurar Wompi sandbox, MercadoPago sandbox y SMTP de pruebas (Mailtrap/Resend).
- [ ] Configurar Sentry (staging y producción) y un monitor de uptime.
- [ ] Crear cuentas de prueba: email nuevo, finca nueva, tarjetas aprobadas/rechazadas/pending/3DS.
- [ ] Documentar la matriz de entornos y secretos (sin valores en el repo).

#### Gate de salida
- [ ] Staging responde `/health/` y permite registro/login.
- [ ] Pago de prueba aprobado y rechazado en sandbox.
- [ ] Sentry recibe un error de prueba.
- [ ] Restore de backup verificado.

---

### FASE 1 — Web pública: carga, confianza y conversión
**Duración:** 2–3 días
**Objetivo:** que la landing cargue rápido, no tenga enlaces rotos y no prometa lo que el producto no cumple.

#### Auditoría
- [ ] **Carga real** con Lighthouse móvil/desktop en `/`, `/register`, `/login`, `/templates/billing/pricing`, `/templates/billing/plan-detail`.
- [ ] Core Web Vitals: LCP, CLS, INP; peso de imágenes, fuentes y JS; requests bloqueantes.
- [ ] Revisar consola y red: errores JS, 404, recursos mixtos, CDNs caídos.
- [ ] Responsive en 360, 390, 768, 1280 px; CTA visible sin scroll en móvil.
- [ ] Enlaces: todos los CTA, WhatsApp, email, legales, blog, servicios.
- [ ] SEO: title, description, canonical, OG/Twitter, favicon, sitemap, robots, schema.
- [ ] **Consistencia de precios y límites** entre landing, pricing, plan-detail, checkout y API.
- [ ] **Claims**: “precisión milimétrica”, “ahorra 40%”, “30 cm”, “cada 3-5 días”, “datos reales”. Verificar sustento y eliminar lo que no se pueda probar.
- [ ] Legal: privacidad, términos, tratamiento de datos (Ley 1581), política de cookies.

#### Correcciones
- [ ] Un solo sitio canónico (`agrotechcolombia.com`); retirar/aislar el sitio viejo de Netlify.
- [ ] Un solo pixel de Meta; eliminar el segundo (`936082032542696`).
- [ ] Optimizar hero e imágenes: WebP/AVIF, `srcset`, `width/height`, `loading="lazy"`, preload del LCP.
- [ ] Fuentes con `font-display: swap` y self-host o preconnect; fijar versión de iconos (no `@latest`).
- [ ] Corregir enlaces y placeholders (`wa.me/573001234567`, `href="#"`).
- [ ] Generar pricing y plan-detail desde `/billing/api/plans/` (una sola fuente de verdad) o desde un build que consuma la API.
- [ ] Ajustar copy de oferta para que coincida con lo que realmente se entrega.
- [ ] Añadir favicon real y corregir sitemap (URLs consistentes).

#### Pruebas
- [ ] Lighthouse móvil: LCP < 2.5 s, CLS < 0.1, INP < 200 ms (objetivo; aceptable < 3 s LCP al inicio).
- [ ] 0 errores de consola y 0 404 en las páginas del funnel.
- [ ] Todos los CTA llevan a la página correcta y conservan UTMs.
- [ ] Precios y límites idénticos en todas las páginas y en la API.

#### Gate
- [ ] Web estable en móvil, sin enlaces rotos, con una sola oferta y un solo pixel.

---

### FASE 2 — Medición y tracking para Meta Ads
**Duración:** 2–3 días
**Objetivo:** que Meta vea todo el funnel y pueda optimizar por registro, activación y pago.

#### Auditoría
- [ ] Inventario de eventos actuales (pixel, GA4, `data-ga-event`, `trackEvent`).
- [ ] Verificar dominio en Meta Business, píxel, eventos y calidad de coincidencia.
- [ ] Revisar consentimiento y política de privacidad frente a Meta Pixel/CAPI.
- [ ] Verificar UTMs y parámetros `fbclid`, `fbc`, `fbp`.

#### Implementación mínima (eventos)
| Evento | Dónde se dispara | Parámetros |
|---|---|---|
| `PageView` | Todas las páginas del funnel | `page`, `utm_*` |
| `ViewContent` | Landing de servicio, pricing, plan-detail | `content_name`, `value`, `currency` |
| `Lead` | Vista de `/register` | `content_name` |
| `CompleteRegistration` | `POST /api/auth/register/` exitoso (servidor) | `value=0`, `currency=COP`, `event_id` |
| `StartTrial` | Creación de cuenta free / trial | `value`, `predicted_ltv` |
| `InitiateCheckout` | Vista de checkout | `value`, `currency`, `plan_tier` |
| `AddPaymentInfo` | Antes de enviar a Wompi | `value`, `currency` |
| `Purchase` | Pago aprobado (servidor, webhook) | `value`, `currency`, `transaction_id`, `event_id` |
| `Subscribe` | Renovación o suscripción recurrente | `value`, `currency` |
| `Contact` | Clic en WhatsApp | `content_name` |

#### Implementación
- [ ] Pixel en `/register`, checkout, success y páginas de servicio (no solo landing).
- [ ] **CAPI server-side** desde Django en registro, verificación y pago aprobado.
  - Hash SHA-256 de email, teléfono, nombre y apellido.
  - `event_id` compartido con el pixel para deduplicar.
  - Enviar `client_ip_address`, `client_user_agent`, `fbc`, `fbp`.
- [ ] GA4 real (dejar de usar `G-XXXXXXXXXX`) o retirar el script.
- [ ] Consent banner (Ley 1581) con categorías: necesarias, analítica, marketing.
- [ ] Actualizar política de privacidad para declarar Meta Pixel/CAPI y GA4.
- [ ] UTMs estándar: `utm_source=meta&utm_medium=paid&utm_campaign=...&utm_content=...&utm_term=...`.

#### Pruebas
- [ ] Meta Events Manager → Test Events recibe cada evento una sola vez.
- [ ] `Purchase` con valor y moneda correctos (COP), sin duplicados.
- [ ] CAPI y pixel deduplican por `event_id`.
- [ ] Con consentimiento rechazado, no se envían eventos de marketing.
- [ ] GA4 recibe `generate_lead`, `sign_up`, `begin_checkout`, `purchase`.

#### Gate
- [ ] Funnel 100% visible en Meta: visita → registro → verificación → activación → pago.
- [ ] Sin eventos duplicados ni valores incorrectos.

---

### FASE 3 — Registro, verificación, login y onboarding
**Duración:** 3–4 días
**Objetivo:** que un cliente nuevo complete registro → email → login → primera parcela sin ayuda, en menos de 10 minutos.

#### Auditoría
- [ ] Formulario de registro: campos, validaciones, errores por campo, autofill, gestores de contraseña, teclado móvil.
- [ ] Contrato API: `POST /api/auth/register/` y respuesta (`requires_email_verification`, sin tokens).
- [ ] Creación de tenant, dominio, usuario y suscripción; transaccionalidad.
- [ ] Verificación de email: envío, remitente, SPF/DKIM/DMARC, spam, expiración de token, reenvío.
- [ ] Login con email y con usuario; mensaje de cuenta inactiva; tokens; refresh; logout.
- [ ] Recuperación de contraseña: página `/recover-password`, `/reset-password`, email y confirmación.
- [ ] Primer login: dashboard, empty states, CTA para crear primera parcela, muestra de plan/límites.
- [ ] Medir abandono por paso (registro iniciado, completado, verificado, primera parcela).

#### Correcciones
- [ ] Implementar **trial real** o alinear la oferta a freemium permanente (ver decisión D1).
- [ ] Agregar reenvío de verificación visible en login y en el mensaje post-registro.
- [ ] Mostrar el 403 “verifica tu email” en el login (hoy se oculta).
- [ ] Token de verificación con expiración y un solo uso; verificación por POST o confirmación explícita.
- [ ] Enviar email de bienvenida con próximos pasos y enlace directo al dashboard.
- [ ] Onboarding first-run: “Crea tu primera parcela” con wizard de 3 pasos y datos de ejemplo.
- [ ] Empty states con CTA en dashboard, parcelas, cultivos, facturación.
- [ ] Recuperación de contraseña end-to-end con plantilla y redirect correctos.
- [ ] Medir y registrar `signup_started`, `signup_completed`, `email_verified`, `first_parcel_created`.

#### Pruebas
- [ ] 10 registros nuevos (emails distintos) completan el flujo sin intervención.
- [ ] Email llega a inbox (no spam) en Gmail, Outlook y correo corporativo; probar reenvío.
- [ ] Usuario inactivo ve mensaje claro y puede reenviar.
- [ ] Reset de contraseña funciona desde el enlace hasta el login.
- [ ] Primer login lleva a crear parcela en ≤ 3 clics.
- [ ] Tiempo medio registro → primera parcela < 10 min.

#### Gate
- [ ] 10/10 usuarios de prueba completan el flujo sin soporte.
- [ ] Tasa de verificación > 90%; entrega de email > 95%.

---

### FASE 4 — Planes, precios y límites
**Duración:** 2–3 días
**Objetivo:** una sola verdad comercial y técnica: lo que se muestra = lo que se cobra = lo que se permite.

#### Auditoría
- [ ] Catálogo real en DB: tiers, precios, ciclos, límites, features, trial.
- [ ] Comparar DB vs pricing vs plan-detail vs checkout vs emails vs dashboard.
- [ ] Revisar descuento anual (hoy 10 meses = 16.7%, se comunica 20%).
- [ ] Revisar overage (500 COP/análisis) y su exposición.
- [ ] Matriz de enforcement por endpoint: parcelas, hectáreas, usuarios, análisis, reportes, clima, monitoreo, almacenamiento, API.
- [ ] Verificar límites en creación **y** edición; concurrencia; upgrades/downgrades.
- [ ] Verificar que el trial/plan free realmente expire o no bloquee.

#### Correcciones
- [ ] **Fuente única de verdad**: `Plan` en DB + `/billing/api/plans/`; eliminar tablas y fallbacks hardcodeados.
- [ ] Definir matriz oficial:

| Plan | Precio/mes | Parcelas | Hectáreas | Usuarios | Análisis/mes | Features |
|---|---:|---:|---:|---:|---:|---|
| Explorador | $0 | 1 | 30 | 1 | 5 | NDVI |
| Agricultor | $79.000 | 10 | 100 | 2 | 100 | NDVI, NDMI, SAVI, clima básico, histórico |
| Empresarial | $179.000 | 50 | 300 | 3 | 500 | Todo + reportes, monitoreo, analytics |
| Corporativo | $600.000+ | Custom | Custom | Custom | Custom | Custom |

- [ ] Corregir descuento anual: 12 meses con 2 gratis = 16.7% (o cambiar a 20% real).
- [ ] Implementar límites faltantes: usuarios en todos los endpoints, almacenamiento, clima basic/full, tiles WMTS.
- [ ] Enforzar en servidor, no en UI; devolver códigos claros (`parcels_limit_exceeded`, `hectares_limit_exceeded`, `eosda_limit_exceeded`, `feature_not_available`).
- [ ] UI: barra de uso, aviso al 80% y 100%, CTA de upgrade contextual.
- [ ] Definir y documentar qué pasa al bajar de plan con uso por encima del límite.

#### Pruebas
- [ ] Crear parcela N, N+1 (debe fallar con mensaje y CTA).
- [ ] Hectáreas: límite exacto y un metro más.
- [ ] Usuarios: invitar/crear hasta el límite y uno más.
- [ ] Análisis: agotar cuota y verificar 429 + mensaje.
- [ ] Upgrade/downgrade: cambio de plan, fechas, features y UI.
- [ ] Trial: día 0, día 14, día 15; gracia y bloqueo.

#### Gate
- [ ] Cero contradicciones de precio/límite entre páginas y API.
- [ ] Todos los límites se cumplen en servidor con pruebas automatizadas.

---

### FASE 5 — Pagos end-to-end y suscripciones
**Duración:** 4–6 días
**Objetivo:** cobrar bien, activar bien, renovar bien y no regalar acceso.

#### Decisión de pasarela
- **Recomendado:** Wompi como pasarela principal en Colombia (Nequi, PSE, tarjetas, Bancolombia).
- **MercadoPago:** mantener solo si se corrige; hoy acepta `pending` y no genera factura.
- **Paddle:** deshabilitar hasta corregir firma, product IDs y provisioning.

#### Auditoría
- [ ] Flujo por pasarela: plan → checkout → redirect → pago → webhook → provisioning → login → factura → email.
- [ ] Monto, moneda, plan y ciclo: ¿se validan contra el pago real?
- [ ] Idempotencia: webhook duplicado, reintento, evento tardío, doble clic.
- [ ] Firma de webhooks y ventana de replay.
- [ ] `confirm-payment` y `subscribe-card`: confianza, autenticación, throttle.
- [ ] Fechas: mensual (30/31 días o mes calendario), anual (365 días), renovación, gracia, cancelación.
- [ ] Factura: subtotal, impuestos, total, numeración, email.
- [ ] Upgrade/downgrade/proration y cancelación.
- [ ] Dunning y reintentos.

#### Correcciones P0
- [ ] **`confirm-payment` no debe confiar en `plan_tier`/`billing_cycle` del cliente.** Derivar plan y ciclo del pago verificado (referencia firmada o metadata de la pasarela).
- [ ] Validar monto y moneda contra el plan; rechazar diferencias.
- [ ] MercadoPago: aceptar solo `authorized`/`approved`, nunca `pending`.
- [ ] Wompi: guardar `billing_cycle` real; anual = 365 días; renovación según ciclo.
- [ ] Idempotencia por `transaction_id`/`event_id` en tabla única; no extender dos veces.
- [ ] Webhooks: devolver 4xx/5xx ante fallo real para que la pasarela reintente; no 200 silencioso.
- [ ] Un solo camino de provisioning (webhook) y `confirm-payment` como consulta idempotente, no como creador alterno.
- [ ] Autenticar `subscribe-card` o eliminarlo si no se usa.
- [ ] Throttle real en endpoints públicos (DRF o middleware; el decorador actual no aplica a vistas Django planas).
- [ ] Corregir factura: impuesto no duplicado; numeración atómica; email de recibo.
- [ ] Implementar cancelación y reactivación; downgrade al final del periodo.
- [ ] Cron de renovación y dunning (o pasarela con cobro recurrente real).

#### Matriz de pruebas de pago
| Caso | Esperado |
|---|---|
| Básico mensual aprobado | Tenant/suscripción activos 30 días, factura correcta |
| Pro anual aprobado | 365 días, `billing_cycle=yearly`, monto anual correcto |
| Pago rechazado | No se crea tenant; mensaje claro; reintento |
| Pago pendiente | No se activa acceso |
| Webhook duplicado | No extiende dos veces; 200 idempotente |
| Webhook tardío | Activa una vez; no duplica |
| Monto alterado | Rechazo |
| Plan alterado en `confirm-payment` | Rechazo; se usa el plan pagado |
| Pago exitoso sin webhook | `confirm-payment` verifica y activa una vez |
| Cancelación | No renueva; acceso hasta fin de periodo |
| Upgrade | Cobra diferencia o programa cambio; sin regalo |
| Downgrade | Se aplica al final del periodo |

#### Gate
- [ ] 100% de los casos de la matriz pasan en staging.
- [ ] Cero posibilidad de activar plan superior pagando inferior.
- [ ] Anual otorga 365 días y renovación correcta.
- [ ] Factura cuadra al peso con el dinero recibido.

---

### FASE 6 — Plataforma: UX, funcionalidad y rendimiento
**Duración:** 4–5 días
**Objetivo:** que el producto que se vende funcione y se sienta fácil en desktop y móvil.

#### Auditoría de journeys
- [ ] Login → dashboard → crear parcela → ver análisis → ver histórico → descargar reporte.
- [ ] Cultivos, inventario, labores, RRHH, alertas.
- [ ] Facturación: ver plan, uso, facturas, cancelar.
- [ ] Perfil y configuración.
- [ ] Errores, empty states, loading states, reintentos.
- [ ] Móvil: mapa, tabla de parcelas, menú, facturación.

#### Correcciones
- [ ] Resolver tenant en todas las vistas de billing (`resolve_tenant_for_request`).
- [ ] Quitar “Plan Básico” hardcodeado; renderizar desde API con fallback honesto.
- [ ] Corregir KPIs y actividad reciente si aún leen shapes incorrectos.
- [ ] Límites hardcodeados en UI (50 parcelas / 300 ha) → leer del plan.
- [ ] Errores de límite con CTA de upgrade, no toasts genéricos.
- [ ] EOSDA: timeouts, reintentos, mensajes “no disponible”; **nunca** mostrar datos sintéticos como reales.
- [ ] Paginación en parcelas y listados grandes; evitar N+1.
- [ ] Mapa móvil: altura adaptable; tabla responsive.
- [ ] Reducir scripts CDN y unificar versión.

#### Pruebas
- [ ] Recorrido completo en iPhone/Android y desktop sin errores de consola.
- [ ] Crear/editar/eliminar parcela; análisis; reporte PDF.
- [ ] Simular EOSDA caído/429/timeout: mensaje claro, sin datos falsos.
- [ ] p95 del dashboard < 3 s con 50 parcelas.
- [ ] Facturación muestra plan, uso y facturas reales.

#### Gate
- [ ] Los 5 journeys críticos pasan en móvil y desktop.
- [ ] Ningún dato simulado se presenta como real.

---

### FASE 7 — Operación, seguridad y confiabilidad
**Duración:** 3–4 días
**Objetivo:** que el sistema aguante tráfico pago y que un fallo se detecte y se recupere.

#### Auditoría / correcciones
- [ ] **Secretos y entornos**: `.env` fuera del repo; `ALLOWED_HOSTS` con wildcard de tenants; CORS/CSRF correctos; admin en URL no obvia.
- [ ] **Monitoreo**: Sentry inicializado; logs estructurados; alertas a Slack/email; uptime externo.
- [ ] **Healthchecks**: `/health/` profundo (DB, Redis, cache) y rutas de readiness/liveness.
- [ ] **Backups**: backup diario, retención, restore probado, PITR si el proveedor lo permite.
- [ ] **Cron/worker**: renovaciones, dunning, expiración de trial, alertas de uso, monitoreo de cultivos, alertas agronómicas, inventario.
- [ ] **Capacidad EOSDA**: rate limit global 8/min, 2 workers, polling bloqueante; decidir cola/worker y límites por tenant.
- [ ] **Redis**: servicio real, `IGNORE_EXCEPTIONS=False` en producción, monitoreo.
- [ ] **Seguridad**: revisar endpoints públicos, CSRF, throttles, headers, dependencias, Paddle sin firma, `subscribe-card`.
- [ ] **CI/tests**: pytest con DB de test real, smoke E2E, lint, cobertura mínima, workflow en GitHub Actions.
- [ ] **Deploy**: collectstatic en build (no en boot), migraciones controladas, healthcheck real, rollback.

#### Pruebas
- [ ] Simular caída de DB/Redis/EOSDA/SMTP y verificar detección y mensaje.
- [ ] Restore de backup en staging.
- [ ] Cron ejecuta renovación y expiración en staging.
- [ ] Suite de tests verde y CI bloqueando merges.
- [ ] Escaneo de dependencias y secretos.

#### Gate
- [ ] Alertas funcionan; restore probado; cron corriendo; CI verde.
- [ ] Sin hallazgos críticos de seguridad abiertos.

---

### FASE 8 — Preparación de campañas Meta Ads
**Duración:** 3–4 días
**Objetivo:** lanzar con hipótesis, creativos y presupuesto claros.

#### 8.1 Configuración de cuenta
- [ ] Business Manager, ad account, método de pago, roles, 2FA.
- [ ] Dominio verificado; pixel único; Aggregated Event Measurement.
- [ ] Eventos priorizados: `CompleteRegistration`, `StartTrial`, `Purchase`, `Lead`.
- [ ] Catálogo de UTMs y convención de nombres (`AGRO_Prospecting_CO_...`).

#### 8.2 Oferta y landings
- [ ] Oferta principal: “Análisis satelital gratis de tu lote” o “14 días de prueba” (según decisión D1).
- [ ] Landing dedicada por ángulo, con mensaje espejo del anuncio.
- [ ] Prueba social: casos, logos, testimonios, capturas reales del dashboard.
- [ ] Riesgo reverso: sin tarjeta, cancela cuando quieras, soporte por WhatsApp.
- [ ] CTA primario y secundario (WhatsApp).

#### 8.3 Audiencias
- [ ] Prospección amplia Colombia (Advantage+ o ABO con 3–4 conjuntos).
- [ ] Intereses: agricultura, agronegocios, café, arroz, cacao, aguacate, ganadería, fincas.
- [ ] Lookalike 1–3% de registrados y de compradores.
- [ ] Retargeting: visitantes 30d, registro sin activar 7d, activado sin pagar 14d.
- [ ] Exclusión de clientes actuales y empleados.

#### 8.4 Creativos (3 ángulos x 3 formatos)
1. **Dolor:** “Tu lote tiene estrés hídrico y no lo ves” → NDMI.
2. **Objeción:** “Las nubes ya no son excusa” → radar Sentinel-1.
3. **Prueba/valor:** “El historial que tu técnico o el banco te pide” → reportes PDF.
4. **Diferenciador:** “Hasta 30 cm: cuenta árboles, canales y caminos”.
5. **Testimonio/UGC:** productor colombiano contando el antes/después.

Formatos: reel 9:16, feed 4:5, carrusel, story con CTA a WhatsApp. Subtítulos siempre. Español colombiano.

#### 8.5 Presupuesto y metas
- **Test:** COP 80.000–120.000/día durante 14 días (COP 1,1–1,7 M).
- **Escalado:** COP 200.000–400.000/día solo en ganadores.
- **Metas iniciales:** CTR > 1,5%; CPC < COP 2.500; CPL < COP 25.000; registro > 2,5%; activación > 40%; CAC < COP 150.000 (Básico) y < COP 250.000 (Pro); payback < 3 meses.
- **Criterios de corte:** CTR < 1%, CPC > COP 3.500, LP conversion < 1,5%, CAC > 3x objetivo.
- **ROAS objetivo:** ≥ 1,5 a 90 días; ≥ 3 a 12 meses.

#### Gate
- [ ] Tracking validado con Test Events.
- [ ] 9 creativos aprobados y landings publicadas.
- [ ] Presupuesto y criterios de corte aprobados por negocio.
- [ ] Campaña en borrador lista para publicar.

---

### FASE 9 — Lanzamiento, medición y optimización
**Duración:** 14–30 días
**Objetivo:** aprender rápido, cortar lo que no funciona y escalar lo que sí.

#### Días 0–3
- [ ] Publicar test; verificar gasto, eventos y calidad de coincidencia.
- [ ] Revisar comentarios y WhatsApp; responder < 15 min en horario laboral.
- [ ] Detectar errores de landing o checkout en producción.

#### Días 3–7
- [ ] Cortar anuncios con CTR < 1% o CPC alto.
- [ ] Iterar 3 creativos nuevos por ángulo ganador.
- [ ] Revisar drop-off: landing → register → verify → first parcel.

#### Días 7–14
- [ ] Consolidar en Advantage+ o CBO con ganadores.
- [ ] Activar retargeting y lookalikes.
- [ ] Probar oferta alternativa (informe gratis vs trial).
- [ ] Iniciar venta asistida por WhatsApp para Pro/Empresarial.

#### Días 14–30
- [ ] Optimizar a `Purchase`/`Subscribe` cuando haya ≥ 50 eventos/semana.
- [ ] Probar anual con 2 meses gratis.
- [ ] Reporte semanal: spend, CPL, signup, activación, pago, CAC, ROAS, payback.
- [ ] Decidir escalar, iterar o pausar.

#### Gate
- [ ] CAC por debajo del objetivo durante 2 semanas consecutivas.
- [ ] Activación y pago estables; soporte sin saturación.

---

## 4. Matriz de pruebas E2E (resumen)

| ID | Caso | Resultado esperado |
|---|---|---|
| WEB-01 | Landing en móvil 390px | CTA visible, sin scroll horizontal, LCP < 3 s |
| WEB-02 | Todos los enlaces del funnel | 200, sin 404, UTMs preservados |
| WEB-03 | Pricing vs API vs plan-detail | Mismos precios y límites |
| TRK-01 | Registro completado | `CompleteRegistration` en pixel y CAPI, 1 vez |
| TRK-02 | Pago aprobado | `Purchase` con valor/COP correctos |
| TRK-03 | Consentimiento rechazado | No eventos de marketing |
| AUTH-01 | Registro nuevo | 201, email enviado, usuario inactivo |
| AUTH-02 | Verificación email | Activa usuario y redirige a login |
| AUTH-03 | Reenvío verificación | Email llega; token nuevo |
| AUTH-04 | Login email y usuario | 200, tokens con `tenant_id` |
| AUTH-05 | Usuario inactivo | 403 con mensaje claro |
| AUTH-06 | Reset contraseña | Email → formulario → login |
| AUTH-07 | Primer login | Dashboard + CTA crear parcela |
| LIM-01 | Parcela N+1 | 403 `parcels_limit_exceeded` + CTA |
| LIM-02 | Hectárea N+1 | 403 `hectares_limit_exceeded` |
| LIM-03 | Usuario N+1 | 403 + CTA |
| LIM-04 | Cuota EOSDA agotada | 429 `eosda_limit_exceeded` |
| PAY-01 | Básico mensual | Activo 30 días, factura correcta |
| PAY-02 | Pro anual | Activo 365 días, monto anual |
| PAY-03 | Pago rechazado | Sin acceso, mensaje claro |
| PAY-04 | Pago pending | Sin acceso |
| PAY-05 | Webhook duplicado | Sin doble extensión |
| PAY-06 | Plan alterado | Rechazo |
| PAY-07 | Cancelación | Acceso hasta fin de periodo |
| UX-01 | Crear parcela | ≤ 3 pasos, sin error |
| UX-02 | EOSDA caído | Mensaje “no disponible”, sin datos falsos |
| OPS-01 | DB caída | Healthcheck falla, alerta |
| OPS-02 | Restore backup | Datos recuperados |
| OPS-03 | Cron renovación | Renueva y factura |

---

## 5. Backlog priorizado (P0 → P2)

### P0 — antes de cualquier gasto en ads
1. Tracking completo (pixel + CAPI + GA4 + consentimiento).
2. Oferta y pricing consistentes (trial vs freemium; límites).
3. `confirm-payment` sin confianza en plan/ciclo; MP sin `pending`.
4. Wompi anual = 365 días; renovación según ciclo; idempotencia.
5. Billing self-service resuelto por tenant del JWT.
6. Registro/verificación/login sin bloqueos; reenvío visible.
7. Cron de renovación/expiración y monitoreo mínimo.
8. Eliminar segundo pixel/sitio y enlaces rotos.

### P1 — antes de escalar presupuesto
9. Límites completos (usuarios, storage, clima, tiles) y mensajes con upgrade.
10. Onboarding first-run y empty states.
11. Optimización de imágenes/fuentes y performance móvil.
12. Facturación correcta (impuestos, numeración, email).
13. Cancelación/upgrade/downgrade.
14. Tests E2E automatizados y CI.
15. Backups/restore y alertas.

### P2 — mejora continua
16. Proration y dunning avanzado.
17. Reportes de consumo y facturas descargables.
18. Experimentos de pricing y anual.
19. SEO/blog y contenido de captación.
20. Optimización de capacidad EOSDA (cola/worker).

---

## 6. Cronograma sugerido

| Semana | Foco | Entregable |
|---|---|---|
| 1 | Fases 0–2 | Staging, web estable, tracking validado |
| 2 | Fases 3–4 | Registro/onboarding y planes/límites consistentes |
| 3 | Fase 5 | Pagos y suscripciones E2E seguros |
| 4 | Fases 6–8 | Plataforma estable + campañas listas |
| 5+ | Fase 9 | Test de ads, optimización y escalado |

**Ruta rápida (7–10 días) si la urgencia es vender ya:**
- Días 1–3: Fase 0 + tracking + web.
- Días 4–6: registro/login + pricing consistente.
- Días 7–8: bloquear fraude de pagos y corregir anual.
- Día 9: campaña de **leads a WhatsApp** (no venta directa).
- Día 10+: cerrar autoservicio y activar campaña de compra.

> La ruta rápida solo es aceptable si se acepta que la venta directa autoservicio espera. No se debe pautar compra con pagos vulnerables.

---

## 7. KPIs y economía del funnel

### Web
- LCP móvil < 2,5 s; CLS < 0,1; INP < 200 ms.
- 0 errores de consola; 0 enlaces rotos.
- Conversión landing → registro ≥ 2,5%.

### Activación
- Registro → email verificado ≥ 90%.
- Verificado → primera parcela ≥ 40%.
- Tiempo registro → primera parcela < 10 min.

### Pagos
- Pago aprobado → acceso activo ≥ 99%.
- Webhooks duplicados con doble extensión = 0.
- Facturas descuadradas = 0.
- Cancelaciones procesadas ≥ 99%.

### Meta Ads
- CTR > 1,5%.
- CPC < COP 2.500.
- CPL < COP 25.000.
- CAC Básico < COP 150.000; Pro < COP 250.000.
- Payback < 3 meses.
- ROAS ≥ 1,5 a 90 días.

### Ejemplo de embudo (para dimensionar)
Si la landing convierte 2,5%, activación 40% y activado→pago 15%:
- 10 clientes pagos ≈ 167 registros ≈ 6.680 sesiones.
- Con CPC COP 2.000 → COP 13,4 M en clics.
- CAC ≈ COP 1,34 M por cliente (insostenible para plan de COP 79k).

**Conclusión:** el autoservicio puro con planes de COP 79k–179k es difícil de rentabilizar con Meta Ads frío en Colombia. Recomendación:
1. Priorizar **leads** y venta asistida por WhatsApp para Pro/Empresarial.
2. Usar el plan free como imán, no como producto final.
3. Vender **anual** y **paquetes** para mejorar el payback.
4. Optimizar a `Purchase` solo cuando haya volumen; mientras tanto, a `CompleteRegistration`/`Lead`.

---

## 8. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Pagar ads y no poder medir | Alta | Alto | Fase 2 antes de pautar |
| Cliente paga y no recibe acceso | Media | Muy alto | Webhook idempotente + reconciliación + alerta |
| Fraude de plan superior | Alta | Alto | Validar plan/monto en servidor |
| Anual otorga 30 días | Alta | Alto | Corregir ciclo y probar |
| Email de verificación no llega | Media | Alto | SMTP transaccional + reenvío + monitoreo |
| EOSDA satura con tráfico | Media | Alto | Cola/worker y límites por tenant |
| Claims exagerados → rechazo de ads | Media | Medio | Revisión legal y de políticas Meta |
| CAC mayor que LTV | Alta | Alto | Leads + venta asistida + anual |
| Pérdida de datos | Baja | Muy alto | Backups + restore probado |
| Caída no detectada | Media | Alto | Sentry + uptime + health profundo |

---

## 9. Decisiones requeridas (respuesta del negocio)

| ID | Decisión | Opciones | Recomendación |
|---|---|---|---|
| D1 | Oferta de entrada | (a) Freemium permanente 1 parcela/30 ha/5 análisis; (b) trial 14 días de Pro; (c) híbrido: freemium + trial Pro | **Híbrido**: free para captar, trial Pro 14 días para activar valor; comunicar exactamente eso |
| D2 | Pasarela principal | Wompi / MercadoPago / ambas | **Wompi**; deshabilitar Paddle; MP solo si se corrige |
| D3 | Descuento anual | 2 meses gratis (16,7%) / 20% real | **2 meses gratis** y comunicarlo bien |
| D4 | Precios | Mantener 79k/179k / ajustar | Mantener; revisar tras 30 días de datos |
| D5 | Presupuesto Meta | COP 60k/80k/120k por día | **COP 80.000/día x 14 días** para test |
| D6 | Tipo de campaña inicial | Compra directa / leads WhatsApp / mixta | **Leads + informe gratis** primero; compra después |
| D7 | Responsable de fixes | In-house / agencia / Kilo | Definir antes de Fase 0 |
| D8 | Staging | Sí / no | **Sí, obligatorio** |

---

## 10. Próximo paso

1. Aprobar este plan y las decisiones D1–D8.
2. Ejecutar **Fase 0** (staging, backups, monitoreo, cuentas de prueba).
3. Ejecutar **Fase 1 y 2** en paralelo (web + tracking).
4. Revisar el **gate de Fase 2** antes de crear la primera campaña.
5. Recién entonces avanzar a registro, planes y pagos.

**Regla de oro:** no se gasta un peso en Meta Ads hasta que el funnel pueda responder con datos: *¿quién llegó, quién se registró, quién activó y quién pagó?*
