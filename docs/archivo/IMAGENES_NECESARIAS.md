# 📸 Imágenes Necesarias para Landing Page

## 🎯 Imágenes Requeridas

### 1. **Hero Background** (Fondo principal)
- **Nombre archivo**: `hero-bg.jpg`
- **Ubicación**: `metrica/static/images/hero-bg.jpg`
- **Dimensiones**: 1920x1080px (mínimo)
- **Tema**: Vista aérea/satelital de campos agrícolas, dron sobre cultivos, o imagen espacial
- **Ejemplo**: Campo verde desde arriba, con patrones de cultivo visibles
- **Peso**: < 500KB (optimizada)

---

### 2. **Producto 1 - Monitoreo de Cultivos**
- **Nombre archivo**: `product-monitoring.jpg`
- **Ubicación**: `metrica/static/images/product-monitoring.jpg`
- **Dimensiones**: 800x600px
- **Tema**: Dashboard con mapas satelitales, o imagen de cultivos con análisis NDVI
- **Ejemplo**: Captura de pantalla de tu plataforma, o mapa con colores NDVI
- **Peso**: < 200KB

---

### 3. **Producto 2 - Análisis de Datos**
- **Nombre archivo**: `product-analytics.jpg`
- **Ubicación**: `metrica/static/images/product-analytics.jpg`
- **Dimensiones**: 800x600px
- **Tema**: Gráficos, dashboards, análisis de datos agrícolas
- **Ejemplo**: Dashboard con estadísticas, gráficos temporales
- **Peso**: < 200KB

---

### 4. **Feature Background** (Opcional - Fondo sutil)
- **Nombre archivo**: `features-bg.jpg`
- **Ubicación**: `metrica/static/images/features-bg.jpg`
- **Dimensiones**: 1920x800px
- **Tema**: Textura de tierra, patrón sutil de agricultura
- **Ejemplo**: Imagen muy clara (opacity baja) de cultivos
- **Peso**: < 300KB

---

## 🔍 Dónde Conseguir Imágenes (Gratis y Legales)

### Opción 1: Usar tus propias capturas
- Captura de pantalla de tu dashboard
- Fotos de campos que hayas visitado
- Imágenes de análisis NDVI de tu plataforma

### Opción 2: Bancos de imágenes gratuitos

#### **Unsplash** (Mejor calidad)
- https://unsplash.com/s/photos/agriculture-aerial
- https://unsplash.com/s/photos/farm-drone
- https://unsplash.com/s/photos/satellite-view-farm
- https://unsplash.com/s/photos/precision-agriculture

Búsquedas recomendadas:
```
- "agriculture aerial view"
- "farm from above"
- "crop field drone"
- "precision agriculture"
- "satellite agriculture"
- "farmland aerial"
```

#### **Pexels**
- https://www.pexels.com/search/agriculture%20aerial/
- https://www.pexels.com/search/farm%20technology/

#### **Pixabay**
- https://pixabay.com/images/search/agriculture%20drone/

---

## 📥 Cómo Optimizar las Imágenes

### Antes de subir:

1. **Redimensionar** a las dimensiones indicadas
   - Usa: https://www.iloveimg.com/resize-image
   - O: Photoshop, GIMP, Preview (Mac)

2. **Comprimir** sin perder calidad
   - Usa: https://tinypng.com/
   - O: https://squoosh.app/

3. **Convertir a WebP** (opcional, mejor performance)
   - Usa: https://cloudconvert.com/jpg-to-webp

---

## 📁 Estructura Final de Carpeta

```
metrica/static/images/
├── hero-bg.jpg              (1920x1080, <500KB) - Fondo hero principal
├── product-monitoring.jpg    (800x600, <200KB)   - Tarjeta producto 1
├── product-analytics.jpg     (800x600, <200KB)   - Tarjeta producto 2
├── features-bg.jpg          (1920x800, <300KB)  - Fondo features (opcional)
├── logo.png                 (200x50)             - Logo navbar
├── logo-white.png           (200x50)             - Logo footer
└── favicon.ico              (32x32)              - Favicon
```

---

## 🚀 Pasos a Seguir

### Paso 1: Descargar/Crear Imágenes
1. Ve a Unsplash: https://unsplash.com/s/photos/agriculture-aerial
2. Descarga 3-4 imágenes que te gusten
3. Guárdalas con los nombres indicados arriba

### Paso 2: Optimizar
```bash
# Opción A: Online
1. Ve a https://tinypng.com/
2. Sube todas las imágenes
3. Descarga las optimizadas

# Opción B: Terminal (si tienes ImageMagick)
convert hero-original.jpg -resize 1920x1080^ -quality 85 hero-bg.jpg
convert product1-original.jpg -resize 800x600^ -quality 85 product-monitoring.jpg
```

### Paso 3: Subir a tu proyecto
```bash
# Crear carpeta si no existe
mkdir -p metrica/static/images

# Copiar imágenes
cp ~/Downloads/hero-bg.jpg metrica/static/images/
cp ~/Downloads/product-monitoring.jpg metrica/static/images/
cp ~/Downloads/product-analytics.jpg metrica/static/images/
```

### Paso 4: Verificar
```bash
ls -lh metrica/static/images/
# Debe mostrar:
# hero-bg.jpg (< 500KB)
# product-monitoring.jpg (< 200KB)
# product-analytics.jpg (< 200KB)
```

---

## 💡 Recomendaciones de Estilo

### Para Hero Background:
- ✅ Vista aérea de campos verdes
- ✅ Líneas de cultivo visibles
- ✅ Colores: Verde, marrón, azul cielo
- ❌ Evitar: Imágenes muy oscuras o con mucho texto

### Para Productos:
- ✅ Capturas de tu dashboard real
- ✅ Mapas con colores NDVI
- ✅ Gráficos y estadísticas
- ❌ Evitar: Stock photos genéricas

### Para Features Background:
- ✅ Textura sutil (se usará con opacity baja)
- ✅ Patrón repetible
- ❌ Evitar: Imágenes con demasiado detalle

---

## 🎨 Ejemplos de Búsqueda en Unsplash

Copia y pega estos links:

**Hero Background:**
```
https://unsplash.com/s/photos/agriculture-aerial-view
https://unsplash.com/s/photos/farmland-drone
https://unsplash.com/s/photos/crop-field-above
```

**Productos:**
```
https://unsplash.com/s/photos/agriculture-technology
https://unsplash.com/s/photos/farming-data
https://unsplash.com/s/photos/smart-farming
```

---

## ✅ Checklist

Una vez tengas las imágenes:

- [ ] Hero background descargada y optimizada
- [ ] Producto 1 descargada y optimizada
- [ ] Producto 2 descargada y optimizada
- [ ] Todas las imágenes renombradas correctamente
- [ ] Todas las imágenes copiadas a `metrica/static/images/`
- [ ] Verificado que el peso sea adecuado
- [ ] ¡Listo para ver el resultado! 🎉

---

**Cuando tengas las imágenes listas, avísame y actualizaré el HTML para que se vean perfectamente integradas.**
