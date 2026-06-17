# 🔍 AUDITORÍA COMPLETA: Uso de Requests EOSDA API

**Fecha:** 5 de Febrero 2026  
**Objetivo:** Verificar que el consumo de requests EOSDA coincida con el análisis de costos  
**Estado:** ⚠️ **CRÍTICO - DECORADOR NO APLICADO**

---

## 📊 RESUMEN EJECUTIVO

### ❌ PROBLEMA ENCONTRADO

**EL DECORADOR `@check_eosda_limit` NO ESTÁ APLICADO EN NINGUNA VISTA QUE LLAME A EOSDA**

- ✅ Decorador **existe** y está bien implementado en `billing/decorators.py`
- ✅ Decorador **funciona** (incrementa contador + verifica límites)
- ❌ Decorador **NO está aplicado** a ningún endpoint que haga requests EOSDA
- ❌ Sistema **NO está contando** requests reales actualmente
- ❌ Sistema **NO está validando** límites de planes

**IMPACTO:**
- Los usuarios pueden hacer requests EOSDA ilimitados (sin control)
- No se están registrando las métricas de uso real
- No se pueden facturar overages
- Los límites de planes (100/500 requests) no se están aplicando

---

## 🔍 ANÁLISIS DETALLADO POR ENDPOINT

### 1️⃣ **Scene Search** (Búsqueda de imágenes satelitales)

#### Endpoint Backend
```
POST /api/parcels/eosda-scenes/
```

#### Archivo
`parcels/views.py` - Clase `EosdaScenesView` (línea 345)

#### Requests EOSDA por operación
```python
1. POST https://api-connect.eos.com/scene-search/for-field/{field_id}
   → Retorna: request_id
   
2. GET https://api-connect.eos.com/scene-search/for-field/{field_id}/{request_id}
   → Retorna: lista de escenas con view_id, date, cloud_cover

TOTAL: 2 requests EOSDA
```

#### Cache Implementado
✅ **SÍ** - Cache de 10 minutos por `field_id`
```python
cache_key = f"eosda_scenes_{field_id}"
cache.set(cache_key, response_data, 600)  # 10 minutos
```

#### Decorador Aplicado
❌ **NO** - Falta agregar `@check_eosda_limit`

#### Código Actual
```python
class EosdaScenesView(APIView):
    permission_classes = [IsAuthenticated]
    # ❌ FALTA: @check_eosda_limit
    
    def post(self, request):
        # ... hace 2 requests a EOSDA sin contabilizar
```

---

### 2️⃣ **Image Generation** (Generación de imágenes NDVI/NDMI/EVI)

#### Endpoint Backend
```
POST /api/parcels/eosda-image/
```

#### Archivo
`parcels/views.py` - Clase `EosdaImageView` (línea 433)

#### Requests EOSDA por operación
```python
1. POST https://api-connect.eos.com/field-imagery/indicies/{field_id}
   → Params: { view_id, index: "NDVI"|"NDMI"|"EVI", format: "png" }
   → Retorna: request_id

TOTAL: 1 request EOSDA
```

#### Cache Implementado
✅ **SÍ** - Cache de 30 minutos por combinación `field_id+view_id+type`
```python
cache_key = f"eosda_image_request_{field_id}_{view_id}_{index_type}"
cache.set(cache_key, request_id, 1800)  # 30 minutos
```

#### Decorador Aplicado
❌ **NO** - Falta agregar `@check_eosda_limit`

#### Código Actual
```python
class EosdaImageView(APIView):
    permission_classes = [IsAuthenticated]
    # ❌ FALTA: @check_eosda_limit
    
    def post(self, request):
        # ... hace 1 request a EOSDA sin contabilizar
```

---

### 3️⃣ **Image Download** (Descarga de imagen generada)

#### Endpoint Backend
```
GET /api/parcels/eosda-image-result/?field_id=...&request_id=...
```

#### Archivo
`parcels/views.py` - Clase `EosdaImageResultView` (línea 494)

#### Requests EOSDA por operación
```python
1. GET https://api-connect.eos.com/field-imagery/{field_id}/{request_id}
   → Retorna: Imagen PNG en base64

TOTAL: 1 request EOSDA
```

