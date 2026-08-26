# Roadmap: Integración de Ciclos de Cultivo con Análisis Satelital

**Proyecto:** Agrotech Digital  
**Fecha:** 17 de febrero de 2026  
**Autor:** Equipo de desarrollo  
**Estado:** Planificación aprobada, pendiente de ejecución

---

## 1. Contexto y justificación

El sistema actual permite crear parcelas, obtener imágenes satelitales Sentinel-2 vía EOSDA y calcular índices vegetativos (NDVI, NDMI, SAVI) con interpretación genérica por color.

El módulo de cultivos (`crop/`) existe con modelos básicos (`Crop`, `CropStage`, `CropType`) pero opera de forma independiente. No hay vinculación entre el análisis satelital y el estado real del cultivo en campo.

**Problema:** Un NDVI de 0.45 puede ser excelente para un cultivo recién emergido o alarmante para uno en floración. Sin contexto agronómico, la interpretación pierde valor técnico.

**Objetivo:** Crear un catálogo de cultivos con rangos óptimos de índices por etapa fenológica, y un modelo intermedio (`CropCycle`) que vincule opcionalmente una parcela con un cultivo durante un período. Cuando este vínculo existe, los análisis satelitales se contextualizan automáticamente.

---

## 2. Inventario del estado actual

### 2.1 Modelos existentes que NO se modifican

| Modelo | App | Archivo | Descripción |
|--------|-----|---------|-------------|
| `Parcel` | `parcels` | `parcels/models.py` | Terreno físico con geometría GeoJSON, eosda_id, tipo de suelo, topografía |
| `Crop` | `crop` | `crop/models.py` | Cultivo con FK a `Parcel`, fechas de siembra/cosecha, rendimiento |
| `CropType` | `crop` | `crop/models.py` | Catálogo simple (nombre + descripción) |
| `CropStage` | `crop` | `crop/models.py` | Etapa vinculada a `Crop` (nombre, fechas, notas) |
| `CropInput` | `crop` | `crop/models.py` | Insumos aplicados al cultivo |
| `CropEvent` | `crop` | `crop/models.py` | Eventos registrados (riego, plagas, etc.) |
| `CropProgressPhoto` | `crop` | `crop/models.py` | Seguimiento fotográfico |

### 2.2 Endpoints existentes que NO se modifican

| Ruta | Método | Descripción |
|------|--------|-------------|
| `api/parcels/parcel/` | GET/POST | CRUD de parcelas |
| `api/parcels/parcel/<pk>/` | GET/PUT/DELETE | Detalle de parcela |
| `api/parcels/parcel/<pk>/scenes/` | GET | Escenas por rango de fechas |
| `api/parcels/eosda-scenes/` | POST | Listar escenas EOSDA |
| `api/parcels/eosda-image/` | POST | Solicitar imagen de índice |
| `api/parcels/eosda-image-result/` | POST | Obtener resultado de imagen |
| `api/parcels/eosda-analytics/` | GET | Analytics científico |
| `api/crop/types/` | GET/POST | CRUD tipos de cultivo |
| `api/crop/crops/` | GET/POST | CRUD cultivos |
| `api/crop/stages/` | GET/POST | CRUD etapas |

### 2.3 Frontend existente que NO se modifica

| Archivo | Funciones principales |
|---------|----------------------|
| `staticfiles/js/parcels/parcel.js` | `initializeLeaflet()`, `loadParcels()`, `selectParcel()`, `flyToParcel()`, `showSceneSelectionTable()`, `buscarEscenasPorRango()` |
| `staticfiles/js/parcels/layers.js` | Capas NDVI/NDMI sobre el mapa |
| `staticfiles/js/parcels/analytics.js` | `obtenerAnalyticsCientifico()` |

### 2.4 Configuración existente relevante

- **SHARED_APPS** incluye `"parcels"` y `"crop"` (ambos disponibles en todos los tenants)
- **TENANT_APPS** incluye `"parcels"` y `"crop"` (migran por schema)
- **Router DRF** de crop: `api/crop/` con ViewSets para todos los modelos
- **Router DRF** de parcels: `api/parcels/parcel/` con ParcelViewSet
- **Autenticación:** JWT obligatorio en todos los ViewSets (`IsAuthenticated`)

