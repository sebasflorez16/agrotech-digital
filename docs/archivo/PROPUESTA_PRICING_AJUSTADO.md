# 🎯 PROPUESTA DE PRICING AJUSTADO - AGROTECH DIGITAL

## 📋 RESUMEN EJECUTIVO

Después del análisis exhaustivo de costos, **el pricing actual está 50-70% por debajo del punto óptimo**. Esta propuesta define:

1. ✅ Pricing ajustado para rentabilidad sostenible
2. ✅ Estrategia de lanzamiento en 2 fases (Beta → Producción)
3. ✅ Optimizaciones técnicas para reducir costos
4. ✅ Plan de implementación paso a paso

---

## 1️⃣ COMPARACIÓN: PRICING ACTUAL VS PROPUESTO

### 📊 TABLA COMPARATIVA

| Plan | Actual COP | Propuesto COP | Cambio % | Actual USD | Propuesto USD |
|------|------------|---------------|----------|------------|---------------|
| **FREE** | 0 | 0 | - | 0 | 0 |
| **STARTER** | ❌ No existe | ✅ 49,000 | NEW | - | $12 |
| **BASIC** | 49,000 | 99,000 | +102% | $12 | $25 |
| **PRO** | 149,000 | 249,000 | +67% | $37 | $62 |
| **ENTERPRISE** | Custom | 800,000+ | - | Custom | $200+ |

### 🎯 JUSTIFICACIÓN DE AJUSTES

**STARTER (NUEVO):**
- ✅ Punto de entrada accesible para pequeños agricultores
- ✅ Mejora conversión de FREE → Pagos (barrera más baja)
- ✅ Cubre costos básicos de EOSDA (~20k COP) + Railway (~15k COP) + margen 30%

**BASIC (+102%):**
- ✅ Precio anterior demasiado bajo vs costos EOSDA estimados
- ✅ Nuevo precio competitivo vs mercado ($25 USD/mes es estándar en SaaS agro)
- ✅ Margen saludable 60-70% para reinversión

**PRO (+67%):**
- ✅ Mayor valor percibido (1000 ha, 500 requests = uso intensivo)
- ✅ Cubre costos EOSDA estimados (~120k COP) + Railway (~50k COP) + margen 70%
- ✅ Precio competitivo vs EOSDA Crop Monitoring directo ($125 USD/mes)

**ENTERPRISE (NUEVO MÍNIMO):**
- ✅ Contratos personalizados con mínimo $200 USD/mes
- ✅ Descuentos por volumen (10-30% según hectáreas/requests)
- ✅ Soporte prioritario, SLA garantizado

---

## 2️⃣ NUEVOS LÍMITES Y FEATURES

### 📋 TABLA COMPLETA DE PLANES

| Feature | FREE | STARTER | BASIC | PRO | ENTERPRISE |
|---------|------|---------|-------|-----|------------|
| **Precio COP/mes** | 0 | 49,000 | 99,000 | 249,000 | Custom 800k+ |
| **Precio USD/mes** | 0 | $12 | $25 | $62 | Custom $200+ |
| **Hectáreas** | 50 | 150 | 300 | 1,000 | Unlimited |
| **EOSDA Requests** | 20 | 50 | 100 | 500 | Unlimited |
| **Usuarios** | 1 | 2 | 3 | 10 | Unlimited |
| **Parcelas** | 3 | 5 | 10 | 50 | Unlimited |
| **Storage** | 100 MB | 250 MB | 500 MB | 2 GB | Unlimited |
| **Histórico** | 3 meses | 6 meses | 12 meses | 36 meses | Unlimited |
| **Análisis NDVI** | ✅ Básico | ✅ Completo | ✅ Completo | ✅ Avanzado | ✅ Premium |
| **Clima actual** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Pronóstico 7 días** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Pronóstico 14 días** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Alertas clima** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Comparación parcelas** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Exportar reportes** | ❌ | ❌ | ✅ PDF | ✅ PDF/Excel | ✅ PDF/Excel/API |
| **API access** | ❌ | ❌ | ❌ | ✅ Limitado | ✅ Full |
| **Soporte** | Email | Email | Email + Chat | Priority | Dedicado + SLA |
| **Trial** | - | 14 días | 14 días | 14 días | 30 días |

---