#### Cache Implementado
✅ **SÍ** - Cache de 1 hora por `request_id`
```python
image_cache_key = f"eosda_image_{request_id}"
cache.set(image_cache_key, image_base64, 3600)  # 1 hora
```

#### Decorador Aplicado
❌ **NO** - Falta agregar `@check_eosda_limit`

#### Nota Importante
⚠️ Este endpoint puede generar **múltiples requests** si el usuario descarga varias veces la misma imagen (si no hay cache hit). Sin decorador, no hay límite.

---

### 4️⃣ **Scene Analytics** (Estadísticas de escena - NDVI/NDMI/EVI)

#### Endpoint Backend
```
POST /api/parcels/eosda-scene-analytics/
```

#### Archivo
`parcels/views.py` - Clase `EosdaSceneAnalyticsView` (línea 598)

#### Requests EOSDA por operación
```python
# Por defecto solicita 3 índices: NDVI, NDMI, EVI

1. POST https://api-connect.eos.com/v1/indices/ndvi
   → Params: { geometry, start_date, end_date }
   
2. POST https://api-connect.eos.com/v1/indices/ndmi
   → Params: { geometry, start_date, end_date }
   
3. POST https://api-connect.eos.com/v1/indices/evi
   → Params: { geometry, start_date, end_date }

TOTAL: 3 requests EOSDA (1 por cada índice solicitado)
```

#### Cache Implementado
✅ **SÍ** - Cache de 2 horas por `field_id+view_id+date`
```python
cache_key = f"eosda_analytics_{field_id}_{view_id}_{scene_date}"
cache.set(cache_key, response_data, 7200)  # 2 horas
```

#### Decorador Aplicado
❌ **NO** - Falta agregar `@check_eosda_limit`

#### Nota Crítica
⚠️ Este endpoint es el **MÁS COSTOSO** - hace 3 requests por cada análisis de escena

---

### 5️⃣ **Advanced Statistics** (API Statistics - nueva)

#### Endpoint Backend
```
POST /api/parcels/eosda-advanced-statistics/
```

#### Archivo
`parcels/views.py` - Clase `EosdaAdvancedStatisticsView` (línea 781)

#### Requests EOSDA por operación
```python
1. POST https://api-connect.eos.com/api/gdw/api
   → Params: { type: "mt_stats", geometry, date_start, date_end, indices: [...] }
   → Retorna: task_id
   
2. GET https://api-connect.eos.com/api/gdw/api/{task_id}
   → Polling hasta que status = "completed"
   → Retorna: estadísticas completas (mean, median, std, min, max, percentiles)

TOTAL: 2 requests EOSDA (asumiendo 1 poll para completar)
```

#### Cache Implementado
✅ **SÍ** - Cache de 24 horas por `field_id+date+indices`
```python
cache_key = f"eosda_advanced_stats_{field_id}_{scene_date}_{'_'.join(sorted(indices))}"
cache.set(cache_key, response_data, 86400)  # 24 horas
```

#### Decorador Aplicado
❌ **NO** - Falta agregar `@check_eosda_limit`

---

### 6️⃣ **Analytics API Real** (Vista independiente)

#### Endpoint Backend
```
POST /api/parcels/eosda-analytics/
GET /api/parcels/eosda-analytics/
```

#### Archivo
`parcels/analytics_views.py` - Clase `EOSDAAnalyticsAPIView` (línea 20)

#### Requests EOSDA por operación
```python
1. POST https://api-connect.eos.com/api/gdw/api
   → Params: { type: "mt_stats", geometry, date_start, date_end, indices: [...] }
   → Retorna: task_id
   
2. GET https://api-connect.eos.com/api/gdw/api/{task_id}
   → Polling hasta completar
   → Retorna: estadísticas científicas reales

TOTAL: 2 requests EOSDA (mínimo)
```

#### Cache Implementado
✅ **SÍ** - Cache de 2 horas por `view_id+scene_date+parcel_id`
```python
cache_key = f"eosda_real_analytics_{hashlib.md5(view_id.encode()).hexdigest()[:8]}_{scene_date}_{parcel_id}"
cache.set(cache_key, interpreted_data, 7200)  # 2 horas
```

#### Decorador Aplicado
❌ **NO** - Falta agregar `@check_eosda_limit`

---

