# Handover — Contexto completo del proyecto para Kilo (Mac Mini)

> Documento para que el agente (Kilo) en el **Mac Mini** retome el hilo exacto del
> trabajo. Léelo completo antes de tocar código.
>
> Estado del repo al sincronizar: rama `main`, commits
> `bf86208` (backend) + `30be284` (frontend).

---

## 1. Qué es AgroTech (contexto de negocio)

Plataforma SaaS agrícola multi-tenant. Un agricultor/empresa (tenant) gestiona
sus **parcelas**, ve **análisis satelital** (índices de vegetación), pronóstico
climático, elevación, y ahora **monitoreo radar**. Hay **planes de suscripción**
(free/basic/pro/enterprise) con límites (hectáreas, usuarios, parcelas, análisis/mes).

**Dos fuentes satelitales (importante, son distintas):**

| Fuente | Qué da | Rol | Costo |
|---|---|---|---|
| **Sentinel-2 vía EOSDA** | NDVI, NDMI, EVI, SAVI, NDRE (índices ópticos) | Análisis óptico principal | De pago (una sola API key para todos los tenants) |
| **Sentinel-1 vía Planetary Computer** | sigma0 VV/VH + RVI (retrodispersión radar) | Vigilancia cuando hay nubes + detección de cambio | Gratis (catálogo público) |

**Regla de marca:** el cliente **NUNCA** ve "EOSDA" ni "Planetary Computer". La
experiencia es **AgroTech**. Esas referencias solo van en código/documentación interna.

---

## 2. Arquitectura técnica (lo esencial)

- **Backend**: Django 5 + **django-tenants** (cada tenant = un schema PostgreSQL).
- **Frontend operativo**: HTML/JS servido por Django — `metrica/static/js/parcels/`
  (dashboard Leaflet) y `metrica/templates/parcels/parcels-dashboard.html`.
- **SPA React**: `frontend/` (registro/login/landing). Parcialmente conectado.
- **Autenticación**: JWT (simplejwt) con `tenant_id` en el token; middleware
  `config/middleware.py` resuelve el tenant.
- **EOSDA**: todo pasa por `parcels/eosda_client.py` (cache + rate limiter + log).
- **Radar**: `parcels/sentinel1.py` (Planetary Computer STAC + COG por rango HTTP).
- **Nota de import**: `metrica/` debe estar en `sys.path` (hack en `manage.py`/`conftest.py`).

---

## 3. El hilo del trabajo hecho (fases, en orden)

1. **Consumo EOSDA centralizado** — `parcels/eosda_client.py` + `eosda_rate_limiter.py`.
   - Cache + deduplicación (clave `eosda:{tenant}:{parcela}:{operacion}:{indice}:{fecha}`).
   - Rate limiter global **8 req/min** (una sola API key).
   - Registro: `UsageMetrics.eosda_requests` (cuota por tenant) + `EosdaRequestLog`
     (auditoría global, schema `public`, con tenant/usuario/parcela/operación/fecha/source).
   - Definición exacta del conteo: `docs/EOSDA_REQUESTS_DEFINICION.md`.

2. **Auditoría integral** — `docs/FLUJO_CLIENTE.md` (flujo del cliente) y
   `docs/EOSDA_CONSUMO.md` (cómo se calcula el consumo).

3. **Fase de corrección** — `docs/AUDITORIA_CORRECCIONES.md` + `docs/RESUMEN_CAMBIOS.md`:
   - Eliminados los fallbacks sintéticos (datos random) que alimentaban salud/reportes.
   - Registro de usuario corregido (frontend alineado, reenvío de verificación).
   - Recuperación de contraseña implementada.
   - Gestión de usuarios del tenant (contraseña, roles, scope por tenant).
   - `sync_status` de parcelas + reintento (`POST /parcel/<id>/sync-eosda/`).
   - Cálculo de área unificado (`parcels/geometry.py`).
   - Dashboard de consumo corregido; "Mi Suscripción" implementado.
   - Referencias visibles a EOSDA eliminadas del frontend/mensajes/PDF.

4. **Segunda ronda + validación** — `docs/AUDITORIA_SEGUNDA_RONDA.md` y
   `docs/VALIDACION_FINAL.md` (pruebas con BD real + entorno).

5. **NDRE** — implementado como índice real en imagen, escenas-analytics y analytics.

6. **Radar Sentinel-1** — reescrito con **datos reales** (Planetary Computer RTC):
   - `parcels/sentinel1.py`: búsqueda STAC + lectura AOI del COG (sin descargar 1GB),
     sigma0 VV/VH, RVI, serie temporal, detección de cambio, heatmaps por celda.
   - Vista `GET /parcel/<id>/radar/` (resumen) y `/parcel/<id>/radar-layers/` (capas PNG).
   - Frontend: panel "Monitoreo Radar" + overlay de RVI y cambio con `L.imageOverlay`.

7. **Preguntas para EOSDA** — `docs/PREGUNTAS_EOSDA.md` (para la reunión).

---

## 4. Repositorios (IMPORTANTE — son DOS)

| Repo | Qué contiene | Deploy |
|---|---|---|
| `agrotech-digital` (el de siempre) | Backend Django + dashboard (`metrica/`). ⚠️ La carpeta `frontend/` aquí es una **copia vieja**, NO es la fuente de verdad | — |
| `agrotech-client-frontend` | Frontend React (SPA: registro/login/landing) | Netlify |

- `https://github.com/sebasflorez16/agrotech-digital.git`
- `https://github.com/sebasflorez16/agrotech-client-frontend.git`

