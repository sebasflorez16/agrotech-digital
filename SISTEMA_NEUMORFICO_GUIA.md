# 🎨 Sistema de Diseño Neumórfico - AgroTech Digital

## 📋 Índice
1. [Introducción](#introducción)
2. [Archivos del Sistema](#archivos-del-sistema)
3. [Implementación](#implementación)
4. [Componentes Disponibles](#componentes-disponibles)
5. [Ejemplos de Uso](#ejemplos-de-uso)
6. [Funciones JavaScript](#funciones-javascript)
7. [Responsive Design](#responsive-design)
8. [Personalización](#personalización)

---

## 🎯 Introducción

Este sistema de diseño neumórfico ha sido adaptado del proyecto AgroTech Histórico y aplicado a AgroTech Digital, manteniendo todas las funcionalidades existentes intactas.

**Características principales:**
- ✅ Diseño neumórfico (soft UI) con efectos 3D
- ✅ Paleta de colores corporativa AgroTech
- ✅ Totalmente responsive (mobile-first)
- ✅ Animaciones suaves y transiciones
- ✅ Componentes reutilizables
- ✅ Sistema de notificaciones integrado
- ✅ Compatible con todas las funcionalidades existentes

---

## 📁 Archivos del Sistema

### Archivos Creados

```
metrica/static/
├── css/
│   └── agrotech-neomorphic.css          # Sistema de estilos neumórficos
└── js/
    └── agrotech-neomorphic.js           # Utilidades JavaScript
```

### Archivos Actualizados

```
metrica/static/templates/
├── vertical_base.html                    # Template base actualizado
├── dashboard.html                        # Dashboard con estilos
└── parcels/
    └── parcels-dashboard.html           # Dashboard de parcelas actualizado
```

---

## 🚀 Implementación

### 1. Sistema ya Integrado

El sistema neumórfico **ya está integrado** en los siguientes templates:
- `vertical_base.html`
- `dashboard.html`
- `parcels-dashboard.html`

### 2. Para Nuevos Templates

Si creas un nuevo template, incluye estos archivos en el `<head>`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <!-- ... otros meta tags y CSS ... -->
    
    <!-- Bootstrap 5.3.2 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet" 
          integrity="sha384-T3c6CoIi6uLrA9TneNEoa7RxnatzjcDSCmG1MXxSR1GAsXEV/Dwwykc2MPK8M2HN" crossorigin="anonymous">
    
    <!-- Font Awesome 6.4.2 -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css" 
          integrity="sha512-z3gLpd7yknf1YoNbCzqRKc4qyor8gaKU1qmn+CShxbuBusANI9QpRohGBreCFkKxLhei6S9CQXFEbbKuqLg0DA==" 
          crossorigin="anonymous" referrerpolicy="no-referrer"/>
    
    <!-- Google Fonts - Inter -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    
    <!-- ⭐ SISTEMA NEUMÓRFICO AGROTECH ⭐ -->
    <link href="../css/agrotech-neomorphic.css" rel="stylesheet" type="text/css" />
</head>

<body class="neomorphic-theme">
    <!-- Tu contenido aquí -->
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js" 
            integrity="sha384-C6RzsynM9kWDrMNeT87bh95OGNyZPhcTNXj1NW7RuBCsyN/o0jlpcV8Qyq46cDfL" 
            crossorigin="anonymous"></script>
    
    <!-- ⭐ SISTEMA JAVASCRIPT NEUMÓRFICO ⭐ -->
    <script src="../js/agrotech-neomorphic.js"></script>
</body>
</html>
```

**Nota:** La clase `neomorphic-theme` en el body activa automáticamente el tema.

---

## 🎨 Componentes Disponibles

### 1. Cards Neumórficos

```html
<!-- Card básico -->
<div class="card neomorphic">
    <div class="card-header">
        <h5><i class="fas fa-seedling"></i> Título de la Card</h5>
    </div>
    <div class="card-body">
        <p>Contenido de la card con efecto neumórfico 3D</p>
    </div>
</div>

<!-- Card automática (se aplica estilos automáticamente) -->
<div class="card">
    <div class="card-header">
        <h5>Card Normal</h5>
    </div>
    <div class="card-body">
        <p>El sistema aplicará automáticamente estilos neumórficos</p>
    </div>
</div>
```

### 2. Botones Neumórficos

```html
<!-- Botones con clase neomorphic -->
<button class="btn neomorphic btn-primary">
    <i class="fas fa-save"></i> Guardar
</button>

<button class="btn neomorphic btn-warning">
    <i class="fas fa-edit"></i> Editar
</button>

<button class="btn neomorphic btn-success">
    <i class="fas fa-check"></i> Confirmar
</button>

<button class="btn neomorphic btn-info">
    <i class="fas fa-info-circle"></i> Información
</button>

<!-- Botón light (neumórfico puro) -->
<button class="btn neomorphic btn-light">
    <i class="fas fa-times"></i> Cancelar
</button>

<!-- Los botones normales también reciben estilos automáticamente -->
<button class="btn btn-primary">
    Botón Normal (con estilos neumórficos automáticos)
</button>
```

### 3. Stats Cards (Tarjetas de Estadísticas)

```html
<div class="stats-card">
    <div class="card-body">
        <h6 class="text-uppercase text-muted mb-1">Total Parcelas</h6>
        <h3 class="mb-0 text-dark">1,234</h3>
        <small class="text-success">
            <i class="fas fa-arrow-up"></i> 12% más que el mes pasado
        </small>
    </div>
</div>

<!-- Stats card naranja -->
<div class="stats-card orange">
    <div class="card-body">
        <h6 class="text-uppercase text-muted mb-1">Alertas Activas</h6>
        <h3 class="mb-0 text-dark">23</h3>
    </div>
</div>
```

### 4. Formularios Neumórficos

```html
<form>
    <div class="mb-3">
        <label for="nombre" class="form-label">Nombre</label>
        <input type="text" class="form-control neomorphic" id="nombre" placeholder="Ingrese el nombre">
    </div>
    
    <div class="mb-3">
        <label for="tipo" class="form-label">Tipo</label>
        <select class="form-select neomorphic" id="tipo">
            <option>Opción 1</option>
            <option>Opción 2</option>
        </select>
    </div>
    
    <button type="submit" class="btn neomorphic btn-primary">
        <i class="fas fa-save"></i> Guardar
    </button>
</form>
```

### 5. Tablas Neumórficas

```html
<table class="table neomorphic">
    <thead>
        <tr>
            <th><i class="fas fa-hashtag"></i> ID</th>
            <th><i class="fas fa-map"></i> Parcela</th>
            <th><i class="fas fa-chart-area"></i> Área</th>
            <th><i class="fas fa-cog"></i> Acciones</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>1</td>
            <td>Parcela Norte</td>
            <td>15.5 ha</td>
            <td>
                <button class="btn neomorphic btn-sm btn-info">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        </tr>
    </tbody>
</table>
```

### 6. Alerts Neumórficos

```html
<div class="alert neomorphic alert-success">
    <i class="fas fa-check-circle me-2"></i>
    Operación completada exitosamente
</div>

<div class="alert neomorphic alert-warning">
    <i class="fas fa-exclamation-triangle me-2"></i>
    Advertencia: Revise los datos antes de continuar
</div>

<div class="alert neomorphic alert-danger">
    <i class="fas fa-times-circle me-2"></i>
    Error: No se pudo completar la operación
</div>
```

### 7. Badges Neumórficos

```html
<span class="badge neomorphic bg-success">Activo</span>
<span class="badge neomorphic bg-warning">Pendiente</span>
<span class="badge neomorphic bg-danger">Inactivo</span>
<span class="badge neomorphic bg-info">Nuevo</span>
```

### 8. Contenedores Neumórficos

```html
<div class="neomorphic-container">
    <h4 class="text-gradient-primary">
        <i class="fas fa-chart-line"></i> Título con Gradiente
    </h4>
    <p>Contenido del contenedor con efecto neumórfico</p>
</div>
```

---

## 🛠️ Funciones JavaScript

### 1. Mostrar Notificaciones

```javascript
// Notificación de éxito
mostrarNotificacion('Datos guardados correctamente', 'success', 5000);

// Notificación de error
mostrarNotificacion('Ocurrió un error al procesar', 'error', 5000);

// Notificación de advertencia
mostrarNotificacion('Verifique los campos obligatorios', 'warning', 5000);

// Notificación de información
mostrarNotificacion('Procesando solicitud...', 'info', 3000);

// También disponible vía objeto AgroTech
window.AgroTech.UI.mostrarNotificacion('Mensaje', 'success');
```

### 2. Mostrar Error Crítico

```javascript
mostrarErrorCritico(
    'Error de Conexión',
    'No se pudo conectar con el servidor',
    'Error 500: Internal Server Error\nStack trace...'
);

// También disponible vía objeto AgroTech
window.AgroTech.UI.mostrarErrorCritico(titulo, mensaje, detalles);
```

### 3. Loading Overlay

```javascript
// Mostrar loading
const loading = mostrarLoading('Cargando datos...');

// Simular carga
setTimeout(() => {
    ocultarLoading();
    mostrarNotificacion('Datos cargados', 'success');
}, 3000);

// También disponible vía objeto AgroTech
window.AgroTech.UI.mostrarLoading('Mensaje');
window.AgroTech.UI.ocultarLoading();
```

### 4. Confirmación de Acciones

```javascript
confirmarAccion(
    '¿Eliminar parcela?',
    '¿Está seguro de que desea eliminar esta parcela? Esta acción no se puede deshacer.',
    function() {
        // Usuario confirmó
        console.log('Eliminando...');
        mostrarNotificacion('Parcela eliminada', 'success');
    },
    function() {
        // Usuario canceló
        console.log('Cancelado');
    }
);

// También disponible vía objeto AgroTech
window.AgroTech.UI.confirmarAccion(titulo, mensaje, onConfirm, onCancel);
```

### 5. Aplicar Estilos Automáticamente

```javascript
// Aplicar estilos neumórficos a elementos nuevos creados dinámicamente
aplicarEstilosNeomorficos();

// Aplicar animaciones a tarjetas
aplicarAnimacionesTarjetas();

// Inicializar tema completo (ya se hace automáticamente)
inicializarTemaNeumorfico();

// También disponible vía objeto AgroTech
window.AgroTech.UI.aplicarEstilosNeomorficos();
window.AgroTech.UI.aplicarAnimacionesTarjetas();
```

### 6. Configuración Global

```javascript
// Acceder a configuración global
console.log(window.AgroTech.colors.verde);      // #2E8B57
console.log(window.AgroTech.colors.naranja);    // #FF7A00

// Configuración de mapas
console.log(window.AgroTech.mapConfig.defaultCenter);  // [4.570868, -74.297333]
console.log(window.AgroTech.mapConfig.defaultZoom);    // 10
```

---

## 📱 Responsive Design

El sistema es **completamente responsive** con breakpoints en:

- **991px** - Tablets grandes
- **768px** - Tablets y móviles horizontales
- **576px** - Smartphones
- **400px** - Smartphones pequeños

### Comportamiento en Mobile

```css
/* Botones ocupan 100% del ancho en móvil */
@media (max-width: 768px) {
    .btn.neomorphic {
        width: 100%;
        margin: 4px 0;
    }
}

/* Cards más compactas en móvil */
@media (max-width: 576px) {
    .card.neomorphic .card-body {
        padding: 16px;
    }
}
```

---

## 🎨 Personalización

### Cambiar Colores Corporativos

Edita el archivo `/metrica/static/css/agrotech-neomorphic.css`:

```css
:root {
    --agrotech-orange: #TU_NARANJA;    /* Cambia aquí */
    --agrotech-green: #TU_VERDE;       /* Cambia aquí */
    /* ... más variables ... */
}
```

### Ajustar Sombras Neumórficas

```css
:root {
    /* Sombras más suaves */
    --neuro-shadow-light: -6px -6px 12px rgba(255, 255, 255, 0.7);
    --neuro-shadow-dark: 6px 6px 12px rgba(46, 139, 87, 0.1);
    
    /* O sombras más pronunciadas */
    --neuro-shadow-light: -10px -10px 20px rgba(255, 255, 255, 0.9);
    --neuro-shadow-dark: 10px 10px 20px rgba(46, 139, 87, 0.2);
}
```

### Cambiar Border Radius

```css
.card.neomorphic {
    border-radius: 20px;  /* Menos redondeado */
    /* o */
    border-radius: 32px;  /* Más redondeado */
}
```

---

## ✅ Checklist de Integración

Para verificar que el sistema esté funcionando correctamente:

- [ ] Se carga `agrotech-neomorphic.css` en el inspector de red
- [ ] Se carga `agrotech-neomorphic.js` en el inspector de red
- [ ] El `<body>` tiene la clase `neomorphic-theme`
- [ ] Los cards tienen efectos de sombra 3D
- [ ] Los botones tienen efecto hover con elevación
- [ ] Las notificaciones aparecen con `mostrarNotificacion()`
- [ ] El tema se ve bien en desktop
- [ ] El tema se ve bien en móvil
- [ ] No se rompieron funcionalidades existentes

---

## 🐛 Troubleshooting

### Los estilos no se aplican

1. Verifica que el CSS esté cargándose: Inspector → Network → CSS
2. Comprueba la ruta del archivo: `../css/agrotech-neomorphic.css`
3. Verifica que el `<body>` tenga `class="neomorphic-theme"`
4. Limpia caché del navegador: `Ctrl + Shift + R` (Windows) o `Cmd + Shift + R` (Mac)

### Las funciones JavaScript no funcionan

1. Verifica que el JS esté cargándose: Inspector → Network → JS
2. Comprueba la consola por errores: `F12` → Console
3. Verifica que Bootstrap esté cargado antes del script
4. Prueba ejecutar: `console.log(window.AgroTech)` en la consola

### Los estilos se ven mal en móvil

1. Verifica el viewport meta tag: `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
2. Usa las herramientas de desarrollador en modo responsive
3. Prueba en un dispositivo real
4. Revisa que `mobile-clean-redesign.css` no esté en conflicto

---

## 📚 Ejemplos Completos

### Ejemplo 1: Formulario de Crear Parcela

```html
<div class="card neomorphic">
    <div class="card-header">
        <h5><i class="fas fa-map-marked-alt"></i> Nueva Parcela</h5>
    </div>
    <div class="card-body">
        <form id="formParcela">
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label class="form-label">Nombre</label>
                    <input type="text" class="form-control neomorphic" placeholder="Ej: Parcela Norte">
                </div>
                <div class="col-md-6 mb-3">
                    <label class="form-label">Área (ha)</label>
                    <input type="number" class="form-control neomorphic" placeholder="15.5">
                </div>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Tipo de Suelo</label>
                <select class="form-select neomorphic">
                    <option>Arcilloso</option>
                    <option>Arenoso</option>
                    <option>Franco</option>
                </select>
            </div>
            
            <div class="d-flex gap-2">
                <button type="submit" class="btn neomorphic btn-primary flex-fill">
                    <i class="fas fa-save"></i> Guardar
                </button>
                <button type="button" class="btn neomorphic btn-light" onclick="history.back()">
                    <i class="fas fa-times"></i> Cancelar
                </button>
            </div>
        </form>
    </div>
</div>

<script>
document.getElementById('formParcela').addEventListener('submit', function(e) {
    e.preventDefault();
    
    mostrarLoading('Guardando parcela...');
    
    // Simular petición API
    setTimeout(() => {
        ocultarLoading();
        mostrarNotificacion('Parcela creada exitosamente', 'success');
        // Redirigir o limpiar formulario
    }, 2000);
});
</script>
```

### Ejemplo 2: Dashboard con Stats

```html
<div class="row mb-4">
    <div class="col-md-3 mb-3">
        <div class="stats-card">
            <div class="card-body">
                <h6 class="text-uppercase text-muted mb-1">
                    <i class="fas fa-map"></i> Parcelas
                </h6>
                <h3 class="mb-0 text-dark">245</h3>
                <small class="text-success">
                    <i class="fas fa-arrow-up"></i> 12%
                </small>
            </div>
        </div>
    </div>
    
    <div class="col-md-3 mb-3">
        <div class="stats-card orange">
            <div class="card-body">
                <h6 class="text-uppercase text-muted mb-1">
                    <i class="fas fa-seedling"></i> Cultivos
                </h6>
                <h3 class="mb-0 text-dark">1,234</h3>
                <small class="text-info">
                    <i class="fas fa-equals"></i> Sin cambios
                </small>
            </div>
        </div>
    </div>
</div>
```

---

## 📞 Soporte

Para más información o ayuda:
- Revisa el código fuente en `/metrica/static/css/agrotech-neomorphic.css`
- Consulta el JavaScript en `/metrica/static/js/agrotech-neomorphic.js`
- Verifica el documento de referencia `INFORME_IMPLEMENTACION_FRONTEND_AGROTECH.md`

---

**¡El sistema neumórfico está listo para usar! 🚀🌾**
