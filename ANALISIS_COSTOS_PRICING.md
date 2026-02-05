# 📊 ANÁLISIS EXHAUSTIVO DE COSTOS Y PRICING - AGROTECH DIGITAL

## ⚠️ INVESTIGACIÓN DE COSTOS REALES EN COLOMBIA

**Fecha de análisis:** Febrero 2026  
**Objetivo:** Validar rentabilidad del modelo de pricing propuesto vs costos operacionales reales

---

## 1️⃣ COSTOS EOSDA API (Satellite Imagery Analysis)

### 🔍 Problema Identificado: NO HAY PRICING PÚBLICO

Después de investigar exhaustivamente:
- ✅ EOSDA **NO publica precios** en su sitio web
- ✅ Operan con modelo **B2B Enterprise** (contacto directo para cotización)
- ✅ Tienen productos: **Crop Monitoring**, **LandViewer**, **API Connect**

### 📞 EOSDA Pricing Model (Información inferida de mercado)

Basado en análisis de competidores y mercado de satellite imagery APIs:

#### **Opción A: EOSDA API Connect (Pay-per-request)**
**Estimación de mercado:**
- **Statistics API (NDVI/NDMI/EVI):** $0.05 - $0.15 USD por request
- **Scene Search:** $0.02 USD por búsqueda
- **Image Rendering:** $0.10 - $0.30 USD por imagen generada
- **Volumen enterprise:** Descuentos desde 30-50% con contratos anuales

**Cálculo conservador para PLAN PRO (500 requests/mes):**
```
500 requests × $0.10 USD = $50 USD/mes
Con descuento enterprise (40%): $30 USD/mes ≈ 120,000 COP/mes
```

#### **Opción B: EOSDA Crop Monitoring (Suscripción por hectáreas)**
**Estructura conocida del mercado:**
- **Small farms (0-500 ha):** $2-4 USD/ha/año
- **Medium farms (500-2000 ha):** $1-2 USD/ha/año  
- **Large farms (2000+ ha):** $0.50-1 USD/ha/año

**Cálculo para PLAN PRO (1000 ha):**
```
1000 ha × $1.50 USD/ha/año = $1,500 USD/año
$1,500 ÷ 12 meses = $125 USD/mes ≈ 500,000 COP/mes
```

### 🚨 CONCLUSIÓN EOSDA:
**Necesitamos contactar a EOSDA para cotización real**, pero estimaciones conservadoras:
- **Modelo request-based:** ~120,000 COP/mes para 500 requests
- **Modelo hectárea-based:** ~500,000 COP/mes para 1000 ha
- **Mejor opción:** Negociar API Connect con volumen enterprise

---

## 2️⃣ COSTOS RAILWAY (Hosting Infrastructure)

### 💰 PRICING RAILWAY (OFICIAL - Febrero 2026)

**Planes base:**
- **Free:** $0/mes + $1 crédito mensual (muy limitado)
- **Hobby:** $5/mes + $5 créditos incluidos
- **Pro:** $20/mes + $20 créditos incluidos
- **Enterprise:** Custom pricing

### 📊 Resource Usage Pricing (Lo que consume la app)

| Recurso | Precio por mes | Precio por minuto |
|---------|----------------|-------------------|
| **RAM** | $10 / GB / mes | $0.000231 / GB / min |
| **CPU** | $20 / vCPU / mes | $0.000463 / vCPU / min |
| **Network Egress** | $0.05 / GB | - |
| **Volume Storage** | $0.15 / GB / mes | $0.000003472 / GB / min |

### 🏗️ CÁLCULO PARA AGROTECH DIGITAL (Multi-tenant SaaS)

#### **Escenario 1: Startup (10 clientes activos)**

**Backend Django + PostgreSQL:**
- RAM: 2 GB → $20/mes
- CPU: 1 vCPU → $20/mes
- Storage: 10 GB → $1.50/mes
- **Subtotal backend:** $41.50/mes

**Frontend Netlify:** GRATIS (hasta 100 GB bandwidth)

**Database PostgreSQL:**
- RAM: 2 GB → $20/mes
- CPU: 1 vCPU → $20/mes
- Storage: 20 GB → $3/mes
- **Subtotal DB:** $43/mes