Los cambios de esta fase están en `agrotech-digital` (backend + dashboard), EXCEPTO
los del frontend React, que van en `agrotech-client-frontend` (ver `docs/CAMBIOS_FRONTEND_REACT.md`).

## 5. Los dos cambios a traer

| Dónde | Contenido |
|---|---|
| `agrotech-digital` (commits `bf86208` + `30be284` + `2acdd6e`) | Backend Django + dashboard `metrica/` + migraciones + tests + docs |
| `agrotech-client-frontend` (aplicar manualmente) | 3 archivos React: `src/api/client.js`, `src/pages/Register.jsx`, `src/pages/Landing.jsx` — ver `docs/CAMBIOS_FRONTEND_REACT.md` |

## 6. Pasos para traer los cambios en el Mac Mini

```bash
# Repo backend + dashboard
cd <ruta>/agrotech-digital
git fetch origin && git pull origin main
# activar venv, luego:
python manage.py migrate_schemas --schema public   # y por cada tenant
python manage.py collectstatic --noinput

# Repo frontend React (Netlify)
cd <ruta>/agrotech-client-frontend
git pull origin main
# aplicar los 3 cambios de docs/CAMBIOS_FRONTEND_REACT.md
npm install && npm run build
# (Netlify hace el deploy al pushear a main)
```

---

## 7. Entorno local (Mac Mini)

- PostgreSQL local: DB `agrotech`, usuario `postgres` (ver `.env`).
- venv `agro-rest` (o el equivalente instalado). Confirmar que tenga: django,
  django-tenants, djangorestframework, simplejwt, django-redis, numpy, scipy,
  rasterio, Pillow, reportlab, sklearn.
- `python manage.py check` debe salir "0 issues".

---

## 8. Estado actual (qué está hecho vs pendiente)

### Hecho y probado
- Consumo EOSDA centralizado (cache + dedup + rate limiter + log) — con tests.
- NDRE implementado (backend + frontend).
- Radar Sentinel-1 con datos reales (búsqueda STAC + lectura AOI + RVI + cambio) — con prueba real.
- Correcciones de auditoría (registro, recuperación, usuarios, sync parcelas, área, dashboard, suscripción, sin EOSDA visible).
- 16 tests de radar + 3 de multi-tenant + 7 de EOSDA validation + 14 de límites = PASS.

### Pendiente / requiere decisión
1. **NDRE contra EOSDA real**: el código está listo; falta validar que EOSDA devuelve datos NDRE (reunión EOSDA).
2. **`field-management`**: confirmar el contrato exacto para crear campo (reunión EOSDA).
3. **Umbral de cambio radar (2 dB)**: calibrar con datos de campo reales.
4. **Overlay radar en navegador**: implementado pero no probado visualmente.
5. **Cómo cuenta EOSDA una "request" comercialmente**: pendiente de confirmar (reunión EOSDA).
6. **Código muerto restante**: `EOSDAMetricsViewSet` (`parcels/metrics_views.py`), Cesium JS,
   `authentication/urls_pages.py`, clase duplicada `ParcelNdviWeatherComparisonView` en `metereological.py`.
7. **Zonificación sintética**: los sectores (`ParcelZonification`) aún usan numpy; hay que conectarlos a NDVI real de EOSDA si se quieren sectores reales.
8. **Latencia radar**: 10-30s por escena; evaluar Celery cuando escale.

### Reglas transversales que el agente DEBE respetar siempre
- Multi-tenant: un tenant nunca accede a otro; validar en backend, no confiar en IDs del frontend.
- Cero datos ficticios presentados como reales (si no hay dato → "no disponible").
- Cero referencias visibles al proveedor (EOSDA/Planetary Computer) en la UI/PDF/mensajes.
- Cero credenciales hardcodeadas (solo `.env`).
- No romper el frontend que funciona; cambios mínimos.
- Todas las llamadas EOSDA pasan por `eosda_client.py`; rate limiter 8/min.

---

## 9. Dónde está cada cosa (mapa rápido)

| Tema | Archivo |
|---|---|
| Cliente EOSDA (embudo) | `parcels/eosda_client.py` |
| Rate limiter global | `parcels/eosda_rate_limiter.py` |
| Registro consumo | `billing/models.py` (`EosdaRequestLog`), `billing/decorators.py` |
| Radar Sentinel-1 | `parcels/sentinel1.py` |
| Área unificada | `parcels/geometry.py` |
| Vistas EOSDA | `parcels/views.py`, `parcels/analytics_views.py`, `parcels/metereological.py`, `parcels/proxy.py` |
| Frontend dashboard | `metrica/static/js/parcels/parcel.js`, `metrica/templates/parcels/parcels-dashboard.html` |
| Config | `config/settings/base.py` |
| Tests radar | `parcels/tests/test_radar_monitoring.py` |
| Docs | `docs/*.md` |

---

## 10. Cómo seguir (siguiente paso sugerido)

Al retomar en el Mac Mini, empezar por:
1. `git pull` + migraciones + `manage.py check`.
2. Correr la suite de radar: `pytest parcels/tests/test_radar_monitoring.py`.
3. Probar el overlay radar en el navegador (parcela + plan con `continuous_monitoring`).
4. Continuar con los pendientes de la sección 7 (empezando por calibrar el umbral de cambio y conectar la zonificación a NDVI real).

Consulta `docs/AUDITORIA_SEGUNDA_RONDA.md` §7 para el detalle técnico del radar.