## 3️⃣ ESTRATEGIA DE LANZAMIENTO EN 2 FASES

### 🚀 FASE 1: BETA PRIVADA (Mes 1-3)

**Objetivo:** Validar product-market fit con pricing agresivo

#### **Pricing BETA (50% descuento):**

```python
# billing/management/commands/create_billing_plans_beta.py

BETA_PLANS = [
    {
        "tier": "free",
        "name": "Plan Gratuito",
        "price_cop": 0,
        "price_usd": 0,
        "limits": {
            "hectares": 50,
            "users": 1,
            "eosda_requests": 20,
            "parcels": 3,
            "storage_mb": 100,
            "historical_months": 3
        },
        "features_included": [
            "Análisis NDVI básico",
            "Clima actual",
            "Mapa base satelital"
        ]
    },
    {
        "tier": "starter",
        "name": "Plan Starter BETA",
        "description": "Ideal para pequeños agricultores",
        "price_cop": 29000,  # 50% off (normal: 49k)
        "price_usd": 7,
        "billing_cycle": "monthly",
        "trial_days": 14,
        "limits": {
            "hectares": 150,
            "users": 2,
            "eosda_requests": 50,
            "parcels": 5,
            "storage_mb": 250,
            "historical_months": 6
        },
        "features_included": [
            "Todo de FREE +",
            "Análisis NDVI/NDMI/EVI completo",
            "Pronóstico 7 días",
            "Comparación básica parcelas",
            "Exportar PDF"
        ]
    },
    {
        "tier": "basic",
        "name": "Plan Básico BETA",
        "description": "Para agricultores medianos",
        "price_cop": 59000,  # 50% off (normal: 99k)
        "price_usd": 15,
        "billing_cycle": "monthly",
        "trial_days": 14,
        "limits": {
            "hectares": 300,
            "users": 3,
            "eosda_requests": 100,
            "parcels": 10,
            "storage_mb": 500,
            "historical_months": 12
        },
        "features_included": [
            "Todo de STARTER +",
            "Pronóstico 14 días",
            "Alertas clima personalizadas",
            "Análisis comparativo avanzado",
            "Exportar PDF/Excel",
            "Soporte prioritario email"
        ]
    },
    {
        "tier": "pro",
        "name": "Plan Profesional BETA",
        "description": "Para operaciones agrícolas grandes",
        "price_cop": 149000,  # 50% off (normal: 249k)
        "price_usd": 37,
        "billing_cycle": "monthly",
        "trial_days": 14,
        "limits": {
            "hectares": 1000,
            "users": 10,
            "eosda_requests": 500,
            "parcels": 50,
            "storage_mb": 2000,
            "historical_months": 36
        },
        "features_included": [
            "Todo de BASIC +",
            "Análisis avanzado multi-parcela",
            "API access limitado",
            "Webhooks para alertas",
            "Histórico 3 años",
            "Soporte chat prioritario",
            "Reuniones mensuales de revisión"
        ]
    }
]
```

#### **Criterios de selección BETA:**
- ✅ Agricultores colombianos con 50+ hectáreas
- ✅ Cultivos: café, aguacate, cacao, flores, frutales
- ✅ Tecnología: uso de smartphone/tablet
- ✅ Compromiso: feedback semanal durante 3 meses

#### **Incentivos BETA:**
- 🎁 **3 meses GRATIS** en plan PRO BETA ($149k × 3 = $447k valor)
- 🎁 **50% descuento** por 6 meses adicionales después de beta
- 🎁 **Créditos EOSDA extra** (200 requests bonus)
- 🎁 **Acceso early access** a nuevas features

---

### 🏆 FASE 2: PRODUCCIÓN (Mes 4+)

**Objetivo:** Escalamiento sostenible con pricing definitivo

#### **Pricing PRODUCCIÓN (Definitivo):**

