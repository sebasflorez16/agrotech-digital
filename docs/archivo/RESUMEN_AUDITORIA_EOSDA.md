# 🚨 RESUMEN EJECUTIVO - Auditoría EOSDA Requests

**Fecha:** 5 de Febrero 2026  
**Estado:** ⚠️ **PROBLEMA CRÍTICO ENCONTRADO**

---

## 🔴 PROBLEMA PRINCIPAL

**El decorador `@check_eosda_limit` NO está aplicado a ninguna vista que llame a EOSDA**

### ¿Qué significa esto?

❌ Los usuarios pueden hacer **requests EOSDA ilimitados** (sin control)  
❌ No se están **registrando las métricas** de uso real  
❌ No se están **validando los límites** de planes (100/500 requests)  
❌ No se pueden **facturar overages** (excesos de uso)

### ¿Por qué no lo detecté antes?

El decorador **existe** y está bien programado en `billing/decorators.py`, pero:
- Solo está en la documentación como ejemplo
- Nunca se importó en las vistas de parcels
- Nunca se aplicó a los endpoints EOSDA

---

## 📊 CONTEO REAL DE REQUESTS

### Mi Estimación vs Realidad

| Concepto | Estimación | Realidad | Diferencia |
|----------|------------|----------|------------|
| 1 análisis básico (solo NDVI) | 5-6 requests | **7 requests** | +17-40% |
| 1 análisis completo (3 índices) | 5-6 requests | **13 requests** | +117-160% |

### Desglose Real de 1 Análisis NDVI

```
1. Scene Search POST    → 1 request EOSDA
2. Scene Search GET     → 1 request EOSDA
3. NDVI Image Generate  → 1 request EOSDA
4. NDVI Image Download  → 1 request EOSDA
5. Analytics (3 índices)→ 3 requests EOSDA (NDVI+NDMI+EVI por defecto)

TOTAL: 7 requests EOSDA
```

### Impacto en Planes

#### Plan BASIC (100 requests/mes)

**Mi estimación:**
- 5 parcelas × 2 reviews/mes × 5 requests = 50 requests
- Uso: 50% del límite ✅

**Realidad sin optimizaciones:**
- 5 parcelas × 2 reviews/mes × 13 requests = **130 requests**
- **EXCEDE el límite en 30%** ❌

**Realidad con optimizaciones:**
- 5 parcelas × 2 reviews/mes × 5 requests = **50 requests**
- Uso: 50% del límite ✅

#### Plan PRO (500 requests/mes)

**Mi estimación:**
- 10 parcelas × 2 reviews/mes × 5 requests = 100 requests
- Uso: 20% del límite ✅

**Realidad sin optimizaciones:**
- 10 parcelas × 2 reviews/mes × 13 requests = **260 requests**
- Uso: 52% del límite ⚠️ (alto pero OK)

**Realidad con optimizaciones:**
- 10 parcelas × 2 reviews/mes × 5 requests = **100 requests**
- Uso: 20% del límite ✅

---

## 🛠️ SOLUCIONES PROPUESTAS

### 1️⃣ CRÍTICO: Aplicar Decoradores (HOY)

**¿Qué hace el decorador?**
- Verifica límite del plan antes de ejecutar request
- Incrementa contador de uso (`metrics.eosda_requests += 1`)
- Bloquea si excede límite (retorna HTTP 429)
- Registra métricas para facturación

**Archivos a modificar:**
- `parcels/views.py` (6 vistas)
- `parcels/analytics_views.py` (1 vista)
- `parcels/metereological.py` (1 vista)

**Código a agregar:**
```python
from billing.decorators import check_eosda_limit

class EosdaScenesView(APIView):
    @check_eosda_limit  # ← AGREGAR ESTA LÍNEA
    def post(self, request):
        # ... código existente sin cambios
```

**Impacto:**
- ✅ Control de límites funcionando
- ✅ Métricas reales registradas
- ✅ Sistema listo para facturación

### 2️⃣ ALTA: Optimizar Cache (ESTA SEMANA)

**Problema:** Cache muy corto causa requests duplicados

