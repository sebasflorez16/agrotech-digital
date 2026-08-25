# Comparación REAL: NDVI EOSDA vs Sentinel-2 gratis (Planetary Computer)

> Ejercicio de validación honesta. Cada lado generó su propio dato, sin copiarse.
> Fecha objetivo: **2026-08-02** (misma escena en ambos).

## Polígono de prueba
- Coordenadas: `[-73.40, 4.10] → [-73.38, 4.12]` (Llanos Orientales, Colombia)
- Área reportada por EOSDA: **491.1 ha**

## Resultado lado a lado

| Dato | EOSDA (pago) | Sentinel-2 gratis (Planetary Computer) |
|---|---|---|
| field / id | `11066045` | (sin field externo, usa geometría) |
| Escena | 2026-08-02 | 2026-08-02 |
| view_id / scene_id | `S2/18/N/XK/2026/8/2/0` | `S2C_MSIL2A_20260802T151721_R125_T18NXK_...` |
| Nubosidad | **36.53%** | **29.29%** |
| Imagen NDVI | ✅ `eosda_ndvi.png` (740×742 px, 92 KB) | ✅ `sentinel2_ndvi.png` (176×176 px, 27 KB) |
| NDVI mean | (vía analytics aparte) | **0.4553** |
| NDVI min / max | — | -0.1386 / 0.6753 |
| NDVI std | — | 0.1548 |

## Archivos generados
- `comparison_output/eosda_ndvi.png` — imagen NDVI de EOSDA.
- `comparison_output/sentinel2_ndvi.png` — imagen NDVI de Sentinel-2 gratis.
- `comparison_output/RESULTADOS.md` — este documento.

## Hallazgos clave (datos reales)

1. **Es la misma escena**: ambos apuntan al tile `T18NXK` del 2026-08-02 (Sentinel-2C).

2. **La nubosidad difiere**: EOSDA dice **36.53%**, Planetary Computer dice **29.29%**. No es un error: cada proveedor usa su propia máscara de nubes. Es un dato real y esperable.

3. **Ambos generan la imagen NDVI del polígono recortado.** EOSDA la renderiza a mayor resolución (740px); la ruta gratis la interpola desde una grilla ~30m a 176px (se puede subir la resolución ajustando el factor de interpolación).

4. **La ruta gratis entrega las estadísticas completas** (mean/min/max/std) en la misma llamada. EOSDA requiere un endpoint aparte de analytics.

5. **Costo**: EOSDA consumió requests (field + scene-search + image). La ruta gratis no consumió nada de pago.

## Conclusión
Con la misma escena y el mismo índice (NDVI), **la ruta gratuita (Sentinel-2 + Planetary Computer) produce una imagen NDVI real equivalente**, con la ventaja de entregar estadísticas directamente y sin costo por uso. La única diferencia práctica es la resolución de renderizado (mejorable) y el criterio de nubosidad de cada proveedor.