```python
# billing/management/commands/create_billing_plans_production.py

PRODUCTION_PLANS = [
    # FREE sin cambios
    {
        "tier": "free",
        # ... igual que beta
    },
    {
        "tier": "starter",
        "name": "Plan Starter",
        "price_cop": 49000,  # ← Precio real
        "price_usd": 12,
        # ... resto igual
    },
    {
        "tier": "basic",
        "name": "Plan Básico",
        "price_cop": 99000,  # ← Precio real
        "price_usd": 25,
        # ... resto igual
    },
    {
        "tier": "pro",
        "name": "Plan Profesional",
        "price_cop": 249000,  # ← Precio real
        "price_usd": 62,
        # ... resto igual
    },
    {
        "tier": "enterprise",
        "name": "Plan Empresarial",
        "description": "Soluciones personalizadas para grandes operaciones",
        "price_cop": 800000,  # Precio mínimo base
        "price_usd": 200,
        "is_custom": True,
        "billing_cycle": "monthly",
        "trial_days": 30,
        "limits": {
            "hectares": "unlimited",
            "users": "unlimited",
            "eosda_requests": "unlimited",
            "parcels": "unlimited",
            "storage_mb": "unlimited",
            "historical_months": "unlimited"
        },
        "features_included": [
            "Todo de PRO +",
            "API completo sin límites",
            "Integración con ERP/sistemas propios",
            "White-label opcional",
            "Soporte 24/7 con SLA",
            "Account manager dedicado",
            "Reuniones semanales de estrategia",
            "Capacitación equipo técnico",
            "Desarrollo features personalizadas"
        ]
    }
]
```

#### **Migración BETA → PRODUCCIÓN:**

```python
# billing/management/commands/migrate_beta_to_production.py

class Command(BaseCommand):
    """
    Migra clientes beta a pricing de producción con grace period.
    """
    
    def handle(self, *args, **options):
        beta_subscriptions = Subscription.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=90),  # Creadas en beta
            plan__tier__in=['starter', 'basic', 'pro']
        )
        
        for subscription in beta_subscriptions:
            # Mantener precio beta por 6 meses adicionales
            if subscription.created_at > timezone.now() - timedelta(days=180):
                self.stdout.write(f"✅ {subscription.tenant.name}: Mantiene precio BETA")
                # No hacer nada, mantener plan actual
            else:
                # Después de 6 meses, ofrecer upgrade gradual
                new_price = self._get_production_price(subscription.plan.tier)
                discount = 0.30  # 30% descuento por loyalty
                final_price = new_price * (1 - discount)
                
                self.stdout.write(
                    f"📧 {subscription.tenant.name}: "
                    f"Notificar upgrade de ${subscription.plan.price_cop} "
                    f"a ${final_price} (30% loyalty discount)"
                )
                
                # Enviar email con 30 días de anticipación
                self._send_upgrade_notification(subscription, final_price)
```

---

## 4️⃣ OPTIMIZACIONES TÉCNICAS PARA REDUCIR COSTOS

### 🔧 OPTIMIZACIÓN 1: Cache Agresivo de EOSDA

**Problema:** Cada request EOSDA cuesta ~$0.10 USD

**Solución:**

```python
# parcels/analytics_views.py

CACHE_DURATIONS = {
    'historical': 86400 * 30,  # 30 días (datos históricos no cambian)
    'recent': 86400 * 7,       # 7 días (datos recientes)
    'current': 3600,           # 1 hora (datos actuales)
}

def _get_real_eosda_statistics_with_data(self, field_id, geometry, start_date, end_date):
    # Determinar tipo de fecha
    days_old = (datetime.now().date() - datetime.fromisoformat(start_date).date()).days
    
    if days_old > 30:
        cache_duration = CACHE_DURATIONS['historical']
    elif days_old > 7:
        cache_duration = CACHE_DURATIONS['recent']
    else:
        cache_duration = CACHE_DURATIONS['current']
    
    cache_key = f"eosda_stats_{field_id}_{start_date}_{end_date}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.info(f"[CACHE HIT] Ahorro EOSDA request: ${0.10} USD")
        return cached_data
    
    # Llamar EOSDA solo si no está en cache
    result = self._call_eosda_api(...)
    cache.set(cache_key, result, cache_duration)
    
    return result
```

**Impacto esperado:**
- ✅ Reducción 60-80% de requests EOSDA
- ✅ Ahorro ~$30-50 USD/mes por cada 50 clientes activos

---

### 🔧 OPTIMIZACIÓN 2: Batch Processing de Requests

**Problema:** 1 parcela = 3 requests EOSDA (NDVI + NDMI + EVI)

**Solución:**