---

## 3. Arquitectura de la solución

### 3.1 Modelo de datos

```
Parcel (existente, sin cambios)
  |
  |-- 0..N --> CropCycle (NUEVO: modelo intermedio, opcional)
  |               |
  |               |-- FK --> CropCatalog (NUEVO: catálogo con datos agronómicos)
  |                             |
  |                             |-- 1..N --> PhenologicalStage (NUEVO: etapas con rangos de índices)
  |
  |-- 0..N --> Crop (existente, sin cambios, sigue funcionando independiente)
```

### 3.2 Descripción de modelos nuevos

**CropCatalog** (en `crop/models.py`)
- Catálogo de cultivos con información agronómica verificable.
- Campos: nombre, nombre científico, familia botánica, categoría, ciclo en días (min/max), temperatura óptima (min/max), precipitación óptima (min/max).
- Es un catálogo de referencia. Se puebla con un comando de management y se puede extender desde el admin.
- Diferencia con `CropType`: este último es un catálogo genérico sin datos agronómicos. `CropCatalog` contiene datos técnicos necesarios para la interpretación de índices. Ambos coexisten.

**PhenologicalStage** (en `crop/models.py`)
- Etapas fenológicas de cada cultivo del catálogo, con rangos de días y valores óptimos de índices.
- Campos: nombre, orden, día inicio, día fin, NDVI (min/max/óptimo), NDMI (min/max/óptimo), SAVI (min/max/óptimo), necesidad hídrica (1-5), flag de etapa crítica, mensaje de alerta para etapa crítica.
- FK a `CropCatalog`.
- Diferencia con `CropStage`: este último es un registro de fechas reales de un cultivo específico en campo. `PhenologicalStage` es un dato de referencia agronómica del catálogo.

**CropCycle** (en `crop/models.py`)
- Modelo intermedio que vincula una parcela con un cultivo del catálogo durante un período.
- Campos: FK a `Parcel`, FK a `CropCatalog`, variedad (texto libre), fecha de siembra, fecha estimada de cosecha, fecha real de cosecha (nullable), estado (planificado/activo/cosechado/cancelado), densidad de siembra, rendimiento esperado/real, notas.
- Properties calculadas: `days_since_planting`, `current_stage`, `progress_percent`.
- Método: `get_index_interpretation(index_type, value)` - retorna diagnóstico contextualizado.

### 3.3 Fuentes de datos agronómicos

Los rangos óptimos de índices por etapa se basan en literatura técnica publicada:

| Cultivo | Fuente de referencia |
|---------|---------------------|
| Maíz | FAO Crop Water Information, CIMMYT (Centro Internacional de Mejoramiento de Maíz y Trigo) |
| Arroz | IRRI (International Rice Research Institute), FAO |
| Café | Cenicafé (Centro Nacional de Investigaciones de Café, Colombia), ICO |
| Soja | INTA Argentina, Embrapa Brasil |
| Caña de azúcar | Cenicaña Colombia, FAO |
| Sorgo | ICRISAT, FAO |
| Papa | CIP (Centro Internacional de la Papa), Agrosavia Colombia |
| Pastos/Forrajes | CIAT (Centro Internacional de Agricultura Tropical), Agrosavia |
| Algodón | ICAC (International Cotton Advisory Committee) |
| Palma de aceite | Cenipalma Colombia, MPOB Malaysia |
| Frutales (cítricos, mango) | ASOHOFRUCOL Colombia, FAO |
| Hortalizas | FAO, literatura local |

Los valores de NDVI óptimo por etapa se calibran a partir de estudios de teledetección publicados en journals como Remote Sensing of Environment, Agricultural Water Management, y datos de campo de estaciones experimentales. Los rangos son aproximaciones iniciales que se pueden ajustar con datos reales del usuario.

---

## 4. Plan de ejecución

### Fase 1: Modelos y migración de base de datos

