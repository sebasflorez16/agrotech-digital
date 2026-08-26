# 🚀 Deployment Guide - AgroTech Digital

Guía completa de deployment para frontend (Netlify) y backend (Railway).

## 📋 Tabla de Contenidos

- [Arquitectura](#arquitectura)
- [Variables de Entorno](#variables-de-entorno)
- [Backend (Railway)](#backend-railway)
- [Frontend (Netlify)](#frontend-netlify)
- [Verificación](#verificación)
- [Troubleshooting](#troubleshooting)

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────┐
│   agrotechcolombia.com (Netlify)        │
│   ├── Static Frontend                   │
│   ├── Landing Page                      │
│   └── Dashboard UI                      │
└──────────────┬──────────────────────────┘
               │
               │ API Requests (/api/*)
               ▼
┌──────────────────────────────────────────┐
│   Railway Backend                        │
│   ├── Django REST API                    │
│   ├── Multi-tenant Logic                 │
│   ├── EOSDA Integration                  │
│   └── PostgreSQL Database                │
└──────────────────────────────────────────┘
```

**Flujo**:
1. Usuario accede a `agrotechcolombia.com` (Netlify)
2. Frontend hace requests a `/api/*` → Netlify redirect → Railway
3. Backend procesa y retorna JSON
4. Frontend renderiza datos

---

## 🔐 Variables de Entorno

### Backend (Railway)

#### Requeridas
```bash
# Django
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<generar-con-djecrety.ir>
DJANGO_ALLOWED_HOSTS=agrotechcolombia.com,*.railway.app,agrotechcolombia.netlify.app

# Database (auto-configurado por Railway PostgreSQL)
DATABASE_URL=postgresql://...

# APIs
EOSDA_API_KEY=<tu-api-key-eosda>
CESIUM_ACCESS_TOKEN=<tu-token-cesium>

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<tu-email@gmail.com>
EMAIL_HOST_PASSWORD=<app-password>
DEFAULT_FROM_EMAIL=AgroTech Digital <noreply@agrotechcolombia.com>

# Security
CSRF_TRUSTED_ORIGINS=https://agrotechcolombia.com,https://*.agrotechcolombia.com,https://*.railway.app
```

#### Opcionales
```bash
# Redis Cache (recomendado)
REDIS_URL=redis://...

# Sentry (recomendado)
SENTRY_DSN=https://...@sentry.io/...

# Logging
DJANGO_LOG_LEVEL=WARNING  # INFO para debug

# Admin
DJANGO_ADMINS=Admin:admin@agrotechcolombia.com
```

### Frontend (Netlify)

Configurado en `netlify.toml` (ya incluido):
```toml
[build]
  publish = "metrica/static"
  
[[redirects]]
  from = "/api/*"
  to = "https://site-production-208b.up.railway.app/api/:splat"
  status = 200
  force = true
```

---

## 🚂 Backend (Railway)

### 1. Setup Inicial

#### 1.1 Crear Proyecto en Railway
1. Ir a [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Conectar repositorio
4. Seleccionar branch `main`

#### 1.2 Agregar PostgreSQL
1. En el proyecto → New → Database → PostgreSQL
2. Railway auto-configura `DATABASE_URL`

#### 1.3 Configurar Variables
1. Variables → Raw Editor
2. Pegar variables de entorno (ver sección arriba)
3. Save

### 2. Configuración de Deploy

Railway detecta automáticamente:
- `Dockerfile` → Usa build de Docker
- `start.sh` → Script de inicio
- `nixpacks.toml` → Configuración alternativa

#### 2.1 Verificar Dockerfile
```dockerfile
# Ya incluido en el proyecto
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["bash", "start.sh"]
```

#### 2.2 Verificar start.sh
```bash
# Ya incluido - ejecuta:
# 1. Verifica DATABASE_URL
# 2. Setup Railway (migraciones)
# 3. Inicia Gunicorn
```

### 3. Deploy

#### 3.1 Deploy Automático
```bash
git push origin main
# Railway detecta y despliega automáticamente
```

#### 3.2 Deploy Manual
1. Railway Dashboard → Deployments
2. Redeploy → Latest commit

### 4. Migraciones

#### 4.1 Aplicar Migraciones
Railway ejecuta automáticamente en `start.sh`:
```bash
python manage.py migrate_schemas --shared --noinput
```

#### 4.2 Migraciones Manuales (si necesario)
```bash
# Desde Railway CLI
railway run python manage.py migrate_schemas --shared

# O desde Railway shell
railway shell
python manage.py migrate_schemas --shared
```

### 5. Crear Superusuario

```bash
# Railway CLI
railway run python manage.py createsuperuser

# O Railway shell
railway shell
python manage.py createsuperuser --username admin --email admin@agrotechcolombia.com
```

### 6. Collectstatic

Ya configurado con WhiteNoise - se ejecuta automáticamente.

---

## 🌐 Frontend (Netlify)

### 1. Setup Inicial

#### 1.1 Conectar Repositorio
1. Ir a [netlify.com](https://netlify.com)
2. New site from Git → GitHub
3. Seleccionar repositorio
4. Branch: `main`

#### 1.2 Configuración de Build
```
Build command: (vacío - es estático)
Publish directory: metrica/static
```

### 2. Configurar Dominio

#### 2.1 Dominio Personalizado
1. Site settings → Domain management
2. Add custom domain → `agrotechcolombia.com`
3. Seguir instrucciones DNS

#### 2.2 SSL
Netlify configura automáticamente Let's Encrypt SSL.

### 3. Configurar Redirects

Ya configurado en `netlify.toml`:
```toml
[[redirects]]
  from = "/api/*"
  to = "https://site-production-208b.up.railway.app/api/:splat"
  status = 200
  force = true

[[headers]]
  for = "/*"
  [headers.values]
    Content-Security-Policy = "default-src 'self' 'unsafe-inline' 'unsafe-eval' ..."
```

### 4. Variables de Entorno (Frontend)

Si necesitas variables en JS:
1. Site settings → Environment variables
2. Agregar `CESIUM_TOKEN`, etc.

### 5. Deploy

#### 5.1 Deploy Automático
```bash
git push origin main
# Netlify despliega automáticamente
```

#### 5.2 Deploy Manual
```bash
# Instalar Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Deploy
netlify deploy --prod --dir=metrica/static
```

---

## ✅ Verificación

### 1. Backend Health Check
```bash
curl https://site-production-208b.up.railway.app/health/
# Esperado: {"status": "ok"}

curl https://site-production-208b.up.railway.app/api/health/detailed/
# Esperado: JSON con estado de servicios
```

### 2. Frontend
```bash
curl -I https://agrotechcolombia.com
# Esperado: 200 OK

curl https://agrotechcolombia.com/api/health/
# Esperado: {"status": "ok"} (redirect funciona)
```

### 3. API Endpoints
```bash
# Login
curl -X POST https://agrotechcolombia.com/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}'

# Parcels (requiere token)
curl https://agrotechcolombia.com/api/parcels/ \
  -H "Authorization: Bearer <token>"
```

### 4. Swagger Docs
Visitar: `https://agrotechcolombia.com/api/docs/`

### 5. Tests Locales Antes de Deploy
```bash
# Simular producción localmente
export DJANGO_SETTINGS_MODULE=config.settings.production
export DATABASE_URL=<local-postgres>

python manage.py runserver

# Ejecutar tests
bash scripts/run_tests.sh --all
```

---

## 🔧 Troubleshooting

### Backend

#### Error: "DisallowedHost at /"
**Problema**: Dominio no en `ALLOWED_HOSTS`
```bash
# Agregar en Railway variables
DJANGO_ALLOWED_HOSTS=agrotechcolombia.com,*.railway.app,agrotechcolombia.netlify.app
```

#### Error: "OperationalError: could not connect to server"
**Problema**: DATABASE_URL incorrecta
```bash
# Verificar en Railway
railway variables
# Debe existir DATABASE_URL
```

#### Error: "No such table: ..."
**Problema**: Migraciones no aplicadas
```bash
railway run python manage.py migrate_schemas --shared --noinput
```

#### Error: "CSRF verification failed"
**Problema**: CSRF_TRUSTED_ORIGINS
```bash
# Agregar en Railway
CSRF_TRUSTED_ORIGINS=https://agrotechcolombia.com,https://*.agrotechcolombia.com
```

### Frontend

#### Error: API requests fallan (CORS)
**Problema**: CORS no configurado
```bash
# Verificar en backend Railway
CORS_ALLOWED_ORIGINS=https://agrotechcolombia.netlify.app,https://agrotechcolombia.com
```

#### Error: Redirects no funcionan
**Problema**: netlify.toml mal configurado
```bash
# Verificar que netlify.toml esté en la raíz
cat netlify.toml
```

#### Error: CSP bloquea Cesium
**Problema**: Content-Security-Policy
```toml
# Ya configurado en netlify.toml
Content-Security-Policy = "... cesium.com ..."
```

---

## 🔄 Rollback

### Railway
```bash
# Desde Dashboard
Deployments → <version-anterior> → Redeploy

# O desde CLI
railway rollback
```

### Netlify
```bash
# Desde Dashboard
Deploys → <deploy-anterior> → Publish deploy

# O desde CLI
netlify deploy --prod --dir=metrica/static
```

---

## 📊 Monitoring

### Railway
1. Deployments → Logs (tiempo real)
2. Metrics → CPU/Memory/Network
3. Settings → Webhooks para notificaciones

### Netlify
1. Deploys → Deploy log
2. Functions → Logs (si usas)
3. Analytics → Traffic

### Sentry (Recomendado)
```bash
# Agregar en Railway
SENTRY_DSN=https://...@sentry.io/...

# Ya configurado en código
import sentry_sdk
sentry_sdk.init(dsn=settings.SENTRY_DSN)
```

---

## 🔐 Seguridad

### SSL
- ✅ Netlify: Let's Encrypt automático
- ✅ Railway: SSL automático

### Secrets
- ❌ NUNCA commitear secrets a Git
- ✅ Usar variables de entorno
- ✅ Rotar API keys periódicamente

### Backups
```bash
# Configurar backup automático
bash scripts/setup_backup_cron.sh

# O manualmente
python scripts/backup_database.py --s3-bucket agrotech-backups
```

---

## 📞 Soporte

- Railway: https://railway.app/help
- Netlify: https://docs.netlify.com
- Proyecto: GitHub Issues

---

## ✨ Checklist de Deploy

- [ ] Variables de entorno configuradas en Railway
- [ ] PostgreSQL agregado y conectado
- [ ] Migraciones aplicadas
- [ ] Superusuario creado
- [ ] Health check responde
- [ ] Frontend desplegado en Netlify
- [ ] Dominio configurado y SSL activo
- [ ] API redirects funcionan
- [ ] Tests passing en CI/CD
- [ ] Backup automático configurado
- [ ] Monitoring activo (Sentry opcional)

**¡Listo para producción! 🎉**
