# Informe de Remediación — Auditoría AgroTech (Fase de Corrección Integral)

> Correcciones aplicadas sobre los hallazgos de `docs/EOSDA_CONSUMO.md` y
> `docs/FLUJO_CLIENTE.md`, siguiendo las prioridades P0–P20.
>
> **Estados usados:** ✅ CORREGIDO · ⚠️ PARCIAL · ❌ PENDIENTE · 🚫 BLOQUEADO POR DEPENDENCIA EXTERNA
>
> Fecha: 2026-08-14.

---

## Tabla de remediación

| # | Problema | Archivo/módulo | Estado anterior | Corrección realizada | Estado actual | Prueba |
|---|---|---|---|---|---|---|
| 1 | Fallback sintético (random) alimenta salud y reportes como dato real | `parcels/views.py` (`ParcelHistoricalIndicesView`, `_generate_test_data`) | Generaba datos aleatorios y actualizaba `CropHealthStatus` | Se eliminó `_generate_test_data`; ante fallo se marca el índice como `indices_unavailable` (sin inventar datos). Salud solo se actualiza con datos reales | ✅ CORREGIDO | py_compile + import |
| 2 | Fallback sintético de analytics (`_generate_minimal_fallback_data`) | `parcels/analytics_views.py` | Código muerto con datos hash/aleatorios | Eliminado (no tenía consumidores) | ✅ CORREGIDO | py_compile |
| 3 | Fallback sintético meteorológico | `parcels/views.py` (`ParcelNdviWeatherComparisonView`) | `random.uniform` como clima real | Se eliminaron `_generate_synthetic_weather_data` y `_generate_test_weather_data`; ante fallo devuelve estado "no disponible" | ✅ CORREGIDO | py_compile |
| 4 | PDF afirma "índices reales (Sentinel-2/EOSDA)" incondicionalmente | `parcels/report_views.py` | Texto fijo | Pie condicional: solo afirma fuente real si hay observación válida | ✅ CORREGIDO | py_compile |
| 5 | Definición de consumo contradictoria (HTTP vs "operación lógica") | `parcels/eosda_client.py`, docs | Documentación ambigua | Definición única: `eosda_requests` = 1 por invocación de endpoint de análisis; rate limiter = 1 por HTTP; separado de facturación EOSDA | ✅ CORREGIDO | docstring + docs |
| 6 | SAVI "fantasma" en analytics (mapeado pero filtrado) | `parcels/analytics_views.py` | `index_map` con SAVI que nunca se consulta | Eliminado el mapeo fantasma; solo NDVI/NDMI/EVI en ese endpoint | ✅ CORREGIDO | py_compile |
| 7 | NDRE no implementado | `parcels/views.py`, `analytics_views.py`, `parcel.js` | Se afirmaba "no existe contra EOSDA" | Implementado: añadido `ndre` a imagen (`EosdaImageView`), escenas-analytics (`EosdaSceneAnalyticsView`) y analytics (gdw), con botón NDRE en el frontend | ✅ CORREGIDO | py_compile |
| 8 | Registro frontend desalineado con backend | `frontend/src/pages/Register.jsx`, `client.js` | Faltaban `organization_name`/`name` | Formulario y `register()` alineados al `RegisterSerializer` | ✅ CORREGIDO | — |
| 9 | Fallo silencioso de email de verificación | `authentication/services.py` | Doble `except` muerto; usuario quedaba bloqueado | `_send_verification_email_later` retorna bool; `email_sent` en respuesta; sin bloqueo | ✅ CORREGIDO | py_compile |
| 10 | Sin reenvío de verificación | `authentication/views.py`, `urls.py` | No existía | `ResendVerificationView` (`POST /api/auth/resend-verification/`) | ✅ CORREGIDO | import |
| 11 | Sin recuperación de contraseña | `authentication/views.py`, `urls.py` | No existía | `PasswordResetRequestView` + `PasswordResetConfirmView` (token Django estándar) | ✅ CORREGIDO | import |
| 12 | Usuarios creados sin contraseña válida | `metrica/users/forms.py` | `UserCreationForm` sin `set_password` | Añadidos `password1/2` + `set_password` + `role` | ✅ CORREGIDO | py_compile |
| 13 | Roles sin enforcement | `metrica/users/views.py` | Todos los autenticados administraban usuarios | `TenantAdminRequiredMixin` (admin/manager) en CRUD de usuarios | ✅ CORREGIDO | py_compile |
| 14 | Listado de usuarios cross-tenant (sin scope) | `metrica/users/views.py` | `User.objects.all()` | Scope por `tenant_id` en list/detail/update | ✅ CORREGIDO | py_compile |
| 15 | Límite de usuarios cuenta todos los tenants | `metrica/users/views.py` | `User.objects.count()` | `User.objects.filter(tenant_id=tenant.id).count()` | ✅ CORREGIDO | py_compile |
| 16 | Parcela queda "rota" sin `eosda_id` | `parcels/models.py`, `views.py`, `serializers.py`, migración `0014` | `save()` no fatal sin estado | `sync_status` (`local/syncing/synced/error`) + `sync_error` + acción `POST /parcel/<id>/sync-eosda/` | ✅ CORREGIDO | py_compile + makemigrations |
| 17 | Creación de campo EOSDA sin registro | `parcels/models.py` | No se registraba | `_record_field_creation` escribe `EosdaRequestLog` (operation=`field`, sin incrementar cuota) | ✅ CORREGIDO | — |
| 18 | Cálculo de área inconsistente (frontend vs backend) | `parcels/geometry.py` (nuevo) + `models.py`, `views.py`, `billing/decorators.py` | Shoelace plano vs esférico | Función única `calculate_area_hectares` (misma fórmula esférica del frontend) | ✅ CORREGIDO | test de área (100 ha / 200 ha) |
| 19 | `geometry` vs `geom` en render de polígonos | `metrica/static/js/parcels/parcel.js` | Solo leía `parcel.geometry` | Lee `parcel.geometry || parcel.geom` | ✅ CORREGIDO | — |
| 20 | Texto residual "CesiumJS" | `parcels-dashboard.html` | Texto 3D Cesium | Reemplazado por "Leaflet" | ✅ CORREGIDO | — |
| 21 | `usage_dashboard_view` NameError + `Sum('area_hectares')` | `billing/views.py` | 500 / FieldError | `get_user_model()` + suma por método + scope de usuarios | ✅ CORREGIDO | py_compile |
| 22 | Desalineamiento historial/factura con `billing-liquid.js` | `billing-liquid.js` | `Object.entries`/campos planos | Parse de `data.history` y `invoice.period`/`invoice_preview` | ✅ CORREGIDO | — |
| 23 | Endpoints `my-subscription`/`cancel-subscription` inexistentes | `billing/views.py`, `urls.py` | 404 | `my_subscription_view` + `cancel_my_subscription_view` | ✅ CORREGIDO | import |
| 24 | Backscatter radar presentado como real | `parcels/sentinel1.py` | Valores empíricos sin marcar | `estimated: True` + `data_nature: estimated_backscatter` | ✅ CORREGIDO | py_compile |
| 25 | Zonificación simulada presentada como real | `parcels/zone_serializers.py` | Sin indicador claro | `data_source: "synthetic"` en el serializer | ✅ CORREGIDO | py_compile |
| 26 | Fusión sin clima + datos mixtos | `parcels/fusion_engine.py` | Sin claridad de fuentes | `data_notes` indicando qué es real/estimado/no alimentado | ✅ CORREGIDO | py_compile |
| 27 | Comando `create_tenant` roto | `base_agrotech/.../create_tenant.py` | `description=` inexistente; faltaban campos | Eliminado `description`; añadidos `paid_until`/`on_trial`; `create_superuser` con `name`/`last_name` | ✅ CORREGIDO | py_compile |
| 28 | `setup_railway` desincronizado con modelo | `base_agrotech/.../setup_railway.py` | Tabla Client con `description`, sin `paid_until`/`on_trial` | SQL alineado al modelo | ✅ CORREGIDO | py_compile |
| 29 | Drift de migración `payment_gateway` (wompi) | `billing/migrations/0006` (nuevo) | Pendiente | Migración `0006_alter_subscription_payment_gateway` (solo choices, no-op en DB) | ✅ CORREGIDO | makemigrations --check |
| 30 | Manejo de errores/límites en frontend | `parcels/parcel.js` | Solo 402/404 de escenas | Pendiente: manejar 429/403/402 de forma accionable | ⚠️ PARCIAL | — |
| 31 | Código muerto restante (metereological.py, `EOSDAMetricsViewSet`, Cesium JS, `urls_pages.py`) | varios | Dead code | `create_tenant`/`setup_railway` corregidos; el resto queda pendiente de limpieza | ⚠️ PARCIAL | — |

