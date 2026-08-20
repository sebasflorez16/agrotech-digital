# Cómo se calcula el consumo de EOSDA

Este documento explica con precisión cómo se mide el consumo de la API satelital
EOSDA en AgroTech Digital, y la diferencia entre una **request real a EOSDA** y
una **respuesta servida desde caché**.

---

## 1. Las tres capas del consumo

El consumo de EOSDA se mide en **tres niveles distintos**. Es importante no
confundirlos, porque cuentan cosas diferentes.

| Nivel | Qué cuenta | Dónde se guarda | Alcance |
|---|---|---|---|
| **A. Rate limiter (consumo REAL)** | Cada **llamada HTTP** que sale hacia EOSDA | Redis (clave `eosda:rate:sliding`) | **Global** (una sola API Key) |
| **B. Cuota mensual por tenant** | Cada **operación de análisis** (1 por invocación de endpoint) | `UsageMetrics.eosda_requests` | Por tenant |
| **C. Registro de auditoría** | Cada **operación de análisis** (1 fila por `record()`) | `EosdaRequestLog` (schema `public`) | Global + por tenant |

> ⚠️ **Separación importante**: el contador interno de AgroTech (`eosda_requests`)
> **no** representa necesariamente cómo EOSDA contabiliza comercialmente sus
> requests (su facturación). Son dos cosas distintas: el nuestro es contabilidad
> interna por tenant; la facturación real de EOSDA queda pendiente de confirmación
> del proveedor y se gestiona aparte.

### A. Rate limiter — el consumo REAL (el que importa para EOSDA)

- EOSDA nos da **1 sola API Key** con un plan Starter de **10 requests/minuto**.
- Para no pasarnos, limitamos las llamadas a **máximo 8 requests/minuto** (dejamos
  margen de 2).
- Este límite es **global**: lo comparten **todos los tenants** a la vez, porque
  todos usan la misma API Key.
- **Cada llamada HTTP cuenta 1 token**: un `POST` cuenta 1, y cada `GET` de
  polling también cuenta 1. Es decir, es el conteo más fino y real.

### B. Cuota mensual por tenant (`eosda_requests`)

- Es la contabilidad **por cliente** que se usa para saber si un tenant se pasó
  de su plan (ej. 100 análisis/mes en el plan Básico).
- **Definición única**: se incrementa **1 por cada invocación de un endpoint de
  análisis EOSDA** que realizó al menos una llamada HTTP real (cache miss).
  - Generar imagen (`image`) = 1.
  - Descargar imagen (`image_result`) = 1.
  - Buscar escenas (`scenes`) = 1.
  - Analytics de una escena (varios índices) = 1.
- Por tanto, una "imagen completa" de un índice (generar + descargar) cuenta
  **2** operaciones (`image` + `image_result`). Es la misma granularidad que el
  registro de auditoría.

### C. Registro de auditoría (`EosdaRequestLog`)

- **1 fila** por cada `record()` (misma granularidad que `eosda_requests`).
  Guarda: tenant, usuario, parcela, operación, índice, fecha, y origen
  (`eosda` o `cache`).
- Al estar en el schema `public`, es el **registro global de Agrotech** y a la
  vez se puede filtrar por tenant.

---

## 2. Request REAL vs respuesta de CACHÉ

| | **Request real a EOSDA** | **Respuesta desde caché** |
|---|---|---|
| ¿Llama a EOSDA? | Sí | No |
| ¿Consume token del rate limiter? | Sí (1 por HTTP) | No |
| ¿Incrementa `eosda_requests`? | Sí (1 por operación) | No |
| ¿Escribe en `EosdaRequestLog`? | Sí (`source="eosda"`) | No |
| ¿Cuesta dinero a EOSDA? | Sí | No |

**Regla de oro:** solo cuenta como consumo lo que **realmente sale hacia EOSDA**.
Si la respuesta ya estaba guardada en caché, se entrega al instante y **no gasta nada**.

---

## 3. Operaciones y cuánto consumen

Cada endpoint hace un patrón distinto de llamadas HTTP. Lo que se **cobra/cuenta**
al tenant es **1 operación de análisis por invocación de endpoint**, aunque esa
operación haga varias llamadas HTTP internas (POST + polling) o varios índices.

