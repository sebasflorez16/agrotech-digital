// Importar función buscarEscenas dinámicamente para evitar ciclos
// Eliminado: función buscarEscenas y toda lógica de escenas EOSDA
// Elimina credenciales y lógica de autenticación del frontend
// Ahora el frontend solo consumirá imágenes NDVI/NDMI a través del backend seguro

// El backend ahora expone un proxy seguro para tiles WMTS EOSDA.
// El frontend solo debe consumir las imágenes WMTS usando la URL del proxy.

// Utilidad: Determina si un punto [lon, lat] está dentro de un polígono (array de [lon, lat])
// Algoritmo: Ray-casting
function pointInPolygon(point, vs) {
    let x = point[0], y = point[1];
    let inside = false;
    for (let i = 0, j = vs.length - 1; i < vs.length, j = i++;) {
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

// Configuración para Render API
// Estos valores deben ser dinámicos según la parcela/escena seleccionada
window.EOSDA_RENDER_PARAMS = {
    view_id: 'S2', // Sentinel-2 por defecto
    scene_id: null, // Debe ser asignado dinámicamente
    layer: 'NDVI',
    time: null // Debe ser asignado dinámicamente (YYYY-MM-DD)
};

function buildEosdaRenderUrl({view_id, scene_id, layer, z, x, y, time}) {
    if (!view_id || !scene_id || !layer || !z || !x || !y) return null;
    let url = `/api/parcels/eosda-wmts-tile/?view_id=${view_id}&scene_id=${scene_id}&layer=${layer}&z=${z}&x=${x}&y=${y}`;
    if (time) url += `&time=${encodeURIComponent(time)}`;
    return url;
}


// Eliminado: lógica antigua de WMTS de prueba. Ahora solo Render API.

/**
 * Alterna la capa NDVI usando WMTS seguro
 */
export async function toggleNDVILayer(viewer) {
    if (!viewer) {
        showErrorToast("Error: El visor 3D no está disponible. Recarga la página o contacta soporte.");
        return;
    }
    // Eliminado: toda la lógica de escenas y Render API para NDVI. Esta función queda vacía.
    // Si necesitas mostrar NDVI, implementa el flujo directo según la documentación EOSDA.
    return;
}

/**
 * Alterna la capa NDMI usando WMTS seguro
 */
export async function toggleNDMILayer(viewer) {
    if (!viewer) {
        showErrorToast("Error: El visor 3D no está disponible. Recarga la página o contacta soporte.");
        return;
    }
    // Validar que los parámetros necesarios estén presentes
    const params = window.EOSDA_RENDER_PARAMS;
    if (!params.scene_id || !params.time) {
        showErrorToast("Selecciona una parcela y una fecha válida para visualizar NDMI.");
        return;
    }
    if (ndmiLayer && ndmiEnabled) {
        try {
            viewer.imageryLayers.remove(ndmiLayer, true);
            ndmiLayer = null;
            ndmiEnabled = false;
            updateNDMIButtonText(false);
            showInfoToast("Capa NDMI desactivada.");
        } catch (err) {
            showErrorToast("Error al desactivar la capa NDMI.");
            console.error(err);
        }
        return;
    }
    try {
        ndmiLayer = viewer.imageryLayers.addImageryProvider(
            new Cesium.UrlTemplateImageryProvider({
                url: buildEosdaRenderUrl({
                    view_id: params.view_id,
                    scene_id: params.scene_id,
                    layer: 'NDMI',
                    z: '{z}',
                    x: '{x}',
                    y: '{y}',
                    time: params.time
                }),
                tilingScheme: new Cesium.WebMercatorTilingScheme(),
                maximumLevel: 18,
                tileWidth: 256,
                tileHeight: 256,
            })
        );
        ndmiEnabled = true;
        updateNDMIButtonText(true);
        showInfoToast("Capa NDMI activada correctamente.");
        console.log("NDMI Render API agregado correctamente.");
    } catch (err) {
        showErrorToast("No se pudo cargar la capa NDMI. Verifica la conexión o los parámetros.");
        console.error(err);
    }
}

// Exportar correctamente las funciones de toast para ES Modules
const showErrorToast = (msg) => {
    showToast(msg, 'danger');
};

const showInfoToast = (msg) => {
    showToast(msg, 'info');
};

export { showErrorToast, showInfoToast };

function showToast(msg, type = 'info') {
    // Busca o crea el contenedor de toasts
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = 9999;
        document.body.appendChild(container);
    }
    // Crea el toast
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-bg-${type} border-0 show`;
    toast.role = 'alert';
    toast.ariaLive = 'assertive';
    toast.ariaAtomic = 'true';
    toast.style.minWidth = '220px';
    toast.style.marginBottom = '10px';
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${msg}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    // Cierra el toast al hacer click en la X
    toast.querySelector('.btn-close').onclick = () => toast.remove();
    container.appendChild(toast);
    // Auto-destruye el toast después de 4s
    setTimeout(() => toast.remove(), 4000);
}


/**
 * Muestra el botón para alternar la capa NDVI.
 * Modular, sincronizado con EOSDA_STATE.
 */
export function showNDVIToggleButton(viewer) {
    let btn = document.getElementById("ndviToggle");
    if (!btn) return;
    btn.innerText = "NDVI (deshabilitado)";
    btn.className = "btn btn-secondary";
    btn.onclick = null;
}

/**
 * Cambia el texto del botón NDVI según el estado.
 */
function updateNDVIButtonText(enabled) {
    const btn = document.getElementById("ndviToggle");
    if (btn) {
        btn.innerText = enabled ? "Ocultar NDVI" : "Mostrar NDVI";
        btn.classList.remove("btn-success", "btn-secondary");
        btn.classList.add(enabled ? "btn-secondary" : "btn-success");
    }
}

/**
 * Muestra el botón para alternar la capa NDMI.
 * Modular, sincronizado con EOSDA_STATE.
 */
export function showNDMIToggleButton(viewer) {
    let btn = document.getElementById("ndmiToggle");
    if (!btn) return;
    btn.innerText = !window.EOSDA_STATE.ndmiActive ? "Mostrar NDMI" : "Ocultar NDMI";
    btn.className = !window.EOSDA_STATE.ndmiActive ? "btn btn-info" : "btn btn-secondary";
    btn.onclick = () => toggleNDMILayer(viewer);
}

function updateNDMIButtonText(enabled) {
    const btn = document.getElementById("ndmiToggle");
    if (btn) {
        btn.innerText = enabled ? "Ocultar NDMI" : "Mostrar NDMI";
        btn.classList.remove("btn-info", "btn-secondary");
        btn.classList.add(enabled ? "btn-secondary" : "btn-info");
    }
    if (window.EOSDA_STATE) window.EOSDA_STATE.ndmiActive = !!enabled;
}
// --- NDMI: Buscar escenas y selección ---
// Eliminado: función buscarEscenasNDMI y toda lógica de escenas NDMI/EOSDA

// MODAL PROFESIONAL PARA SELECCIÓN DE ESCENA SATELITAL NDMI
// Eliminado: showSceneSelectionModalNDMI y toda lógica de selección de escenas NDMI/EOSDA

// Lógica para obtener la escena cacheada y renderizarla en Cesium para NDMI
async function handleSceneSelectionNDMI(scene, viewer = null) {
    if (!scene || !(scene.view_id || scene.id)) {
        showErrorToast("Error: escena NDMI inválida. Faltan datos esenciales (view_id o id).");
        return;
    }
    const eosda_id = window.SELECTED_EOSDA_ID || scene.eosda_id || null;
    const view_id = scene.view_id || scene.id;
    if (!eosda_id) {
        showErrorToast("No se pudo determinar eosda_id para la petición NDMI. Verifica que window.SELECTED_EOSDA_ID esté asignado antes de abrir el modal.");
        console.error('[NDMI] Error: eosda_id no encontrado. scene:', scene);
        return;
    }
    if (!view_id) {
        showErrorToast("No se pudo determinar view_id para la petición NDMI.");
        console.error('[NDMI] Error: view_id no encontrado. scene:', scene);
        return;
    }
    try {
        const token = localStorage.getItem("accessToken");
        const resp = await fetch(`/api/parcels/eosda-ndmi-image/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ eosda_id, view_id })
        });
        if (!resp.ok) {
            showErrorToast("No se pudo obtener la imagen NDMI (" + resp.status + ").");
            return;
        }
        const data = await resp.json();
        if (!data || !data.image_url) {
            showErrorToast("Respuesta inválida del backend NDMI.");
            return;
        }
        // Actualizar los parámetros globales para renderizar NDMI
        window.EOSDA_RENDER_PARAMS.scene_id = scene.id;
        window.EOSDA_RENDER_PARAMS.time = scene.date ? scene.date.split('T')[0] : '';
        window.EOSDA_RENDER_PARAMS.view_id = view_id;
        // Actualizar el estado global NDMI
        window.EOSDA_STATE.selectedSceneNDMI = scene;
        window.EOSDA_STATE.ndmiActive = true;
        // Renderizar la capa NDMI
        if (viewer) toggleNDMILayer(viewer);
        showInfoToast("Imagen NDMI consultada en EOSDA.");
    } catch (err) {
        showErrorToast("Error al obtener la imagen NDMI: " + err.message);
    }
}