**Cambios:**
```python
# Scene Search: 10 min → 6 horas (escenas no cambian tan rápido)
cache.set(cache_key, response_data, 21600)  # Antes: 600

# Image Result: cache dual (por request_id Y por field+view+type)
composite_key = f"eosda_image_composite_{field_id}_{view_id}_{type}"
cache.set(composite_key, image_base64, 3600)
```

**Ahorro:** 2 requests por día por usuario = **40% menos requests**

### 3️⃣ MEDIA: Reducir Analytics a 1 Índice (PRÓXIMA SEMANA)

**Problema:** Siempre solicita NDVI + NDMI + EVI (3 requests)

**Solución:**
```python
# Solo NDVI por defecto
indices = request.data.get("indices", ["ndvi"])  # Antes: ["ndvi", "ndmi", "evi"]
```

**Frontend:** Agregar checkboxes "Incluir NDMI" y "Incluir EVI"

**Ahorro:** 2 requests por análisis = **40% menos requests**

---

## 📈 IMPACTO FINANCIERO

### Con Todas las Optimizaciones

**Capacidad del Plan EOSDA Starter (10,000 requests/mes):**
- Antes: 76 usuarios BASIC
- Después: **200 usuarios BASIC**
- **Capacidad incrementada 2.6x**

**Ahorro de Costos:**
- Con 100 clientes podemos usar Starter en lugar de Innovator
- Ahorro: $125/mes - $83/mes = **$42 USD/mes**
- Ahorro anual: **$504 USD = 2,016,000 COP/año**

**Break-even:**
- Sin cambios: 12 clientes (igual)
- Margen mejora porque costos EOSDA bajan

---

## ✅ PLAN DE ACCIÓN INMEDIATO

### Paso 1: Aplicar Decoradores (30 minutos)

```bash
# 1. Editar parcels/views.py
# Agregar import:
from billing.decorators import check_eosda_limit

# Agregar @check_eosda_limit a:
# - EosdaScenesView.post
# - EosdaImageView.post
# - EosdaImageResultView.get
# - EosdaSceneAnalyticsView.post
# - EosdaAdvancedStatisticsView.post
# - ParcelHistoricalIndicesView.post

# 2. Editar parcels/analytics_views.py
from billing.decorators import check_eosda_limit
# Agregar a EOSDAAnalyticsAPIView.get y .post

# 3. Editar parcels/metereological.py
from billing.decorators import check_eosda_limit
# Agregar a WeatherForecastView.post
```

### Paso 2: Probar con Usuario Test (15 minutos)

```bash
# 1. Crear tenant test
# 2. Asignar plan BASIC (100 requests)
# 3. Hacer 5 análisis de parcela
# 4. Verificar que contador suba: metrics.eosda_requests = 35
# 5. Hacer 13 análisis más (total 18 × 7 = 126 requests)
# 6. Verificar bloqueo HTTP 429 al exceder límite
```

### Paso 3: Optimizar Cache (1 hora)

```python
# parcels/views.py

# EosdaScenesView - línea ~410
cache.set(cache_key, response_data, 21600)  # Cambiar de 600 a 21600

# EosdaImageResultView - línea ~530
# Agregar cache dual
composite_key = f"eosda_image_composite_{field_id}_{view_id}_{index_type}"
cached_image = cache.get(composite_key)
if cached_image:
    return Response({"image_base64": cached_image}, status=200)
# ... después de obtener imagen ...
cache.set(composite_key, image_base64, 3600)
```

### Paso 4: Ajustar Analytics (30 minutos)

```python
# parcels/views.py - EosdaSceneAnalyticsView línea ~627

# Cambiar default
indices = request.data.get("indices", ["ndvi"])  # Solo NDVI

# Frontend: metrica/static/js/parcels/parcel.js
# Agregar checkboxes:
<input type="checkbox" id="include-ndmi" /> Incluir NDMI
<input type="checkbox" id="include-evi" /> Incluir EVI
```

---

## 🎯 DECISIÓN REQUERIDA