**Archivos a modificar:**
- `crop/models.py` - Agregar 3 clases al final del archivo. No se modifica ningún modelo existente.

**Archivos a crear:**
- Ninguno. Los modelos van en el archivo existente.

**Acciones:**
1. Agregar clase `CropCatalog` al final de `crop/models.py`
2. Agregar clase `PhenologicalStage` al final de `crop/models.py`
3. Agregar clase `CropCycle` al final de `crop/models.py` (con FK a `Parcel` importado existente)
4. Ejecutar `python manage.py makemigrations crop`
5. Ejecutar `python manage.py migrate_schemas` (aplica a todos los schemas de tenant)

**Validación:** Verificar que las tablas `crop_cropcatalog`, `crop_phenologicalstage`, `crop_cropcycle` existan en el schema del tenant.

**Riesgo:** Bajo. Solo se agregan tablas nuevas. No se alteran tablas existentes.

---

### Fase 2: Comando de poblado del catálogo

**Archivos a crear:**
- `crop/management/__init__.py`
- `crop/management/commands/__init__.py`
- `crop/management/commands/populate_crop_catalog.py`

**Acciones:**
1. Crear comando que inserte los cultivos con sus etapas fenológicas.
2. Cultivos a incluir en la primera iteración (los más relevantes para Colombia):
   - Maíz (Zea mays) - Cereales
   - Arroz (Oryza sativa) - Cereales
   - Café (Coffea arabica) - Industriales
   - Soja (Glycine max) - Oleaginosas
   - Caña de azúcar (Saccharum officinarum) - Industriales
   - Sorgo (Sorghum bicolor) - Cereales
   - Papa (Solanum tuberosum) - Tubérculos
   - Frijol (Phaseolus vulgaris) - Leguminosas
   - Pastura Brachiaria (Brachiaria spp.) - Pastos y Forrajes
   - Pastura Kikuyo (Cenchrus clandestinus) - Pastos y Forrajes
   - Algodón (Gossypium hirsutum) - Industriales
   - Palma de aceite (Elaeis guineensis) - Industriales
3. Cada cultivo con 4-6 etapas fenológicas y rangos de NDVI/NDMI/SAVI por etapa.
4. Comando idempotente: si ya existe el cultivo, no lo duplica.
5. Ejecutar contra Railway: `python manage.py populate_crop_catalog --schema=finca_florez`

**Validación:** Consultar `CropCatalog.objects.count()` y `PhenologicalStage.objects.count()` desde shell.

**Riesgo:** Ninguno. Solo inserta datos en tablas nuevas.

---

### Fase 3: Serializers y API REST

**Archivos a modificar:**
- `crop/serializers.py` - Agregar 3 serializers al final.
- `crop/views.py` - Agregar 3 ViewSets al final.
- `crop/routers.py` - Registrar 3 rutas nuevas.

**Nuevos endpoints:**

| Ruta | Método | Descripción |
|------|--------|-------------|
| `api/crop/catalog/` | GET | Listar cultivos del catálogo con sus etapas |
| `api/crop/catalog/<pk>/` | GET | Detalle de un cultivo (incluye etapas) |
| `api/crop/cycles/` | GET/POST | Listar/crear ciclos de cultivo |
| `api/crop/cycles/<pk>/` | GET/PUT/DELETE | Detalle/editar/eliminar ciclo |
| `api/crop/cycles/<pk>/interpret/` | POST | Interpretar un valor de índice con contexto del ciclo |

**Detalle del endpoint de interpretación:**
```
POST api/crop/cycles/<pk>/interpret/
Body: { "index_type": "ndvi", "value": 0.45 }
Response: {
    "status": "warning",
    "message": "NDVI por debajo del esperado para Maiz en Floracion",
    "stage": { "name": "Floracion", "day_start": 56, "day_end": 70, "is_critical": true },
    "index": { "type": "ndvi", "value": 0.45, "optimal": 0.85, "range": [0.75, 0.92] },
    "crop": { "name": "Maiz" },
    "days_since_planting": 63,
    "progress_percent": 48.5
}
```

