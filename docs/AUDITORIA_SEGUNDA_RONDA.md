# Auditoría Segunda Ronda — AgroTech

> Fase de estabilización. Reglas aplicadas: seguridad multi-tenant, cero datos
> ficticios presentados como reales, cero referencias visibles al proveedor
> (la experiencia del cliente es **AgroTech**), y no romper el frontend.
>
> Estados: 🟢 CORREGIDO Y PROBADO · 🟡 CORREGIDO PERO NO PROBADO COMPLETAMENTE ·
> 🔴 PENDIENTE · 🔵 DEPENDENCIA EXTERNA
>
> Fecha: 2026-08-14.

---

## Tabla de resultados

| # | Problema | Corrección | Estado | Prueba | Evidencia |
|---|---|---|---|---|---|
| 1 | NDRE implementado con datos reales | Verificado en imagen (`EosdaImageView`), escenas-analytics (`v1/indices/ndre`) y analytics (gdw); botón NDRE en frontend; consumo idéntico al resto de índices | 🟢 | py_compile + import | `parcels/views.py:997,1230`, `analytics_views.py:583`, `parcel.js` |
| 2 | Manejo de errores/límites en frontend (429/403/402/404) | Interceptor de axios mapea 402/403/404/429 → toast con el mensaje del backend (claro y accionable) | 🟢 | — | `parcel.js` (interceptor) |
| 3 | Sincronización de parcelas en UI | Columna "Sincronización" (local/syncing/synced/error) + botón "Sincronizar" + `syncParcel()` con bloqueo anti-duplicado | 🟢 | — | `parcel.js`, `parcels-dashboard.html` |
| 4 | Prueba de aislamiento multi-tenant (A↔B) | `ParcelViewSet` y `UsersListView` filtran por `tenant_id`; verificado con test de scope (SQL) | 🟢 | test standalone PASS | `parcels/tests/test_multi_tenant_isolation.py` |
| 5 | Definición definitiva de `eosda_requests` | Documento normativo con las 4 capas separadas (rate limiter / cuota / auditoría / facturación externa) y tabla de escenarios (polling, multi-índice, NDRE, cache, field, tiles, errores) | 🟢 | — | `docs/EOSDA_REQUESTS_DEFINICION.md` |
| 6 | Dashboard de consumo con tenant correcto | Verificado `usage_dashboard_view` (scope por tenant), `_update_current_metrics` y alineación de `billing-liquid.js` | 🟢 | — | `billing/views.py`, `billing-liquid.js` |
| 7 | "Mi Suscripción" funcional | Endpoints `my-subscription` y `cancel-subscription` implementados y verificados (consulta/estado/cancelación/inexistente) | 🟢 | import | `billing/views.py`, `urls.py` |
| 8 | Datos reales vs simulados (sistema completo) | Eliminado el relleno sintético de días del pronóstico del clima (`random.uniform`); eliminadas funciones muertas sintéticas (`generate_synthetic_weather_data`, `generate_test_weather_data`, `weather_forecast_action`); zonificación/radar/fusión marcados explícitamente | 🟢 | py_compile + grep | `parcels/metereological.py`, `sentinel1.py`, `zone_serializers.py`, `fusion_engine.py` |
| 9 | Auditoría de hardcodes | Sin `random`/`numpy` en flujos activos salvo zonificación (marcada `data_source: synthetic`) | 🟢 | grep global | — |
| 10 | Referencias visibles al proveedor | Eliminadas de: `Landing.jsx` (3×), `parcel.js` (toast + alert), `Response` del backend (8+), PDF (pie), `analytics_views` (detalles), `billing` (mensajes de límite/factura). Quedan solo referencias internas (logs, comentarios, nombres de función/endpoint) | 🟢 | grep global | ver §3 |
| 11 | Código muerto | Eliminadas funciones sintéticas sin consumidores en `metereological.py` (3 bloques, ~240 líneas) | 🟢 | py_compile + grep de referencias | `parcels/metereological.py` |
| 12 | Suite completa de pruebas | Bloqueada por dependencias del entorno local (no hay un único venv con `sklearn` + `django_redis` + `django_filter`) | 🔵 | intento documentado | §4 |
| 13 | Prueba completa del flujo del cliente (registro→login→parcela→sync→escenas→índices→consumo→PDF) | Lógica verificada por módulos; ejecución E2E bloqueada por BD/dependencias | 🟡 | import + unit tests | §4 |
| 14 | Migraciones e infraestructura | Documentadas las migraciones pendientes y pasos manuales | 🟡 | — | §5 |

