# Validación Final — AgroTech

> Fase de validación. Se preparó un entorno de prueba real (PostgreSQL local +
> venv `agro-rest`, que sí reúne Django 5.0 + django-tenants + sklearn + DRF).
> Solo se marca "PROBADO" lo que realmente se ejecutó contra la BD de prueba o
> con tests de lógica; lo demás queda explícitamente **PENDIENTE DE VALIDACIÓN**.
>
> Fecha: 2026-08-14.

---

## 0. Entorno de prueba preparado

| Componente | Estado |
|---|---|
| PostgreSQL local (`localhost:5432`, DB `agrotech`, user `postgres`) | ✅ disponible (`pg_isready` OK) |
| Venv con todas las dependencias | ✅ `agro-rest` (Django 5.0.1, django-tenants, sklearn, DRF, reportlab). `django_redis` y `django_filter` **no son necesarios** (imports lazy / no usados) |
| Migraciones | ✅ `billing.0005_eosdarequestlog`, `billing.0006_alter_subscription_payment_gateway`, `parcels.0014_parcel_sync_status` se aplicaron correctamente a los schemas de tenant en la BD de prueba |
| Test DB | ✅ se crea y destruye correctamente (`manage.py test` / `pytest` con django-tenants) |

---

## 1. Pruebas ejecutadas y resultados reales

### 1.1 Pruebas con base de datos real (django-tenants + PostgreSQL)

| Suite / archivo | Resultado | Detalle |
|---|---|---|
| `billing/tests/test_limits_enforcement.py` | ✅ **14/14 PASS** | Límites de hectáreas, parcelas, suscripción y métricas |
| `parcels/tests/test_multi_tenant_isolation.py` | ✅ **3/3 PASS** | Parcela, usuario y métricas aisladas entre Tenant A ↔ B |
| `parcels/tests/test_eosda_validation.py` | ✅ **7/7 PASS** | NDRE (3), sync de parcela (2), consumo (2) |

Detalle de `test_eosda_validation.py` (todos contra BD real, con HTTP a EOSDA mockeado):

| Test | Verificación |
|---|---|
| `test_ndre_wired_in_all_index_lists` | NDRE presente en validación de imagen, mapeo de nombres y scene-analytics |
| `test_ndre_payload_uses_uppercase` | El índice se envía como `NDRE` |
| `test_ndre_in_scene_analytics_valid_indices` | `valid_indices` incluye `ndre` |
| `test_parcel_sync_status_error_without_api_key` | Sin API key → `sync_status='error'` + `sync_error` (no fatal) |
| `test_parcel_sync_synced_with_valid_response` | Respuesta 201 → `eosda_id` guardado + `sync_status='synced'` |
| `test_consumption_record_increments_quota_and_logs` | `record()` → `eosda_requests +1` + fila en `EosdaRequestLog` con user/parcel/source |
| `test_field_operation_does_not_increment_quota` | `record(increment_quota=False)` → NO incrementa cuota pero SÍ loguea |

### 1.2 Pruebas de lógica (sin BD)

| Test | Resultado |
|---|---|
| Deduplicación: 20 requests simultáneos → 1 llamada real | ✅ PASS |
| Caché: 2 llamadas secuenciales → 0 nuevas | ✅ PASS |
| Rate limiter: 8 tokens, 9ª bloqueada | ✅ PASS |
| Carga: 24 concurrentes → 0 ventanas >8/min | ✅ PASS |
| Área (fórmula única): Polygon/MultiPolygon/inválidos | ✅ PASS |
| Scope multi-tenant (SQL de `ParcelViewSet`/`UsersListView` filtra por `tenant_id`) | ✅ PASS |

### 1.3 Suite existente (hallazgo)

`authentication/test_auth_multitenant.py`: **8 pass / 15 fail**.
Los 15 fallos son **tests obsoletos (stale)**, no regresiones de esta ronda:
- Leen el contrato de login plano (`data['access']`) cuando el backend devuelve
  `data.tokens.access` (el **frontend sí lo maneja**: `login-liquid.js` y
  `client.js` leen `data.tokens?.access || data.access`).
- Crean usuarios sin los campos requeridos `email`/`name`/`last_name`.
- Crean tenants sin `on_trial` (columna NOT NULL) o con `paid_until` como string.
- `test_inactive_user_cannot_login` espera 401 pero recibe 403 (inactivo sin verificar).

---

## 2. Estado por área