| Operación | Endpoint(s) | HTTP por operación | Operaciones (eosda_requests) | Índices soportados |
|---|---|---|---|---|
| `scenes` (buscar escenas) | `EosdaScenesView`, `ParcelScenesByDateView` | 1 POST + hasta 10 GET de polling | 1 | — |
| `image` (generar imagen de índice) | `EosdaImageView` | 1 POST | 1 | ndvi, ndmi, evi, savi, **ndre** |
| `image_result` (descargar imagen) | `EosdaImageResultView` | 1 GET | 1 | (el mismo índice) |
| `scene_analytics` (analítica por escena) | `EosdaSceneAnalyticsView` | 1 POST por índice (N POSTs) | 1 (por toda la vista) | ndvi, ndmi, evi, ndre, savi, lai, fpar, fcover |
| `advanced_statistics` (estadística avanzada) | `EosdaAdvancedStatisticsView` | 1 POST | 1 | bandas B01–B12 |
| `analytics` (analítica científica) | `EOSDAAnalyticsAPIView` | 1 POST + hasta 5 GET de polling | 1 | (mt_stats) |
| `historical_indices` (histórico) | `ParcelHistoricalIndicesView` | 3 POST + hasta 6 GET (3 índices) | 1 | ndvi, ndmi, evi |
| `index` (índice puntual) | `ndvi_historical`, `water_stress_historical`, `detectar_alertas` | 1 POST por índice | 1 por índice | ndvi / ndmi |
| `field` (crear campo) | `Parcel.save()` | 1 POST | **0** (solo rate limit, no se registra) | — |
| `render` (tiles del mapa) | `proxy.py` | 1 GET (sin rate limit, caché 24 h) | **0** (no se registra) | — |

> **Importante:** `field` (creación de parcela) y `render` (tiles) **no** cuentan
> en la cuota mensual `eosda_requests` ni en el log, porque no son "análisis
> satelitales". Los tiles además no pasan por el rate limiter de 8/min (son la
> Render API, otro producto, y romperían el mapa).

---

## 4. Ejemplo: análisis completo de 1 parcela

### Escenario

Un tenant (Finca Demo) pide un **análisis completo de una parcela** generando la
imagen de **5 índices: NDVI, NDMI, SAVI, EVI y NDRE**, por primera vez (sin caché).

El flujo real por índice es: **generar imagen** (`image`) + **descargar imagen**
(`image_result`). Cada uno es 1 operación lógica y 1 llamada HTTP.

| Índice | `image` (1 HTTP) | `image_result` (1 HTTP) | Operaciones lógicas | ¿Soportado? |
|---|---|---|---|---|
| NDVI | ✅ 1 | ✅ 1 | 2 | Sí |
| NDMI | ✅ 1 | ✅ 1 | 2 | Sí |
| SAVI | ✅ 1 | ✅ 1 | 2 | Sí |
| EVI | ✅ 1 | ✅ 1 | 2 | Sí |
| NDRE | ✅ 1 | ✅ 1 | 2 | Sí |

> ℹ️ Los 5 índices (NDVI, NDMI, SAVI, EVI, **NDRE**) están soportados en el flujo
> de imagen (`field-imagery/indicies`). NDRE es especialmente útil para cultivos
> altos (palma, caucho, frutales) porque el borde rojo (red-edge) es más sensible
> al contenido de clorofila en dosel denso.

### Resultado (primera vez, sin caché)

| Concepto | Valor |
|---|---|
| Índices procesados de verdad | 5 (NDVI, NDMI, SAVI, EVI, NDRE) |
| Llamadas HTTP reales a EOSDA | **10** (5 índices × 2) |
| Tokens consumidos del rate limiter (8/min) | **10** |
| Incremento de `eosda_requests` (cuota mensual) | **+10** |
| Filas nuevas en `EosdaRequestLog` | **10** |

> Nota: 10 tokens equivalen a ~1 minuto 15 segundos al límite de 8/min. Las 2
> últimas llamadas se encolarán hasta liberarse un token.

### Resultado (segunda vez, todo en caché)

Si el mismo tenant repite **el mismo análisis** de la misma parcela (misma escena
e índice) dentro del tiempo de caché:

| Concepto | Valor |
|---|---|
| Llamadas HTTP reales a EOSDA | **0** |
| Tokens del rate limiter | **0** |
| Incremento de `eosda_requests` | **0** |
| Filas en `EosdaRequestLog` | **0** |

Todo se sirve desde la caché: el análisis es instantáneo y **no cuesta nada**.

---

## 5. Resumen de una línea

> **Se gasta solo lo que sale de verdad hacia EOSDA**: cada llamada HTTP consume
> 1 token del límite global de 8/min, y cada "análisis" (operación lógica) suma
> 1 a la cuota mensual del tenant y 1 fila al registro. Lo que se sirve desde
> caché no consume nada.