```python
# parcels/eosda_batch.py

class EOSDABatchProcessor:
    """
    Agrupa múltiples parcelas en una sola request EOSDA.
    """
    
    def batch_analytics_request(self, parcel_ids, scene_date):
        """
        Solicita analytics para múltiples parcelas en un solo API call.
        
        EOSDA Statistics API acepta array de geometrías:
        POST /api/gdw/statistic_api/v2
        {
            "scenes": [...],
            "geometry": [geom1, geom2, geom3],  ← Array de geometrías
            "indices": ["NDVI", "NDMI", "EVI"]
        }
        """
        parcels = Parcel.objects.filter(id__in=parcel_ids)
        geometries = [p.geom.geojson for p in parcels]
        
        # 1 request = Todas las parcelas
        result = self._call_eosda_batch(geometries, scene_date)
        
        # Distribuir resultados a cada parcela
        for i, parcel in enumerate(parcels):
            parcel_data = result[i]
            cache.set(f"analytics_{parcel.id}_{scene_date}", parcel_data, 86400*7)
        
        logger.info(
            f"[BATCH] {len(parcels)} parcelas procesadas en 1 request EOSDA. "
            f"Ahorro: {len(parcels)-1} requests × $0.10 = ${(len(parcels)-1)*0.10} USD"
        )
        
        return result
```

**Impacto esperado:**
- ✅ Reducción 70-90% de requests cuando usuario analiza múltiples parcelas
- ✅ Ahorro ~$40-60 USD/mes por cada 50 clientes activos

---

### 🔧 OPTIMIZACIÓN 3: Lazy Loading de Imágenes

**Problema:** Scene search carga todas las imágenes inmediatamente

**Solución:**

```python
# parcels/views.py - EosdaScenesView

class EosdaScenesView(APIView):
    def post(self, request):
        # ... existing code ...
        
        scenes = scenes_data.get('result', [])
        
        # NO generar request_id para imágenes inmediatamente
        # Solo retornar metadata de escenas
        return Response({
            'scenes': [{
                'view_id': scene['view_id'],
                'date': scene['date'],
                'cloud_cover': scene.get('cloud_cover', 0),
                # NO incluir request_id aquí
            } for scene in scenes]
        })

# Frontend solicita imagen solo cuando usuario hace click en escena específica
# POST /api/parcels/eosda-image/ con view_id
```

**Impacto esperado:**
- ✅ Reducción 90% de image requests innecesarios
- ✅ Ahorro ~$20-30 USD/mes por cada 50 clientes activos

---

### 🔧 OPTIMIZACIÓN 4: Railway Autoscaling

**Problema:** Railway cobra por RAM/CPU aunque no se use 100%

**Solución:**

```toml
# railway.toml

[build]
builder = "NIXPACKS"

[[services]]
name = "backend"

[services.autoscale]
enabled = true
min_instances = 1
max_instances = 5
target_cpu_percent = 70  # Scale up cuando CPU > 70%
target_memory_percent = 80  # Scale up cuando RAM > 80%

[services.resources]
# Recursos base mínimos (noche/madrugada)
min_memory_gb = 1
min_vcpu = 0.5

# Recursos máximos (horas pico)
max_memory_gb = 8
max_vcpu = 4

[[services]]
name = "database"

[services.autoscale]
enabled = true
min_instances = 1
max_instances = 3

[services.resources]
min_memory_gb = 2
min_vcpu = 1
max_memory_gb = 8
max_vcpu = 4
```

**Impacto esperado:**
- ✅ Reducción 30-40% costos Railway en horas de bajo tráfico
- ✅ Ahorro ~$30-50 USD/mes

---

### 📊 RESUMEN DE OPTIMIZACIONES

| Optimización | Ahorro mensual | Complejidad | Prioridad |
|--------------|----------------|-------------|-----------|
| **Cache agresivo** | $30-50 USD | Baja ⭐ | 🔥 Alta |
| **Batch processing** | $40-60 USD | Media ⭐⭐ | 🔥 Alta |
| **Lazy loading** | $20-30 USD | Baja ⭐ | 🔥 Alta |
| **Railway autoscaling** | $30-50 USD | Baja ⭐ | ⚡ Media |
| **TOTAL** | **$120-190 USD** | - | - |

**Con 50 clientes activos:**
- Costos sin optimización: ~$1,388k COP
- Costos con optimización: ~$900k COP
- **Ahorro:** 35% en costos operacionales