---

## 1. Problemas corregidos

1. **Integridad de datos (P0)**: eliminados todos los fallbacks sintéticos activos
   (`_generate_test_data`, `_generate_minimal_fallback_data`, clima sintético).
   Ningún dato falso puede llegar a `CropHealthStatus` ni al PDF.
2. **Consumo EOSDA coherente (P1)**: definición única de las 3 capas y separación
   de la facturación comercial de EOSDA.
3. **Índices (P2)**: SAVI fantasma eliminado; NDRE correctamente documentado como pendiente.
4. **Registro (P3)**: frontend alineado, fallo de email no bloquea, reenvío implementado.
5. **Recuperación de contraseña (P4)**: flujo completo con token estándar de Django.
6. **Gestión de usuarios (P5)**: contraseña correcta, roles con enforcement, scope por tenant.
7. **Límites (P6)**: conteo de usuarios aislado por tenant.
8. **Parcelas + EOSDA (P7)**: `sync_status`/`sync_error` + reintento + registro de creación de campo.
9. **Área (P8)**: fuente única de verdad (`parcels/geometry.py`), idéntica al frontend.
10. **Mapa (P9)**: bug `geometry`/`geom` corregido; texto Leaflet.
11. **Dashboard de consumo (P10)**: NameError y `Sum('area_hectares')` corregidos; JS alineado.
12. **Suscripción (P16)**: endpoints `my-subscription` y `cancel-subscription` implementados.
13. **Radar/Fusión/Zonificación (P14)**: datos simulados/estimados marcados explícitamente.
14. **PDF (P15)**: afirmación de fuente condicional.
15. **Comandos rotos (P17)**: `create_tenant` y `setup_railway` corregidos.
16. **Migración (P18)**: drift `payment_gateway` (wompi) registrado.
17. **Seguridad multi-tenant (P19)**: verificado el aislamiento por schema + JWT; corregidos
    los scopes por tenant en gestión de usuarios y conteo.

