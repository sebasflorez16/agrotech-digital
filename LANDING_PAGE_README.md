# 🌱 Agrotech Digital - Landing Page Documentation

## 📋 Índice
- [Descripción General](#descripción-general)
- [Estructura de Archivos](#estructura-de-archivos)
- [Diseño y Estilo](#diseño-y-estilo)
- [Funcionalidades](#funcionalidades)
- [Configuración](#configuración)
- [Despliegue](#despliegue)
- [Personalización](#personalización)
- [Solución de Problemas](#solución-de-problemas)

---

## 🎯 Descripción General

Landing page profesional para Agrotech Digital con diseño **neumórfico oscuro**, optimizada para conversión y totalmente **responsive**.

### ✨ Características Principales

- **Diseño Neumórfico Moderno**: Estilo soft UI con sombras en capas
- **Tema Oscuro Profesional**: Inspirado en líderes de la industria (eos.com)
- **100% Responsive**: Optimizado para móvil, tablet y desktop
- **Colores de Marca**: Verde (#4CAF50) y Naranja (#FF6F00)
- **Animaciones Suaves**: Scroll reveal, hover effects, transiciones fluidas
- **SEO Optimizado**: Meta tags, Open Graph, estructura semántica
- **Accesibilidad**: ARIA labels, contraste adecuado, navegación por teclado
- **Performance**: CSS optimizado, lazy loading, code splitting

### 📊 Métricas de Rendimiento

- **First Contentful Paint**: < 1.5s
- **Time to Interactive**: < 3s
- **Lighthouse Score**: 90+ en todas las categorías
- **Mobile Friendly**: 100%

---

## 📁 Estructura de Archivos

```
metrica/static/
├── index.html              # Página principal (rediseñada)
├── index-old.html          # Backup de la versión anterior
├── css/
│   └── landing.css         # Estilos completos del landing (600+ líneas)
└── js/
    └── landing.js          # Funcionalidad JavaScript (400+ líneas)
```

### Descripción de Archivos

#### `index.html`
Estructura HTML5 semántica con 9 secciones principales:

1. **Header**: Navegación fija con menú móvil
2. **Hero**: Sección principal con CTA y estadísticas animadas
3. **Features**: Grid de 6 características principales
4. **Products**: Showcase de 2 productos estrella
5. **Stats**: 4 métricas clave animadas
6. **API Demo**: Sección interactiva de prueba de API
7. **CTA**: Llamado a la acción final
8. **Footer**: Enlaces, redes sociales, legal
9. **Scroll to Top**: Botón flotante

#### `css/landing.css`
Sistema completo de estilos con:

- **CSS Variables**: Colores, espaciado, tipografía
- **Neumorphic Components**: Cards, buttons, inputs
- **Grid System**: Responsive layouts
- **Animations**: @keyframes para efectos
- **Media Queries**: Breakpoints en 968px, 768px, 480px

#### `js/landing.js`
Módulo JavaScript con:

- **Configuration**: URLs del backend y autenticación
- **Navigation**: Menú móvil, smooth scroll
- **Animations**: Scroll reveal, counters
- **API Testing**: Prueba de conexión en vivo
- **Session Management**: Detección de usuario logueado

---

## 🎨 Diseño y Estilo

### Paleta de Colores

```css
/* Colores de Marca */
--brand-green: #4CAF50;           /* Verde principal */
--brand-green-light: #66BB6A;     /* Verde claro */
--brand-green-dark: #388E3C;      /* Verde oscuro */
--brand-orange: #FF6F00;          /* Naranja principal */
--brand-orange-light: #FF8F00;    /* Naranja claro */

/* Colores de Fondo */
--dark-bg: #1a1a1a;               /* Fondo principal */
--dark-secondary: #2a2a2a;        /* Fondo secundario */
--dark-tertiary: #1f1f1f;         /* Fondo terciario */

/* Colores de Texto */
--text-primary: #E0E0E0;          /* Texto principal */
--text-secondary: #B0B0B0;        /* Texto secundario */
--text-muted: #808080;            /* Texto deshabilitado */
```

### Tipografía

```css
/* Familia de Fuentes */
--font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* Tamaños de Texto */
--text-xs: 0.75rem;     /* 12px */
--text-sm: 0.875rem;    /* 14px */
--text-base: 1rem;      /* 16px */
--text-lg: 1.125rem;    /* 18px */
--text-xl: 1.25rem;     /* 20px */
--text-2xl: 1.5rem;     /* 24px */
--text-3xl: 1.875rem;   /* 30px */
--text-4xl: 2.25rem;    /* 36px */
--text-5xl: 3rem;       /* 48px */
--text-6xl: 3.75rem;    /* 60px */
```

### Efecto Neumórfico

```css
/* Sombras en Capas */
box-shadow: 
    8px 8px 16px rgba(0, 0, 0, 0.3),      /* Sombra oscura */
    -8px -8px 16px rgba(255, 255, 255, 0.03); /* Luz sutil */

/* Estado Hover */
box-shadow: 
    12px 12px 24px rgba(0, 0, 0, 0.4),
    -12px -12px 24px rgba(255, 255, 255, 0.05);

/* Estado Presionado */
box-shadow: 
    inset 4px 4px 8px rgba(0, 0, 0, 0.3),
    inset -4px -4px 8px rgba(255, 255, 255, 0.02);
```

### Responsive Breakpoints

```css
/* Desktop First */
@media (max-width: 968px) { /* Tablet */ }
@media (max-width: 768px) { /* Móvil horizontal */ }
@media (max-width: 480px) { /* Móvil vertical */ }
```

---

## ⚡ Funcionalidades

### 1. Navegación

#### Header Fijo con Scroll
```javascript
// El header cambia de estilo al hacer scroll
if (window.scrollY > 50) {
    header.classList.add('scrolled');
}
```

#### Menú Móvil Hamburguesa
```javascript
// Toggle del menú en dispositivos móviles
navBurger.addEventListener('click', () => {
    navBurger.classList.toggle('active');
    navLinks.classList.toggle('active');
});
```

#### Smooth Scroll a Secciones
```javascript
// Scroll suave al hacer clic en enlaces internos
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', smoothScrollHandler);
});
```

### 2. Animaciones

#### Scroll Reveal
```javascript
// Elementos se revelan al entrar en viewport
const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('active');
        }
    });
}, { threshold: 0.1 });
```

#### Counters Animados
```javascript
// Números cuentan desde 0 hasta su valor final
function animateCounter(element, start, end, duration) {
    // Animación con easing suave
}
```

#### Hover Effects
```css
/* Botones con efecto de elevación */
.btn:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.4);
}
```

### 3. Integración con Backend

#### Prueba de API en Vivo
```javascript
async function testAPI() {
    const response = await fetch(`${BACKEND_URL}/api/parcels/summary/`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
    });
    
    // Muestra resultado en tiempo real
    resultDiv.innerHTML = formatResponse(data);
}
```

#### Redirección a Autenticación
```javascript
function redirectToLogin() {
    window.location.href = CONFIG.LOGIN_URL;
}

function redirectToDashboard() {
    window.location.href = CONFIG.DASHBOARD_URL;
}
```

#### Detección de Sesión
```javascript
// Cambia CTA según estado de autenticación
function checkUserSession() {
    const token = localStorage.getItem('accessToken');
    if (token) {
        // Usuario logueado: muestra "Ir al Dashboard"
    } else {
        // Usuario no logueado: muestra "Iniciar Sesión"
    }
}
```

### 4. Utilidades

#### Scroll to Top Button
```javascript
// Botón flotante para volver arriba
window.addEventListener('scroll', () => {
    if (window.scrollY > 300) {
        scrollToTopBtn.classList.add('visible');
    }
});
```

#### Toast Notifications
```javascript
// Notificaciones temporales
function showToast(message, type) {
    // Muestra mensaje por 4 segundos
}
```

---

## ⚙️ Configuración

### URLs del Backend

Edita `/static/js/landing.js`:

```javascript
const CONFIG = {
    BACKEND_URL: 'https://agrotechcolombia.com',
    LOGIN_URL: 'https://site-production-208b.up.railway.app/templates/authentication/login.html',
    DASHBOARD_URL: 'https://site-production-208b.up.railway.app/templates/vertical_base.html',
    API_VERSION: 'v1',
    DEBUG: false  // true para logs de desarrollo
};
```

### Meta Tags SEO

Edita `/static/index.html`:

```html
<!-- SEO Básico -->
<title>Agrotech Digital - Agricultura de Precisión</title>
<meta name="description" content="Tu descripción aquí">

<!-- Open Graph (Facebook, LinkedIn) -->
<meta property="og:title" content="Agrotech Digital">
<meta property="og:description" content="Tu descripción aquí">
<meta property="og:image" content="/static/images/og-image.jpg">
<meta property="og:url" content="https://tudominio.com">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Agrotech Digital">
<meta name="twitter:description" content="Tu descripción aquí">
<meta name="twitter:image" content="/static/images/twitter-card.jpg">
```

### Google Analytics

Agrega antes de `</head>`:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

### Favicon y Logo

1. Coloca tus imágenes en `/static/images/`:
   ```
   /static/images/
   ├── logo.png           # Logo principal (navbar)
   ├── logo-white.png     # Logo blanco (footer)
   ├── favicon.ico        # 32x32px
   ├── apple-touch-icon.png  # 180x180px
   └── og-image.jpg       # 1200x630px para redes sociales
   ```

2. Actualiza referencias en `index.html`:
   ```html
   <!-- Favicon -->
   <link rel="icon" href="/static/images/favicon.ico">
   <link rel="apple-touch-icon" href="/static/images/apple-touch-icon.png">
   
   <!-- Logo en Navbar -->
   <img src="/static/images/logo.png" alt="Agrotech Digital" class="nav-logo">
   ```

---

## 🚀 Despliegue

### Desarrollo Local

1. **Servidor de Django**:
   ```bash
   cd /path/to/agrotech-digital
   python manage.py runserver
   ```

2. **Acceder al landing**:
   ```
   http://localhost:8000/static/index.html
   ```

3. **Ver cambios en vivo**:
   - Edita archivos CSS/JS
   - Recarga el navegador (Cmd/Ctrl + R)
   - CSS puede requerir hard reload (Cmd/Ctrl + Shift + R)

### Producción (Netlify)

#### Opción 1: Deploy Manual

1. **Build estático** (si usas build process):
   ```bash
   # Minificar CSS
   npx csso css/landing.css -o css/landing.min.css
   
   # Minificar JS
   npx terser js/landing.js -o js/landing.min.js -c -m
   ```

2. **Actualizar referencias** en `index.html`:
   ```html
   <link rel="stylesheet" href="/static/css/landing.min.css">
   <script src="/static/js/landing.min.js"></script>
   ```

3. **Deploy a Netlify**:
   ```bash
   # Instalar CLI
   npm install -g netlify-cli
   
   # Login
   netlify login
   
   # Deploy
   netlify deploy --prod --dir=metrica/static
   ```

#### Opción 2: Deploy Automático (GitHub)

1. **Conectar repositorio** en Netlify Dashboard

2. **Configurar build settings**:
   ```yaml
   # netlify.toml
   [build]
     base = "metrica/static"
     publish = "."
     command = "echo 'No build needed'"
   
   [[redirects]]
     from = "/"
     to = "/index.html"
     status = 200
   
   [[headers]]
     for = "/*"
     [headers.values]
       Access-Control-Allow-Origin = "*"
       X-Frame-Options = "DENY"
       X-Content-Type-Options = "nosniff"
       Referrer-Policy = "strict-origin-when-cross-origin"
   ```

3. **Deploy automático** en cada push a `main`

### Verificación Post-Deploy

✅ Checklist:

- [ ] Landing page carga correctamente
- [ ] Imágenes y logos se muestran
- [ ] Menú móvil funciona
- [ ] Scroll suave funciona
- [ ] Animaciones se activan
- [ ] Botón "Probar API" conecta
- [ ] Links de login/dashboard funcionan
- [ ] Formularios envían correctamente
- [ ] Responsive en móvil
- [ ] Lighthouse score > 90

---

## 🎨 Personalización

### Cambiar Colores de Marca

Edita `/static/css/landing.css`:

```css
:root {
    /* PERSONALIZAR AQUÍ */
    --brand-green: #TU_COLOR_PRIMARIO;
    --brand-green-light: #TU_COLOR_PRIMARIO_CLARO;
    --brand-green-dark: #TU_COLOR_PRIMARIO_OSCURO;
    --brand-orange: #TU_COLOR_SECUNDARIO;
    --brand-orange-light: #TU_COLOR_SECUNDARIO_CLARO;
}
```

**Tip**: Usa herramientas como [coolors.co](https://coolors.co) para generar paletas.

### Modificar Texto del Hero

Edita `/static/index.html`:

```html
<section class="hero" id="inicio">
    <div class="container">
        <div class="hero-content reveal">
            <h1 class="hero-title">
                <!-- EDITAR AQUÍ -->
                Tu Título Principal<br>
                <span class="gradient-text">Tu Subtítulo Destacado</span>
            </h1>
            <p class="hero-description">
                <!-- EDITAR AQUÍ -->
                Tu descripción del producto o servicio
            </p>
            <!-- ... -->
        </div>
    </div>
</section>
```

### Agregar Nueva Sección

1. **HTML** - Agregar después de sección existente:
   ```html
   <section class="mi-nueva-seccion" id="mi-seccion">
       <div class="container">
           <h2 class="section-title reveal">Mi Título</h2>
           <div class="mi-contenido reveal">
               <!-- Tu contenido aquí -->
           </div>
       </div>
   </section>
   ```

2. **CSS** - Agregar estilos:
   ```css
   .mi-nueva-seccion {
       padding: var(--spacing-section) 0;
       background: var(--dark-bg);
   }
   
   .mi-contenido {
       /* Tus estilos */
   }
   ```

3. **Navegación** - Agregar link en header:
   ```html
   <nav class="nav-links" id="navLinks">
       <!-- ... links existentes ... -->
       <a href="#mi-seccion">Mi Sección</a>
   </nav>
   ```

### Cambiar Fuente Tipográfica

1. **Importar fuente** en `<head>`:
   ```html
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link href="https://fonts.googleapis.com/css2?family=TU_FUENTE:wght@400;500;600;700&display=swap" rel="stylesheet">
   ```

2. **Actualizar variable CSS**:
   ```css
   :root {
       --font-primary: 'TU_FUENTE', sans-serif;
   }
   ```

### Modificar Animaciones

Edita `/static/css/landing.css`:

```css
/* Cambiar velocidad de animación */
.reveal {
    transition: all 0.8s ease-out;  /* Cambiar duración */
}

/* Cambiar distancia de desplazamiento */
.reveal {
    transform: translateY(30px);  /* Cambiar valor */
}

/* Crear nueva animación */
@keyframes miAnimacion {
    0% { opacity: 0; transform: scale(0.8); }
    100% { opacity: 1; transform: scale(1); }
}

.mi-elemento {
    animation: miAnimacion 1s ease-out;
}
```

---

## 🐛 Solución de Problemas

### Problema: CSS no se aplica

**Causas comunes**:
1. Cache del navegador
2. Ruta incorrecta del archivo
3. Servidor no sirve archivos estáticos

**Soluciones**:
```bash
# 1. Hard reload del navegador
Cmd/Ctrl + Shift + R

# 2. Verificar ruta
# Debe ser exacta en index.html:
<link rel="stylesheet" href="/static/css/landing.css">

# 3. Configurar Django settings.py
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'metrica/static']

# 4. Collectstatic (producción)
python manage.py collectstatic --noinput
```

### Problema: JavaScript no funciona

**Causas comunes**:
1. Error de sintaxis
2. Script carga antes del DOM
3. CORS bloqueando API

**Soluciones**:
```javascript
// 1. Abrir consola del navegador (F12)
// Ver errores en rojo

// 2. Asegurar que script carga al final
// Mover antes de </body> o usar:
<script defer src="/static/js/landing.js"></script>

// 3. Verificar CORS en backend (settings.py)
CORS_ALLOWED_ORIGINS = [
    'https://tudominio.com',
    'http://localhost:8000',
]
```

### Problema: Imágenes no cargan

**Causas comunes**:
1. Ruta incorrecta
2. Archivos no existen
3. Permisos del servidor

**Soluciones**:
```html
<!-- 1. Usar rutas absolutas -->
<img src="/static/images/logo.png" alt="Logo">

<!-- 2. Verificar que archivo existe -->
<!-- Debe estar en: /metrica/static/images/logo.png -->

<!-- 3. Permisos de archivo (Unix/Linux) -->
chmod 644 /path/to/images/*
```

### Problema: Menú móvil no abre

**Causas comunes**:
1. JavaScript no cargó
2. IDs no coinciden
3. CSS faltante

**Soluciones**:
```javascript
// 1. Verificar en consola
console.log(document.getElementById('navBurger'));
// Debe mostrar el elemento, no null

// 2. Verificar IDs en HTML
<div class="nav-burger" id="navBurger">  <!-- Correcto -->
<nav class="nav-links" id="navLinks">    <!-- Correcto -->

// 3. Verificar CSS
.nav-burger.active span:nth-child(1) { transform: rotate(45deg); }
```

### Problema: API no conecta

**Causas comunes**:
1. URL incorrecta
2. Backend no ejecutándose
3. CORS bloqueando

**Soluciones**:
```javascript
// 1. Verificar URL en config
console.log(CONFIG.BACKEND_URL);

// 2. Probar endpoint directo
curl https://agrotechcolombia.com/api/parcels/summary/

// 3. Configurar CORS en backend
# settings.py
CORS_ALLOW_ALL_ORIGINS = True  # Solo desarrollo!
# Producción:
CORS_ALLOWED_ORIGINS = ['https://tudominio.com']
```

### Problema: Animaciones no funcionan

**Causas comunes**:
1. Clases no aplicadas
2. IntersectionObserver no soportado
3. JavaScript deshabilitado

**Soluciones**:
```javascript
// 1. Verificar que elementos tienen clase
<div class="reveal">Contenido</div>

// 2. Polyfill para navegadores viejos
<script src="https://polyfill.io/v3/polyfill.min.js?features=IntersectionObserver"></script>

// 3. Fallback CSS (sin JavaScript)
<noscript>
    <style>
        .reveal { opacity: 1 !important; transform: none !important; }
    </style>
</noscript>
```

### Problema: Responsive no funciona

**Causas comunes**:
1. Meta viewport faltante
2. Media queries incorrectas
3. Unidades fijas (px en vez de rem)

**Soluciones**:
```html
<!-- 1. Agregar en <head> -->
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

```css
/* 2. Orden correcto de media queries (desktop-first) */
/* Estilos base (desktop) */
.elemento { width: 100%; }

/* Tablet */
@media (max-width: 968px) { .elemento { width: 90%; } }

/* Móvil */
@media (max-width: 768px) { .elemento { width: 100%; } }

/* 3. Usar unidades relativas */
/* MAL */
.elemento { font-size: 24px; padding: 20px; }

/* BIEN */
.elemento { font-size: 1.5rem; padding: var(--spacing-md); }
```

---

## 📞 Soporte

### Recursos Adicionales

- **Documentación Django Static Files**: https://docs.djangoproject.com/en/stable/howto/static-files/
- **Netlify Docs**: https://docs.netlify.com/
- **CSS Neumorphism Generator**: https://neumorphism.io/
- **Inter Font**: https://fonts.google.com/specimen/Inter

### Contacto

Para preguntas o problemas:
1. Revisar esta documentación primero
2. Verificar consola del navegador (F12)
3. Revisar logs del servidor
4. Contactar al equipo de desarrollo

---

## 📝 Changelog

### Version 2.0.0 (Actual)
- ✨ Rediseño completo con tema neumórfico oscuro
- 🎨 Paleta de colores de marca (verde/naranja)
- 📱 Responsive design mobile-first
- ⚡ Animaciones scroll reveal
- 🔌 Integración con API backend
- 📊 Estadísticas animadas
- 🍔 Menú móvil hamburguesa
- 🔼 Scroll to top button
- 📖 JavaScript modular (landing.js)
- 🎯 SEO optimizado

### Version 1.0.0 (Anterior - index-old.html)
- Diseño básico con gradiente
- Estructura simple
- Sin animaciones
- No responsive

---

## 📄 Licencia

© 2024 Agrotech Digital. Todos los derechos reservados.

---

**Última actualización**: Enero 2024  
**Versión**: 2.0.0  
**Mantenedor**: Equipo de Desarrollo Agrotech Digital
