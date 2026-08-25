# Plan: Sentinel-2 como motor principal (ocultar EOSDA) + Análisis de píxeles profesional

> Decisión tomada: **Sentinel-2 gratis es el motor principal**. EOSDA se **oculta** (NO se borra la integración, queda para urgencias).

---

## Contexto

- Backend ya tiene: `get_index_images` (PNG con contraste/modos/colormaps), `get_index_analysis` (mean/min/max/std/percentiles), máscara SCL, NDVI/NDMI/SAVI/NDRE reales.
- El "Análisis de Imagen" actual (`parcel.js` → `mostrarImagenNDVIConAnalisis`) usa **detección de colores** sobre la imagen EOSDA (impreciso).
- El "Estado Rápido" (Vegetación/Humedad/Próx. Lluvia/Últ. Imagen) y el "Análisis dinámico" dependen de EOSDA.

---

## FASE 1 — Backend: análisis de píxeles REAL (no color)

1. **`get_index_categories(geometry, scene_date, index)`** en `parcels/sentinel2.py`:
   - Clasifica cada píxel válido del índice por **umbrales NDVI reales** (no colores).
   - Categorías: `Vegetación Escasa (<0.25)`, `Estrés Moderado (0.25–0.40)`, `Vigor Bajo (0.40–0.50)`, `Vegetación Densa (0.50–0.65)`, `Muy Densa (0.65–0.75)`, `Vigor Óptimo (>0.75)`.
   - Devuelve: `total_pixels`, `mean`, `categories [{key, label, pct, count}]`, `alerts`, `recommendations`.
2. **Alertas/recomendaciones** derivadas de los %: si escasa >30% → "atención/suelo expuesto"; si estrés+bajo >40% → "posible estrés nutricional/hídrico"; si densa+muy densa+óptimo >50% → "buena cobertura".
3. Exponer en el endpoint de imágenes: agregar campo `analysis` (categorías del NDVI) y soportar `?analysis_index=`.

## FASE 2 — Ocultar EOSDA (sin borrar integración)

1. **Botón "Buscar escenas satelitales"** (`parcels-dashboard.html` línea ~654): ocultarlo o renombrarlo a algo neutral (ej. "Historial de escenas") pero marcarlo como "no principal". NO borrar el flujo `parcel.js` que lo respalda.
2. **Quitar branding "EOSDA"** visible al usuario:
   - `sentinel2-compare.js`: título "Sentinel-2 gratis (comparar con EOSDA)" → "Análisis satelital de la parcela" (quitar "gratis" y "EOSDA").
   - Toasts/logs con "Datos EOSDA reales" (`meteorological-analysis.js`, `analytics-cientifico.js`, etc.) → quitar la palabra EOSDA del texto visible.
   - `index-old.html` meta keywords/description → quitar "EOSDA".
3. **No tocar** `parcels/eosda_client.py`, `eosda-*` endpoints, ni el `eosda_id` (la integración queda intacta para urgencia).

## FASE 3 — Frontend: Estado Rápido + Análisis con S2

1. **Análisis de píxeles real**: reemplazar `mostrarImagenNDVIConAnalisis` (color) por una función que consuma `analysis` (categorías reales) del endpoint S2 y pinte el panel "Análisis de Imagen":
   - Tarjetas % por categoría (con tooltip de significado).
   - "Total píxeles analizados".
   - Alerta + recomendaciones.
2. **Estado Rápido**: cablear Vegetación (NDVI mean), Humedad (NDMI mean) y Últ. Imagen (fecha de escena) desde S2, no EOSDA.
3. **Leyenda fija** en el panel de análisis (🔴 Atención → 🟠 Bajo → 🟡 Intermedio → 🟢 Bueno → 🟢 Excelente).

## FASE 4 — Brechas para el siguiente nivel (priorizadas)

1. **Leyenda fija sobre el mapa** (no solo en el modal) — coherencia visual.
2. **Series temporales NDVI/NDMI** (evolución entre escenas) — ya existe `get_index_analysis`, falta graficar.
3. **Comparativa entre fechas** (misma parcela, dos escenas) — el modo STANDARD ya lo permite.
4. **Alertas históricas** (registrar cuándo una zona estuvo en "atención").
5. **Exportación/reporte** (PDF de análisis de parcela).
6. **Caché de análisis** por parcela+fecha (evitar relectura del COG).