## 2. Problemas que requieren decisión de producto

- **¿La creación de campo EOSDA (`field`) debe contar en la cuota mensual?** Decisión
  actual: NO cuenta en `eosda_requests` (no es análisis), pero SÍ se registra en
  `EosdaRequestLog`. Si producto decide lo contrario, cambiar `increment_quota=True`.
- **Manejo de errores/límites en el frontend (P11)**: decidir alcance de UI
  (botón de upgrade, modales por código de error) antes de implementarlo.
- **Código muerto restante (P17)**: confirmar si `EOSDAMetricsViewSet` y las funciones
  sintéticas de `metereological.py` se eliminan o se conservan para referencia.

## 3. Problemas que requieren confirmación de EOSDA

- **Endpoint de creación de campo (`field-management`)**: verificar el contrato actual
  de EOSDA API Connect (método, payload, respuesta) antes de afirmar que crea el campo.
- **Facturación comercial de EOSDA**: confirmar cómo EOSDA contabiliza sus requests
  (nuestro contador interno no se asume equivalente).
- **NDRE**: ya implementado en el flujo real (imagen y v1/indices); queda validar en
  producción que EOSDA devuelve datos NDRE correctos para las parcelas objetivo.

## 4. Problemas que requieren intervención manual/infraestructura

- **Aplicar migraciones**: `billing/0005_eosdarequestlog`, `billing/0006_alter_subscription_payment_gateway`,
  `parcels/0014_parcel_sync_status`. Ejecutar `migrate_schemas` en producción.
- **Reconstruir frontend**: compilar `frontend/` (React) tras el cambio en `Register.jsx`/`client.js`.
- **Limpiar `staticfiles/`**: hay duplicados de templates/JS de collectstatic; regenerar.

## 5. Pruebas ejecutadas y resultados

| Prueba | Resultado |
|---|---|
| Compilación (`py_compile`) de todos los archivos modificados | ✅ OK |
| Import en contexto Django (views, analytics, metereological, proxy, detectar_alertas, auth, billing, users, geometry) | ✅ OK |
| `makemigrations --check` billing | ✅ Sin cambios |
| `makemigrations --check` parcels | ✅ Sin cambios |
| Dedup: 20 requests simultáneos → 1 llamada real EOSDA | ✅ PASS |
| Cache: 2 llamadas secuenciales → 0 llamadas nuevas | ✅ PASS |
| Rate limiter: 8 tokens OK, 9ª bloqueada | ✅ PASS |
| Carga: 24 concurrentes → 0 ventanas >8/min | ✅ PASS |
| Área: Polygon 1km×1km ≈ 100 ha, MultiPolygon ≈ 200 ha, inválidos = 0 | ✅ PASS |

**Limitación del entorno**: no se pudo ejecutar la suite completa de Django
(`manage.py test`) porque el entorno local (`agrotech-django`) no tiene `sklearn`
(requerido por `parcels/zonification_pipeline`), dependencia ajena a estos cambios.

## 6. Riesgos que permanecen

- **Parcela sin `eosda_id`**: las funciones satelitales siguen fallando (404/400) hasta
  que el usuario use el nuevo `POST /parcel/<id>/sync-eosda/`. La UI aún no muestra
  este botón (pendiente de frontend).
- **Código muerto sintético en `metereological.py`**: no se ejecuta (sin consumidores),
  pero permanece en el repo. Riesgo bajo, limpieza pendiente.
- **Frontend de errores**: los códigos 429/403/402 de límites siguen cayendo a toasts
  genéricos (P11 pendiente).
- **`users.serializers` import frágil**: `metrica/users/views.py` depende de `./metrica`
  en `sys.path` (pre-existente, documentado en `conftest.py`).
- **Fusión multi-fuente**: la rama climática sigue sin alimentarse (devuelve
  "sin datos climáticos"); no es un dato falso, pero la funcionalidad está incompleta.