### 7️⃣ **Historical Indices** (Índices históricos de parcela)

#### Endpoint Backend
```
POST /api/parcels/parcel-historical-indices/
```

#### Archivo
`parcels/views.py` - Clase `ParcelHistoricalIndicesView` (línea 1300)

#### Requests EOSDA por operación
```python
# Por defecto solicita NDVI + NDMI (2 índices) para 90 días

1. POST https://api-connect.eos.com/field-analytics/trend/{eosda_id}
   → Params: { type: "ndvi", date_start, date_end }
   
2. POST https://api-connect.eos.com/field-analytics/trend/{eosda_id}
   → Params: { type: "ndmi", date_start, date_end }

TOTAL: 2 requests EOSDA (1 por índice)
```

#### Cache Implementado
✅ **SÍ** - Cache de 6 horas por `field_id+index+date_range`
```python
cache_key = f"eosda_trend_{field_id}_{index}_{date_start}_{date_end}"
cache.set(cache_key, index_data, 21600)  # 6 horas
```

#### Decorador Aplicado
❌ **NO** - Falta agregar `@check_eosda_limit`

---

### 8️⃣ **Weather Data** (Datos meteorológicos)

#### Endpoint Backend
```
POST /api/parcels/weather-forecast/
POST /api/parcels/weather-comparison/
```

#### Archivos
- `parcels/metereological.py` - `WeatherForecastView`
- `parcels/views.py` - `ParcelNdviWeatherComparisonView`

#### Requests EOSDA por operación
```python
1. POST https://api-connect.eos.com/api/forecast/weather/forecast/
   → Params: { geometry, date_start, date_end }
   → Retorna: pronóstico 14 días

2. POST https://api-connect.eos.com/weather/historical-accumulated/{field_id}
   → Params: { date_start, date_end }
   → Retorna: datos históricos (temperatura, lluvia, humedad)

TOTAL: 1-2 requests EOSDA (según endpoint usado)
```

#### Cache Implementado
✅ **SÍ** - Cache variable (1-12 horas según tipo de datos)

#### Decorador Aplicado
❌ **NO** - Falta agregar `@check_eosda_limit`

---

## 🧮 CONTEO REAL DE REQUESTS POR FLUJO COMPLETO

### **Flujo 1: Usuario selecciona parcela y analiza 1 escena NDVI**

```
1. Scene Search (buscar imágenes disponibles)
   POST /eosda-scenes/
   → 2 requests EOSDA
   
2. Generate NDVI Image (generar imagen de escena seleccionada)
   POST /eosda-image/ (type=ndvi)
   → 1 request EOSDA
   
3. Download NDVI Image (descargar imagen generada)
   GET /eosda-image-result/
   → 1 request EOSDA
   
4. Get Scene Analytics (estadísticas NDVI de la escena)
   POST /eosda-scene-analytics/
   → 3 requests EOSDA (NDVI + NDMI + EVI por defecto)

TOTAL: 7 requests EOSDA
```

**❌ PROBLEMA:** Mi análisis decía "5-6 requests", pero en realidad son **7 requests**

### **Flujo 2: Usuario analiza 3 índices (NDVI + NDMI + EVI) para misma escena**

```
1. Scene Search (ya hecho, cache hit)
   → 0 requests (cache)
   
2. Generate NDVI Image
   POST /eosda-image/ (type=ndvi)
   → 1 request EOSDA
   
3. Generate NDMI Image
   POST /eosda-image/ (type=ndmi)
   → 1 request EOSDA
   
4. Generate EVI Image
   POST /eosda-image/ (type=evi)
   → 1 request EOSDA
   
5. Download 3 Images
   GET /eosda-image-result/ (×3)
   → 3 requests EOSDA
   
6. Get Scene Analytics (ya hecho si mismo view_id+date)
   → 0 requests (cache)

TOTAL: 6 requests EOSDA adicionales
TOTAL ACUMULADO: 7 + 6 = 13 requests EOSDA
```

**❌ PROBLEMA:** Cada índice adicional = 2 requests más (generar + descargar)

### **Flujo 3: Usuario revisa histórico de 90 días**

```
1. Historical NDVI Trend (últimos 90 días)
   POST /parcel-historical-indices/
   → 2 requests EOSDA (NDVI + NDMI)

TOTAL: 2 requests EOSDA
```