| Área | Estado | Evidencia |
|---|---|---|
| **NDRE (código + integración)** | 🟢 CORREGIDO Y PROBADO (integración) | `test_ndre_*` (3 PASS) |
| **NDRE (datos reales del proveedor)** | 🔵 PENDIENTE DE VALIDACIÓN | requiere API key + proveedor real (ver §3.1) |
| **Multi-tenant (aislamiento)** | 🟢 CORREGIDO Y PROBADO | `test_multi_tenant_isolation` (3 PASS) |
| **Consumo (cuota + log)** | 🟢 CORREGIDO Y PROBADO | `test_consumption_*` (2 PASS) + `test_limits_enforcement` (14 PASS) |
| **Sincronización de parcelas** | 🟢 CORREGIDO Y PROBADO (backend) | `test_parcel_sync_*` (2 PASS) |
| **Sincronización de parcelas (UI)** | 🟡 CORREGIDO PERO NO PROBADO (navegador) | §3.2 |
| **Errores/límites frontend** | 🟡 CORREGIDO PERO NO PROBADO (navegador) | §3.3 |
| **Flujo E2E (registro→login→parcela→sync→escenas→índices→consumo→PDF)** | 🔵 PENDIENTE DE VALIDACIÓN | §3.4 |
| **Frontend (mapa/escenas/botones)** | 🔵 PENDIENTE DE VALIDACIÓN | requiere navegador (no se ejecutó; solo checks estáticos) |

---

## 3. Cómo probar lo que queda PENDIENTE DE VALIDACIÓN

### 3.1 NDRE con datos reales (requiere API key + proveedor)
1. Verificar que `EOSDA_API_KEY` esté configurada en el servidor.
2. Crear una parcela con geometría y sincronizarla (`POST /api/parcels/parcel/<id>/sync-eosda/`).
3. Buscar escenas (`POST /api/parcels/eosda-scenes/`) y tomar un `view_id`.
4. Generar la imagen NDRE: `POST /api/parcels/eosda-image/` con `{"field_id":..., "view_id":..., "type":"ndre", "format":"png"}`.
5. Descargarla: `GET /api/parcels/eosda-image-result/?field_id=...&request_id=...&type=ndre`.
6. Verificar que `EosdaRequestLog` registra `operation=image_result` / `image` con `index_type=NDRE`, y que `eosda_requests` incrementa.
7. Confirmar visualmente que la imagen NDRE se renderiza (índice de borde rojo).

### 3.2 Sincronización de parcelas en UI (navegador)
1. Crear una parcela **sin** API key configurada (o con key inválida) → debe aparecer estado "Error" + botón "Sincronizar".
2. Con API key válida, crear parcela → debe aparecer "Sincronizada".
3. Pulsar "Sincronizar" en una parcela en "Error" y verificar que cambia a "Sincronizada" (o muestra el error).
4. Verificar que el botón se deshabilita mientras sincroniza (no duplica requests).

### 3.3 Errores/límites en frontend (navegador)
1. Provocar 429 (agotar 8/min) → toast "Has alcanzado el límite de análisis satelitales...".
2. Provocar 403 de hectáreas → toast con el mensaje del backend (nombre del plan + límite).
3. Provocar 402 sin suscripción → toast con mensaje accionable.
4. Confirmar que NO aparece ninguna referencia a "EOSDA" en toasts/alertas/mensajes.

### 3.4 Flujo E2E completo (requiere stack completo + API real)
Pasos exactos:
1. Registro → verificación → login (JWT con `tenant_id`).
2. Crear parcela (dibujo en Leaflet) → observar `sync_status`.
3. Sincronizar con el proveedor.
4. Buscar escenas → generar NDVI/NDMI/EVI/SAVI/NDRE → visualizar.
5. Ver dashboard de consumo (que refleje el tenant correcto y el consumo incrementado).
6. Descargar PDF y confirmar que solo muestra datos reales y ninguna referencia al proveedor.

### 3.5 Suite completa de pytest
Comando: `python -m pytest --reuse-db` (con el venv `agro-rest`).
Resultado esperado: los tests nuevos pasan; los **tests obsoletos** de
`authentication/test_auth_multitenant.py` (y otros `test_*.py` legacy) fallan por
contratos desactualizados y deben actualizarse por separado (fuera de esta ronda).

---

## 4. Conclusiones

- El sistema **sí se puede probar localmente** con PostgreSQL + venv `agro-rest`.
- **Probado con BD real**: aislamiento multi-tenant, consumo (cuota + log),
  sincronización de parcelas, integración de NDRE, y límites de plan.
- **Pendiente de validación** (por requerir proveedor/navegador/credenciales):
  NDRE contra EOSDA real, flujo E2E, UI de sincronización y de errores, y la
  suite completa (tests legacy obsoletos por actualizar).
- **No se marcó nada como "PROBADO" basado solo en py_compile/import.**