// MODAL PROFESIONAL PARA SELECCIÓN DE ESCENA SATELITAL NDVI/NDMI
export async function showSceneSelectionModal(scenes, onSelect, type = 'NDVI', viewer = null) {
    // Elimina cualquier modal anterior
    let oldModal = document.getElementById("sceneSelectionModal");
    if (oldModal) oldModal.remove();

    // Crear modal
    const modal = document.createElement("div");
    modal.id = "sceneSelectionModal";
    modal.style.position = "fixed";
    modal.style.top = "0";
    modal.style.left = "0";
    modal.style.width = "100vw";
    modal.style.height = "100vh";
    modal.style.background = "rgba(0,0,0,0.35)";
    modal.style.zIndex = "9999";
    modal.style.display = "flex";
    modal.style.alignItems = "center";
    modal.style.justifyContent = "center";

    // Contenido del modal
    const content = document.createElement("div");
    content.style.background = "#fff";
    content.style.padding = "28px 24px";
    content.style.borderRadius = "16px";
    content.style.boxShadow = "0 4px 24px rgba(0,0,0,0.18)";
    content.style.maxWidth = "480px";
    content.style.width = "100%";
    content.style.maxHeight = "80vh";
    content.style.overflow = "hidden";
    content.style.display = "flex";
    content.style.flexDirection = "column";

    // Título
    const title = document.createElement("h4");
    title.textContent = "Selecciona la escena satelital";
    title.style.marginBottom = "12px";
    title.style.fontWeight = "bold";
    title.style.color = "#145A32";
    content.appendChild(title);

    // Scroll interno para la tabla
    const scrollBox = document.createElement("div");
    scrollBox.style.overflowY = "auto";
    scrollBox.style.maxHeight = "48vh";
    scrollBox.style.marginBottom = "10px";

    // Tabla
    const table = document.createElement("table");
    table.style.width = "100%";
    table.style.borderCollapse = "collapse";
    table.innerHTML = `
        <thead>
            <tr style="background:#f5f5f5">
                <th style="padding:7px 4px;border-bottom:1px solid #ccc;font-size:14px;">Fecha</th>
                <th style="padding:7px 4px;border-bottom:1px solid #ccc;font-size:14px;">Nubes (%)</th>
                <th style="padding:7px 4px;border-bottom:1px solid #ccc;font-size:14px;">Acción</th>
            </tr>
        </thead>
        <tbody>
            ${scenes.map((scene, idx) => `
                <tr>
                    <td style="padding:7px 4px;border-bottom:1px solid #eee;font-size:13px;">${scene.date ? scene.date.split('T')[0] : '-'}</td>
                    <td style="padding:7px 4px;border-bottom:1px solid #eee;font-size:13px;">${scene.cloudCoverage != null ? scene.cloudCoverage : '-'}</td>
                    <td style="padding:7px 4px;border-bottom:1px solid #eee;">
                        <button class="btn btn-sm btn-success" data-idx="${idx}" style="font-size:13px;">Visualizar</button>
                    </td>
                </tr>
            `).join('')}
        </tbody>
    `;
    scrollBox.appendChild(table);
    content.appendChild(scrollBox);

    // Botón cerrar
    const closeBtn = document.createElement("button");
    closeBtn.textContent = "Cerrar";
    closeBtn.className = "btn btn-secondary";
    closeBtn.style.marginTop = "10px";
    closeBtn.onclick = () => modal.remove();
    content.appendChild(closeBtn);

    modal.appendChild(content);
    document.body.appendChild(modal);

    // Manejar click en visualizar
    table.querySelectorAll('button[data-idx]').forEach(btn => {
        btn.onclick = () => {
            const idx = btn.getAttribute('data-idx');
            const scene = scenes[idx];
            modal.remove();
            handleSceneSelection(scene, type, viewer);
            if (onSelect) onSelect(scene);
        };
    });
}