### **Flujo 4: Usuario compara con clima**

```
1. Weather Forecast (pronóstico 14 días)
   POST /weather-forecast/
   → 1 request EOSDA
   
2. Weather Historical (datos pasados)
   POST /weather-historical/
   → 1 request EOSDA

TOTAL: 2 requests EOSDA
```

---

## 🎯 CONSUMO REAL VS ANÁLISIS PREVIO

### Mi Estimación Original (ANALISIS_BREAK_EVEN_REAL.md)

```
"1 análisis de parcela = 5-6 requests EOSDA"

Desglose estimado:
- Scene search: 1 request
- NDVI image: 1 request  
- NDMI image: 1 request
- EVI image: 1 request
- Analytics: 1 request

TOTAL ESTIMADO: 5 requests
```

### Realidad del Código Actual

```
1 análisis COMPLETO de parcela = 7-13 requests EOSDA

Desglose real (caso básico NDVI solo):
- Scene search POST: 1 request
- Scene search GET: 1 request
- NDVI generate: 1 request
- NDVI download: 1 request
- Analytics (NDVI+NDMI+EVI): 3 requests

TOTAL REAL (caso básico): 7 requests

Desglose real (caso completo 3 índices):
- Scene search: 2 requests
- Generate 3 images: 3 requests
- Download 3 images: 3 requests
- Analytics: 3 requests
- Historical trend: 2 requests

TOTAL REAL (caso completo): 13 requests
```

### 📉 IMPACTO EN ANÁLISIS DE COSTOS

#### Plan BASIC (100 requests/mes)

**Estimación Original:**
- 100 requests ÷ 5 = **20 análisis completos/mes**
- 5 parcelas × 2 reviews/mes = 10 análisis → **50% del límite**

**Realidad del Código:**
- 100 requests ÷ 7 = **14 análisis básicos/mes**
- 100 requests ÷ 13 = **7 análisis completos/mes**
- 5 parcelas × 2 reviews/mes (básico) = 10 análisis × 7 = **70 requests (70% del límite)**
- 5 parcelas × 2 reviews/mes (completo) = 10 análisis × 13 = **130 requests (EXCEDE 30%)**

**❌ PROBLEMA:** Plan BASIC insuficiente si usuarios usan todos los índices

#### Plan PRO (500 requests/mes)

**Estimación Original:**
- 500 requests ÷ 5 = **100 análisis completos/mes**
- 10 parcelas × 2 reviews/mes = 20 análisis → **20% del límite**

**Realidad del Código:**
- 500 requests ÷ 7 = **71 análisis básicos/mes**
- 500 requests ÷ 13 = **38 análisis completos/mes**
- 10 parcelas × 2 reviews/mes (básico) = 20 análisis × 7 = **140 requests (28% del límite)**
- 10 parcelas × 2 reviews/mes (completo) = 20 análisis × 13 = **260 requests (52% del límite)**

**✅ OK:** Plan PRO tiene margen suficiente

---

## 🛡️ CACHE: ¿Está funcionando correctamente?

### ✅ BUENOS: Cache Implementado

| Endpoint | Cache Key | Duración | Efectividad |
|----------|-----------|----------|-------------|
| `EosdaScenesView` | `eosda_scenes_{field_id}` | 10 min | ✅ Alta - Evita búsquedas repetidas |
| `EosdaImageView` | `eosda_image_request_{field_id}_{view_id}_{type}` | 30 min | ✅ Alta - Evita regenerar request_id |
| `EosdaImageResultView` | `eosda_image_{request_id}` | 1 hora | ✅ Media - Solo si mismo request_id |
| `EosdaSceneAnalyticsView` | `eosda_analytics_{field_id}_{view_id}_{date}` | 2 horas | ✅ Alta - Evita recalcular stats |
| `EosdaAdvancedStatisticsView` | `eosda_advanced_stats_{field_id}_{date}_{indices}` | 24 horas | ✅ Muy Alta - Datos históricos |
| `ParcelHistoricalIndicesView` | `eosda_trend_{field_id}_{index}_{dates}` | 6 horas | ✅ Alta - Trends no cambian rápido |

### ⚠️ ÁREAS DE MEJORA