**Filtros disponibles en `api/crop/cycles/`:**
- `?parcel=<id>` - Ciclos de una parcela específica
- `?status=active` - Solo ciclos activos
- `?parcel=<id>&status=active` - Ciclo activo de una parcela (el más común)

**Validación:** Probar cada endpoint con curl o Postman contra Railway.

**Riesgo:** Bajo. Se agregan ViewSets nuevos al router existente. No se modifican ViewSets existentes.

---

### Fase 4: Registro en Django Admin

**Archivos a modificar:**
- `crop/admin.py` - Agregar 3 registros al final. No se modifican los registros existentes.

**Acciones:**
1. Registrar `CropCatalog` con inline de `PhenologicalStage` (permite editar etapas desde el admin del cultivo).
2. Registrar `CropCycle` con filtros por parcela, cultivo y estado.

**Validación:** Acceder a `/admin/crop/` y verificar que los nuevos modelos aparecen.

**Riesgo:** Ninguno.

---

### Fase 5: Frontend - Archivo nuevo `crop-cycles.js`

**Archivos a crear:**
- `staticfiles/js/parcels/crop-cycles.js`

**Funciones del archivo:**
1. `cargarCicloActivo(parcelId)` - GET a `api/crop/cycles/?parcel={id}&status=active`. Si hay ciclo activo, almacena en `window.AGROTECH_STATE.activeCropCycle`.
2. `mostrarBadgeCiclo(cycle)` - Renderiza un badge en el panel lateral: nombre del cultivo, etapa actual, barra de progreso, días desde siembra.
3. `mostrarModalCrearCiclo(parcelId)` - Modal para asociar un cultivo. Desplegable con `api/crop/catalog/`, campos de fecha de siembra y variedad.
4. `interpretarIndiceConContexto(indexType, indexValue)` - POST a `api/crop/cycles/{id}/interpret/`. Retorna el diagnóstico contextualizado.
5. `renderizarDiagnostico(diagnostico)` - Renderiza el resultado debajo del análisis existente: nivel de alerta, etapa, rangos, recomendación.

**Validación:** Verificar en consola del navegador que las funciones se ejecutan sin errores.

**Riesgo:** Bajo. Es un archivo nuevo e independiente.

---

### Fase 6: Integración mínima con código existente

**Archivos a modificar:**

1. **`staticfiles/js/parcels/parcel.js`** - 2 cambios puntuales:
   - En `selectParcel()`: agregar una línea al final → `cargarCicloActivo(parcel.id);`
   - En la sección donde se renderiza el análisis de imagen: agregar un bloque condicional al final que invoque `interpretarIndiceConContexto()` si `window.AGROTECH_STATE.activeCropCycle` existe.

2. **`staticfiles/templates/parcels/parcels-dashboard.html`** (o equivalente):
   - Agregar `<script src="/static/js/parcels/crop-cycles.js"></script>` junto a los otros scripts de parcelas.
   - Agregar un `<div id="cropCycleBadge"></div>` en el panel lateral, debajo de la información de parcela.
   - Agregar un botón "Asociar Cultivo" condicional.

**Detalle de los cambios en `selectParcel()`:**
```javascript
// Al final de la función existente, antes del cierre:
if (typeof cargarCicloActivo === 'function') {
    cargarCicloActivo(parcel.id);
}
```

**Detalle del bloque condicional en el análisis:**
```javascript
// Después del análisis existente (no se reemplaza nada):
if (window.AGROTECH_STATE.activeCropCycle && typeof interpretarIndiceConContexto === 'function') {
    const diagnostico = await interpretarIndiceConContexto(tipo, valorPromedio);
    if (diagnostico) {
        renderizarDiagnostico(diagnostico);
    }
}
```

**Validación:** Sin ciclo activo, todo funciona exactamente como antes. Con ciclo activo, aparece el diagnóstico adicional.

**Riesgo:** Bajo. Los cambios están protegidos por `typeof` checks. Si el archivo `crop-cycles.js` no carga por cualquier razón, el flujo existente no se ve afectado.

---

## 5. Despliegue

### 5.1 Orden de despliegue