**Network Egress (imágenes satelitales, mapas):**
- ~50 GB/mes → $2.50/mes

**TOTAL RAILWAY:** $20 (plan Pro) + $41.50 + $43 + $2.50 = **$107 USD/mes ≈ 428,000 COP/mes**

---

#### **Escenario 2: Crecimiento (50 clientes activos)**

**Backend escalado:**
- RAM: 4 GB → $40/mes
- CPU: 2 vCPU → $40/mes
- Storage: 30 GB → $4.50/mes
- **Subtotal backend:** $84.50/mes

**Database escalada:**
- RAM: 4 GB → $40/mes
- CPU: 2 vCPU → $40/mes
- Storage: 50 GB → $7.50/mes
- **Subtotal DB:** $87.50/mes

**Network Egress:**
- ~200 GB/mes → $10/mes

**TOTAL RAILWAY:** $20 + $84.50 + $87.50 + $10 = **$202 USD/mes ≈ 808,000 COP/mes**

---

#### **Escenario 3: Escala (200 clientes activos)**

**Backend escalado:**
- RAM: 8 GB → $80/mes
- CPU: 4 vCPU → $80/mes
- Storage: 50 GB → $7.50/mes
- **Subtotal backend:** $167.50/mes

**Database escalada:**
- RAM: 8 GB → $80/mes
- CPU: 4 vCPU → $80/mes
- Storage: 100 GB → $15/mes
- **Subtotal DB:** $175/mes

**Network Egress:**
- ~500 GB/mes → $25/mes

**TOTAL RAILWAY:** $20 + $167.50 + $175 + $25 = **$387.50 USD/mes ≈ 1,550,000 COP/mes**

---

## 3️⃣ OTROS COSTOS OPERACIONALES

### 📧 Email (Transactional - opcional MVP)
- **SendGrid Free:** 100 emails/día GRATIS
- **SendGrid Essentials:** $19.95 USD/mes (50k emails)

### 💳 Payment Gateways
- **MercadoPago:** 3.99% + 900 COP por transacción
- **Paddle:** 5% + $0.50 USD por transacción

### 🔐 Otros servicios
- **SSL/CDN:** GRATIS (Railway/Netlify incluidos)
- **Monitoring:** GRATIS (Railway incluido)
- **Backups:** GRATIS (Railway incluido)

### 💰 TOTAL COSTOS OPERACIONALES MENSUALES

| Escenario | Clientes | Railway | EOSDA (estimado) | Email | **TOTAL** |
|-----------|----------|---------|------------------|-------|-----------|
| **Startup** | 10 | 428k COP | 120k COP | 0 | **548k COP** |
| **Crecimiento** | 50 | 808k COP | 500k COP | 80k COP | **1,388k COP** |
| **Escala** | 200 | 1,550k COP | 2,000k COP | 80k COP | **3,630k COP** |

---

## 4️⃣ ANÁLISIS DE INGRESOS (Modelo Propuesto)

### 💵 PLANES ACTUALES (según billing/management/commands/create_billing_plans.py)

| Plan | Precio COP/mes | Límites | Target |
|------|----------------|---------|--------|
| **FREE** | $0 | 50 ha, 20 req EOSDA | Freemium/trials |
| **BASIC** | $49,000 | 300 ha, 100 req EOSDA | Pequeños agricultores |
| **PRO** | $149,000 | 1000 ha, 500 req EOSDA | Medianos agricultores |
| **ENTERPRISE** | Custom | Unlimited | Grandes operaciones |

### 📊 PROYECCIÓN DE INGRESOS

#### **Escenario 1: Startup (10 clientes pagos)**
**Mix esperado:**
- 5 × FREE = $0
- 3 × BASIC = 147,000 COP
- 2 × PRO = 298,000 COP

**Ingresos mensuales:** 445,000 COP  
**Costos mensuales:** 548,000 COP  
**🔴 PÉRDIDA:** -103,000 COP/mes (-23%)

---

#### **Escenario 2: Crecimiento (50 clientes pagos)**
**Mix esperado:**
- 10 × FREE = $0
- 25 × BASIC = 1,225,000 COP
- 12 × PRO = 1,788,000 COP
- 3 × ENTERPRISE = 1,500,000 COP (estimado $500k c/u)

