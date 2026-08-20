# Resumen de Cambios — Corrección Integral AgroTech

> Resumen ejecutivo de las correcciones aplicadas en la fase de corrección integral
> (P0–P20), siguiendo los hallazgos de `docs/EOSDA_CONSUMO.md` y `docs/FLUJO_CLIENTE.md`.
>
> El detalle completo está en `docs/AUDITORIA_CORRECCIONES.md`.
>
> Fecha: 2026-08-14.

---

## 1. Integridad de datos (P0) — lo más crítico

- Se eliminó `_generate_test_data` y todos los fallbacks sintéticos activos
  (histórico, analytics, clima).
- **Ya ningún dato aleatorio puede alimentar `CropHealthStatus` ni aparecer en el
  PDF como dato real.**
- El PDF ahora usa una afirmación de fuente **condicional** (solo afirma
  "Sentinel-2/EOSDA" cuando hay una observación válida real).

## 2. Consumo EOSDA (P1)

- Definición única de las 3 capas:
  - **Rate limiter** = 1 token por HTTP (global, 8/min).
  - **`eosda_requests`** = 1 por invocación de endpoint de análisis.
  - **`EosdaRequestLog`** = 1 fila por `record()`.
- Separado explícitamente de la facturación comercial de EOSDA (no se asume igual).

## 3. Índices (P2)

- SAVI "fantasma" en analytics eliminado (solo se consulta en imagen, donde es real).
- **NDRE implementado** en los flujos reales: imagen (`EosdaImageView`), escenas-analytics
  (`EosdaSceneAnalyticsView`) y analytics (gdw), con botón NDRE en el frontend.

## 4. Registro y recuperación (P3/P4)

- Frontend React (`Register.jsx`, `client.js`) alineado con `RegisterSerializer`.
- El fallo de email ya no bloquea: `email_sent` en la respuesta + reenvío.
- Nuevo endpoint de **reenvío de verificación**.
- Flujo completo de **recuperación de contraseña** con token estándar de Django.

## 5. Gestión de usuarios del tenant (P5/P6)

- `UserCreationForm` ahora sí crea usuarios con contraseña válida.
- Roles con enforcement (`TenantAdminRequiredMixin`: solo admin/manager gestionan usuarios).
- Listado y conteo de usuarios aislados por tenant (antes contaban todos los tenants).

## 6. Creación de parcelas + EOSDA (P7)

- Nuevo estado de sincronización: `sync_status` (`local/syncing/synced/error`) + `sync_error`.
- Endpoint `POST /parcel/<id>/sync-eosda/` para **reintentar** la sincronización.
- La creación de campo se registra en `EosdaRequestLog` (operación `field`, sin cuota).

## 7. Cálculo de área (P8)

- Fuente única de verdad: `parcels/geometry.py`, con la **misma fórmula esférica
  que el frontend**. Backend y UI ya no discrepan.

## 8. Mapa y geometría (P9)

- Corregido el bug `geometry` vs `geom` en el render de polígonos.
- Texto residual "CesiumJS" reemplazado por "Leaflet" (implementación real).

## 9. Dashboard de consumo (P10)

- Corregidos `NameError` de `User` y `Sum('area_hectares')` en `usage_dashboard_view`.
- Alineado `billing-liquid.js` (historial y factura ahora parsean la estructura real).

## 10. Suscripción (P16)

- Implementados los endpoints `my-subscription` y `cancel-subscription` que el
  frontend ya llamaba.

## 11. Radar, fusión y zonificación (P14)

- Datos simulados/estimados marcados explícitamente:
  - Radar: `estimated: True` + `data_nature: estimated_backscatter`.
  - Zonificación: `data_source: "synthetic"`.
  - Fusión: `data_notes` (qué es real, estimado o no alimentado).

## 12. Código muerto y config (P17)

- Comandos rotos corregidos: `create_tenant` y `setup_railway`.

## 13. Migraciones (P18)

- `billing/0005_eosdarequestlog` (con campo `user`).
- `billing/0006_alter_subscription_payment_gateway` (drift `wompi`).
- `parcels/0014_parcel_sync_status`.

## 14. Seguridad multi-tenant (P19)

- Verificado el aislamiento por schema + JWT (el `tenant_id` del JWT no permite
  escapar del tenant autorizado).
- Corregidos los scopes por tenant en gestión de usuarios y conteo de métricas.

---

## Pruebas ejecutadas

| Prueba | Resultado |
|---|---|
| Compilación (`py_compile`) de todos los archivos | ✅ OK |
| Import en contexto Django | ✅ OK |
| `makemigrations --check` billing / parcels | ✅ Sin cambios |
| Dedup: 20 simultáneos → 1 llamada real | ✅ PASS |
| Cache: 2 secuenciales → 0 nuevas | ✅ PASS |
| Rate limiter: 8/min | ✅ PASS |
| Carga: 24 concurrentes → 0 ventanas >8 | ✅ PASS |
| Área: Polygon/MultiPolygon/inválidos | ✅ PASS |

## Pendientes

- **Endpoint `field-management`** → requieren confirmación de EOSDA.
- **Manejo de errores/límites en frontend (P11)** → parcial.
- **Código muerto restante** (`metereological.py`, `EOSDAMetricsViewSet`, Cesium JS) → pendiente de limpieza.
- **Aplicar migraciones** y **reconstruir el frontend React** (intervención manual/infraestructura).