1. Push del código a Git (modelos, serializers, views, comando, frontend).
2. Railway ejecuta automáticamente las migraciones via `Procfile`.
3. Ejecutar comando de poblado del catálogo manualmente via Railway CLI:
   ```
   railway run python manage.py populate_crop_catalog
   ```
4. Verificar endpoints en producción.
5. Verificar frontend en Netlify.

### 5.2 Rollback

Si algo falla, los modelos nuevos no afectan nada existente. Se puede:
- Revertir el commit de Git.
- Las tablas nuevas quedan en la DB pero no causan conflicto (no hay FK desde modelos existentes hacia los nuevos).
- Los `typeof` checks en el frontend impiden errores si el script no está disponible.

---

## 6. Pruebas requeridas

| Caso de prueba | Resultado esperado |
|---|---|
| Crear parcela sin ciclo de cultivo | Funciona exactamente como antes |
| Ver NDVI/NDMI/SAVI sin ciclo activo | Análisis genérico por colores, sin cambios |
| Crear ciclo de cultivo para una parcela | Ciclo se guarda, badge aparece en panel lateral |
| Ver NDVI con ciclo activo de maíz en floración | Análisis genérico + diagnóstico contextualizado debajo |
| Cerrar ciclo (cosechar) | Badge desaparece, análisis vuelve a ser genérico |
| Parcela con múltiples ciclos históricos | Solo el activo afecta la interpretación |
| Eliminar parcela con ciclos | Cascada elimina los ciclos (FK CASCADE) |
| Catálogo de cultivos desde admin | Se pueden agregar/editar cultivos y etapas |
| Endpoint de interpretación con valor fuera de rango | Retorna alerta con nivel correcto |

---

## 7. Estimación de tiempo

| Fase | Horas estimadas |
|------|----------------|
| 1. Modelos y migración | 1.5h |
| 2. Comando de poblado | 2h |
| 3. API REST | 2h |
| 4. Django Admin | 0.5h |
| 5. Frontend (crop-cycles.js) | 3h |
| 6. Integración con código existente | 1h |
| Pruebas y ajustes | 2h |
| **Total** | **12h** |

---

## 8. Archivos afectados (resumen)

### Archivos modificados (cambios menores al final):
- `crop/models.py` - Agregar 3 clases
- `crop/serializers.py` - Agregar 3 serializers
- `crop/views.py` - Agregar 3 ViewSets
- `crop/routers.py` - Registrar 3 rutas
- `crop/admin.py` - Registrar 3 modelos
- `staticfiles/js/parcels/parcel.js` - 2 bloques condicionales
- `staticfiles/templates/parcels/parcels-dashboard.html` - 1 script tag, 1 div, 1 botón

### Archivos nuevos:
- `crop/management/__init__.py`
- `crop/management/commands/__init__.py`
- `crop/management/commands/populate_crop_catalog.py`
- `staticfiles/js/parcels/crop-cycles.js`

### Archivos que NO se tocan:
- `parcels/models.py`
- `parcels/views.py`
- `parcels/serializers.py`
- `parcels/urls.py`
- `parcels/routers.py`
- `config/urls.py`
- `config/settings/base.py`
- Todo el flujo EOSDA existente
- Todo el análisis de colores existente
- Todo el sistema de capas del mapa

---

## 9. Iteraciones futuras (fuera de este roadmap)

Estas funcionalidades quedan documentadas para desarrollo posterior, no forman parte de la implementación actual:

1. **Dashboard de rendimiento por parcela**: gráfico histórico de rendimiento real vs esperado por ciclo.
2. **Alertas automáticas**: notificación cuando un índice cae fuera del rango óptimo en etapa crítica.
3. **Rotación de cultivos**: sugerencia de siguiente cultivo basada en historial de la parcela.
4. **Calibración con datos reales**: ajustar rangos óptimos del catálogo a partir de datos de campo del usuario.
5. **Integración con labores**: vincular labores (fertilización, riego) a etapas fenológicas del ciclo.
6. **Exportación de reportes**: PDF con historial del ciclo, índices por etapa, rendimiento final.