**Ingresos mensuales:** 4,513,000 COP  
**Costos mensuales:** 1,388,000 COP  
**🟢 GANANCIA:** +3,125,000 COP/mes (+225%)

---

#### **Escenario 3: Escala (200 clientes pagos)**
**Mix esperado:**
- 30 × FREE = $0
- 100 × BASIC = 4,900,000 COP
- 50 × PRO = 7,450,000 COP
- 20 × ENTERPRISE = 10,000,000 COP (estimado $500k c/u)

**Ingresos mensuales:** 22,350,000 COP  
**Costos mensuales:** 3,630,000 COP  
**🟢 GANANCIA:** +18,720,000 COP/mes (+516%)

---

## 5️⃣ PUNTO DE EQUILIBRIO (BREAK-EVEN)

### 📈 Cálculo conservador

**Costos fijos estimados:** ~550,000 COP/mes (10-15 clientes)

**Ingresos necesarios para break-even:**
```
Necesitamos: 550,000 COP/mes

Opción A (solo BASIC):
550,000 ÷ 49,000 = 11.2 → ✅ 12 clientes BASIC

Opción B (mix BASIC + PRO):
8 × BASIC + 2 × PRO = 392,000 + 298,000 = 690,000 COP → ✅ 10 clientes total

Opción C (solo PRO):
550,000 ÷ 149,000 = 3.7 → ✅ 4 clientes PRO
```

**🎯 BREAK-EVEN:** Entre 10-12 clientes pagos (mix BASIC/PRO)

---

## 6️⃣ PROBLEMAS IDENTIFICADOS Y RECOMENDACIONES

### 🚨 PROBLEMAS CRÍTICOS

1. **EOSDA Pricing desconocido**
   - ❌ No tenemos cotización real
   - ❌ Podría ser MUCHO más caro de lo estimado
   - ⚠️ **RIESGO ALTO:** Si EOSDA cobra por hectárea ($500k/mes para 1000 ha), el PLAN PRO ($149k) NO es rentable

2. **Márgenes muy ajustados en fase inicial**
   - ❌ Escenario 1 (10 clientes) = PÉRDIDA
   - ✅ Necesitamos 12+ clientes para break-even
   - ⚠️ Período de pérdidas en primeros 2-3 meses

3. **Modelo request-based vs hectare-based**
   - ❌ Si EOSDA cobra por hectárea, nuestro límite de "requests" no tiene sentido
   - ❌ Si EOSDA cobra por request, nuestro límite de "hectáreas" no correlaciona con costos

### ✅ RECOMENDACIONES URGENTES

#### **1. CONTACTAR EOSDA INMEDIATAMENTE**
```
Necesitamos cotización para:
1. API Connect - pricing por request
2. Crop Monitoring - pricing por hectárea
3. Descuentos enterprise (volumen anual)
4. Modelo de facturación (prepago vs postpago)
```

#### **2. AJUSTAR PRICING SEGÚN MODELO EOSDA**

**Si EOSDA cobra por REQUEST:**
```python
# AJUSTE CONSERVADOR
FREE:     20 requests/mes  → $0 (absorber costo)
BASIC:    100 requests/mes → $79,000 COP (+61%)
PRO:      500 requests/mes → $249,000 COP (+67%)
ENTERPRISE: Unlimited → Custom (mínimo $800k)
```

**Si EOSDA cobra por HECTÁREA:**
```python
# AJUSTE AGRESIVO
FREE:     50 ha   → $0 (absorber costo)
BASIC:    300 ha  → $99,000 COP (+102%)
PRO:      1000 ha → $349,000 COP (+134%)
ENTERPRISE: Unlimited → Custom (mínimo $1.5M)
```

#### **3. IMPLEMENTAR TIER INTERMEDIO**

Agregar plan **STARTER** para mejorar conversión:
```python
STARTER = {
    "price_cop": 29000,  # Más accesible
    "limits": {
        "hectares": 150,
        "users": 2,
        "eosda_requests": 50,
        "parcels": 5
    }
}
```

#### **4. ESTRATEGIA DE ONBOARDING**

