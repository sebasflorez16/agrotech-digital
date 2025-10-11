# 🚀 Guía Rápida - Landing Page Agrotech Digital

## ⚡ Comandos Rápidos

### Desarrollo Local

```bash
# Iniciar servidor Django
cd /Users/sebastianflorez/Documents/agrotech-digital/agrotech-digital
python manage.py runserver

# Abrir en navegador
open http://localhost:8000/static/index.html

# Ver logs en tiempo real
tail -f logfile

# Generar favicons
python generate_favicon.py
```

### Edición de Archivos

```bash
# Editar HTML
code metrica/static/index.html

# Editar CSS
code metrica/static/css/landing.css

# Editar JavaScript
code metrica/static/js/landing.js

# Ver backup anterior
code metrica/static/index-old.html
```

### Debugging

```bash
# Verificar que archivos existen
ls -lah metrica/static/
ls -lah metrica/static/css/
ls -lah metrica/static/js/
ls -lah metrica/static/images/

# Verificar sintaxis Python
python -m py_compile generate_favicon.py

# Validar HTML (requiere html5validator)
html5validator --root metrica/static/ --match "*.html"

# Validar CSS (requiere csslint)
csslint metrica/static/css/landing.css
```

### Optimización

```bash
# Minificar CSS (requiere csso)
npx csso metrica/static/css/landing.css -o metrica/static/css/landing.min.css

# Minificar JavaScript (requiere terser)
npx terser metrica/static/js/landing.js -o metrica/static/js/landing.min.js -c -m

# Optimizar imágenes (requiere imagemagick)
mogrify -strip -quality 85 metrica/static/images/*.jpg
mogrify -strip metrica/static/images/*.png

# Ver tamaño de archivos
du -sh metrica/static/css/*
du -sh metrica/static/js/*
du -sh metrica/static/images/*
```

### Git

```bash
# Ver cambios
git status
git diff metrica/static/

# Commit landing page
git add metrica/static/index.html
git add metrica/static/css/landing.css
git add metrica/static/js/landing.js
git add LANDING_PAGE_README.md
git commit -m "feat: Rediseño landing page con tema neumórfico oscuro"

# Push a repositorio
git push origin main

# Crear backup tag
git tag -a v2.0.0-landing -m "Landing page profesional con diseño neumórfico"
git push origin v2.0.0-landing
```

### Testing

```bash
# Probar API desde terminal
curl https://agrotechcolombia.com/api/parcels/summary/

# Probar con autenticación
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://agrotechcolombia.com/api/parcels/summary/

# Lighthouse CI (requiere lighthouse)
lighthouse http://localhost:8000/static/index.html \
  --output html \
  --output-path ./lighthouse-report.html

# Test responsive (diferentes tamaños)
# Abre DevTools > Toggle Device Toolbar (Cmd+Shift+M)
```

### Deploy

```bash
# Netlify CLI
npm install -g netlify-cli
netlify login
netlify init
netlify deploy --prod

# Verificar deploy
netlify open
netlify status

# Railway (backend)
railway login
railway link
railway up
```

---

## 🎨 Personalización Rápida

### Cambiar Colores

```bash
# Editar CSS
code metrica/static/css/landing.css

# Buscar y reemplazar
# Líneas 14-23: Variables de color
# --brand-green: #4CAF50 → TU_COLOR
# --brand-orange: #FF6F00 → TU_COLOR
```

### Cambiar Textos

```bash
# Editar HTML
code metrica/static/index.html

# Secciones principales:
# - Línea 51: Hero title
# - Línea 53: Hero description
# - Línea 73: Features
# - Línea 142: Products
# - Línea 198: Stats
# - Línea 252: CTA
# - Línea 270: Footer
```

### Cambiar Logo

```bash
# 1. Copiar logo a carpeta images
cp /ruta/a/tu/logo.png metrica/static/images/

# 2. Actualizar referencia en HTML
code metrica/static/index.html
# Buscar: <img src="/static/images/logo.png"
# Reemplazar con tu nombre de archivo
```

---

## 🐛 Troubleshooting Rápido

### CSS no se aplica

```bash
# Hard reload
# Chrome/Edge: Cmd+Shift+R (Mac) o Ctrl+Shift+R (Windows)
# Safari: Cmd+Option+R
# Firefox: Ctrl+F5

# Verificar ruta
grep "landing.css" metrica/static/index.html
# Debe mostrar: <link rel="stylesheet" href="/static/css/landing.css">

# Collectstatic (producción)
python manage.py collectstatic --clear --noinput
```

### JavaScript no funciona

