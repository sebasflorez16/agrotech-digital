# Plan de Escalamiento y Seguridad — AgroTech Digital

> **Objetivo**: dejar el SaaS listo para operar a escala (decenas de miles de tenants) con un sistema de consumo de APIs de pago controlado y una postura de seguridad profesional. Prioridad: correcto y despacio, con visión a futuro.

---

## 1. Sistema de Consumo EOSDA (Rate Limiting + Cache)

### Contexto del problema
- EOSDA cobra por request y el plan **Starter** limita a **10 requests/minuto**.
- Sin control, N usuarios simultáneos disparan N requests → costo + errores 429 en cadena.
- Hoy solo existe `@check_eosda_limit` (cuenta por tenant, incrementa en 2xx). No hay cache, cola ni dedup.

### Arquitectura objetivo (5 capas, no 7)

```
[Frontend debounce] → [Cache Redis] → [Cola central] → [Rate limiter 8-9/min] → [EOSDA]
                              ↑                                              ↓
                      [Registro de consumo] ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
```

| # | Capa | Qué resuelve | Tecnología |
|---|------|-------------|-----------|
| 1 | **Cache inteligente + deduplicación** | La misma consulta (parcela+índice+fecha) se sirve 1 sola vez | Redis + TTL |
| 2 | **Registro de consumo** | Saber cuánto gasta CADA tenant | Modelo `EosdaRequestLog` |
| 3 | **Cola central + rate limiter** | Todas las llamadas pasan por un solo embudo a 8-9/min | Celery + Redis |
| 4 | **Cuota por tenant** | Repartir el límite global entre clientes | Ya existe `check_eosda_limit` |
| 5 | **Debounce frontend** | Evitar doble clic / doble submit | 1 línea JS |

### Fase 1 (ahora): Cache + Registro de consumo
- **Cache**: Redis. Clave = `eosda:{tenant_id}:{parcel_id}:{indice}:{fecha}`. TTL 15 min.
  - La cache **ES** la deduplicación: si 10 usuarios piden el mismo análisis, solo el primero llega a EOSDA.
- **Registro de consumo**: nuevo modelo en `billing`:
  ```
  EosdaRequestLog:
    tenant        FK
    parcel        FK (nullable)
    operation     CharField   # "ndvi", "ndmi", "scenes", "analytics"...
    index_type    CharField
    date_requested DateField
    source        CharField   # "cache" | "eosda"
    cost_estimated DecimalField
    created_at    DateTimeField
  ```
  - Solo se loguea cuando el request **sale a EOSDA** (no cuando pega en cache).
  - Esto alimenta el dashboard de facturación con datos reales por cliente.

### Fase 2 (cuando el tráfico lo pida): Cola + Rate limiter
- **Celery** (o un management command con `time.sleep` si no queremos infra nueva).
- Un worker único despacha a 8-9 requests/min. Las peticiones se encolan, no se rechazan.
- Parámetro configurable en settings: `EOSDA_RATE_LIMIT_PER_MIN = 8`.

### Fase 3 (escala real): Celery distribuido
- Broker Redis → N workers → monitorizar con Flower.
- El rate limiter se implementa con un token bucket en Redis (evita que N workers violen el límite global).

---

## 2. Seguridad

### 2.1 Rotación de credenciales (URGENTE)
| Credencial | Estado | Acción |
|-----------|--------|--------|
| `guibsonsid.16` | En historial git + `.env` | Rotar en Railway y BD local |
| Gmail app password | En `.env` | Migrar a correo corporativo (SMTP dedicado) |
| MercadoPago keys | En `.env` | Verificar si siguen activas |
| Earthdata password | En `.env` | OK (cuenta dedicada, sin expiración) |

### 2.2 Purgar historial git
- `git filter-repo` (reemplazo moderno de BFG) para eliminar `.env`, credenciales y `AUDITORIA_SEGURIDAD_AGROTECH.md` del historial.
- Después: `git push --force` + regenerar todos los tokens.

### 2.3 Verificación de email (anti-prefetch Gmail)
- Problema actual: Gmail prefetchea el link y consume el token antes de que el usuario clique.
- Solución: **verificación en 2 pasos** — el link lleva a una página HTML que muestra "Confirmar verificación" y recién ahí se hace el POST de activación. Gmail no ejecuta POST.

### 2.4 Rate limiting de API general (DRF throttling)
- `AnonRateThrottle` y `UserRateThrottle` en `REST_FRAMEWORK`.
- Evita brute-force en login/register (hoy sin protección).

### 2.5 Headers de seguridad
- Verificar `SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, `X_FRAME_OPTIONS`, `SECURE_CONTENT_TYPE_NOSNIFF` en `production.py`.

### 2.6 Correo corporativo
- Crear `info@agrotechdigital.com` (o similar) en un proveedor SMTP dedicado (Google Workspace, Zoho, Resend).
- Reemplazar Gmail personal en `EMAIL_HOST_USER`.

---

## 3. Escalabilidad

### 3.1 Infraestructura objetivo
| Componente | Hoy | Mañana |
|-----------|-----|--------|
| DB | PostgreSQL local | PostgreSQL managed (Railway) |
| Cache | Ninguno | Redis |
| Cola async | Ninguna | Celery + Redis |
| Email | Gmail SMTP | Proveedor dedicado |
| Monitoreo | Print/logs | Sentry + logs estructurados |
| Static | Duplicado (metrica/ + agrotech-client/) | Un solo frontend |

### 3.2 Migración de datos (django-tenants)
- Las migraciones idempotentes ya están listas (ADD COLUMN IF NOT EXISTS).
- Para escalar: `migrate_schemas --executor=parallel` para migrar tenants en paralelo.

### 3.3 Observabilidad
- Sentry para errores en producción.
- Logs estructurados con `tenant_id` en cada línea (para auditar consumo por cliente).

---

## 4. Orden de ejecución (despacio, bien)

1. **Cache Redis + Registro de consumo** (Fase 1 consumo EOSDA) — mayor ahorro inmediato.
2. **Rotar `guibsonsid.16` + purgar historial git** — seguridad crítica.
3. **Verificación email 2 pasos** — anti-prefetch Gmail.
4. **DRF throttling + headers seguridad** — hardening.
5. **Correo corporativo** — profesionalismo.
6. **Desplegar a Railway** — salir a producción.
7. **Cola + rate limiter EOSDA** — cuando el tráfico lo pida.
8. **Sentinel-1 real (Copernicus OAuth2)** — cuando haya tiempo.

---

## 5. Decisiones que NO tomamos aún

- Redis como servicio managed (Railway) vs self-hosted.
- Celery vs management command simple para la cola inicial.
- Proveedor de correo corporativo (Google Workspace / Zoho / Resend).