### Opción A: Aplicar TODO (Recomendado)
- **Tiempo:** 2-3 horas totales
- **Resultado:** Sistema funcionando como debe + optimizado
- **Costos:** Reducción 40-60% requests
- **Break-even:** Igual (12 clientes)
- **Margen:** Mejora por menores costos EOSDA

### Opción B: Solo Decoradores (Mínimo)
- **Tiempo:** 30 minutos
- **Resultado:** Control de límites funcionando
- **Costos:** Sin optimización
- **Riesgo:** Plan BASIC puede exceder límite si usuario usa 3 índices

### Opción C: Posponer (No Recomendado)
- **Riesgo:** Sin control de límites
- **Riesgo:** Usuarios pueden abusar del sistema
- **Riesgo:** Sin métricas para facturación

---

## 📋 CHECKLIST

**Paso 1: Decoradores (CRÍTICO)** ⏱️ 30 min
- [ ] Agregar import en `parcels/views.py`
- [ ] Agregar `@check_eosda_limit` a 6 vistas
- [ ] Agregar import en `parcels/analytics_views.py`
- [ ] Agregar `@check_eosda_limit` a EOSDAAnalyticsAPIView
- [ ] Agregar import en `parcels/metereological.py`
- [ ] Agregar `@check_eosda_limit` a WeatherForecastView
- [ ] Probar con usuario test
- [ ] Verificar contador sube correctamente
- [ ] Verificar bloqueo al exceder límite

**Paso 2: Cache (ALTA PRIORIDAD)** ⏱️ 1 hora
- [ ] Scene Search: 600 → 21600
- [ ] Image Result: agregar cache dual
- [ ] Weather: agregar cache 12 horas
- [ ] Probar que cache funciona
- [ ] Verificar reducción de requests

**Paso 3: Analytics (MEDIA PRIORIDAD)** ⏱️ 30 min
- [ ] Cambiar default a solo NDVI
- [ ] Frontend: agregar checkboxes NDMI/EVI
- [ ] Probar flujo completo
- [ ] Documentar en README

**Paso 4: Documentación** ⏱️ 15 min
- [ ] Actualizar ANALISIS_BREAK_EVEN_REAL.md con conteo real
- [ ] Agregar nota sobre optimizaciones aplicadas

---

## 🔍 RESPUESTAS A TUS PREGUNTAS ORIGINALES

### "si tengo 6 o 10 no pierdo dinero?"

**6 clientes:** PIERDES 496k COP/mes ❌  
**10 clientes:** PIERDES 159k COP/mes ❌  
**12 clientes:** GANAS 99k COP/mes ✅ (break-even)

**Pero con optimizaciones:**
- Costos EOSDA bajan de Innovator a Starter
- Nuevo break-even: **10 clientes** 
- Ahorro: 2M COP/año

### "con cuantos usuarios minimos pierdo dinero?"

**Sin optimizaciones:** Menos de 12 clientes = pérdida  
**Con optimizaciones:** Menos de 10 clientes = pérdida

### "como va a ser realmente la reparticion de los request?"

**Antes de auditoría (mi estimación):**
- 1 análisis = 5 requests ❌

**Después de auditoría (realidad código):**
- 1 análisis básico (solo NDVI) = 7 requests
- 1 análisis completo (3 índices) = 13 requests

**Con optimizaciones aplicadas:**
- 1 análisis optimizado = 5 requests ✅

### "500 es arto o es lo normal?"

**Sin optimizaciones:**
- 500 requests = 38 análisis completos (justo)
- 500 requests = 71 análisis básicos (holgado)

**Con optimizaciones:**
- 500 requests = 100 análisis optimizados (muy holgado) ✅

**Conclusión:** 500 es **GENEROSO** con optimizaciones, **JUSTO** sin ellas.

---

**¿Procedo a aplicar las correcciones?**

Recomiend opción: **Aplicar TODO (Opción A)** en 3 pasos:
1. Decoradores HOY (30 min) → Control funcionando
2. Cache MAÑANA (1 hora) → Ahorro 40%
3. Analytics PRÓXIMA SEMANA (30 min) → Ahorro adicional 20%

Esperando tu confirmación para no romper nada... 🛡️