---

## 5️⃣ PLAN DE IMPLEMENTACIÓN (4 SEMANAS)

### 📅 SEMANA 1: Investigación y ajustes

**Lunes-Martes:**
- [ ] Contactar EOSDA para cotización real
- [ ] Contactar Planet Labs, Sentinel Hub, Google Earth Engine (alternativas)
- [ ] Calcular costos reales vs estimados

**Miércoles-Jueves:**
- [ ] Ajustar `create_billing_plans.py` con pricing definitivo
- [ ] Crear `create_billing_plans_beta.py` para fase 1
- [ ] Actualizar documentación BILLING_GUIDE.md

**Viernes:**
- [ ] Code review de cambios de pricing
- [ ] Testing manual de nuevo sistema de planes

---

### 📅 SEMANA 2: Optimizaciones técnicas

**Lunes-Martes:**
- [ ] Implementar cache agresivo en `analytics_views.py`
- [ ] Testing de cache hit rate (objetivo >70%)

**Miércoles-Jueves:**
- [ ] Implementar batch processing en `eosda_batch.py`
- [ ] Crear endpoint `/api/parcels/batch-analytics/`
- [ ] Testing de ahorro de requests

**Viernes:**
- [ ] Implementar lazy loading en EosdaScenesView
- [ ] Configurar Railway autoscaling (railway.toml)
- [ ] Deploy a staging para testing

---

### 📅 SEMANA 3: Beta privada

**Lunes:**
- [ ] Seleccionar 10 agricultores para beta
- [ ] Enviar invitaciones con código promocional
- [ ] Configurar tracking de métricas beta

**Martes-Miércoles:**
- [ ] Onboarding individual con cada agricultor
- [ ] Capacitación 1:1 (45 min por agricultor)
- [ ] Configurar sistema de feedback semanal

**Jueves-Viernes:**
- [ ] Monitoreo activo de uso
- [ ] Resolver issues/bugs reportados
- [ ] Primera reunión semanal con grupo beta

---

### 📅 SEMANA 4: Análisis y ajustes

**Lunes-Martes:**
- [ ] Analizar métricas de beta (uso EOSDA, features más usadas)
- [ ] Revisar feedback de agricultores
- [ ] Calcular costos reales vs proyectados

**Miércoles:**
- [ ] Ajustar límites/pricing según datos reales
- [ ] Decidir si mantener o modificar planes

**Jueves-Viernes:**
- [ ] Preparar lanzamiento público (mes 2)
- [ ] Crear materiales de marketing
- [ ] Definir estrategia de adquisición

---

## 6️⃣ MÉTRICAS CLAVE A MONITOREAR

### 📊 KPIs Financieros

```python
# billing/analytics/financial_kpis.py

class BillingKPIs:
    """
    Métricas financieras clave del sistema de billing.
    """
    
    def calculate_mrr(self):
        """Monthly Recurring Revenue"""
        active_subs = Subscription.objects.filter(
            status__in=['active', 'trialing']
        )
        return sum(sub.plan.price_cop for sub in active_subs)
    
    def calculate_arr(self):
        """Annual Recurring Revenue"""
        return self.calculate_mrr() * 12
    
    def calculate_ltv(self):
        """Customer Lifetime Value"""
        # Promedio de meses activos × precio mensual
        avg_months = self._calculate_avg_subscription_months()
        avg_price = self._calculate_avg_price()
        return avg_months * avg_price
    
    def calculate_cac(self):
        """Customer Acquisition Cost"""
        # Marketing spend / Nuevos clientes
        return self._get_marketing_spend() / self._get_new_customers()
    
    def calculate_gross_margin(self):
        """Margen bruto %"""
        revenue = self.calculate_mrr()
        costs = self._calculate_operational_costs()  # Railway + EOSDA
        return ((revenue - costs) / revenue) * 100
    
    def calculate_eosda_cost_per_client(self):
        """Costo EOSDA promedio por cliente"""
        total_eosda_cost = self._get_eosda_monthly_cost()
        active_clients = Subscription.objects.filter(status='active').count()
        return total_eosda_cost / active_clients if active_clients > 0 else 0
```

### 🎯 Objetivos Mes 1-3 (Beta)