## Criterios de "listo"
- [ ] El análisis de píxeles sale de valores NDVI reales (no colores).
- [ ] No aparece "EOSDA" ni "gratis" en ninguna pantalla visible.
- [ ] La integración EOSDA sigue funcional (oculta, no borrada).
- [ ] Estado Rápido + Análisis de Imagen funcionan con S2.
- [ ] Brechas documentadas y priorizadas.

---

# FASE 5 — Radar + Monitoreo Constante (plan PREMIUM) · PENDIENTE DE ARRANQUE

> Estado: **PLAN APROBADO, sin fecha de inicio** (el usuario avisará cuándo arrancar).
> Propuesta: radar (Sentinel-1) **solo en plan caro**, que incluya **monitoreo constante automático** con alertas.

## Idea (aprobada por el usuario)

1. **Radar → gated a plan premium** (no free, no Agricultor).
2. Ese plan premium incluye **monitoreo constante sin que el cliente lo pida** + **alertas**.
3. Lógica automática:
   - **Primero Sentinel-2**: si hay escena con nubosidad < 30% → entrega S2 (imagen + índices + análisis + alertas).
   - **Si no** → usa **radar** solo para verificar que **no hay cambios bruscos** en el polígono.

## Por qué es buena (contexto de negocio)

- **Costo marginal cero**: S2 y S1 son gratis (Planetary Computer). El "monitoreo constante" no nos cuesta por request.
- **Upsell claro**: radar + vigilancia = premium, con margen casi puro.

## ⚠️ Dato por investigar

- **Frecuencia de revisita de Sentinel-2**: el usuario señaló que "cada 2-3 días" puede no ser correcto. **Investigar** la frecuencia real (Sentinel-2A/B/C por separado y combinado) antes de prometer nada al cliente.
- Lo mismo para **Sentinel-1** (revisita real).

## Piezas que YA existen (no reimplementar)

| Pieza | Ubicación |
|---|---|
| Lógica "S2 primero, si no radar" (umbral 30%) | `get_observation_recommendation()` en `parcels/sentinel2.py` |
| Radar → detección de cambio brusco | `sentinel1.get_crop_status_from_radar()` + `detect_radar_change()` |
| Análisis S2 + alertas | `get_index_analysis()` + `get_index_categories()` |
| Motor de alertas agronómicas | app `agronomic_alerts` |
| Comando de monitoreo (manual) | `monitor_crops.py` |
| Planes con features | `billing.Plan.features_included` |

## Qué falta (pendiente de implementar)

1. **Programador** (cron / Celery beat) para el monitoreo automático diario.
2. **Feature flags** en planes: `radar` + `continuous_monitoring` en el plan premium.
3. **Modelo de historial**: guardar cada run (fecha, fuente S2/S1, resultado) + alertas generadas.
4. **Entrega de alertas**: email o notificación in-app (hoy solo se ven en dashboard).
5. **Definir/tunar "cambio brusco"** (umbral sigma0 en dB) para evitar falsos positivos.
6. **UI "Monitoreo constante"**: panel con historial de observaciones + alertas.

## Orden de implementación (cuando se arranque)

- **Fase 5.1** — Feature flags (`radar`, `continuous_monitoring`) en plan premium.
- **Fase 5.2** — Pipeline automático: job diario → `get_observation_recommendation` → S2 (<30%) o radar → guardar observación + alertas.
- **Fase 5.3** — Notificación: email / badge in-app al detectar cambio.
- **Fase 5.4** — Panel "Monitoreo constante" con historial.

## Nota técnica de frecuencia (por confirmar)

- Monitoreo "constante" en la práctica = revisar por escenas NUEVAS (no cada hora). La frecuencia depende de la revisita real de S2/S1 (**investigar**).
- A escala (cientos de parcelas) → cola/throttle para Planetary Computer, o migrar a AWS Open Data.