// Lógica para obtener la escena cacheada y renderizarla en Cesium
async function handleSceneSelection(scene, type = 'NDVI', viewer = null) {
    // Validar que la escena tenga los datos necesarios
    if (!scene || !(scene.view_id || scene.id)) {
        showErrorToast("Error: escena inválida. Faltan datos esenciales (view_id o id).");
        return;
    }
    // Obtener el eosda_id desde window o la escena
    // Si no existe, mostrar error y loguear el objeto para depuración
    const eosda_id = window.SELECTED_EOSDA_ID || scene.eosda_id || null;
    const view_id = scene.view_id || scene.id;
    if (!eosda_id) {
        showErrorToast("No se pudo determinar eosda_id para la petición NDVI. Verifica que window.SELECTED_EOSDA_ID esté asignado antes de abrir el modal.");
        console.error('[NDVI] Error: eosda_id no encontrado. scene:', scene);
        return;
    }
    if (!view_id) {
        showErrorToast("No se pudo determinar view_id para la petición NDVI.");
        console.error('[NDVI] Error: view_id no encontrado. scene:', scene);
        return;
    }
    try {
        const token = localStorage.getItem("accessToken");
        const resp = await fetch(`/api/parcels/eosda-ndvi-image/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ eosda_id, view_id })
        });
        if (!resp.ok) {
            showErrorToast("No se pudo obtener la imagen NDVI (" + resp.status + ").");
            return;
        }
        const data = await resp.json();
        if (!data || !data.image_url) {
            showErrorToast("Respuesta inválida del backend NDVI.");
            return;
        }
        // Actualizar los parámetros globales para renderizar
        window.EOSDA_RENDER_PARAMS.scene_id = scene.id;
        window.EOSDA_RENDER_PARAMS.time = scene.date ? scene.date.split('T')[0] : '';
        window.EOSDA_RENDER_PARAMS.view_id = view_id;
        // Renderizar la capa correspondiente
        if (type === 'NDVI') {
            if (viewer) toggleNDVILayer(viewer);
        } else if (type === 'NDMI') {
            if (viewer) toggleNDMILayer(viewer);
        }
        showInfoToast("Imagen NDVI consultada en EOSDA.");
    } catch (err) {
        showErrorToast("Error al obtener la imagen NDVI: " + err.message);
    }
}