| Métrica | Objetivo | Crítico |
|---------|----------|---------|
| **MRR** | 1,500k COP | > 1,000k |
| **Clientes activos** | 20 | > 15 |
| **Gross margin** | 40% | > 30% |
| **EOSDA cost/client** | < 25k COP | < 35k COP |
| **Churn rate** | < 10% | < 15% |
| **NPS** | > 50 | > 40 |

### 🎯 Objetivos Mes 4-6 (Producción)

| Métrica | Objetivo | Crítico |
|---------|----------|---------|
| **MRR** | 5,000k COP | > 3,500k |
| **Clientes activos** | 60 | > 40 |
| **Gross margin** | 65% | > 55% |
| **EOSDA cost/client** | < 20k COP | < 25k COP |
| **Churn rate** | < 5% | < 8% |
| **LTV/CAC ratio** | > 3 | > 2 |

---

## 7️⃣ CONTINGENCIAS Y RIESGOS

### ⚠️ RIESGO 1: EOSDA más caro de lo estimado

**Si EOSDA cotiza >$200 USD/mes para 1000 ha:**

**Opción A - Subir precios aún más:**
```python
PRO: 349,000 COP (+134% vs actual)
ENTERPRISE: 1,200,000 COP mínimo
```

**Opción B - Reducir límites:**
```python
PRO: 249,000 COP pero solo 500 ha y 250 requests
```

**Opción C - Cambiar a competidor:**
```python
Migrar a Sentinel Hub API (más barato):
- NDVI/NDMI: $0.02-0.05 per request
- Sin límite de hectáreas
```

---

### ⚠️ RIESGO 2: Railway costos mayores a proyectados

**Si Railway >$500 USD/mes con 50 clientes:**

**Opción A - Migrar a AWS/GCP:**
```bash
# Pros: Costos 30-40% menores en scale
# Contras: Complejidad DevOps, tiempo setup 2-4 semanas
```

**Opción B - Optimizar agresivamente:**
```python
# Reducir recursos por servicio
# Implementar caching Redis
# CDN para imágenes satelitales
```

---

### ⚠️ RIESGO 3: Conversión FREE → PAID baja

**Si conversión < 10%:**

**Táctica 1 - Limitar FREE agresivamente:**
```python
FREE: Solo 30 ha, 10 requests, 1 mes histórico
```

**Táctica 2 - Trial extendido STARTER:**
```python
STARTER: 30 días trial gratis (vs 14 actual)
```

**Táctica 3 - Feature gating fuerte:**
```python
FREE: Solo NDVI (sin NDMI, EVI, clima, comparaciones)
```

---

## 8️⃣ RESUMEN Y PRÓXIMOS PASOS

### ✅ RECOMENDACIÓN FINAL

**IMPLEMENTAR MODELO DE 2 FASES:**

1. **FASE BETA (Mes 1-3):**
   - Pricing agresivo 50% off
   - 10-20 early adopters
   - Validar costos reales EOSDA
   - Optimizar técnicamente

2. **FASE PRODUCCIÓN (Mes 4+):**
   - Pricing definitivo ajustado
   - Escalar a 50-100 clientes
   - Margen 65-75%
   - Break-even mes 5

### 📞 ACCIÓN INMEDIATA (ESTA SEMANA)

**Prioridad 1 (Crítico):**
- [ ] ✅ Contactar EOSDA para cotización real
- [ ] ✅ Implementar cache agresivo (2 horas dev)
- [ ] ✅ Crear `create_billing_plans_beta.py`

**Prioridad 2 (Alta):**
- [ ] ⚡ Investigar alternativas EOSDA (Planet, Sentinel Hub)
- [ ] ⚡ Configurar Railway autoscaling
- [ ] ⚡ Implementar batch processing

**Prioridad 3 (Media):**
- [ ] 📊 Configurar dashboard de KPIs financieros
- [ ] 📧 Preparar email templates para beta
- [ ] 🎨 Actualizar landing page con nuevo pricing

---

**¿Estás listo para implementar?** 🚀

Confirma si quieres que proceda con:
1. Crear `create_billing_plans_beta.py` con pricing ajustado
2. Implementar optimizaciones de cache
3. Configurar Railway autoscaling

O prefieres esperar cotización EOSDA antes de hacer cambios en el código.
