# 🌍 Configuración de Entornos - AgroTech Digital

## 📋 Resumen

El sistema **detecta automáticamente** si está corriendo en:
- **Local** (localhost:8080)
- **Staging** (staging.agrotechcolombia.com)
- **Producción** (agrotechcolombia.netlify.app)

## 🔧 Configuración Automática

### Archivo Principal: `metrica/static/js/config.js`

Este archivo se carga **primero** en todas las páginas y configura:

```javascript
window.AGROTECH_CONFIG = {
    API_BASE: 'http://localhost:8000' o 'https://agrotechcolombia.com',
    STATIC_BASE: 'http://localhost:8080' o 'https://agrotechcolombia.netlify.app',
    ENV: { IS_LOCALHOST, IS_DEVELOPMENT, IS_STAGING, IS_PRODUCTION },
    ENDPOINTS: { ... }
}
```

### Uso en JavaScript

```javascript
// Opción 1: Usar la configuración global
const apiUrl = window.AGROTECH_CONFIG.buildUrl('/api/parcels/');

// Opción 2: Usar shortcuts
const apiUrl = window.AG.API_BASE + '/api/parcels/';

// Opción 3: Usar endpoints predefinidos
const loginUrl = window.AG.buildUrl(window.AG.ENDPOINTS.LOGIN);
```

## 🏗️ Estructura de Servidores

### Desarrollo Local

```
Frontend: http://localhost:8080  (python3 -m http.server)
Backend:  http://localhost:8000  (Django runserver)
Database: localhost:5432         (PostgreSQL)
```

### Producción

```
Frontend: https://agrotechcolombia.netlify.app  (Netlify)
Backend:  https://agrotechcolombia.com          (Railway)
Database: PostgreSQL en Railway
```

## 📁 Archivos Actualizados

### ✅ JavaScript con detección automática:
- `metrica/static/js/config.js` - **Configuración global**
- `metrica/static/js/utils/api-utils.js` - Helper de URLs
- `metrica/static/js/dashboard-liquid.js` - Dashboard principal
- `metrica/static/js/billing-liquid.js` - Facturación
- `metrica/static/js/login-liquid.js` - Autenticación
- `metrica/static/js/dashboard.js` - Dashboard antiguo
- `metrica/static/js/user-profile.js` - Perfil de usuario
- `metrica/static/js/login.js` - Login antiguo
- `metrica/static/js/dashboarddatos.js` - Datos del dashboard
- `metrica/static/js/landing.js` - Landing page

### 📄 HTML que incluyen config.js:
- `metrica/static/templates/dashboard.html`
- `metrica/static/templates/billing.html`
- `metrica/static/templates/authentication/login.html`

## 🚀 Workflow de Desarrollo → Producción

### 1️⃣ Desarrollo Local

```bash
# Terminal 1: Backend Django
cd agrotech-digital
conda activate agro-rest
DJANGO_SECRET_KEY='test-key' DJANGO_SETTINGS_MODULE='config.settings.local' python manage.py runserver 0.0.0.0:8000

# Terminal 2: Frontend Estático
cd metrica/static
python3 -m http.server 8080
```

### 2️⃣ Testing Local
- Abre `http://localhost:8080/templates/authentication/login.html`
- El sistema detecta automáticamente que está en localhost
- Todas las APIs apuntan a `http://localhost:8000`

### 3️⃣ Deploy a Producción

#### Backend (Railway):
```bash
git add .
git commit -m "feat: nueva funcionalidad"
git push origin main
# Railway detecta cambios y hace deploy automático
```

#### Frontend (Netlify):
```bash
# Netlify está conectado al repo, hace deploy automático
# O manualmente:
netlify deploy --prod --dir=metrica/static
```

### 4️⃣ Producción Automática
- Frontend en Netlify detecta que NO está en localhost
- Todas las APIs apuntan automáticamente a `https://agrotechcolombia.com`
- **¡Sin cambios de código necesarios!**

## 🔍 Debugging

### Verificar configuración actual:
```javascript
// En la consola del navegador:
console.log(window.AGROTECH_CONFIG);
console.log('Entorno:', window.AG.ENV.NAME);
console.log('API Base:', window.AG.API_BASE);
```

### Variables importantes:
```javascript
window.location.hostname  // 'localhost' o 'agrotechcolombia.netlify.app'
window.AG.ENV.IS_LOCALHOST  // true/false
window.AG.DEBUG  // true en local, false en prod
```

## ⚙️ Configuración de CORS

### Django Local (`config/settings/local.py`):
```python
CORS_ALLOW_ALL_ORIGINS = True  # Solo para desarrollo
CORS_ALLOW_CREDENTIALS = True
```

### Django Producción (`config/settings/production.py`):
```python
CORS_ALLOWED_ORIGINS = [
    'https://agrotechcolombia.netlify.app',
]
CORS_ALLOW_CREDENTIALS = True
```

## 📝 Checklist para Nuevas Features

Cuando agregues nueva funcionalidad:

- [ ] Usar `window.AG.API_BASE` en lugar de URLs hardcodeadas
- [ ] Probar en local (localhost:8080)
- [ ] Verificar que las APIs llamen a localhost:8000
- [ ] Commit y push a GitHub
- [ ] Verificar deploy automático en Netlify y Railway
- [ ] Probar en producción que las APIs apunten a agrotechcolombia.com

## 🛡️ Ventajas de Esta Configuración

✅ **Sin duplicación de código** - Un solo código para todos los entornos  
✅ **Detección automática** - No hay que cambiar variables manualmente  
✅ **Debugging fácil** - Logs solo en desarrollo  
✅ **Configuración centralizada** - Un solo archivo (config.js)  
✅ **Escalable** - Fácil agregar staging, QA, etc.  
✅ **Type-safe** - Endpoints predefinidos evitan typos  

## 🔄 Próximos Pasos

1. Agregar ambiente de **staging** para testing antes de producción
2. Configurar **variables de entorno** en Netlify/Railway
3. Agregar **feature flags** para activar/desactivar funcionalidades
4. Implementar **rollback automático** si el deploy falla

---

**Última actualización:** 5 de febrero de 2026  
**Mantenido por:** Equipo AgroTech Digital
