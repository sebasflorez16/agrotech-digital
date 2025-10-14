# 🚀 Guía de Despliegue en Netlify

## 📋 Configuración Actual

### **Arquitectura del Sistema**

```
Usuario
   ↓
Netlify (Frontend + Cesium)
   ↓ (Solo peticiones API)
Railway (Backend Django)
```

### **URLs Importantes**

- **Frontend (Netlify)**: `https://agrotechcolombia.netlify.app`
- **Backend (Railway)**: `https://site-production-208b.up.railway.app` (solo API)

---

## ✅ Configuración Aplicada

### 1. **netlify.toml**

El archivo `netlify.toml` en la raíz del proyecto configura:

- **CSP Permisivo**: Permite `unsafe-eval` necesario para Cesium Workers
- **Redirects API**: `/api/*` → Railway automáticamente
- **Headers CORS**: Permite comunicación cross-origin
- **Cache**: Optimizado para recursos estáticos

### 2. **Content Security Policy (CSP)**

Permite:
- ✅ Scripts de Cesium CDN
- ✅ WebGL y Workers
- ✅ Imágenes satelitales (Esri, OpenStreetMap)
- ✅ APIs externas (EOSDA, Railway)

### 3. **Redirects Automáticos**

```toml
[[redirects]]
  from = "/api/*"
  to = "https://site-production-208b.up.railway.app/api/:splat"
  status = 200
```

Esto significa que:
- `https://agrotechcolombia.netlify.app/api/parcels/` 
- → Se redirige a → 
- `https://site-production-208b.up.railway.app/api/parcels/`

---

## 🎯 Punto de Entrada CORRECTO

### ✅ **USAR SIEMPRE:**
```
https://agrotechcolombia.netlify.app/templates/parcels/parcels-dashboard.html
```

### ❌ **NUNCA USAR:**
```
https://site-production-208b.up.railway.app/templates/parcels/parcels-dashboard.html
```

**Razón**: Railway tiene CSP estricto que bloquea Cesium.

---

## 🔧 Despliegue en Netlify

### **Opción 1: Desde GitHub (Recomendado)**

1. Conectar repositorio en Netlify
2. **Build settings**:
   - Base directory: `/`
   - Build command: `echo 'Desplegando archivos estáticos'`
   - Publish directory: `metrica`

3. **Environment variables** (si es necesario):
   - `NODE_VERSION=18`

### **Opción 2: Deploy Manual**

```bash
# Instalar Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Deploy
netlify deploy --prod --dir=metrica
```

---

## 🐛 Solución de Problemas

### **Error: CSP bloqueando Cesium**

**Síntoma**: `Refused to evaluate a string as JavaScript because 'unsafe-eval' is not an allowed source`

**Solución**: 
1. Verificar que `netlify.toml` esté en la raíz
2. Verificar CSP incluye `'unsafe-eval'` en `script-src`
3. Redesplegar en Netlify

### **Error: e.islon is not a function**

**Síntoma**: Error al inicializar Cesium Viewer

**Solución**:
1. Verificar `CESIUM_BASE_URL` configurado ANTES de cargar Cesium.js
2. Verificar que `baseLayer: false` en configuración del Viewer
3. No usar `creditContainer: document.createElement('div')`

### **Error: API no responde (404, CORS)**

**Síntoma**: Peticiones a `/api/*` fallan

**Solución**:
1. Verificar redirect en `netlify.toml`
2. Verificar Railway está corriendo
3. Verificar headers CORS en `netlify.toml`

---

## 📊 Verificación Post-Despliegue

### **Checklist**

- [ ] ✅ Netlify desplegado correctamente
- [ ] ✅ CSP permite Cesium (sin errores en consola)
- [ ] ✅ Mapa 3D de Cesium se renderiza
- [ ] ✅ APIs funcionan (datos de parcelas cargan)
- [ ] ✅ No hay errores de CORS
- [ ] ✅ Imágenes satelitales cargan (Esri/OSM)

### **Comandos de Diagnóstico**

```bash
# Verificar headers de Netlify
curl -I https://agrotechcolombia.netlify.app

# Verificar redirect de API
curl -I https://agrotechcolombia.netlify.app/api/parcels/

# Verificar Railway directamente
curl -I https://site-production-208b.up.railway.app/api/parcels/
```

---

## 🎯 Resultados Esperados

- ✅ **Cesium carga sin errores**
- ✅ **Mapa 3D se renderiza correctamente**
- ✅ **Lista de parcelas se muestra**
- ✅ **No hay errores de CSP en consola**
- ✅ **APIs responden correctamente**

---

## 📝 Notas Importantes

1. **Netlify es SOLO para frontend**: HTML, CSS, JS, imágenes
2. **Railway es SOLO para backend**: API REST, base de datos
3. **Comunicación**: Netlify → Railway (solo JSON)
4. **CSP de Railway**: NO se usa para servir HTML/Cesium

---

## 🔄 Actualizar Despliegue

```bash
# Después de hacer cambios
git add .
git commit -m "Actualización del frontend"
git push origin main

# Netlify detectará el cambio y redespliegará automáticamente
```

---

## 📞 Soporte

Si tienes problemas:

1. Revisa la consola del navegador (F12)
2. Revisa los logs de Netlify
3. Verifica que Railway esté corriendo
4. Comprueba que `netlify.toml` esté en la raíz

---

**Última actualización**: 14 de octubre de 2025
