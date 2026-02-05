# 🍎 Frontend Liquid Glass - AgroTech Digital

Sistema de diseño inspirado en Apple con glassmorphism para la plataforma AgroTech.

## 📁 Estructura del Frontend

```
metrica/static/
├── css/
│   ├── liquid-glass-system.css    ← Sistema de diseño principal
│   └── ...otros archivos legacy
├── js/
│   ├── dashboard-liquid.js        ← Dashboard principal
│   ├── billing-liquid.js          ← Facturación y uso
│   └── ...otros módulos
├── templates/                      ← NUEVAS PÁGINAS HTML PURAS
│   ├── dashboard.html             ← Dashboard principal ✨
│   ├── billing.html               ← Facturación ✨
│   ├── usage.html                 ← Uso detallado (pendiente)
│   ├── parcels.html               ← Parcelas (pendiente)
│   ├── crops.html                 ← Cultivos (pendiente)
│   ├── employees.html             ← Empleados (pendiente)
│   └── authentication/
│       └── login.html             ← Login (pendiente migración)
├── images/
├── fonts/
├── libs/
└── index.html                      ← Landing page
```

## 🎨 Sistema de Diseño: Liquid Glass

### Características

- **Glassmorphism**: Efectos de vidrio translúcido con `backdrop-filter: blur()`
- **Paleta AgroTech**: Verde #2FB344 + neutrales Apple
- **Tipografía**: SF Pro Display / Inter (system fonts)
- **Componentes**: Cards, buttons, inputs con estilo unificado

### Variables CSS Principales

```css
--agrotech-primary: #2FB344
--glass-white: rgba(255, 255, 255, 0.7)
--glass-blur: blur(40px)
--radius-lg: 24px
--shadow-glass: 0 8px 32px rgba(31, 38, 135, 0.15)
```

### Componentes Disponibles

#### Glass Card
```html
<div class="glass-card">
    <!-- Contenido -->
</div>
```

#### Botón Glass Primary
```html
<button class="btn-glass-primary">
    <i class="ti ti-icon"></i>
    Texto
</button>
```

#### Stat Card
```html
<div class="stat-card">
    <div class="stat-value">150</div>
    <div class="stat-label">Parcelas</div>
</div>
```

#### Progress Bar
```html
<div class="progress-glass">
    <div class="progress-glass-bar" style="width: 75%"></div>
</div>
```

#### Alert Badge
```html
<span class="alert-badge success">✅ Todo bien</span>
<span class="alert-badge warning">⚠️ Advertencia</span>
<span class="alert-badge danger">🚫 Excedido</span>
```

## 🚀 Migración de Templates Legacy

### ⚠️ IMPORTANTE: Separación de Django Templates

El proyecto **YA NO USA** Django Templates ({% extends %}, {% load static %}).

**Antes (Django Monolítico):**
```django
<!-- metrica/templates/dashboard.html -->
{% extends 'base.html' %}
{% load static %}
```

**Ahora (REST API + Frontend Estático):**
```html
<!-- metrica/static/templates/dashboard.html -->
<!DOCTYPE html>
<html>
<!-- HTML puro, sin Django tags -->
```

### Proceso de Migración

1. ✅ **Dashboard** - Migrado a `templates/dashboard.html`
2. ✅ **Billing** - Migrado a `templates/billing.html`
3. ⏳ **Login** - Pendiente migración
4. ⏳ **Parcelas** - Pendiente migración
5. ⏳ **Cultivos** - Pendiente migración
6. ⏳ **Empleados** - Pendiente migración
7. ⏳ **Inventario** - Pendiente migración

## 📡 Integración con Backend REST

### Configuración de API

```javascript
const API_BASE_URL = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://agrotechcolombia.com';
```

### Autenticación

```javascript
function getAuthToken() {
    return localStorage.getItem('accessToken');
}

function getHeaders() {
    return {
        'Authorization': `Bearer ${getAuthToken()}`,
        'Content-Type': 'application/json'
    };
}
```

### Ejemplo de Request

```javascript
const response = await fetch(`${API_BASE_URL}/api/billing/usage/dashboard/`, {
    headers: getHeaders()
});
const data = await response.json();
```

## 🌐 Despliegue en Netlify

### Configuración (netlify.toml)

```toml
[build]
  publish = "metrica/static"

[[redirects]]
  from = "/api/*"
  to = "https://agrotechcolombia.com/api/:splat"
  status = 200
  force = true
```

### Estructura de URLs

```
Landing:     https://agrotechcolombia.netlify.app/
Dashboard:   https://agrotechcolombia.netlify.app/templates/dashboard.html
Billing:     https://agrotechcolombia.netlify.app/templates/billing.html
Login:       https://agrotechcolombia.netlify.app/templates/authentication/login.html
```

## 🎯 Próximos Pasos

### Fase 1: Componentes Core (Completado ✅)
- ✅ Sistema de diseño Liquid Glass
- ✅ Dashboard principal
- ✅ Billing & Usage

### Fase 2: Migración de Módulos (En progreso ⏳)
- ⏳ Login con nuevo diseño
- ⏳ Parcelas (reutilizar lógica de `parcels-dashboard.html`)
- ⏳ Cultivos
- ⏳ Empleados
- ⏳ Inventario

### Fase 3: Limpieza (Pendiente)
- Eliminar `metrica/templates/` (Django templates legacy)
- Consolidar CSS (eliminar archivos duplicados)
- Optimizar JavaScript (bundling)

## 📱 Responsive Design

Todos los componentes son responsive por defecto:

- **Desktop**: Sidebar fijo, layout de 2 columnas
- **Tablet**: Layout adaptativo
- **Mobile**: Sidebar colapsable, layout de 1 columna

## 🔧 Testing Local

```bash
# Desde metrica/static/
python -m http.server 8080

# Abrir en navegador:
http://localhost:8080/templates/dashboard.html
```

## 📝 Convenciones

- **Archivos HTML**: kebab-case (`dashboard.html`, `billing.html`)
- **Archivos JS**: kebab-case con sufijo (`dashboard-liquid.js`)
- **Clases CSS**: kebab-case con prefijo (`glass-card`, `btn-glass`)
- **IDs**: camelCase (`metricsGrid`, `invoiceCard`)

## 🎨 Paleta de Colores

```
Verde Principal:    #2FB344 (Primary)
Verde Oscuro:       #1E7A2E (Primary Dark)
Verde Claro:        #4ADE5E (Primary Light)
Naranja Acento:     #FF9F0A (Accent)

Texto Principal:    #1D1D1F
Texto Secundario:   #6E6E73
Texto Terciario:    #86868B

Background:         #F5F5F7
Glass White:        rgba(255, 255, 255, 0.7)
Glass Border:       rgba(255, 255, 255, 0.5)
```

## 📚 Recursos

- [Tabler Icons](https://tabler-icons.io/)
- [Chart.js](https://www.chartjs.org/)
- [Glassmorphism Generator](https://hype4.academy/tools/glassmorphism-generator)

---

**Última actualización**: 5 de febrero de 2026
**Diseño**: Apple Liquid Glass System
**Framework**: Vanilla JS + REST API