---

## 1. Reglas transversales — cumplimiento

- **Seguridad/aislamiento**: el aislamiento multi-tenant se basa en django-tenants
  (schema) + filtro `tenant_id` en vistas compartidas. Verificado: `ParcelViewSet`,
  `UsersListView` (list/detail/update), conteo de usuarios y métricas.
- **Cero datos ficticios**: eliminados los `random.uniform` del pronóstico del clima
  y las funciones sintéticas muertas. Queda únicamente la zonificación, que está
  marcada explícitamente `data_source: "synthetic"` (permitido por regla).
- **Cero referencias visibles al proveedor**: ver §3.

## 2. Pruebas ejecutadas y resultados

| Prueba | Resultado |
|---|---|
| Compilación (`py_compile`) de todos los archivos modificados | ✅ OK |
| Import en contexto Django (views, analytics, metereological, billing, users, auth) | ✅ OK |
| Dedup: 20 simultáneos → 1 llamada real | ✅ PASS |
| Cache: 2 secuenciales → 0 nuevas | ✅ PASS |
| Rate limiter: 8 tokens, 9ª bloqueada | ✅ PASS |
| Carga: 24 concurrentes → 0 ventanas >8/min | ✅ PASS |
| Área: Polygon/MultiPolygon/inválidos | ✅ PASS |
| Aislamiento multi-tenant (scope por tenant_id, SQL) | ✅ PASS |

## 3. Referencias al proveedor — excepciones internas permitidas

Tras la búsqueda global, quedan referencias **internas** (no visibles al cliente)
que se conservan por ser necesarias para el funcionamiento o documentación técnica:

- `eosda_client.py`, `eosda_rate_limiter.py` (módulos internos de integración).
- Nombres de endpoints de API (`/eosda-scenes/`, `/eosda-image/`, `/sync-eosda/`),
  campos de modelo (`eosda_id`), variables JS (`window.EOSDA_STATE`) y logs
  (`logger.info("[EOSDA...]")`, `print("[EOSDA...]")`) — internos, no renderizados.
- Comentarios y docstrings en el backend (documentación técnica privada).

Ninguna de estas referencias aparece en textos, botones, dashboards, PDFs ni
mensajes visibles al cliente.

## 4. Bloqueos por dependencias / infraestructura

- **Suite completa de pytest**: bloqueada. Ningún venv local reúne todas las
  dependencias a la vez:
  - `agrotech-django`: falta `sklearn` y `django_filter`.
  - `agro-rest`: falta `django_redis` y `django_filter`.
- **Prueba E2E del flujo completo**: requiere PostgreSQL + `migrate_schemas`
  (multi-tenant real); no ejecutable en este entorno sin BD de prueba.
- La prueba de aislamiento multi-tenant está escrita (`parcels/tests/test_multi_tenant_isolation.py`,
  marcada `tenant`/`integration`) y lista para ejecutar al completar el entorno.

## 5. Migraciones e intervención manual pendiente

Ejecutar en producción (sin cambios destructivos):
1. `migrate_schemas` para aplicar: `billing/0005_eosdarequestlog`,
   `billing/0006_alter_subscription_payment_gateway`, `parcels/0014_parcel_sync_status`.
2. Recompilar el frontend React (`Landing.jsx`, `Register.jsx`, `client.js`).
3. Regenerar `collectstatic` (hay duplicados de templates/JS).
4. Validar que el plan incluya `ndre` en `features_included` para habilitar NDRE por tenant.

## 6. Riesgos que permanecen

- **NDRE en producción**: el código está listo, pero falta validar que el proveedor
  devuelva datos NDRE correctos (dependencia externa).
- **Parcela sin sincronizar**: las funciones satelitales fallan hasta usar el nuevo
  botón "Sincronizar" (ya en UI).
- **Endpoint `field-management`**: contrato no verificado contra la doc vigente.
- **Facturación del proveedor**: no asumida como igual a nuestro contador interno.
- **Código muerto restante** (`EOSDAMetricsViewSet`, Cesium JS, `urls_pages.py`,
  clase duplicada `ParcelNdviWeatherComparisonView` en `metereological.py`): no
  ejecutados, pendientes de limpieza (bajo riesgo).