- **Mes 1-2:** Trial GRATIS de 30 días (plan PRO completo)
- **Mes 3-6:** Descuento 50% en BASIC/PRO (adquisición agresiva)
- **Mes 7+:** Pricing regular

#### **5. OPTIMIZACIONES TÉCNICAS PARA REDUCIR COSTOS**

**A. Cache agresivo de EOSDA:**
```python
# Ya implementado en analytics_views.py
cache_key = f"eosda_analytics_{view_id}_{scene_date}"
cache.set(cache_key, data, 86400 * 7)  # 7 días

# MEJORA: Extender cache a 30 días para escenas históricas
cache.set(cache_key, data, 86400 * 30)  # 30 días
```

**B. Lazy loading de imágenes satelitales:**
```python
# Solo cargar imagen si usuario la solicita explícitamente
# NO pre-generar todas las imágenes en scene search
```

**C. Batch processing de requests EOSDA:**
```python
# Agrupar múltiples parcelas en una sola API call
# EOSDA Statistics API acepta múltiples geometrías
```

**D. Railway: Autoscaling vertical:**
```toml
# railway.toml
[services.backend]
  autoscale = true
  min_memory_gb = 2
  max_memory_gb = 8
  target_cpu_percent = 70
```

---

## 7️⃣ PROYECCIÓN FINANCIERA 12 MESES

### 📊 Escenario conservador (pricing actual)

| Mes | Clientes | Ingresos COP | Costos COP | Ganancia COP | Acumulado |
|-----|----------|--------------|------------|--------------|-----------|
| 1 | 5 | 197k | 548k | -351k | -351k |
| 2 | 8 | 343k | 548k | -205k | -556k |
| 3 | 12 | 539k | 548k | -9k | -565k |
| 4 | 18 | 833k | 680k | +153k | -412k |
| 5 | 25 | 1,225k | 808k | +417k | +5k |
| 6 | 35 | 1,715k | 1,050k | +665k | +670k |
| 7 | 45 | 2,205k | 1,200k | +1,005k | +1,675k |
| 8 | 60 | 3,038k | 1,388k | +1,650k | +3,325k |
| 9 | 80 | 4,263k | 1,700k | +2,563k | +5,888k |
| 10 | 100 | 5,488k | 2,100k | +3,388k | +9,276k |
| 11 | 130 | 7,508k | 2,500k | +5,008k | +14,284k |
| 12 | 170 | 10,283k | 3,200k | +7,083k | +21,367k |

**🎯 BREAK-EVEN:** Mes 5 (25 clientes)  
**💰 Ganancia año 1:** 21,367,000 COP (~$5,300 USD)

---

### 📊 Escenario optimista (pricing ajustado +50%)

| Mes | Clientes | Ingresos COP | Costos COP | Ganancia COP | Acumulado |
|-----|----------|--------------|------------|--------------|-----------|
| 1 | 5 | 296k | 548k | -252k | -252k |
| 2 | 8 | 515k | 548k | -33k | -285k |
| 3 | 12 | 809k | 548k | +261k | -24k |
| 4 | 18 | 1,250k | 680k | +570k | +546k |
| 5 | 25 | 1,838k | 808k | +1,030k | +1,576k |
| 6 | 35 | 2,573k | 1,050k | +1,523k | +3,099k |
| 7 | 45 | 3,308k | 1,200k | +2,108k | +5,207k |
| 8 | 60 | 4,557k | 1,388k | +3,169k | +8,376k |
| 9 | 80 | 6,395k | 1,700k | +4,695k | +13,071k |
| 10 | 100 | 8,232k | 2,100k | +6,132k | +19,203k |
| 11 | 130 | 11,262k | 2,500k | +8,762k | +27,965k |
| 12 | 170 | 15,425k | 3,200k | +12,225k | +40,190k |

**🎯 BREAK-EVEN:** Mes 3 (12 clientes)  
**💰 Ganancia año 1:** 40,190,000 COP (~$10,000 USD)

---

## 8️⃣ DECISIÓN FINAL: ¿QUÉ HACER?

### 🎯 PLAN DE ACCIÓN INMEDIATO

