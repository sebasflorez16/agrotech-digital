# 🌱 Monitoreo Continuo — Fase 1 Completada

**Fecha**: 6 de junio de 2026
**Objetivo**: Capa de "último estado conocido" — eliminar el "sin datos disponibles" incluso cuando no hay imágenes nuevas.

---

## ✅ Componentes Implementados

### 1. Modelo `CropHealthStatus`
**Archivo**: `parcels/models.py`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `parcel` | OneToOneField → Parcel | Parcela asociada |
| `tenant_id` | IntegerField (indexado) | Aislamiento multi-tenant |
| `ndvi_last` | FloatField | Último NDVI conocido |
| `ndmi_last` | FloatField | Último NDMI conocido |
| `evi_last` | FloatField | Último EVI conocido |
| `last_observation_date` | DateTimeField | Fecha de última observación |
| `last_image_date` | DateField | Fecha de última imagen |
| `observation_quality` | CharField | Excelente / Buena / Limitada / Sin observación |
| `confidence_score` | IntegerField | 0-100% de confianza |
| `days_without_observation` | IntegerField | Días sin observación óptica |
| `active_alerts` | JSONField | Alertas activas |

**Propiedades**:
- `status_badge` → Diccionario con emoji, label, color para frontend
- `status_message` → Mensaje descriptivo en español para el agricultor

**Métodos**:
- `update_from_observation(ndvi, ndmi, evi, image_date, cloud_cover)` → Actualiza estado con nueva observación
- `get_or_create_for_parcel(parcel)` → Factory method

### 2. Vista `CropHealthAPIView`
**Archivo**: `parcels/views.py`
**Endpoint**: `GET /api/parcels/parcel/{id}/health/`
**Protección**: `IsAuthenticated`

**Respuesta JSON**:
```json
{
  "parcel_id": 1,
  "parcel_name": "La Esperanza",
  "status": {
    "badge": {"emoji": "🟢", "label": "Bueno", "color": "#22c55e"},
    "quality": "good",
    "quality_label": "Buena — Imagen utilizable con algunas limitaciones",
    "confidence_score": 75,
    "days_without_observation": 3,
    "message": "Tu cultivo fue observado hace 3 dias. NDVI estimado: 0.72. Seguimos monitoreando."
  },
  "indices": {"ndvi": 0.72, "ndmi": 0.42, "evi": 0.58},
  "last_observation": "2026-06-03T10:00:00Z",
  "last_image_date": "2026-06-03",
  "recent_scenes": [...],
  "alerts": []
}
```

### 3. Ruta API
**Archivo**: `parcels/urls.py`
```python
path('parcel/<int:parcel_id>/health/', views.CropHealthAPIView.as_view(), name='parcel_health'),
```

---

## 🔄 Lógica de Degradación de Confianza

| Días sin observación | Calidad | Confianza | Badge |
|---------------------|---------|-----------|-------|
| 0 | excellent | 95% | 🟢 Excelente |
| 1-7 | good | 75-85% | 🟢 Bueno |
| 8-14 | limited | 30-55% | 🟡 Atención |
| 15+ | no_observation | 10-20% | 🔴 Sin datos |

---

## 📋 Próximos Pasos (Fase 2-5)

| Fase | Objetivo | Archivos nuevos |
|------|----------|-----------------|
| 2 | Integrar `CropHealthStatus.update_from_observation()` en endpoints EOSDA existentes | `parcels/views.py` |
| 3 | Mapa de calor visual (verde/amarillo/rojo) sobre la parcela | `staticfiles/js/parcels/parcel.js` |
| 4 | Sentinel-1 como detector interno de cambios | `parcels/sentinel1.py` (nuevo) |
| 5 | Motor de fusión multi-fuente | `parcels/fusion_engine.py` (nuevo) |

---

## 🧪 Verificación en Local

```bash
# Generar migración
python manage.py makemigrations parcels

# Aplicar migración
python manage.py migrate parcels

# Probar endpoint (requiere token JWT)
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/parcels/parcel/1/health/
```

---

*Fase 1 del roadmap de Monitoreo Continuo — 6 de junio de 2026*