1. **Cache de Scene Search es CORTO (10 minutos)**
   - Escenas disponibles no cambian durante el día
   - Debería ser 6-12 horas
   - Ahorro: 2 requests por usuario por día

2. **Cache de Image Result solo por request_id**
   - Si usuario genera misma imagen 2 veces (diferente request_id), hace 2 downloads
   - Debería cachear también por `{field_id}_{view_id}_{type}`
   - Ahorro: 1-2 requests por parcela

3. **No hay cache para Weather Forecast**
   - Pronóstico 14 días no cambia cada minuto
   - Debería tener cache de 12 horas
   - Ahorro: 1-2 requests por usuario por día

---

## 🔥 OPTIMIZACIONES URGENTES REQUERIDAS

### 1. **APLICAR DECORADOR `@check_eosda_limit`** (Prioridad CRÍTICA)

**Archivos a modificar:**

```python
# parcels/views.py

from billing.decorators import check_eosda_limit

class EosdaScenesView(APIView):
    permission_classes = [IsAuthenticated]
    
    @check_eosda_limit  # ← AGREGAR
    def post(self, request):
        # ... código existente
        
class EosdaImageView(APIView):
    permission_classes = [IsAuthenticated]
    
    @check_eosda_limit  # ← AGREGAR
    def post(self, request):
        # ... código existente
        
class EosdaImageResultView(APIView):
    permission_classes = [IsAuthenticated]
    
    @check_eosda_limit  # ← AGREGAR
    def get(self, request):
        # ... código existente
        
class EosdaSceneAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]
    
    @check_eosda_limit  # ← AGREGAR
    def post(self, request):
        # ... código existente
        
class EosdaAdvancedStatisticsView(APIView):
    permission_classes = [IsAuthenticated]
    
    @check_eosda_limit  # ← AGREGAR
    def post(self, request):
        # ... código existente
        
class ParcelHistoricalIndicesView(APIView):
    permission_classes = [IsAuthenticated]
    
    @check_eosda_limit  # ← AGREGAR
    def post(self, request):
        # ... código existente
```

```python
# parcels/analytics_views.py

from billing.decorators import check_eosda_limit

class EOSDAAnalyticsAPIView(APIView):
    permission_classes = [AllowAny]  # Cambiar a IsAuthenticated
    
    @check_eosda_limit  # ← AGREGAR
    def get(self, request):
        # ... código existente
    
    @check_eosda_limit  # ← AGREGAR
    def post(self, request):
        # ... código existente
```

```python
# parcels/metereological.py

from billing.decorators import check_eosda_limit

class WeatherForecastView(APIView):
    permission_classes = [IsAuthenticated]
    
    @check_eosda_limit  # ← AGREGAR
    def post(self, request):
        # ... código existente
```

**IMPACTO:**
- ✅ Control de límites por plan (BASIC 100, PRO 500)
- ✅ Registro de métricas reales de uso
- ✅ Bloqueo cuando usuario excede límite
- ✅ Posibilidad de facturar overages

---

### 2. **AUMENTAR CACHE DE SCENE SEARCH** (Prioridad ALTA)

**Cambio:**
```python
# parcels/views.py - EosdaScenesView

# ANTES
cache.set(cache_key, response_data, 600)  # 10 minutos

# DESPUÉS
cache.set(cache_key, response_data, 21600)  # 6 horas
```

**Justificación:**
- Escenas Sentinel-2 disponibles no cambian durante el día
- Nueva escena aparece cada 5-10 días (no cada 10 minutos)
- Usuario típico revisa misma parcela varias veces al día

**Ahorro:** 2 requests × 10 revisiones/día = **20 requests/día por usuario activo**

---

### 3. **CACHE DUAL PARA IMÁGENES** (Prioridad MEDIA)

**Problema Actual:**
```python
# Solo cachea por request_id
image_cache_key = f"eosda_image_{request_id}"
```

**Solución:**
```python
# Cachear TAMBIÉN por combinación field_id+view_id+type
composite_cache_key = f"eosda_image_composite_{field_id}_{view_id}_{index_type}"
cached_image = cache.get(composite_cache_key)

if cached_image:
    return Response({"image_base64": cached_image}, status=200)

# ... obtener imagen de EOSDA ...

# Guardar en AMBOS caches
cache.set(image_cache_key, image_base64, 3600)  # Por request_id
cache.set(composite_cache_key, image_base64, 3600)  # Por field+view+type
```