```bash
# Ver errores en consola del navegador
# Chrome/Edge/Firefox: F12 > Console

# Verificar sintaxis
node -c metrica/static/js/landing.js

# Ver si carga correctamente
grep "landing.js" metrica/static/index.html
# Debe mostrar: <script src="/static/js/landing.js"></script>
```

### Imágenes no cargan

```bash
# Verificar que existen
ls -l metrica/static/images/

# Verificar permisos
chmod 644 metrica/static/images/*

# Verificar rutas en HTML
grep "src=\"/static/images" metrica/static/index.html
```

### API no conecta

```bash
# Verificar backend está corriendo
curl https://agrotechcolombia.com/

# Ver logs del servidor
tail -f logfile

# Verificar CORS
grep CORS config/settings/base.py
# Debe tener: CORS_ALLOWED_ORIGINS = [...]
```

---

## 📊 Métricas de Performance

### Lighthouse Scores (Objetivo)

```
✅ Performance:     90+
✅ Accessibility:   95+
✅ Best Practices:  95+
✅ SEO:            100
```

### Tamaño de Archivos (Objetivo)

```
✅ HTML:    < 50 KB
✅ CSS:     < 50 KB
✅ JS:      < 30 KB
✅ Images:  < 200 KB (total)
```

### Tiempos de Carga (Objetivo)

```
✅ First Contentful Paint:  < 1.5s
✅ Largest Contentful Paint: < 2.5s
✅ Time to Interactive:      < 3.0s
✅ Cumulative Layout Shift:  < 0.1
```

---

## 🔗 Links Útiles

### Herramientas de Diseño
- [Neumorphism Generator](https://neumorphism.io/)
- [Coolors - Paleta de Colores](https://coolors.co/)
- [Google Fonts](https://fonts.google.com/)
- [Hero Patterns](https://heropatterns.com/)

### Herramientas de Desarrollo
- [VS Code](https://code.visualstudio.com/)
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/)
- [Lighthouse](https://developers.google.com/web/tools/lighthouse)
- [Can I Use](https://caniuse.com/)

### Optimización
- [TinyPNG - Compresión de Imágenes](https://tinypng.com/)
- [Real Favicon Generator](https://realfavicongenerator.net/)
- [CSS Minifier](https://cssminifier.com/)
- [JavaScript Minifier](https://javascript-minifier.com/)

### Testing
- [PageSpeed Insights](https://pagespeed.web.dev/)
- [GTmetrix](https://gtmetrix.com/)
- [WebPageTest](https://www.webpagetest.org/)
- [BrowserStack](https://www.browserstack.com/)

### Deploy
- [Netlify Docs](https://docs.netlify.com/)
- [Railway Docs](https://docs.railway.app/)
- [Vercel Docs](https://vercel.com/docs)

---

## 📱 Breakpoints Responsive

```css
/* Desktop Large: > 1200px */
/* Desktop: 969px - 1200px */
/* Tablet: 769px - 968px */
/* Mobile Large: 481px - 768px */
/* Mobile: < 480px */
```

### Probar en Diferentes Dispositivos

```bash
# Chrome DevTools
# 1. F12
# 2. Cmd+Shift+M (Toggle Device Toolbar)
# 3. Seleccionar dispositivo:
#    - iPhone 12 Pro (390x844)
#    - iPad Air (820x1180)
#    - Desktop (1920x1080)
```

---

## 🎯 Checklist Pre-Deploy

```bash
✅ Verificar colores de marca
✅ Actualizar textos e imágenes
✅ Probar todos los enlaces
✅ Probar menú móvil
✅ Probar formularios
✅ Verificar responsive (móvil/tablet/desktop)
✅ Optimizar imágenes
✅ Minificar CSS/JS (opcional)
✅ Configurar meta tags SEO
✅ Generar favicons
✅ Lighthouse score > 90
✅ Test en diferentes navegadores
✅ Configurar analytics (opcional)
✅ Backup de versión anterior
✅ Git commit y push
✅ Deploy a producción
✅ Verificar en URL de producción
```

---

## 💡 Tips Pro

### Performance
```bash
# Lazy loading para imágenes
<img src="image.jpg" loading="lazy">

# Preconnect a dominios externos
<link rel="preconnect" href="https://fonts.googleapis.com">

# Prefetch para páginas siguientes
<link rel="prefetch" href="/dashboard.html">
```

### SEO
```bash
# Sitemap.xml
# Crear en /static/sitemap.xml

# robots.txt
# Crear en /static/robots.txt
```

### Analytics
```bash
# Google Analytics
# Agregar GA_MEASUREMENT_ID en index.html

# Hotjar (Heatmaps)
# Agregar tracking code en <head>
```

### Seguridad
```bash
# Content Security Policy
# Agregar en settings.py:
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

---

**Última actualización**: Enero 2024  
**Versión**: 2.0.0
