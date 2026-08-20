# Definición definitiva de `eosda_requests` y consumo EOSDA

> Documento normativo. Define con precisión qué cuenta cada capa del consumo.
> Sustituye cualquier ambigüedad previa entre "operación lógica" y "HTTP".

---

## Las 4 capas (separadas e independientes)

| Capa | Qué cuenta | Unidad | Alcance | Dónde |
|---|---|---|---|---|
| **A. Rate limiter** | Cada **HTTP real** a EOSDA | 1 por `POST` y 1 por cada `GET` de polling | **Global** (una sola API Key) | Redis `eosda:rate:sliding`, 8/min |
| **B. Cuota interna** (`eosda_requests`) | Cada **operación de análisis** | 1 por invocación de endpoint de análisis | Por tenant (mensual) | `UsageMetrics.eosda_requests` |
| **C. Auditoría** (`EosdaRequestLog`) | Cada operación real | 1 fila por `record()` | Global + por tenant | `EosdaRequestLog` (schema public) |
| **D. Facturación del proveedor** | Cómo EOSDA cobra | **Externo, NO asumido** | — | Pendiente de confirmar con EOSDA |

> ⚠️ **Nunca asumir que B o C equivalen a D.** La facturación del proveedor es un
> concepto externo que queda pendiente de confirmación.

---

## Definición exacta de B (`eosda_requests`) — cuota interna por tenant

**`eosda_requests` se incrementa exactamente 1 vez por cada invocación de un
endpoint de análisis EOSDA que realizó al menos una llamada HTTP real
(cache miss) y que resultó exitosa.**

Se incrementa **solo** en `EosdaClient.record()` (con `increment_quota=True`).

| Escenario | ¿Incrementa `eosda_requests`? | Explicación |
|---|---|---|
| Generar imagen (`image`) | +1 | 1 endpoint |
| Descargar imagen (`image_result`) | +1 | 1 endpoint (la imagen completa = 2: `image` + `image_result`) |
| Buscar escenas (`scenes`) | +1 | 1 endpoint, aunque haga 1 POST + N GET de polling |
| Analytics de escena (varios índices) | +1 | 1 endpoint, aunque haga N POST (uno por índice) |
| Analytics científico (gdw) | +1 | 1 endpoint, aunque haga POST + N GET de polling |
| Histórico (3 índices) | +1 | 1 endpoint, aunque haga 3 POST + N GET |
| NDVI/NDMI histórico puntual | +1 | 1 endpoint por índice |
| **NDRE** | +1 (igual que NDVI/NDMI/SAVI/EVI) | Es un índice más; 1 endpoint = 1 operación |
| **Polling** | **No suma aparte** | El polling es parte de la misma operación lógica |
| **Múltiples índices en una vista** | **No suma por índice** | 1 operación por invocación de endpoint |
| **Cache hit** | **0** | No sale a EOSDA |
| **Creación de campo (`field`)** | **0** (solo se registra en `EosdaRequestLog`) | No es análisis; `record(increment_quota=False)` |
| **Tiles (`render`)** | **0** | Render API, no es análisis; no se registra |
| **Error de EOSDA / timeout** | **0** | `record()` solo se llama en éxito |

---

## Regla de oro

- **Rate limiter** = cuántas veces golpeamos a EOSDA (HTTP). Protege el plan Starter (8/min).
- **`eosda_requests`** = cuántos "análisis" hizo el tenant (para su cuota mensual).
- **`EosdaRequestLog`** = quién, cuándo, qué parcela, qué índice, y si salió a EOSDA o fue cache.
- **Facturación EOSDA** = lo que cobra el proveedor (externo, no asumido).

## NDRE

- NDRE se trata como un índice más. Su consumo es idéntico al de NDVI/NDMI/EVI/SAVI:
  1 operación de análisis (`image` o `scene_analytics`) por invocación de endpoint.
- No hay un trato especial de cuota ni de registro para NDRE.