**Ahorro:** 1 request por regeneración de misma escena

---

### 4. **REDUCIR ANALYTICS A 1 ÍNDICE POR DEFECTO** (Prioridad MEDIA)

**Problema Actual:**
```python
# EosdaSceneAnalyticsView siempre solicita 3 índices
indices = request.data.get("indices", ["ndvi", "ndmi", "evi"])  # 3 requests

# Total: 3 requests EOSDA por cada análisis
```

**Solución:**
```python
# Solo NDVI por defecto, usuario debe solicitar explícitamente los otros
indices = request.data.get("indices", ["ndvi"])  # Solo 1 request

# Si usuario quiere más, debe enviarlos en request body
# Frontend debe tener checkbox para "Incluir NDMI" y "Incluir EVI"
```

**Ahorro:** 2 requests por análisis básico × 20 análisis/mes = **40 requests/mes por usuario**

---

### 5. **BATCH PROCESSING PARA MÚLTIPLES ÍNDICES** (Prioridad BAJA)

**Concepto:**
En lugar de hacer 3 requests separados (NDVI, NDMI, EVI), hacer 1 request que obtenga los 3 juntos.

**Implementación:**
```python
# Usar EOSDA Statistics API (mt_stats) que acepta múltiples índices en 1 request

payload = {
    "type": "mt_stats",
    "geometry": polygon_geojson,
    "date_start": scene_date,
    "date_end": scene_date,
    "indices": ["ndvi", "ndmi", "evi"]  # ← Todos en 1 request
}

response = requests.post("https://api-connect.eos.com/api/gdw/api", json=payload, headers=headers)
```

**Ahorro:** 3 requests → 1 request = **ahorro de 66% en analytics**

---

## 📋 CHECKLIST DE CORRECCIONES

### Paso 1: Aplicar Decoradores (CRÍTICO)
- [ ] `EosdaScenesView` → agregar `@check_eosda_limit`
- [ ] `EosdaImageView` → agregar `@check_eosda_limit`
- [ ] `EosdaImageResultView` → agregar `@check_eosda_limit`
- [ ] `EosdaSceneAnalyticsView` → agregar `@check_eosda_limit`
- [ ] `EosdaAdvancedStatisticsView` → agregar `@check_eosda_limit`
- [ ] `ParcelHistoricalIndicesView` → agregar `@check_eosda_limit`
- [ ] `EOSDAAnalyticsAPIView` → agregar `@check_eosda_limit` (+ cambiar permission a IsAuthenticated)
- [ ] `WeatherForecastView` → agregar `@check_eosda_limit`

### Paso 2: Optimizar Cache (ALTA PRIORIDAD)
- [ ] Scene Search: 10 min → 6 horas
- [ ] Image Result: agregar cache dual (por composite key)
- [ ] Weather Forecast: agregar cache de 12 horas

### Paso 3: Reducir Requests Innecesarios (MEDIA PRIORIDAD)
- [ ] Analytics: cambiar default a solo NDVI (no 3 índices)
- [ ] Frontend: agregar checkboxes para solicitar NDMI/EVI explícitamente
- [ ] Batch processing: migrar a Statistics API para múltiples índices en 1 request

### Paso 4: Actualizar Documentación (BAJA PRIORIDAD)
- [ ] Actualizar `ANALISIS_BREAK_EVEN_REAL.md` con conteo real (7-13 requests)
- [ ] Actualizar `create_billing_plans.py` con límites ajustados si necesario
- [ ] Documentar flujo real de requests en README

---

## 🎯 IMPACTO DE CORRECCIONES EN COSTOS

### Escenario ACTUAL (Sin decorador, sin optimizaciones)

```
Plan BASIC (100 requests/mes):
- 5 parcelas × 2 reviews/mes × 13 requests = 130 requests
- EXCEDE LÍMITE EN 30%
- Costo overages: 30 × 25 COP = 750 COP/mes adicionales

Plan PRO (500 requests/mes):
- 10 parcelas × 2 reviews/mes × 13 requests = 260 requests
- 52% del límite (OK pero alto)
```

