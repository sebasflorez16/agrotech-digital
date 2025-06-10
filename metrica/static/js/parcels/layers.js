// Elimina credenciales y lógica de autenticación del frontend
// Ahora el frontend solo consumirá imágenes NDVI/NDMI a través del backend seguro

// Utilidad: Determina si un punto [lon, lat] está dentro de un polígono (array de [lon, lat])
// Algoritmo: Ray-casting
function pointInPolygon(point, vs) {
    let x = point[0], y = point[1];
    let inside = false;
    for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
        let xi = vs[i][0], yi = vs[i][1];
        let xj = vs[j][0], yj = vs[j][1];
        let intersect = ((yi > y) !== (yj > y)) &&
            (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
}

/**
 * Obtiene el polígono actual dibujado en Cesium (en formato [[lon, lat], ...])
 * Si no hay polígono, retorna null
 */
function getCurrentPolygonLonLat() {
    if (!window.positions || window.positions.length < 3) return null;
    return window.positions.map(pos => {
        const carto = Cesium.Cartographic.fromCartesian(pos);
        return [Cesium.Math.toDegrees(carto.longitude), Cesium.Math.toDegrees(carto.latitude)];
    });
}

// Variables globales para las capas
let ndviLayer = null;
let ndviEnabled = false;
let ndmiLayer = null;
let ndmiEnabled = false;
let sentinelWMTS = { ndvi: null, ndmi: null };

// Cargar las URLs WMTS seguras desde el backend al iniciar
function getBackendUrl(path) {
    // Detecta si estamos en 3000 (dev) y redirige a 8000 (backend)
    const isDev = window.location.port === "3000";
    if (isDev) {
        // Mantiene el subdominio del tenant
        const host = window.location.hostname.replace('localhost', 'localhost:8000');
        return window.location.protocol + '//' + host + path;
    } else {
        return path; // relativo en producción/backend
    }
}

async function fetchSentinelWMTS() {
    try {
        const url = getBackendUrl("/parcels/sentinel-wmts-urls/");
        const resp = await fetch(url, {
            headers: {
                'Accept': 'application/json',
            },
            credentials: 'include'
        });
        if (!resp.ok) throw new Error("No se pudo obtener las URLs WMTS seguras");
        const data = await resp.json();
        sentinelWMTS.ndvi = data.ndvi;
        sentinelWMTS.ndmi = data.ndmi;
    } catch (err) {
        console.error("Error obteniendo WMTS seguros:", err);
        alert("No se pudieron cargar las capas satelitales. Contacta al administrador.");
    }
}

// Llama a esta función al cargar la app
fetchSentinelWMTS();

/**
 * Alterna la capa NDVI usando WMTS seguro
 */
export async function toggleNDVILayer(viewer) {
    if (!viewer) {
        console.warn("Viewer no está definido.");
        return;
    }
    if (!sentinelWMTS.ndvi) {
        alert("Las capas NDVI aún no están listas. Intenta de nuevo en unos segundos.");
        return;
    }
    // Si ya está activa, la quitamos
    if (ndviLayer && ndviEnabled) {
        viewer.imageryLayers.remove(ndviLayer, true);
        ndviLayer = null;
        ndviEnabled = false;
        viewer.scene.screenSpaceCameraController.enableZoom = true;
        updateNDVIButtonText(false);
        // Volver a mostrar los bordes de las parcelas
        viewer.entities.values.forEach(entity => {
            if (entity.polyline && entity.polyline.material && entity.polyline.material.color && entity.polyline.material.color.getValue().toCssColorString() === '#145a32') {
                entity.show = true;
            }
        });
        console.log("Capa NDVI desactivada. Zoom habilitado.");
        return;
    }
    // Ocultar los bordes de las parcelas
    viewer.entities.values.forEach(entity => {
        if (entity.polyline && entity.polyline.material && entity.polyline.material.color && entity.polyline.material.color.getValue().toCssColorString() === '#145a32') {
            entity.show = false;
        }
    });
    // Agregar la capa WMTS NDVI
    ndviLayer = viewer.imageryLayers.addImageryProvider(
        new Cesium.WebMapTileServiceImageryProvider({
            url: sentinelWMTS.ndvi,
            layer: 'NDVI',
            style: 'default',
            format: 'image/png',
            tileMatrixSetID: 'PopularWebMercator512',
        })
    );
    ndviEnabled = true;
    viewer.scene.screenSpaceCameraController.enableZoom = false;
    updateNDVIButtonText(true);
    console.log("NDVI WMTS agregado correctamente.");
}

/**
 * Alterna la capa NDMI usando WMTS seguro
 */
export async function toggleNDMILayer(viewer) {
    if (!viewer) return;
    if (!sentinelWMTS.ndmi) {
        alert("Las capas NDMI aún no están listas. Intenta de nuevo en unos segundos.");
        return;
    }
    if (ndmiLayer && ndmiEnabled) {
        viewer.imageryLayers.remove(ndmiLayer, true);
        ndmiLayer = null;
        ndmiEnabled = false;
        updateNDMIButtonText(false);
        return;
    }
    // Agregar la capa WMTS NDMI
    ndmiLayer = viewer.imageryLayers.addImageryProvider(
        new Cesium.WebMapTileServiceImageryProvider({
            url: sentinelWMTS.ndmi,
            layer: 'NDMI',
            style: 'default',
            format: 'image/png',
            tileMatrixSetID: 'PopularWebMercator512',
        })
    );
    ndmiEnabled = true;
    updateNDMIButtonText(true);
    console.log("NDMI WMTS agregado correctamente.");
}

/**
 * Muestra el botón para alternar la capa NDVI.
 * Si ya existe, solo actualiza el evento.
 */
export function showNDVIToggleButton(viewer) {
    let btn = document.getElementById("ndviToggle");
    if (!btn) {
        btn = document.createElement("button");
        btn.id = "ndviToggle";
        btn.innerText = "Mostrar NDVI";
        btn.className = "btn btn-success";
    }
    btn.onclick = () => toggleNDVILayer(viewer);
    updateNDVIButtonText(ndviEnabled);
}

/**
 * Cambia el texto del botón según el estado de la capa NDVI.
 */
function updateNDVIButtonText(enabled) {
    const btn = document.getElementById("ndviToggle");
    if (btn) {
        btn.innerText = enabled ? "Ocultar NDVI" : "Mostrar NDVI";
    }
}

/**
 * Muestra el botón para alternar la capa NDMI.
 * Si ya existe, solo actualiza el evento.
 */
export function showNDMIToggleButton(viewer) {
    let btn = document.getElementById("ndmiToggle");
    if (!btn) {
        btn = document.createElement("button");
        btn.id = "ndmiToggle";
        btn.innerText = "Mostrar NDMI";
        btn.className = "btn btn-info";
    }
    btn.onclick = () => toggleNDMILayer(viewer);
    updateNDMIButtonText(ndmiEnabled);
}

function updateNDMIButtonText(enabled) {
    const btn = document.getElementById("ndmiToggle");
    if (btn) {
        btn.innerText = enabled ? "Ocultar NDMI" : "Mostrar NDMI";
    }
}