# 🎨 Guía de Integración de Logos - Agrotech Digital

## 📋 Resumen

Esta guía te ayudará a integrar tus logos reales en el landing page, reemplazando los placeholders actuales.

---

## 📁 Estructura de Carpeta de Imágenes

Crea la siguiente estructura:

```
metrica/static/images/
├── logo.png                    # Logo principal para navbar (fondo oscuro)
├── logo-white.png              # Logo blanco para footer (opcional)
├── logo-icon.png               # Icono solo (para favicon base)
├── favicon.ico                 # 32x32px
├── apple-touch-icon.png        # 180x180px para iOS
├── android-chrome-192x192.png  # 192x192px para Android
├── android-chrome-512x512.png  # 512x512px para Android
├── og-image.jpg                # 1200x630px para redes sociales
└── twitter-card.jpg            # 1200x675px para Twitter
```

---

## 🖼️ Especificaciones de Imágenes

### 1. Logo Principal (navbar)

**Archivo**: `logo.png`

**Especificaciones**:
- **Dimensiones**: Ancho máximo 200px, Alto 50-60px
- **Formato**: PNG con transparencia
- **Fondo**: Transparente (se verá sobre fondo oscuro)
- **Colores**: Verde (#4CAF50) y/o Naranja (#FF6F00)
- **Resolución**: @2x (400px ancho) para pantallas Retina

**Ejemplo de exportación desde diseño**:
```bash
# Si tienes SVG original
inkscape logo.svg --export-png=logo.png --export-width=200

# Si tienes imagen grande
convert logo-large.png -resize 200x logo.png
```

---

### 2. Logo Footer (opcional)

**Archivo**: `logo-white.png`

**Especificaciones**:
- **Dimensiones**: Ancho máximo 180px, Alto 45-55px
- **Formato**: PNG con transparencia
- **Colores**: Versión monocromática blanca o en colores de marca
- **Uso**: Se muestra en el footer sobre fondo oscuro

---

### 3. Favicons

Tienes **3 opciones**:

#### Opción A: Usar el script automático

```bash
# 1. Instalar Pillow
pip install Pillow

# 2. Ejecutar generador
python generate_favicon.py

# 3. Revisar salida
ls -lah metrica/static/images/
```

El script genera:
- ✅ favicon.ico (32x32)
- ✅ apple-touch-icon.png (180x180)
- ✅ android-chrome-192x192.png (192x192)
- ✅ android-chrome-512x512.png (512x512)
- ✅ og-image.jpg (1200x630)

#### Opción B: Usar Real Favicon Generator (Recomendado)

1. **Visita**: https://realfavicongenerator.net/

2. **Sube tu logo** (mínimo 260x260px, idealmente 512x512px)

3. **Configura opciones**:
   - iOS: Ajustar colores de fondo
   - Android: Nombre "Agrotech Digital", color tema #4CAF50
   - Windows: Tile color #1a1a1a
   - macOS Safari: Color tema #4CAF50

4. **Descarga el paquete** generado

5. **Extrae archivos** a `metrica/static/images/`

6. **Copia el código HTML** proporcionado y reemplaza en `index.html`

#### Opción C: Crear manualmente con diseño gráfico

Si usas **Figma/Sketch/Adobe XD**:

1. **Crea un artboard** de 512x512px
2. **Diseña tu icono** centrado
3. **Exporta múltiples tamaños**:
   - 32x32 → favicon.ico
   - 180x180 → apple-touch-icon.png
   - 192x192 → android-chrome-192x192.png
   - 512x512 → android-chrome-512x512.png

---

### 4. Open Graph Image (Redes Sociales)

**Archivo**: `og-image.jpg`

**Especificaciones**:
- **Dimensiones**: 1200x630px (exacto)
- **Formato**: JPG o PNG
- **Peso máximo**: 8MB (idealmente < 300KB)
- **Área segura**: Evita texto/logos en bordes (100px de margen)
- **Contenido sugerido**:
  - Logo de Agrotech
  - Título: "Agrotech Digital"
  - Subtítulo: "Agricultura de Precisión"
  - Fondo: Gradiente verde/oscuro

**Herramientas recomendadas**:
- [Canva](https://www.canva.com/) - Template "Facebook Post"
- [Figma](https://www.figma.com/) - Artboard 1200x630
- [Photoshop](https://www.adobe.com/photoshop) - Nuevo archivo 1200x630

**Vista previa**:
- [Facebook Debugger](https://developers.facebook.com/tools/debug/)
- [Twitter Card Validator](https://cards-dev.twitter.com/validator)
- [LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/)

---

## 🔧 Pasos de Integración

### Paso 1: Preparar tus imágenes

```bash
# Crear carpeta si no existe
mkdir -p metrica/static/images

# Copiar tus logos (reemplaza con tus rutas reales)
cp /ruta/a/tu/logo.png metrica/static/images/
cp /ruta/a/tu/logo-white.png metrica/static/images/

# Opcionalmente, optimizar imágenes
# Requiere imagemagick: brew install imagemagick
mogrify -strip -quality 85 metrica/static/images/*.png
mogrify -strip -quality 90 metrica/static/images/*.jpg
```

---

### Paso 2: Generar favicons

**Opción A - Script automático**:
```bash
pip install Pillow
python generate_favicon.py
```

**Opción B - Real Favicon Generator**:
1. Visita: https://realfavicongenerator.net/
2. Sube logo de 512x512px
3. Descarga paquete
4. Extrae a `metrica/static/images/`

---

### Paso 3: Actualizar referencias en HTML

Edita `metrica/static/index.html`:

```html
<!-- 1. Actualizar favicon en <head> (líneas 7-13) -->
<link rel="icon" type="image/x-icon" href="/static/images/favicon.ico">
<link rel="apple-touch-icon" sizes="180x180" href="/static/images/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="32x32" href="/static/images/favicon.ico">
<link rel="icon" type="image/png" sizes="16x16" href="/static/images/favicon.ico">
<link rel="manifest" href="/static/images/site.webmanifest">

<!-- 2. Actualizar Open Graph (líneas 21-23) -->
<meta property="og:image" content="https://tudominio.com/static/images/og-image.jpg">
<meta name="twitter:image" content="https://tudominio.com/static/images/og-image.jpg">

<!-- 3. Actualizar logo navbar (línea ~35) -->
<a href="#inicio" class="nav-brand">
    <img src="/static/images/logo.png" alt="Agrotech Digital" class="nav-logo">
    <span class="brand-text">Agrotech Digital</span>
</a>

<!-- 4. Actualizar logo footer (línea ~335) -->
<div class="footer-brand">
    <img src="/static/images/logo-white.png" alt="Agrotech Digital" class="footer-logo">
    <p class="footer-tagline">Agricultura de Precisión con Tecnología Satelital</p>
</div>
```

---

### Paso 4: Ajustar estilos CSS (si es necesario)

Edita `metrica/static/css/landing.css`:

```css
/* Logo navbar (línea ~200) */
.nav-logo {
    height: 50px;              /* Ajustar altura según tu logo */
    width: auto;               /* Mantener proporción */
    margin-right: var(--spacing-sm);
}

/* Logo footer (línea ~650) */
.footer-logo {
    height: 45px;              /* Ajustar altura según tu logo */
    width: auto;
    margin-bottom: var(--spacing-sm);
    opacity: 0.9;
}

/* Responsive móvil */
@media (max-width: 480px) {
    .nav-logo {
        height: 40px;          /* Más pequeño en móvil */
    }
}
```

---

### Paso 5: Crear site.webmanifest (opcional)

Crea `metrica/static/images/site.webmanifest`:

```json
{
  "name": "Agrotech Digital",
  "short_name": "Agrotech",
  "icons": [
    {
      "src": "/static/images/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/images/android-chrome-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ],
  "theme_color": "#4CAF50",
  "background_color": "#1a1a1a",
  "display": "standalone",
  "start_url": "/",
  "scope": "/"
}
```

---

### Paso 6: Verificar integración

```bash
# 1. Iniciar servidor
python manage.py runserver

# 2. Abrir en navegador
open http://localhost:8000/static/index.html

# 3. Inspeccionar elementos
# Chrome DevTools → Elements → Buscar <img> tags
# Verificar que src apunta a tus logos

# 4. Verificar favicon
# Chrome DevTools → Application → Manifest
# Verificar que todos los iconos cargan

# 5. Verificar Open Graph
# Visitar: https://developers.facebook.com/tools/debug/
# Ingresar URL de tu sitio
# Ver preview de cómo se vería en redes sociales
```

---

## ✅ Checklist de Verificación

Después de integrar los logos, verifica:

- [ ] Logo principal se ve correctamente en navbar (desktop)
- [ ] Logo principal se ve correctamente en navbar (móvil)
- [ ] Logo footer se ve correctamente
- [ ] Favicon aparece en pestaña del navegador
- [ ] Apple touch icon funciona en iOS (Safari > Agregar a Inicio)
- [ ] Android chrome icons funcionan
- [ ] Open Graph image preview correcto en Facebook Debugger
- [ ] Twitter card image preview correcto
- [ ] Logos tienen buena resolución (@2x para Retina)
- [ ] Imágenes están optimizadas (< 100KB cada una)
- [ ] Transparencias funcionan correctamente
- [ ] Colores de marca son consistentes

---

## 🎨 Opciones de Diseño

### Si solo tienes texto/logotipo simple

Puedes usar **solo CSS** sin imágenes:

```html
<!-- En navbar -->
<a href="#inicio" class="nav-brand">
    <div class="logo-icon">🌱</div>
    <span class="brand-text">Agrotech Digital</span>
</a>
```

```css
.logo-icon {
    font-size: 2rem;
    margin-right: var(--spacing-sm);
    filter: drop-shadow(0 2px 4px rgba(76, 175, 80, 0.3));
}

.brand-text {
    font-weight: 700;
    font-size: var(--text-xl);
    background: linear-gradient(135deg, var(--brand-green), var(--brand-orange));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
```

### Si tienes SVG

Ventajas de usar SVG:
- ✅ Escala perfecta en cualquier resolución
- ✅ Peso muy ligero (< 10KB)
- ✅ Puedes cambiar colores con CSS

```html
<img src="/static/images/logo.svg" alt="Agrotech Digital" class="nav-logo">
```

```css
.nav-logo {
    height: 50px;
    width: auto;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

/* Cambiar color de SVG con CSS (requiere SVG inline) */
.nav-logo path {
    fill: var(--brand-green);
}
```

---

## 🐛 Problemas Comunes

### Logo no aparece

```bash
# Verificar que archivo existe
ls -lah metrica/static/images/logo.png

# Verificar permisos
chmod 644 metrica/static/images/logo.png

# Verificar ruta en HTML
grep "logo.png" metrica/static/index.html

# Abrir directamente la imagen en navegador
open http://localhost:8000/static/images/logo.png
```

### Logo se ve borroso

```bash
# Exportar a resolución @2x (doble tamaño)
# Si logo es 200px ancho, exportar a 400px
# Luego especificar tamaño en CSS

# CSS
.nav-logo {
    height: 50px;  /* Tamaño real */
    width: auto;
}

# El navegador reducirá automáticamente la imagen @2x
# resultando en nitidez perfecta en pantallas Retina
```

### Logo demasiado grande/pequeño

```css
/* Ajustar en CSS */
.nav-logo {
    height: 50px;        /* Cambiar a tu gusto */
    max-width: 200px;    /* Límite de ancho */
    width: auto;         /* Mantener proporción */
}
```

### Favicon no se actualiza

```bash
# 1. Hard reload
# Chrome: Cmd+Shift+R (Mac) o Ctrl+Shift+R (Windows)

# 2. Limpiar cache del navegador
# Chrome: Settings > Privacy > Clear browsing data

# 3. Agregar query string temporal
<link rel="icon" href="/static/images/favicon.ico?v=2">
```

---

## 📚 Recursos Adicionales

### Herramientas de Diseño
- [Figma](https://www.figma.com/) - Diseño de logos y assets
- [Canva](https://www.canva.com/) - Templates para Open Graph
- [Inkscape](https://inkscape.org/) - Editor SVG gratuito

### Generadores de Favicon
- [Real Favicon Generator](https://realfavicongenerator.net/) - El más completo
- [Favicon.io](https://favicon.io/) - Simple y rápido
- [Favicon Generator](https://www.favicon-generator.org/) - Alternativa

### Optimización de Imágenes
- [TinyPNG](https://tinypng.com/) - Compresión PNG/JPG
- [Squoosh](https://squoosh.app/) - Optimizador web
- [ImageOptim](https://imageoptim.com/) - App para Mac

### Validadores
- [Facebook Debugger](https://developers.facebook.com/tools/debug/)
- [Twitter Card Validator](https://cards-dev.twitter.com/validator)
- [LinkedIn Inspector](https://www.linkedin.com/post-inspector/)

---

## 💡 Tips Profesionales

1. **Exporta siempre @2x**: Doble resolución para pantallas Retina
2. **Optimiza peso**: Logos < 50KB, OG images < 300KB
3. **Mantén consistencia**: Usa los mismos colores de marca en todos los assets
4. **Prueba en oscuro y claro**: Asegura que logo funciona en ambos fondos
5. **Usa SVG cuando sea posible**: Mejor calidad y peso
6. **Versiona tus assets**: Agrega `?v=2` a URLs para forzar recarga
7. **Documenta dimensiones**: Mantén registro de tamaños utilizados

---

**Última actualización**: Enero 2024  
**Versión**: 1.0.0