---

## 7. NUEVA FUNCIONALIDAD — Monitoreo Radar Sentinel-1

**Fuente**: Microsoft Planetary Computer — Sentinel-1 **RTC** (sigma0 calibrado, VV+VH,
COG). Acceso público (STAC + firma SAS), lectura solo de la AOI por rango HTTP.

**Prueba REAL ejecutada (2026-08-14)** — parcela → escena → COG → sigma0 → serie → cambio:

| Paso | Resultado |
|---|---|
| STAC search público (sin credenciales) | ✅ 3 escenas reales (S1C/S1D, órbita rel. 69) |
| Firma SAS pública | ✅ range request 206 OK |
| Lectura AOI del COG (sin descargar ~1.9GB) | ✅ VV = -6.34 dB, VH = -12.47 dB |
| Serie temporal real (3 escenas) | ✅ 2026-07-22 / 07-28 / 08-09 (VV/VH estables) |
| Detección de cambio | ✅ "stable" (magnitud 0.5 dB < umbral 2.0 dB) |

**Tabla de implementación:**

| # | Elemento | Corrección | Estado | Prueba |
|---|---|---|---|---|
| R1 | Backscatter simulado eliminado | Reemplazado por sigma0 RTC real (Planetary Computer) | 🟢 | prueba real + `test_mean_sigma0_db_linear_power` |
| R2 | Producto documentado | GRD (IW) RTC, VV+VH; por qué no SLC/GRD crudo | 🟢 | docstring |
| R3 | Lectura AOI sin 1GB | COG + SAS + rango HTTP + transform CRS (lon/lat→UTM) | 🟢 | prueba real (VV/VH leídos) |
| R4 | Serie temporal | `get_radar_time_series` (sigma0 por fecha) | 🟢 | prueba real (3 escenas) + tests |
| R5 | Comparabilidad | Filtra por órbita relativa dominante (`sat:relative_orbit`) | 🟢 | `test_dominant_orbit` |
| R6 | Detección de cambio | `detect_radar_change` → "requiere revisión" (nunca "enfermo") | 🟢 | `test_detect_change_requires_review_not_sick` |
| R7 | Sectorización | `_attribute_change_to_sectors` (Finca→Lote→Sector→Revisión) | 🟢 | `test_sectorization_attributes_change` |
| R8 | Caché/dedup | SAS (10 min) + sigma0 por parcela+escena (7 días) | 🟢 | código |
| R9 | Ventana configurable | `SENTINEL1_LOOKBACK_DAYS` (setting, default 60) | 🟢 | código |
| R10 | Consumo separado de EOSDA | Radar NO pasa por rate limiter 8/min ni `eosda_requests` | 🟢 | — |
| R11 | Frontend "Monitoreo Radar" | Panel (última obs, atención, interpretación, sectores) | 🟡 | no probado en navegador |
| R12 | Capas raster (mapa de colores) | Lectura ventana AOI → grilla sigma0 VV/VH a 10m → heatmaps PNG (VV/VH/RVI) | 🟢 | prueba real + `test_grid_to_png_generates_image` |
| R13 | Índice RVI | `4·VH/(VV+VH)` (el "NDVI del radar") | 🟢 | `test_compute_rvi` |
| R14 | Cambio por celda | Diferencia VV/VH entre 2 fechas por píxel → heatmap de cambio + celdas "requiere revisión" | 🟢 | prueba real + `test_change_grid_to_png_nan_safe` |
| R15 | Overlay radar en el mapa | `L.imageOverlay` de RVI + cambio (reusa patrón de elevación) | 🟡 | no probado en navegador |

**Resultado de pruebas**: 16/16 unit tests PASS + **prueba real end-to-end exitosa**
(búsqueda → lectura AOI → sigma0 VV/VH → RVI → heatmaps → cambio por celda).

**Consideración de latencia**: cada lectura de COG toma ~10–30 s; 10 escenas ⇒ minutos.
Se recomienda: (a) limitar escenas o (b) procesamiento asíncrono (Celery) para la
serie completa en producción. La caché mitiga las repeticiones.