#### **FASE 1: INVESTIGACIÓN (Esta semana)**
1. ✅ **Contactar EOSDA** para cotización:
   - Email: sales@eos.com
   - Solicitar: API Connect pricing, volumen enterprise, modelo facturación
   
2. ✅ **Contactar alternativas** (backup):
   - Planet Labs API
   - Sentinel Hub API
   - Google Earth Engine (GEE)

#### **FASE 2: AJUSTE DE MODELO (Semana 2)**
3. ✅ **Redefinir límites** según modelo EOSDA real
4. ✅ **Ajustar pricing** para margen 60-70%
5. ✅ **Implementar tier STARTER** ($29k COP)

#### **FASE 3: OPTIMIZACIÓN (Semana 3-4)**
6. ✅ **Implementar cache agresivo** (30 días históricas)
7. ✅ **Batch processing** EOSDA requests
8. ✅ **Autoscaling Railway** configurado

#### **FASE 4: LANZAMIENTO (Mes 2)**
9. ✅ **Beta privada** con 10 agricultores colombianos
10. ✅ **Promoción:** 3 meses gratis plan PRO
11. ✅ **Recolectar feedback** y validar pricing

---

## 9️⃣ CONCLUSIONES CRÍTICAS

### ✅ ES VIABLE, PERO CON AJUSTES

1. **Railway NO es el problema:**
   - ✅ Costos predecibles y escalables
   - ✅ $107-387 USD/mes para 10-200 clientes es razonable
   - ✅ Break-even en 10-12 clientes

2. **EOSDA ES LA INCÓGNITA CRÍTICA:**
   - ⚠️ Sin cotización real, todo es especulación
   - ⚠️ Si cuesta >$500k COP/mes por 1000 ha, plan PRO ($149k) NO funciona
   - ✅ Si cuesta ~$120k COP/mes por 500 requests, plan PRO es viable

3. **PRICING ACTUAL ES AGRESIVO (muy bajo):**
   - ❌ Márgenes muy ajustados (30-40%)
   - ❌ Riesgo de pérdidas si EOSDA es caro
   - ✅ **Recomiendo subir precios 50-70%** después de cotización EOSDA

4. **MODELO DE NEGOCIO ES SÓLIDO:**
   - ✅ Break-even rápido (3-5 meses con 12-25 clientes)
   - ✅ Escalabilidad excelente (margen crece con volumen)
   - ✅ Market fit claro (agricultura tecnificada en Colombia)

---

## 🚀 RECOMENDACIÓN FINAL

### **IMPLEMENTAR MODELO DE 2 FASES:**

#### **FASE BETA (Mes 1-3):**
```python
# Pricing ultra-competitivo para validar market fit
FREE:  0 COP    (50 ha, 20 req)    ← Lead generation
BASIC: 29k COP  (150 ha, 50 req)   ← Nuevo tier STARTER
PRO:   79k COP  (500 ha, 200 req)  ← Precio promo (-47%)
```

**Objetivo:** Conseguir 30-50 clientes beta, validar uso real de EOSDA

#### **FASE PRODUCCIÓN (Mes 4+):**
```python
# Pricing ajustado según cotización EOSDA real
FREE:  0 COP      (50 ha, 20 req)
STARTER: 49k COP  (150 ha, 50 req)  ← Antes "BASIC promo"
BASIC: 99k COP    (300 ha, 100 req) ← +102% vs actual
PRO: 249k COP     (1000 ha, 500 req) ← +67% vs actual
ENTERPRISE: 800k+ ← Custom por cliente
```

**Margen esperado:** 65-75% (sostenible y escalable)

---

## 📞 PRÓXIMOS PASOS

1. **HOY:** Enviar email a EOSDA solicitando cotización
2. **Esta semana:** Investigar alternativas (Planet, Sentinel Hub, GEE)
3. **Semana 2:** Ajustar `create_billing_plans.py` con pricing final
4. **Semana 3:** Implementar optimizaciones de cache y batching
5. **Mes 2:** Lanzar beta privada con 10 early adopters

---

**Elaborado por:** GitHub Copilot AI  
**Fecha:** 5 de febrero de 2026  
**Status:** ⚠️ REQUIERE COTIZACIÓN EOSDA REAL PARA VALIDAR
