# 🍎 Guía de Desarrollo Local — AgroTech Digital

## Arquitectura

```
┌─────────────────────────┐     ┌─────────────────────────┐
│   Frontend (Netlify)    │     │   Backend (Django)      │
│   localhost:8080        │────▶│   127.0.0.1:8000        │
│   Proxy: /api/* /billing/*│   │   django-tenants        │
└─────────────────────────┘     │   PostgreSQL local      │
                                └─────────────────────────┘
```

- **Frontend**: Netlify CLI sirve archivos estáticos y proxea `/api/*` y `/billing/*` al backend.
- **Backend**: Django con `django-tenants` resuelve el tenant desde el JWT (SmartTenantMiddleware).
- **BD**: PostgreSQL local con schemas por tenant (`public`, `prueba`, `finca_juan`).

---

## Prerrequisitos

1. **PostgreSQL** corriendo localmente (`pg_isready` debe retornar "accepting connections")
2. **Python 3.11+** con entorno conda `agrotech` activado
3. **Node.js** y **Netlify CLI** instalados (`npm install -g netlify-cli`)
4. Repos clonados:
   - `agrotech-digital` (backend)
   - `agrotech-client-frontend` (frontend)

---

## Inicio Rápido

### 1. Backend

```bash
cd agrotech-digital
conda activate agrotech
DJANGO_SETTINGS_MODULE=config.settings.local python manage.py runserver 0.0.0.0:8000
```

> ⚠️ **SIEMPRE** usar `DJANGO_SETTINGS_MODULE=config.settings.local`. El `manage.py` tiene `production` por defecto.

### 2. Frontend

```bash
cd agrotech-client-frontend
cp netlify-local.toml netlify.toml
netlify dev --port 8080
```

> El `netlify-local.toml` proxea `/api/*` y `/billing/*` a `http://127.0.0.1:8000`.

### 3. Abrir en el navegador

- Login: http://localhost:8080/login
- Dashboard: http://localhost:8080/dashboard

---

## Usuarios de prueba

| Email | Password | Tenant | Schema |
|-------|----------|--------|--------|
| admin@gmail.com | admin123 | prueba | prueba |
| juan@gmail.com | juan123 | Finca de Juan | finca_juan |

---

## Cómo funciona la resolución de Tenant

### Flujo completo:

1. **Login**: Frontend envía email+password a `/api/auth/login/`
2. **Respuesta**: Backend devuelve JWT + info del tenant (incluyendo `domain`)
3. **Storage**: Frontend guarda `accessToken` y `tenantDomain` en localStorage
4. **API calls**: Frontend envía:
   - `Authorization: Bearer <JWT>` 
   - `X-Tenant-Domain: prueba.localhost` (header custom)
5. **SmartTenantMiddleware** resuelve el tenant en este orden:
   1. Header `X-Tenant-Domain` → busca el Domain en BD
   2. Hostname → resolve via django-tenants estándar
   3. Si hostname resuelve a `public` + hay JWT → resuelve tenant desde `user.tenant` FK

### ¿Por qué funciona sin subdominios?

El `SmartTenantMiddleware` decodifica el JWT, busca el `user_id`, y obtiene el tenant desde el FK `user.tenant`. Esto permite que `localhost` (que resuelve a `public`) funcione correctamente para todos los tenants.

---

## Endpoints del Dashboard

| Endpoint | Descripción | Tenant-aware |
|----------|-------------|:------------:|
| `POST /api/auth/login/` | Login por email | No (public schema) |
| `GET /api/parcels/parcel/` | Parcelas del tenant | ✅ |
| `GET /api/crop/crops/` | Cultivos del tenant | ✅ |
| `GET /api/RRHH/empleados/` | Empleados del tenant | ✅ |
| `GET /billing/api/usage/dashboard/` | Métricas de uso | ✅ |

---

## Switching entre Local y Producción

### Frontend (`netlify.toml`)

- **Local**: `cp netlify-local.toml netlify.toml`
- **Producción**: `git checkout netlify.toml`

> Hay un **pre-commit hook** que previene pushear la config local accidentalmente.

### Backend

- **Local**: `DJANGO_SETTINGS_MODULE=config.settings.local`
- **Producción**: Railway usa `config.settings.production` por defecto

---

## Troubleshooting

### Error: `DATABASE_URL no está definida`
→ Estás usando settings de producción. Usa `DJANGO_SETTINGS_MODULE=config.settings.local`.

### Error: `Client matching query does not exist` en billing
→ El middleware no resolvió el tenant. Verifica que el JWT sea válido y que el user tenga un `tenant_id` asignado.

### Netlify proxy devuelve 502
→ Backend no está corriendo en `127.0.0.1:8000`. Verifica con `curl http://127.0.0.1:8000/api/auth/login/ -X POST`.

### Las parcelas de un tenant aparecen en otro
→ Verifica que cada user tiene un `tenant_id` correcto:
```bash
DJANGO_SETTINGS_MODULE=config.settings.local python -c "
import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.local'
django.setup()
from django.contrib.auth import get_user_model
for u in get_user_model().objects.all():
    print(f'{u.email} → tenant_id={u.tenant_id}')
"
```

### El login no funciona con email
→ El endpoint correcto es `/api/auth/login/` (NO `/api/token/`). El `/api/token/` usa username.

---

## Archivos clave

### Backend
| Archivo | Propósito |
|---------|-----------|
| `config/middleware.py` | SmartTenantMiddleware (resolución JWT/header) |
| `config/settings/local.py` | Settings para desarrollo local |
| `authentication/views.py` | LoginView (email-based) |
| `billing/views.py` | Dashboard de billing + `resolve_tenant_for_request()` |
| `metrica/users/models.py` | User model con FK a Client (tenant) |

### Frontend
| Archivo | Propósito |
|---------|-----------|
| `netlify-local.toml` | Config de proxy local |
| `js/dashboard-liquid.js` | Lógica del dashboard |
| `js/login-liquid.js` | Lógica de login (guarda tenantDomain) |
