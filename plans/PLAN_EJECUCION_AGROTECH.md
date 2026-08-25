# Plan de Ejecución — AgroTech Digital (Fase Producción/Ventas)

> Estado: **PLAN** · Fecha: 2026-08-21
> Principio rector: **datos 100% reales** (no hardcodeado, no simulado) y **cero spaghetti** (cada pieza con responsabilidad única y dependencias explícitas).

---

## 0. Contexto y estado actual (ya verificado)

| Componente | Estado | Detalle |
|---|---|---|
| Panel super-admin (dueño) | ✅ Existe | `billing/views_staff.py` (5 endpoints), `billing/permissions.py` (doble verificación), `billing/tests/test_staff_dashboard.py`, frontend `staff/dashboard.html` |
| Cliente EOSDA real | ✅ Existe | `parcels/eosda_client.py`. Key actual = free (real), será paga |
| Zonificación / recomendación | ⚠️ Simulado | `parcels/zonification_pipeline.py` usa `_simulate_pixel_indices` (sintético) |
| Modelo de elevación (DEM) | ✅ Existe | `parcels/elevation.py` (Open-Meteo, ~30m). Falta: grilla más fina + drenaje direccional |
| Tracking de consumo EOSDA | ⚠️ Parcial | `billing.UsageMetrics.eosda_requests` existe; hay que verificar que cada request real quede registrado |

---

## 1. Estrategia de recomendación (sin "kg", no genérica)

**Decisión**: NO prescribir dosis absolutas ("376 kg urea") por riesgo legal (sin agrónomo). En su lugar, **prescripción relativa + priorización + drenaje direccional**.

**Fórmula del mensaje** (por zona):

> "Zona noreste (2.3 ha) · NDVI 0.42 · brecha **-31%** vs promedio del lote · Prioridad **ALTA**. Acción: reforzar fertilización nitrogenada y revisar drenaje — el terreno drena hacia el **sur** (modelo de elevación)."

**Componentes (todos de datos reales):**
1. **Zonas de manejo**: grilla + K-means sobre NDVI/NDMI/NDRE **reales** (Sentinel-2 vía EOSDA).
2. **Diagnóstico relativo**: brecha (%) de cada zona vs el promedio **del propio lote** (no un estándar externo → menos riesgo, más útil).
3. **Priorización**: severidad (baja/media/alta/crítica) según brecha → ordena qué intervenir primero.
4. **Tipo de acción** (no dosis): fertilización nitrogenada / riego / drenaje / monitoreo de plagas.
5. **Drenaje direccional**: pendiente + aspecto del DEM interpolado → "drenar hacia N/S/E/O".
6. **Trazabilidad temporal**: evolución de la zona entre escenas (mejorando / estable / empeorando).

**Por qué funciona**: es específico (números reales + dirección + prioridad) sin ser una receta agronómica absoluta. Y es el diferenciador de mercado que pide el usuario.

---

## 2. Bloques de trabajo y concordancia (anti-spaghetti)

```
                    ┌─────────────────────────────┐
                    │  CAPA DATOS REALES (base)  │
                    │  EOSDA client + DEM         │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
 ┌──────────────┐        ┌──────────────────┐        ┌────────────────┐
 │ B. Motor     │        │ C. Elevación/DEM │        │ A. Panel dueño │
 │ zonificación │──usa──▶│ (drenaje dir.)   │        │ (consumo real) │
 └──────────────┘        └──────────────────┘        └────────────────┘
        │                                                  ▲
        │  (cada request EOSDA)                            │
        └──────────────────────────────────────────────────┘
                     → UsageMetrics.eosda_requests (único punto de conteo)
```

**Regla de concordancia**: todo request a EOSDA pasa por **un único** contador (`UsageMetrics`), que alimenta tanto el panel del dueño (consumo) como el límite del plan del cliente. No se cuenta dos veces.

---

## 3. Orden de ejecución priorizado (FASE a FASE)

### FASE 0 — Cimientos (bloquea todo lo "real")
1. **Verificar cliente EOSDA real** (`parcels/eosda_client.py`): confirmar endpoints de indices/analytics Sentinel-2 que soporta la key free.
2. **Unificar el conteo de requests**: un solo helper (ej. `parcels/consumption.py`) que registre cada request EOSDA en `UsageMetrics.eosda_requests` — usado por el motor y visible en el panel.
3. **Interpolar DEM a grilla fina**: en `parcels/elevation.py`, subir de ~30m a ~10m efectivos con interpolación (scipy `griddata`/`RectBivariateSpline`) y calcular **pendiente + aspecto** para el drenaje direccional.

### FASE 1 — Panel del dueño (rápido, ya casi está)
4. **Crear cuenta dueño** (`owner`, superusuario) + generar **STAFF_ACCESS_KEY** real (script `scripts/create_owner_account.py` + `.env`).
5. **Validar end-to-end** los 5 endpoints (`/staff/api/*`) con JWT + `X-Staff-Access-Key`.
6. **Conectar datos reales**: confirmar que KPIs (MRR, usuarios, consumo EOSDA, tenants) salen de BD real, no simulada.

### FASE 2 — Motor de recomendación (el diferenciador)
7. **Reemplazar `_simulate_pixel_indices`** por lectura del raster real (Sentinel-2 vía EOSDA) en `parcels/zonification_pipeline.py`.
8. **Diagnóstico relativo + priorización**: brecha % vs promedio del lote, severidad, tipo de acción.
9. **Drenaje direccional**: cruzar zona de NDMI alto con pendiente/aspecto del DEM → "drenar hacia N/S".
10. **Frontend**: visualizar zonas (GeoJSON), brechas, prioridades y dirección de drenaje.

### FASE 3 — Cierre y transición a pago
11. **Preparar el switch a key paga**: config por env, sin cambios de código; alertas de límite de requests en el panel.
12. **Tests**: aislamiento multi-tenant + recomendaciones sobre datos reales.

---

## 4. Preguntas/decisiones aún abiertas
- Confirmar el endpoint EOSDA exacto de indices/analytics disponible con la key free.
- Nombre final de la cuenta dueño (`owner` ok?) y si el email es `contacto@agrotechcolombia.com`.
- Resolución objetivo del DEM interpolado (¿10m ok?).

---

## 5. Criterios de "listo"
- [ ] El panel del dueño muestra consumo EOSDA real y funciona con key propia.
- [ ] La zonificación usa NDVI/NDMI/NDRE reales (cero sintético).
- [ ] El mensaje de recomendación es relativo + priorizado + direccional (sin dosis absolutas).
- [ ] El drenaje direccional sale del DEM interpolado.
- [ ] Todo request EOSDA se cuenta una sola vez.