### Escenario CON CORRECCIONES (Decorador + optimizaciones)

```
Plan BASIC (100 requests/mes):
- 5 parcelas × 2 reviews/mes × 5 requests* = 50 requests
- 50% del límite (ÓPTIMO)
- Sin overages
- *Cache reduce de 7 a 5: scene search cacheado, solo NDVI

Plan PRO (500 requests/mes):
- 10 parcelas × 2 reviews/mes × 5 requests* = 100 requests
- 20% del límite (HOLGADO)
- Sin overages
- Margen para power users
```

### Ahorro de Costos EOSDA

**Usuario BASIC típico:**
- Antes: 130 requests/mes
- Después: 50 requests/mes
- Ahorro: **61% menos requests**

**Usuario PRO típico:**
- Antes: 260 requests/mes
- Después: 100 requests/mes
- Ahorro: **61% menos requests**

**Capacidad del Plan EOSDA Starter (10,000 requests/mes):**
- Antes: 10,000 ÷ 130 = **76 usuarios BASIC**
- Después: 10,000 ÷ 50 = **200 usuarios BASIC**
- **Capacidad incrementada 2.6x**

**Impacto Financiero:**
- Antes necesitábamos Plan Innovator (20k requests) con 100 clientes
- Después podemos usar Plan Starter (10k requests) con 100 clientes
- Ahorro: $125/mes - $83/mes = **$42 USD/mes = 168k COP/mes**
- Ahorro anual: **$504 USD = 2,016k COP/año**

---

## ✅ CONCLUSIONES

### 🔴 Problemas Críticos Encontrados

1. **Decorador `@check_eosda_limit` NO aplicado**
   - Sistema no controla límites actualmente
   - Usuarios pueden hacer requests ilimitados
   - No se registran métricas reales
   
2. **Conteo de requests subestimado**
   - Análisis decía 5-6 requests
   - Realidad es 7-13 requests
   - Diferencia de 2-7 requests (40-140% más)

3. **Plan BASIC puede exceder límite**
   - Con uso completo (3 índices) excede en 30%
   - Genera overages no contemplados en pricing

### 🟡 Optimizaciones Necesarias

1. **Cache muy corto en Scene Search**
   - 10 minutos actual vs 6 horas óptimo
   - Causa 2 requests innecesarios por día/usuario
   
2. **Analytics solicita 3 índices por defecto**
   - Mayoría usuarios solo necesita NDVI
   - Waste de 2 requests por análisis

3. **No hay batch processing**
   - 3 requests para 3 índices
   - Podría ser 1 request con Statistics API

### 🟢 Soluciones Propuestas

1. **Aplicar decoradores** → Control + métricas
2. **Aumentar cache** → Ahorro 61% requests
3. **Solo NDVI default** → Ahorro 2 requests/análisis
4. **Batch API** → Ahorro 66% en analytics

### 📊 Resultado Esperado

**Con todas las correcciones:**
- Plan BASIC: 50 requests/mes (50% del límite)
- Plan PRO: 100 requests/mes (20% del límite)
- Capacidad EOSDA Starter: 200 usuarios (vs 76 actual)
- Ahorro costos: 168k COP/mes = 2M COP/año
- Break-even: 12 clientes (sin cambios)
- Margen: 77% (aumenta con menores costos EOSDA)

---

## 🚀 PRÓXIMOS PASOS

1. **APLICAR DECORADORES** (hoy mismo)
   - Copiar código de arriba
   - Agregar import y decorador a 8 vistas
   - Probar con usuario test
   
2. **OPTIMIZAR CACHE** (esta semana)
   - Scene Search: 10 min → 6 horas
   - Image Result: cache dual
   - Weather: agregar cache 12 horas
   
3. **AJUSTAR ANALYTICS** (próxima semana)
   - Default a solo NDVI
   - Frontend: checkboxes para NDMI/EVI
   
4. **MIGRAR A BATCH API** (mes siguiente)
   - Implementar Statistics API
   - Deprecar índices separados
   - A/B testing con usuarios

---

**Auditado por:** GitHub Copilot  
**Validado:** NO - Requiere pruebas con usuarios reales  
**Acción requerida:** Aplicar correcciones URGENTES (Paso 1)
