// Modal Bootstrap para mostrar escenas EOSDA
function crearModalEscenasEOSDA() {
    let modal = document.getElementById('eosdaScenesModal');
    if (modal) return modal; // Ya existe
    modal = document.createElement('div');
    modal.id = 'eosdaScenesModal';
    modal.className = 'modal fade';
    modal.tabIndex = -1;
    // Estilos para hacer el modal responsive y con scroll
    modal.innerHTML = `
      <div class="modal-dialog modal-lg modal-dialog-centered" style="max-width: 95vw;">
        <div class="modal-content" style="max-height: 90vh; overflow: hidden;">
          <div class="modal-header">
            <h5 class="modal-title">Escenas satelitales EOSDA</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
          </div>
          <div class="modal-body" style="overflow-y: auto; max-height: 65vh;">
            <div id="eosdaScenesTableContainer">
              <div class="text-center">Cargando escenas...</div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    // Permitir cerrar el modal al hacer click fuera de él
    modal.addEventListener('click', function(e) {
      if (e.target === modal) {
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) bsModal.hide();
      }
    });
    return modal;
}


// Función para abrir el modal y mostrar las escenas
window.mostrarModalEscenasEOSDA = async function(parcelId) {
    const modal = crearModalEscenasEOSDA();
    // Usar Bootstrap 5
    const bsModal = new bootstrap.Modal(modal);
    // Limpiar contenido
    document.getElementById('eosdaScenesTableContainer').innerHTML = '<div class="text-center">Cargando escenas...</div>';
    bsModal.show();
    
    // Obtener eosda_id
    let eosda_id = null;
    try {
        const parcelResp = await axiosInstance.get(`/parcel/${parcelId}/`);
        eosda_id = parcelResp.data.eosda_id;
        if (!eosda_id) {
            document.getElementById('eosdaScenesTableContainer').innerHTML = '<div class="alert alert-danger">La parcela no tiene eosda_id configurado.</div>';
            return;
        }
        // Actualizar el estado global EOSDA para asegurar que esté disponible
        window.AGROTECH_STATE.selectedParcelId = parcelId;
        window.AGROTECH_STATE.selectedSatelliteId = eosda_id;
    } catch (err) {
        document.getElementById('eosdaScenesTableContainer').innerHTML = '<div class="alert alert-danger">Error al obtener la parcela.</div>';
        return;
    }
    
    // OPTIMIZACIÓN: Verificar cache de escenas primero
    const scenesCache = window.EOSDA_SCENES_CACHE || {};
    const sceneCacheKey = `scenes_${eosda_id}`;
    if (scenesCache[sceneCacheKey]) {
        console.log('[CACHE HIT] Escenas encontradas en cache frontend');
        renderScenesTable(scenesCache[sceneCacheKey]);
        return;
    }
    
    // Consultar escenas solo si no están en cache
    try {
        const token = localStorage.getItem("accessToken");
        const resp = await fetch(`${BASE_URL}/eosda-scenes/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ field_id: eosda_id })
        });
        const data = await resp.json();
        const scenes = data.scenes || [];
        
        // Guardar en cache frontend
        if (!window.EOSDA_SCENES_CACHE) window.EOSDA_SCENES_CACHE = {};
        window.EOSDA_SCENES_CACHE[sceneCacheKey] = scenes;
        console.log('[CACHE SET] Escenas guardadas en cache frontend');
        
        if (!scenes.length) {
            document.getElementById('eosdaScenesTableContainer').innerHTML = '<div class="alert alert-warning">No hay escenas disponibles para este campo.</div>';
            return;
        }
        
        renderScenesTable(scenes);
    } catch (err) {
        document.getElementById('eosdaScenesTableContainer').innerHTML = '<div class="alert alert-danger">Error al consultar escenas EOSDA.</div>';
    }
};

// Función helper para renderizar tabla de escenas
function renderScenesTable(scenes) {
    if (!scenes || scenes.length === 0) {
        document.getElementById('eosdaScenesTableContainer').innerHTML = '<p>No hay escenas disponibles.</p>';
        return;
    }

    // Filtrar escenas duplicadas: mantener solo la mejor calidad por fecha
    const uniqueScenes = [];
    const seenDates = new Set();
    
    // Ordenar por fecha desc y luego por calidad (menor nubosidad = mejor)
    const sortedScenes = [...scenes].sort((a, b) => {
        const dateCompare = new Date(b.date) - new Date(a.date);
        if (dateCompare !== 0) return dateCompare;
        
        // Si misma fecha, ordenar por nubosidad (menor es mejor)
        const cloudA = a.cloudCoverage ?? a.cloud ?? a.nubosidad ?? 100;
        const cloudB = b.cloudCoverage ?? b.cloud ?? b.nubosidad ?? 100;
        return cloudA - cloudB;
    });

    // Mantener solo la mejor escena por fecha
    for (const scene of sortedScenes) {
        const dateKey = scene.date ? scene.date.split('T')[0] : 'no-date';
        if (!seenDates.has(dateKey)) {
            seenDates.add(dateKey);
            uniqueScenes.push(scene);
        }
    }

    // No aplicar filtro de nubosidad aquí - se hace en showSceneSelectionTable (búsqueda por fechas)
    // Mostrar todas las escenas únicas ordenadas por fecha
    const finalScenes = uniqueScenes;

    let html = `<table class="table table-striped table-bordered">
        <thead>
            <tr>
                <th>Fecha</th>
                <th>View ID</th>
                <th>Nubosidad (%)</th>
                <th>NDVI</th>
                <th>NDMI</th>
                <th>SAVI</th>
                <th>Analytics</th>
            </tr>
        </thead>
        <tbody>
            ${finalScenes.map(scene => {
                // cloudCoverage, cloud o nubosidad
                let cloud = scene.cloudCoverage ?? scene.cloud ?? scene.nubosidad;
                let cloudText = (typeof cloud === 'number') ? cloud.toFixed(2) : (cloud || 'N/A');
                
                return `
                    <tr>
                        <td>${scene.date || '-'}</td>
                        <td>${scene.view_id || '-'}</td>
                        <td>${cloudText}</td>
                        <td><button class="btn btn-success btn-sm" onclick="procesarImagenEOSDA('${scene.view_id}', 'ndvi', this)">Ver NDVI</button></td>
                        <td><button class="btn btn-info btn-sm" onclick="procesarImagenEOSDA('${scene.view_id}', 'ndmi', this)">Ver NDMI</button></td>
                        <td><button class="btn btn-secondary btn-sm" style="background: linear-gradient(135deg, #8B4513, #228B22); border: none;" onclick="procesarImagenEOSDA('${scene.view_id}', 'savi', this)">Ver SAVI</button></td>
                        <td>
                            <button class="btn btn-warning btn-sm" onclick="obtenerAnalyticsEscena('${scene.view_id}', '${scene.date}')">📊 Stats</button>
                        </td>
                    </tr>
                `;
            }).join('')}
        </tbody>
    </table>`;
    document.getElementById('eosdaScenesTableContainer').innerHTML = html;
}

// Función para obtener analíticas científicas de una escena
window.obtenerAnalyticsEscena = async function(viewId, sceneDate) {
    try {
        console.log(`[ANALYTICS_ESCENA] Iniciando análisis para escena: ${viewId}, fecha: ${sceneDate}`);
        
        // Validar que la función de analíticas científicas esté disponible
        if (typeof window.obtenerAnalyticsCientifico !== 'function') {
            console.error('[ANALYTICS_ESCENA] Función de analíticas científicas no disponible');
            if (typeof showErrorToast === 'function') {
                showErrorToast('Error: Módulo de analíticas científicas no cargado');
            }
            return;
        }
        
        // Llamar a la función de analíticas científicas
        await window.obtenerAnalyticsCientifico(viewId, sceneDate);
        
    } catch (error) {
        console.error('[ANALYTICS_ESCENA] Error al obtener analíticas:', error);
        if (typeof showErrorToast === 'function') {
            showErrorToast(`Error al obtener analíticas: ${error.message}`);
        }
    }
};

// Función para buscar escenas EOSDA y mostrar el modal
export async function buscarEscenas(parcelId, viewer) {
  // Eliminado: toda la lógica de escenas EOSDA y NDVI. Esta función ya no realiza ninguna acción.
  // Si necesitas mostrar NDVI, hazlo directamente desde el botón o el flujo principal.
}
// Estado global centralizado para EOSDA
window.AGROTECH_STATE = {
  selectedParcelId: null,
  selectedSatelliteId: null,
  selectedScene: null, // NDVI
  selectedSceneNDMI: null, // NDMI
  ndviActive: false,
  ndmiActive: false,
  requestIds: {},
  // Nuevo: tracking de capa activa en analytics
  activeAnalyticsLayer: 'ndvi' // 'ndvi' o 'ndmi'
};
// --- CACHE DE IMÁGENES NDVI/NDMI ---
window.EOSDA_IMAGE_CACHE = window.EOSDA_IMAGE_CACHE || {};
// --- CACHE DE ESCENAS POR FIELD_ID ---
window.EOSDA_SCENES_CACHE = window.EOSDA_SCENES_CACHE || {};

// Función para limpiar cache cuando sea necesario
window.clearEOSDACache = function() {
    window.EOSDA_IMAGE_CACHE = {};
    window.EOSDA_SCENES_CACHE = {};
    window.AGROTECH_STATE.requestIds = {};
    console.log('[CACHE CLEARED] Cache de EOSDA limpiado');
};

// BASE_URL: Detectar correctamente el backend en desarrollo local
// En localhost, el frontend puede estar en puerto diferente (8080, 3000) que el backend (8000)
function getBaseUrl() {
    // Si ApiUrls está disponible, usarlo
    if (window.ApiUrls) {
        return window.ApiUrls.parcels();
    }
    
    // Detectar si estamos en localhost/desarrollo
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    
    if (isLocalhost) {
        // En desarrollo local, el backend Django está en puerto 8000
        return 'http://localhost:8000/api/parcels';
    }
    
    // En producción (Netlify), usar rutas relativas que el proxy redirige
    return '/api/parcels';
}

const BASE_URL = getBaseUrl();
console.log('[PARCEL.JS] BASE_URL configurado:', BASE_URL);

// Variables globales
let axiosInstance; // Declarar axiosInstance como global
let positions = []; // Almacena las posiciones del polígono (coordenadas lat/lng)
let currentPolygon = null; // Referencia al polígono dibujado en Leaflet
let drawnItems = null; // FeatureGroup para elementos dibujados

let map; // Declarar mapa Leaflet como global
let mapReady = false;



// Inicializar el mapa con Leaflet
function initializeLeaflet() {
    console.log('[LEAFLET] Iniciando carga del mapa...');
    
    // Verificar que Leaflet esté disponible
    if (typeof L === 'undefined') {
        console.error('[LEAFLET] Leaflet no está cargado. Reintentando en 500ms...');
        setTimeout(initializeLeaflet, 500);
        return;
    }

    try {
        // Configurar axios (mantener para el resto de la app)
        const token = localStorage.getItem("accessToken");
        if (!token) {
            console.error("No se encontró el token. Redirigiendo...");
            window.location.href = "/templates/authentication/login.html";
            return;
        }
        axiosInstance = axios.create({
            baseURL: BASE_URL,
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            }
        });
        window.axiosInstance = axiosInstance;

        // Interceptor de respuesta: maneja token expirado (401) automáticamente
        // Usa las funciones de api-utils.js con protección contra múltiples 401 simultáneos
        axiosInstance.interceptors.response.use(
            response => response,
            async error => {
                const originalRequest = error.config;
                const status = error.response?.status;
                
                if (status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;
                    console.warn('[AUTH] Token expirado (401), intentando refresh...');
                    
                    const refreshed = typeof window.refreshAccessToken === 'function'
                        ? await window.refreshAccessToken()
                        : false;
                    
                    if (refreshed) {
                        const newToken = localStorage.getItem('accessToken');
                        axiosInstance.defaults.headers['Authorization'] = `Bearer ${newToken}`;
                        originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
                        return axiosInstance.request(originalRequest);
                    } else {
                        // Redirect inmediato al login
                        if (typeof window.handleAuthFailure === 'function') {
                            window.handleAuthFailure();
                        } else {
                            // Fallback directo si api-utils.js no cargó
                            localStorage.removeItem('accessToken');
                            localStorage.removeItem('refreshToken');
                            window.location.href = '/templates/authentication/login.html';
                        }
                        // Retornar un error silencioso para no mostrar toasts de error
                        return Promise.reject(new Error('session_expired'));
                    }
                }
                return Promise.reject(error);
            }
        );

        // Inicializar el mapa Leaflet centrado en Colombia
        map = L.map('mapContainer', {
            center: [4.6097, -74.0817], // Colombia
            zoom: 6,
            zoomControl: true,
            attributionControl: true,
            fullscreenControl: false // Lo agregamos manualmente después
        });

        // Agregar la capa satelital Esri World Imagery
        const esriSatellite = L.tileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            {
                attribution: 'Esri, DigitalGlobe, GeoEye, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN, and the GIS User Community',
                maxZoom: 19 // Permitir máximo zoom posible para Esri
            }
        ).addTo(map);

        // Capa alternativa OpenStreetMap para zoom extremo
        const osm = L.tileLayer(
            'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 21 // OSM soporta zoom muy alto
            }
        );

        // Control de capas para alternar entre satélite y OSM
        L.control.layers({
            'Satélite Esri': esriSatellite,
            'OpenStreetMap': osm
        }).addTo(map);

        // Opcional: Agregar capa de etiquetas sobre el satélite para referencia
        const esriLabels = L.tileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
            {
                attribution: 'Esri',
                maxZoom: 19,
                opacity: 0.7
            }
        ).addTo(map);

        // 🔍 Agregar control de búsqueda de geocodificación (lupa)
        // Usando el proxy backend para evitar CORS
        if (typeof L.Control.Geocoder !== 'undefined') {
            L.Control.geocoder({
                defaultMarkGeocode: false,
                placeholder: 'Buscar ubicación...',
                errorMessage: 'No se encontró la ubicación',
                position: 'topright',
                geocoder: L.Control.Geocoder.nominatim({
                    serviceUrl: BASE_URL + '/geocode/', // Usar proxy backend
                    geocodingQueryParams: {
                        countrycodes: 'co', // Priorizar resultados en Colombia
                        limit: 5
                    }
                })
            }).on('markgeocode', function(e) {
                const bbox = e.geocode.bbox;
                const poly = L.polygon([
                    bbox.getSouthEast(),
                    bbox.getNorthEast(),
                    bbox.getNorthWest(),
                    bbox.getSouthWest()
                ]);
                map.fitBounds(poly.getBounds());
                // Agregar marcador temporal en la ubicación encontrada
                const marker = L.marker(e.geocode.center).addTo(map)
                    .bindPopup(e.geocode.name)
                    .openPopup();
                // Remover marcador después de 5 segundos
                setTimeout(() => {
                    map.removeLayer(marker);
                }, 5000);
            }).addTo(map);
            console.log('[LEAFLET] Control de búsqueda agregado (proxy backend)');
        } else {
            console.warn('[LEAFLET] Plugin Geocoder no disponible - verifique que el script esté cargado');
        }

        // 📺 Agregar control de pantalla completa
        if (typeof L.Control.Fullscreen !== 'undefined') {
            map.addControl(new L.Control.Fullscreen({
                position: 'topright',
                title: 'Ver en pantalla completa',
                titleCancel: 'Salir de pantalla completa'
            }));
            console.log('[LEAFLET] Control de pantalla completa agregado');
        } else {
            console.warn('[LEAFLET] Plugin Fullscreen no disponible - verifique que el script esté cargado');
        }

        console.log('[LEAFLET] Mapa satelital Esri World Imagery cargado correctamente');

        // Inicializar FeatureGroup para elementos dibujados
        drawnItems = new L.FeatureGroup();
        map.addLayer(drawnItems);

        // Agregar controles de dibujo
        setupDrawingTools(map);
        
        // Cargar parcelas
        loadParcels();
        
        // Marcar como listo
        mapReady = true;
        console.log('[LEAFLET] Inicialización completa');
        
    } catch (error) {
        console.error('[LEAFLET] Error durante inicialización:', error);
        
        // Mostrar mensaje amigable al usuario
        const mapContainer = document.getElementById('mapContainer');
        if (mapContainer) {
            mapContainer.innerHTML = `
                <div style="color: white; background: #c00; padding: 2em; text-align: center; margin: 2em;">
                    <h3>⚠️ Error al cargar el mapa</h3>
                    <p>${error.message}</p>
                    <button onclick="location.reload()" style="background: white; color: #c00; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px;">
                        🔄 Recargar página
                    </button>
                </div>
            `;
        }
    }
}

// 🔹 Función separada para manejar el dibujo con Leaflet
function setupDrawingTools(map) {
    // Referencia al botón de cancelar
    const cancelBtn = document.getElementById("cancel-button");

    // Inicializar control de dibujo de Leaflet
    const drawControl = new L.Control.Draw({
        draw: {
            polygon: {
                allowIntersection: false,
                shapeOptions: {
                    color: '#ff0000',
                    fillColor: '#ff0000',
                    fillOpacity: 0.5
                }
            },
            polyline: false,
            circle: false,
            rectangle: false,
            marker: false,
            circlemarker: false
        },
        edit: {
            featureGroup: drawnItems,
            remove: false
        }
    });
    map.addControl(drawControl);

    // Variable para controlar si estamos dibujando
    let isDrawing = false;

    // Funciones globales para iniciar y cancelar dibujo
    window.startDrawing = function () {
        // Limpiar cualquier dibujo previo
        drawnItems.clearLayers();
        positions = [];
        currentPolygon = null;
        
        // Activar modo de dibujo
        new L.Draw.Polygon(map, drawControl.options.draw.polygon).enable();
        isDrawing = true;
        
        cancelBtn.style.display = "block";
        console.log("[LEAFLET] Dibujo iniciado.");
    };

    window.cancelDrawing = function () {
        // Desactivar modo de dibujo
        map.fire('draw:drawstop');
        
        // Limpiar
        drawnItems.clearLayers();
        positions = [];
        currentPolygon = null;
        isDrawing = false;
        
        cancelBtn.style.display = "none";
        console.log("[LEAFLET] Dibujo cancelado.");
    };

    // Evento cuando se completa el dibujo
    map.on('draw:created', function (e) {
        const layer = e.layer;
        
        // Agregar al FeatureGroup
        drawnItems.addLayer(layer);
        currentPolygon = layer;
        
        // Extraer coordenadas [lat, lng]
        const latlngs = layer.getLatLngs()[0]; // Obtener array de LatLng
        positions = latlngs.map(latlng => [latlng.lat, latlng.lng]);
        
        console.log("[LEAFLET] Polígono dibujado con", positions.length, "vértices");
        
        // Ocultar botón cancelar
        if (cancelBtn) {
            cancelBtn.style.display = "none";
        }
        
        isDrawing = false;
    });

    // Evento cuando se inicia el dibujo
    map.on('draw:drawstart', function (e) {
        isDrawing = true;
        if (cancelBtn) {
            cancelBtn.style.display = "block";
        }
    });

    // Evento cuando se detiene el dibujo
    map.on('draw:drawstop', function (e) {
        isDrawing = false;
    });
}

// Función para abrir el modal
window.openModal = function () {
    document.getElementById("parcelModal").style.display = "block";
};

// Función para cerrar el modal
window.closeModal = function () {
    document.getElementById("parcelModal").style.display = "none";
};

// Función para guardar el polígono
function savePolygon() {
    // Validar si se ha dibujado un polígono
    if (!positions || positions.length === 0) {
        alert("Primero dibuje el polígono de la parcela antes de guardar.");
        return;
    }

    // Obtener los valores del formulario
    const name = document.getElementById("parcelName").value.trim();
    const description = document.getElementById("parcelDescription").value.trim();
    const fieldType = document.getElementById("parcelFieldType").value.trim();
    const soilType = document.getElementById("parcelSoilType").value.trim();
    const topography = document.getElementById("parcelTopography").value.trim();

    // Validar que el nombre esté completo
    if (!name) {
        alert("El campo 'Nombre' es obligatorio.");
        return;
    }

    // Convertir las posiciones [lat, lng] a GeoJSON [lng, lat]
    const coordinates = positions.map(pos => [pos[1], pos[0]]); // [lng, lat]

    // Cerrar el polígono (repetir el primer punto al final)
    coordinates.push(coordinates[0]);

    const geojson = {
        type: "Polygon",
        coordinates: [coordinates]
    };

    // Enviar los datos al backend (POST crea también en EOSDA y retorna el id)
    axiosInstance.post("/parcel/", {
        name,
        description,
        field_type: fieldType,
        soil_type: soilType,
        topography,
        geom: geojson
    })
    .then(response => {
        const data = response.data;
        if (data.eosda_id) {
            showInfoToast("Parcela guardada y sincronizada con EOSDA (ID: " + data.eosda_id + ")");
        } else {
            showErrorToast("Parcela guardada localmente, pero NO sincronizada con EOSDA.");
        }
        closeModal();
        location.reload();
    })
    .catch(error => {
        console.error("Error al guardar la parcela:", error);
        showErrorToast("Hubo un error al guardar la parcela. Revisa la consola para más detalles.");
    });
}

function loadParcels() {
    console.log("Iniciando carga de parcelas...");

    const token = localStorage.getItem("accessToken");
    if (!token) {
        console.error("No se encontró el token. Redirigiendo...");
        window.location.href = "/templates/authentication/login.html";
        return;
    }

    axiosInstance.get("/parcel/")
        .then(response => {
            console.log("Respuesta del backend para parcelas:", response.data);
            
            // Manejar diferentes formatos de respuesta
            let data;
            if (response.data.parcels && Array.isArray(response.data.parcels)) {
                data = response.data.parcels;
            } else if (response.data.results && Array.isArray(response.data.results)) {
                data = response.data.results;
            } else if (Array.isArray(response.data)) {
                data = response.data;
            } else {
                console.warn("Formato de respuesta inesperado:", response.data);
                data = [];
            }
            
            const tableBody = document.getElementById("parcelTable").getElementsByTagName("tbody")[0] || document.getElementById("parcelTable").appendChild(document.createElement("tbody"));
            tableBody.innerHTML = "";
            
            if (!data.length) {
                tableBody.innerHTML = `<tr><td colspan='7' class='text-center'>No hay parcelas registradas.</td></tr>`;
                return;
            }
            
            data.forEach(parcel => {
                const props = parcel.properties || parcel;
                const row = document.createElement("tr");
                
                // Agregar data-parcel-id para identificar la fila
                row.setAttribute('data-parcel-id', parcel.id);
                
                // Agregar evento de click para seleccionar parcela
                row.addEventListener('click', function(e) {
                    // No activar si se hizo click en un botón
                    if (e.target.closest('button')) return;
                    selectParcel(parcel);
                });
                
                row.innerHTML = `
                    <td>${props.name || "Sin nombre"}</td>
                    <td>${props.description || "Sin descripción"}</td>
                    <td>${props.field_type || "N/A"}</td>
                    <td>${props.soil_type || "N/A"}</td>
                    <td>${props.topography || "N/A"}</td>
                    <td>
                        <button class="btn btn-info btn-sm" onclick="flyToParcel(${parcel.id});" title="Ver Parcela">
                            <i class="bi bi-eye"></i> Ver
                        </button>
                    </td>
                    <td>
                        <button class="btn btn-primary btn-sm" onclick="editParcel('${parcel.id}')">Editar</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteParcel('${parcel.id}')">Eliminar</button>
                    </td>
                `;
                tableBody.appendChild(row);
                
                // Dibujar parcela en el mapa si tiene geometría
                if (parcel.geometry && parcel.geometry.coordinates && map) {
                    try {
                        // Convertir coordenadas GeoJSON [lng, lat] a Leaflet [lat, lng]
                        const coordinates = parcel.geometry.coordinates[0].map(coord => [coord[1], coord[0]]);
                        
                        // Crear polígono con borde verde oscuro
                        const polygon = L.polygon(coordinates, {
                            color: '#145A32', // Verde oscuro
                            weight: 2,
                            fillColor: 'transparent',
                            fillOpacity: 0
                        }).addTo(map);
                        
                        // Agregar popup con nombre
                        polygon.bindPopup(props.name || "Parcela sin nombre");
                        
                        // Guardar referencia en el polígono para identificarlo después
                        polygon.parcelId = parcel.id;
                        
                        // Agregar evento de click al polígono para seleccionar
                        polygon.on('click', function() {
                            selectParcel(parcel);
                        });
                        
                    } catch (error) {
                        console.error("Error dibujando parcela en el mapa:", error);
                    }
                }
            });
        })
        .catch(error => {
            // Si es error de sesión expirada, no mostrar toast (el interceptor ya redirige)
            if (error.message === 'session_expired') return;
            
            const status = error.response?.status;
            if (status === 401) {
                console.warn('[AUTH] Error 401 en loadParcels, sesión expirada.');
                if (typeof window.handleAuthFailure === 'function') {
                    window.handleAuthFailure();
                }
            } else {
                console.error("Error al cargar las parcelas:", error);
                showErrorToast("Error al cargar las parcelas. Por favor recarga la página.");
            }
        });
}

/**
 * Selecciona una parcela y actualiza el estado global
 * @param {Object} parcel - Datos de la parcela
 */
function selectParcel(parcel) {
    console.log('[SELECT_PARCEL] Seleccionando parcela:', parcel.id, parcel.name);
    
    // Actualizar estado global
    window.AGROTECH_STATE.selectedParcelId = parcel.id;
    window.AGROTECH_STATE.selectedSatelliteId = parcel.eosda_id || null;
    
    // Calcular área si hay geometría
    let areaHectares = 0;
    if (parcel.geometry && parcel.geometry.coordinates) {
        areaHectares = polygonAreaHectares(parcel.geometry.coordinates[0]);
    } else if (parcel.geom && parcel.geom.coordinates) {
        areaHectares = polygonAreaHectares(parcel.geom.coordinates[0]);
    }
    
    // Crear objeto con datos de la parcela para la UI
    const parcelData = {
        id: parcel.id,
        name: parcel.name || parcel.properties?.name || 'Sin nombre',
        area_hectares: areaHectares,
        eosda_id: parcel.eosda_id
    };
    
    // Actualizar UI usando la función global si existe
    if (typeof window.updateSelectedParcelBanner === 'function') {
        window.updateSelectedParcelBanner(parcelData);
    }
    
    // Highlight en la tabla
    document.querySelectorAll('#parcelTable tbody tr').forEach(row => {
        row.classList.remove('table-success', 'selected-parcel');
    });
    const selectedRow = document.querySelector(`#parcelTable tbody tr[data-parcel-id="${parcel.id}"]`);
    if (selectedRow) {
        selectedRow.classList.add('table-success', 'selected-parcel');
    }
    
    // Toast de confirmación
    if (typeof showInfoToast === 'function') {
        showInfoToast(`📍 Parcela "${parcelData.name}" seleccionada`);
    }
    
    // Cargar ciclo de cultivo activo (si el módulo está disponible)
    if (window.AgrotechCropCycles && typeof window.AgrotechCropCycles.showCropCycleBadge === 'function') {
        window.AgrotechCropCycles.showCropCycleBadge(parcel.id);
    }
}
window.selectParcel = selectParcel;

import { showErrorToast, showInfoToast, showWarningToast, showNDVIToggleButton, showNDMIToggleButton, showSceneSelectionModal } from "./layers.js";

// Calcula el área de un polígono en coordenadas [lon, lat] (GeoJSON) en metros cuadrados
function polygonAreaHectares(coords) {
    // Usa el algoritmo del área esférica de Shoelace adaptado a la Tierra
    // coords: [[lon, lat], ...]
    if (!coords || coords.length < 3) return 0;
    const R = 6378137; // Radio de la Tierra en metros
    let area = 0;
    for (let i = 0, len = coords.length; i < len; i++) {
        const [lon1, lat1] = coords[i];
        const [lon2, lat2] = coords[(i + 1) % len];
        area += (toRad(lon2) - toRad(lon1)) * (2 + Math.sin(toRad(lat1)) + Math.sin(toRad(lat2)));
    }
    area = area * R * R / 2.0;
    return Math.abs(area) / 10000; // m² a hectáreas
}
function toRad(deg) {
    return deg * Math.PI / 180;
}

function showWaterStressLayer(viewer) {
    if (!window.SENTINEL_WATER_STRESS_WMTS) {
        console.error("La URL de la capa de estrés hídrico no está definida.");
        return;
    }

    const waterStressLayer = viewer.imageryLayers.addImageryProvider(
        new Cesium.WebMapTileServiceImageryProvider({
            url: window.SENTINEL_WATER_STRESS_WMTS,
            layer: "water_stress",
            style: "default",
            format: "image/png",
            tileMatrixSetID: "EPSG:3857",
        })
    );

    console.log("Capa de estrés hídrico mostrada.");
    return waterStressLayer;
}

// Mostrar el botón de estrés hídrico
function showWaterStressToggleButton(viewer) {
    let waterStressBtn = document.getElementById("waterStressToggle");
    let ndviContainer = document.getElementById("ndviBtnContainer");
    if (!waterStressBtn) {
        waterStressBtn = document.createElement("button");
        waterStressBtn.id = "waterStressToggle";
        waterStressBtn.innerText = "Mostrar Estrés Hídrico";
        waterStressBtn.className = "btn btn-info";
        waterStressBtn.style.marginLeft = "12px";
    }
    waterStressBtn.style.display = "inline-block";
    let waterStressLayer = null;
    waterStressBtn.onclick = () => {
        if (waterStressLayer) {
            viewer.imageryLayers.remove(waterStressLayer);
            waterStressLayer = null;
            waterStressBtn.textContent = "Mostrar Estrés Hídrico";
        } else {
            waterStressLayer = showWaterStressLayer(viewer);
            waterStressBtn.textContent = "Ocultar Estrés Hídrico";
        }
    };
    // Insertar el botón junto al de NDVI
    if (ndviContainer && !ndviContainer.contains(waterStressBtn)) {
        ndviContainer.appendChild(waterStressBtn);
    }
}

function flyToParcel(parcelId) {
    if (!mapReady || !map) {
        alert("El mapa aún no está listo. Intenta en unos segundos.");
        return;
    }

    // Eliminar resaltados previos (polígonos amarillos temporales)
    map.eachLayer(function (layer) {
        if (layer.options && layer.options.className === 'highlighted-parcel') {
            map.removeLayer(layer);
        }
    });

    // Obtener la geometría y centrar el mapa
    axiosInstance.get(`/parcel/${parcelId}/`)
        .then(async response => {
            const feature = response.data;
            let coordinates = [];
            
            if (feature.geometry && feature.geometry.coordinates) {
                // Convertir GeoJSON [lng, lat] a Leaflet [lat, lng]
                coordinates = feature.geometry.coordinates[0].map(coord => [coord[1], coord[0]]);
            } else if (feature.geom && feature.geom.coordinates) {
                coordinates = feature.geom.coordinates[0].map(coord => [coord[1], coord[0]]);
            } else {
                console.error("La geometría de la parcela no es válida.");
                alert("La parcela seleccionada no tiene geometría válida.");
                return;
            }
            
            if (coordinates.length < 3) {
                console.error("La parcela seleccionada no tiene suficientes vértices para formar un polígono válido.");
                alert("La parcela seleccionada no es válida. Por favor, verifica los datos.");
                return;
            }
            
            // Guardar coordenadas en variable global (para savePolygon si es necesario)
            window.positions = coordinates;
            
            // Calcular área en hectáreas y mostrar en el cuadro de datos
            let areaHect = 0;
            if (feature.geometry && feature.geometry.coordinates) {
                areaHect = polygonAreaHectares(feature.geometry.coordinates[0]);
            } else if (feature.geom && feature.geom.coordinates) {
                areaHect = polygonAreaHectares(feature.geom.coordinates[0]);
            }
            const areaCell = document.getElementById("parcelAreaCell");
            if (areaCell) {
                areaCell.textContent = `${areaHect.toLocaleString(undefined, {maximumFractionDigits: 2})} ha`;
            }
            
            // Centrar el mapa en la parcela con animación
            const bounds = L.latLngBounds(coordinates);
            map.flyToBounds(bounds, {
                padding: [50, 50],
                duration: 2.5,
                maxZoom: 16
            });
            
            console.log(`[FLY_TO_PARCEL] Vista centrada en parcela ${parcelId}`);
            
            // Eliminar cualquier resaltado previo
            if (window.selectedParcelLayer) {
                map.removeLayer(window.selectedParcelLayer);
            }
            
            // Crear resaltado amarillo PERMANENTE para la parcela seleccionada
            window.selectedParcelLayer = L.polygon(coordinates, {
                color: '#FFFF00', // Amarillo
                weight: 4,
                fillColor: '#FFFF00',
                fillOpacity: 0.3,
                className: 'selected-parcel-highlight',
                interactive: false // No interfiere con clics en el mapa
            }).addTo(map);
            
            // Guardar referencia del ID de parcela seleccionada
            window.selectedParcelId = parcelId;
            
            console.log(`[FLY_TO_PARCEL] Parcela ${parcelId} seleccionada y resaltada permanentemente`);

            // Actualizar estado global EOSDA
            window.AGROTECH_STATE.selectedParcelId = parcelId;
            window.AGROTECH_STATE.selectedSatelliteId = feature.eosda_id || null;
            window.AGROTECH_STATE.selectedScene = null;
            window.AGROTECH_STATE.ndviActive = false;
            window.AGROTECH_STATE.requestIds = {};

            // Establecer parcela seleccionada para gráfico histórico
            if (typeof window.setSelectedParcelForChart === 'function') {
                window.setSelectedParcelForChart(parcelId);
            }

            // Actualizar parcela seleccionada para análisis meteorológico
            if (typeof window.loadMeteorologicalAnalysis === 'function') {
                window.currentParcelId = parcelId;
            }
            
            if (typeof window.setSelectedParcelForMeteoAnalysis === 'function') {
                window.setSelectedParcelForMeteoAnalysis(parcelId);
            }

            // Actualizar datos de la parcela en el panel
            const parcelNameCell = document.getElementById("parcelNameCell");
            if (parcelNameCell) {
                parcelNameCell.textContent = feature.name || `Parcela ${parcelId}`;
            }

            // Actualizar el botón NDVI
            import('./layers.js').then(mod => {
                mod.showNDVIToggleButton(map);
            }).catch(err => {
                console.warn('[FLY_TO_PARCEL] No se pudo cargar layers.js:', err);
            });
        })
        .catch(error => {
            console.error("Error al centrar en la parcela:", error);
            alert("Hubo un error al centrar el mapa en la parcela.\n" + (error.message || JSON.stringify(error)));
        });
}


function saveEditedParcel() {    
    const form = document.getElementById("editParcelForm");
    const parcelId = form.getAttribute("data-parcel-id");

    // Obtener los valores del formulario
    const name = document.getElementById("editParcelName").value.trim();
    const description = document.getElementById("editParcelDescription").value.trim();
    const fieldType = document.getElementById("editParcelFieldType").value.trim();
    const soilType = document.getElementById("editParcelSoilType").value.trim();
    const topography = document.getElementById("editParcelTopography").value.trim();

    // Validar que el nombre esté completo
    if (!name) {
        alert("El campo 'Nombre' es obligatorio.");
        return;
    }

    // Enviar los datos al backend
    axiosInstance.put(`/parcel/${parcelId}/`, {
        name: name,
        description: description,
        field_type: fieldType,
        soil_type: soilType,
        topography: topography
    })
    .then(response => {
        alert("Parcela actualizada con éxito.");
        closeEditModal(); // Cerrar el modal
        loadParcels(); // Recargar la tabla
    })
    .catch(error => {
        console.error("Error al actualizar la parcela:", error);
        alert("Hubo un error al actualizar la parcela. Revisa la consola para más detalles.");
    });
}
function deleteParcel(parcelId) {
    if (confirm("¿Estás seguro de que deseas eliminar esta parcela?")) {
        axiosInstance.delete(`/parcel/${parcelId}/`)
            .then(response => {
                alert("Parcela eliminada con éxito.");
                loadParcels(); // Recargar la tabla
            })
            .catch(error => {
                console.error("Error al eliminar la parcela:", error);
                alert("Hubo un error al eliminar la parcela. Revisa la consola para más detalles.");
            });
    }
}


// Eliminar funciones y dashboard meteorológico

window.flyToParcel = flyToParcel;
window.savePolygon = savePolygon;
window.saveEditedParcel = saveEditedParcel;
window.deleteParcel = deleteParcel; 

// Ejecutar al cargar la página
document.addEventListener("DOMContentLoaded", () => {
    // PRIMERO: Verificar autenticación ANTES de cualquier otra cosa
    const token = localStorage.getItem('accessToken');
    if (!token || token === 'null' || token === 'undefined' || token.trim() === '') {
        console.warn('[AUTH] No hay token de acceso. Redirigiendo a login...');
        if (typeof window.handleAuthFailure === 'function') {
            window.handleAuthFailure();
        } else {
            window.location.href = '/templates/authentication/login.html';
        }
        return;
    }

    // Verificar si el token JWT ya expiró (sin hacer petición al backend)
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const expTime = payload.exp * 1000; // JWT exp está en segundos
        const now = Date.now();
        if (expTime < now) {
            console.warn('[AUTH] Token JWT ya expirado. Intentando refresh...');
            // Intentar refresh automático
            const doRefresh = async () => {
                const refreshed = typeof window.refreshAccessToken === 'function'
                    ? await window.refreshAccessToken()
                    : false;
                if (refreshed) {
                    console.log('[AUTH] Token refrescado al inicio. Continuando...');
                    location.reload(); // Recargar con el token nuevo
                } else {
                    console.warn('[AUTH] No se pudo refrescar token al inicio. Redirigiendo a login...');
                    if (typeof window.handleAuthFailure === 'function') {
                        window.handleAuthFailure();
                    } else {
                        localStorage.removeItem('accessToken');
                        localStorage.removeItem('refreshToken');
                        window.location.href = '/templates/authentication/login.html';
                    }
                }
            };
            doRefresh();
            return;
        }
    } catch (e) {
        // Si el token no es un JWT válido, continuar y dejar que el backend lo rechace
        console.warn('[AUTH] No se pudo decodificar el token JWT:', e.message);
    }

    // SEGUNDO: Verificar que Leaflet exista
    if (typeof L === 'undefined') {
        console.error('[LEAFLET] Leaflet no está disponible. Verifica la importación del script.');
        
        // Mostrar mensaje al usuario
        const mapContainer = document.getElementById('mapContainer');
        if (mapContainer) {
            mapContainer.innerHTML = `
                <div style="color: white; background: #c00; padding: 2em; text-align: center; margin: 2em;">
                    <h3>⚠️ Error: Leaflet no se cargó correctamente</h3>
                    <p>Verifica que el script de Leaflet esté incluido en el HTML.</p>
                    <button onclick="location.reload()" style="background: white; color: #c00; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px;">
                        🔄 Recargar página
                    </button>
                </div>
            `;
        }
        return;
    }
    
    // SEGUNDO: Inicializar Leaflet
    initializeLeaflet();
    
    // TERCERO: Resto de inicializaciones
    // Inicializar UX de filtro de imágenes
    setupImageFilterUX();
    
    // Inicializar módulo de análisis meteorológico si está disponible
    if (typeof window.initMeteorologicalAnalysis === 'function') {
        console.log('[PARCEL] Inicializando módulo de análisis meteorológico');
        window.initMeteorologicalAnalysis();
    } else {
        console.warn('[PARCEL] El módulo de análisis meteorológico no está disponible');
    }
});

// UX Mejorado: Filtrar imágenes por rango de fechas
// Habilita/deshabilita el filtro según selección de parcela y fechas
// UX: Alertas y validación para el botón de escenas satelitales
function setupImageFilterUX() {
    const tituloFiltro = document.getElementById("imageFilterTitle");
    const fechaInicio = document.getElementById("fechaInicioInput");
    const fechaFin = document.getElementById("fechaFinInput");
    const btnEscenas = document.getElementById("escenasSatelitalesBtn");
    const tooltip = document.getElementById("imageFilterTooltip");

    // Cambiar el título
    if (tituloFiltro) tituloFiltro.textContent = "Buscar escenas satelitales";
    // Tooltip aclaratorio
    if (tooltip) {
        tooltip.title = "Selecciona primero una parcela y luego el rango de fechas para buscar imágenes satelitales disponibles.";
        tooltip.setAttribute('data-bs-toggle', 'tooltip');
        tooltip.setAttribute('data-bs-placement', 'top');
        new bootstrap.Tooltip(tooltip);
    }
    // Deshabilitar el botón hasta que todo esté seleccionado
    function updateButtonState() {
        const parcelaSeleccionada = !!window.AGROTECH_STATE.selectedParcelId;
        const fechasValidas = fechaInicio.value && fechaFin.value;
        btnEscenas.disabled = !(parcelaSeleccionada && fechasValidas);
    }
    if (fechaInicio) fechaInicio.addEventListener('change', updateButtonState);
    if (fechaFin) fechaFin.addEventListener('change', updateButtonState);
    document.addEventListener('parcelSelected', updateButtonState);
    updateButtonState();
    // Acción de búsqueda con alertas UX
    if (btnEscenas) {
        btnEscenas.onclick = async function() {
            const parcelaSeleccionada = !!window.AGROTECH_STATE.selectedParcelId;
            const fechasValidas = fechaInicio.value && fechaFin.value;
            if (!parcelaSeleccionada && !fechasValidas) {
                showErrorToast("Debes seleccionar primero una parcela y el rango de fechas.");
                return;
            }
            if (!parcelaSeleccionada) {
                showErrorToast("Selecciona primero una parcela antes de buscar escenas satelitales.");
                return;
            }
            if (!fechasValidas) {
                showErrorToast("Selecciona el rango de fechas antes de buscar escenas satelitales.");
                return;
            }
            const parcelId = window.AGROTECH_STATE.selectedParcelId;
            const startDate = fechaInicio.value;
            const endDate = fechaFin.value;
            await buscarEscenasPorRango(parcelId, startDate, endDate);
        };
    }

    // Configurar evento para botón de análisis meteorológico
    const btnAnalisisMeteorologico = document.getElementById("analisisMeteorologicoBtn");
    if (btnAnalisisMeteorologico) {
        btnAnalisisMeteorologico.onclick = function() {
            const parcelaSeleccionada = !!window.AGROTECH_STATE.selectedParcelId;
            
            if (!parcelaSeleccionada) {
                showErrorToast("Selecciona primero una parcela para ver el análisis meteorológico.");
                return;
            }
            
            const parcelId = window.AGROTECH_STATE.selectedParcelId;
            
            // Mostrar la sección de análisis meteorológico
            const meteorologicalSection = document.getElementById("meteorologicalAnalysisSection");
            if (meteorologicalSection) {
                meteorologicalSection.style.display = "block";
                
                // Actualizar explícitamente el estado global antes de llamar a la función
            window.AGROTECH_STATE.selectedParcelId = parcelId;
            console.log('[PARCEL] Parcela seleccionada actualizada en estado global:', parcelId);
            
            // Llamar a la función de carga de análisis meteorológico si está disponible
            if (typeof window.loadMeteorologicalAnalysis === 'function') {
                console.log('[PARCEL] Cargando análisis meteorológico para parcela', parcelId);
                window.loadMeteorologicalAnalysis(parcelId);
            } else {
                console.warn('[PARCEL] Función loadMeteorologicalAnalysis no disponible');
            }
            } else {
                console.error('[PARCEL] Sección meteorológicalAnalysisSection no encontrada');
            }
        };
    }
}

// Lógica para buscar escenas por rango de fechas y mostrar el modal
// Cache de escenas por rango de fechas y parcela
window.EOSDA_SCENES_CACHE = window.EOSDA_SCENES_CACHE || {};

async function buscarEscenasPorRango(parcelId, startDate, endDate) {
    const cacheKey = `${parcelId}_${startDate}_${endDate}`;
    if (window.EOSDA_SCENES_CACHE[cacheKey]) {
        await showSceneSelectionTable(window.EOSDA_SCENES_CACHE[cacheKey]);
        return;
    }
    try {
        showSpinner();
        const resp = await axiosInstance.get(`/parcel/${parcelId}/scenes/?start_date=${startDate}&end_date=${endDate}`);
        hideSpinner();
        const scenes = resp.data.scenes || [];
        window.EOSDA_SCENES_CACHE[cacheKey] = scenes;
        if (scenes.length === 0) {
            showInfoToast("No se encontraron imágenes para ese rango de fechas.");
            return;
        }
        await showSceneSelectionTable(scenes);
    } catch (err) {
        hideSpinner();
        
        // Manejo específico de error 402 (límite excedido)
        if (err.response && err.response.status === 402) {
            const errorData = err.response.data || {};
            console.error('[EOSDA_LIMIT_ERROR] Límite de requests excedido:', errorData);
            
            showErrorToast(
                "⚠️ API satelital: Límite de consultas excedido. " +
                "Se ha alcanzado el límite mensual de la API de imágenes satelitales. " +
                "Contacte al administrador del sistema.",
                { duration: 10000 } // Toast más largo para este error crítico
            );
            
            // Mostrar modal con más información
            if (confirm(
                "❌ LÍMITE DE API EOSDA EXCEDIDO\n\n" +
                "Se ha alcanzado el límite mensual de consultas a API satelital Connect.\n" +
                "• Límite: 1000 requests/mes\n" +
                "• Estado: Excedido\n\n" +
                "¿Desea contactar al administrador?"
            )) {
                window.open('mailto:admin@agrotech.com?subject=Límite API satelital Excedido&body=Se necesita renovar el plan de API satelital Connect');
            }
            return;
        }
        
        // Manejo específico de error 404 (campo no encontrado)
        if (err.response && err.response.status === 404) {
            const errorData = err.response.data || {};
            console.error('[EOSDA_FIELD_ERROR] Campo no encontrado en EOSDA:', errorData);
            
            showErrorToast(
                "🔍 Campo no encontrado en EOSDA. " +
                `El campo ID ${errorData.field_id} no existe en la API de imágenes satelitales. ` +
                "Verifique la configuración del campo.",
                { duration: 8000 }
            );
            
            // Mostrar modal con información técnica
            if (confirm(
                "❌ CAMPO NO ENCONTRADO EN EOSDA\n\n" +
                `El campo con ID ${errorData.field_id} no existe en API satelital Connect.\n\n` +
                "Posibles causas:\n" +
                "• El campo no está registrado en EOSDA\n" +
                "• Cambio de API key\n" +
                "• Error en la configuración\n\n" +
                "¿Desea reportar este problema?"
            )) {
                window.open(`mailto:admin@agrotech.com?subject=Campo EOSDA No Encontrado&body=Campo ID: ${errorData.field_id}%0AError: ${errorData.error}`);
            }
            return;
        }
        
        // Error genérico
        console.error('[SCENES_ERROR] Error buscando escenas:', err);
        showErrorToast("Error al buscar imágenes satelitales: " + (err.message || err));
    }
}

// Las URLs WMTS/TMS de EOSDA ahora deben apuntar al proxy backend para evitar CORS y proteger el token.
// Función profesional para buscar escenas y construir URLs WMTS usando el nuevo endpoint de búsqueda
async function fetchEosdaWmtsUrls(polygonGeoJson) {
    // Buscar la fecha más reciente disponible (por ejemplo, hace 10 días)
    const today = new Date();
    const daysAgo = 10;
    const fechaNDVI = new Date(today.getFullYear(), today.getMonth(), today.getDate() - daysAgo)
        .toISOString().split('T')[0];
    // Usar hostname dinámico para el proxy WMTS
    const baseProxy = window.ApiUrls ? window.ApiUrls.eosdaWmts() + '/' : 
                     `${window.location.protocol}//${window.location.hostname}:8000/api/parcels/eosda-wmts-tile/`;
    // const ndviUrl = ...; const ndmiUrl = ...; Eliminado. Usar Render API.
    return { ndvi: ndviUrl, ndmi: ndmiUrl };
}

// Tabla/modal profesional para que el usuario elija la escena satelital a visualizar
async function showSceneSelectionTable(scenes) {
    console.log('[SCENES_TABLE] Mostrando tabla con escenas:', scenes);
    return new Promise((resolve) => {
        // Si ya existe el modal, elimínalo
        let oldModal = document.getElementById("sceneSelectionModal");
        if (oldModal) oldModal.remove();

        // Aplicar el mismo filtro de nubes que en la tabla principal
        if (!scenes || scenes.length === 0) {
            alert('No hay escenas disponibles');
            resolve({ ndvi: null, ndmi: null });
            return;
        }

        // Filtrar escenas duplicadas: mantener solo la mejor calidad por fecha
        const uniqueScenes = [];
        const seenDates = new Set();
        
        // Ordenar por fecha desc y luego por calidad (menor nubosidad = mejor)
        const sortedScenes = [...scenes].sort((a, b) => {
            const dateCompare = new Date(b.date) - new Date(a.date);
            if (dateCompare !== 0) return dateCompare;
            
            // Si misma fecha, ordenar por nubosidad (menor es mejor)
            const cloudA = a.cloudCoverage ?? a.cloud ?? a.nubosidad ?? 100;
            const cloudB = b.cloudCoverage ?? b.cloud ?? b.nubosidad ?? 100;
            return cloudA - cloudB;
        });

        // Mantener solo la mejor escena por fecha
        for (const scene of sortedScenes) {
            const dateKey = scene.date ? scene.date.split('T')[0] : 'no-date';
            if (!seenDates.has(dateKey)) {
                seenDates.add(dateKey);
                uniqueScenes.push(scene);
            }
        }

        // Filtrar escenas por umbral de cobertura de nubes (≤75%)
        const CLOUD_THRESHOLD = 100;
        const lowCloudScenes = uniqueScenes.filter(scene => {
            const cloud = scene.cloudCoverage ?? scene.cloud ?? scene.nubosidad ?? 0;
            return cloud <= CLOUD_THRESHOLD;
        });
        
        const filteredCount = uniqueScenes.length - lowCloudScenes.length;
        const finalScenes = lowCloudScenes.length > 0 ? lowCloudScenes : uniqueScenes.slice(0, 5); // Fallback: mostrar las 5 mejores

        // Crear modal con estilo neomórfico mejorado
        const modal = document.createElement("div");
        modal.id = "sceneSelectionModal";
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(4px);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.2s ease;
        `;

        // Contenido del modal con diseño profesional
        const content = document.createElement("div");
        content.style.cssText = `
            background: linear-gradient(145deg, #ffffff, #f5f7fa);
            padding: 0;
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.25), 0 0 0 1px rgba(255,255,255,0.1);
            max-width: 750px;
            width: 95%;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        `;

        // Header del modal
        const header = document.createElement("div");
        header.style.cssText = `
            background: linear-gradient(135deg, #2E7D32, #4CAF50);
            padding: 20px 28px;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        `;
        header.innerHTML = `
            <div>
                <h4 style="margin:0;font-weight:700;font-size:18px;">�️ Imágenes Satelitales Disponibles</h4>
                <p style="margin:5px 0 0;font-size:13px;opacity:0.9;">${finalScenes.length} escenas encontradas</p>
            </div>
            <button id="closeSceneModal" style="background:rgba(255,255,255,0.2);border:none;color:white;width:36px;height:36px;border-radius:50%;cursor:pointer;font-size:18px;display:flex;align-items:center;justify-content:center;">
                <i class="fas fa-times"></i>
            </button>
        `;
        content.appendChild(header);

        // Cuerpo con scroll
        const body = document.createElement("div");
        body.style.cssText = `
            padding: 20px 28px;
            overflow-y: auto;
            flex: 1;
            max-height: calc(85vh - 140px);
        `;

        // Mensaje informativo sobre nubosidad
        const infoBox = document.createElement("div");
        infoBox.style.cssText = `
            margin-bottom: 16px;
            padding: 14px 16px;
            border-radius: 12px;
            background: linear-gradient(135deg, #e3f2fd, #bbdefb);
            border-left: 4px solid #2196F3;
            font-size: 13px;
            line-height: 1.5;
        `;
        infoBox.innerHTML = `
            <strong>💡 Sobre la nubosidad:</strong> Las imágenes con <span style="color:#28a745;font-weight:600;">menos del 30% de nubes</span> 
            proporcionan análisis más precisos. Las marcadas en rojo tienen alta nubosidad.
        `;
        body.appendChild(infoBox);

        // Mensaje informativo sobre filtrado
        if (filteredCount > 0) {
            const filterMessage = document.createElement("div");
            filterMessage.style.cssText = `
                margin-bottom: 16px;
                padding: 12px 16px;
                border-radius: 12px;
                font-size: 13px;
                ${lowCloudScenes.length > 0 
                    ? 'background: #d1ecf1; color: #0c5460; border-left: 4px solid #17a2b8;' 
                    : 'background: #fff3cd; color: #856404; border-left: 4px solid #ffc107;'}
            `;
            filterMessage.innerHTML = lowCloudScenes.length > 0
                ? `<i class="fas fa-filter"></i> Se ocultaron ${filteredCount} imagen(es) con más del 75% de nubes.`
                : `<i class="fas fa-exclamation-triangle"></i> <strong>Atención:</strong> Todas las imágenes tienen alta nubosidad. Considera otro rango de fechas.`;
            body.appendChild(filterMessage);
        }

        // Tabla con diseño glassmorphism mejorado
        const tableContainer = document.createElement("div");
        tableContainer.style.cssText = `
            border-radius: 16px;
            overflow: hidden;
            background: rgba(255,255,255,0.6);
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.05),
                        inset 0 1px 1px rgba(255,255,255,0.8);
            border: 1px solid rgba(255,255,255,0.5);
        `;
        
        const table = document.createElement("table");
        table.style.cssText = `
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        `;
        table.innerHTML = `
            <thead>
                <tr style="background: linear-gradient(135deg, rgba(46,125,50,0.1), rgba(76,175,80,0.05));">
                    <th style="padding:16px 14px;text-align:left;font-weight:700;color:#2E7D32;border-bottom:2px solid rgba(46,125,50,0.2);font-size:13px;">📅 Fecha</th>
                    <th style="padding:16px 14px;text-align:center;font-weight:700;color:#2E7D32;border-bottom:2px solid rgba(46,125,50,0.2);font-size:13px;">☁️ Nubes</th>
                    <th style="padding:16px 14px;text-align:center;font-weight:700;color:#2E7D32;border-bottom:2px solid rgba(46,125,50,0.2);font-size:13px;">🌱 NDVI</th>
                    <th style="padding:16px 14px;text-align:center;font-weight:700;color:#2E7D32;border-bottom:2px solid rgba(46,125,50,0.2);font-size:13px;">💧 NDMI</th>
                    <th style="padding:16px 14px;text-align:center;font-weight:700;color:#2E7D32;border-bottom:2px solid rgba(46,125,50,0.2);font-size:13px;">🌿 SAVI</th>
                    <th style="padding:16px 14px;text-align:center;font-weight:700;color:#2E7D32;border-bottom:2px solid rgba(46,125,50,0.2);font-size:13px;">📊 Stats</th>
                </tr>
            </thead>
            <tbody>
                ${finalScenes.map((scene, idx) => {
                    let cloud = scene.cloudCoverage ?? scene.cloud ?? scene.nubosidad;
                    let cloudText = (typeof cloud === 'number') ? cloud.toFixed(1) : (cloud ? cloud : '-');
                    
                    // Badge y estilo por nivel de nubosidad
                    let cloudBadge = '', rowBg = '';
                    if (typeof cloud === 'number') {
                        if (cloud <= 30) {
                            cloudBadge = '<span style="background:linear-gradient(135deg,#28a745,#20c997);color:#fff;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:600;box-shadow:0 2px 8px rgba(40,167,69,0.3);">✓ Óptima</span>';
                            rowBg = 'background:rgba(240,255,244,0.7);';
                        } else if (cloud <= 50) {
                            cloudBadge = '<span style="background:linear-gradient(135deg,#ffc107,#ffca2c);color:#000;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:600;box-shadow:0 2px 8px rgba(255,193,7,0.3);">⚠ Aceptable</span>';
                            rowBg = 'background:rgba(255,251,240,0.7);';
                        } else {
                            cloudBadge = '<span style="background:linear-gradient(135deg,#dc3545,#c82333);color:#fff;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:600;box-shadow:0 2px 8px rgba(220,53,69,0.3);">✗ No recomendada</span>';
                            rowBg = 'background:rgba(255,245,245,0.7);';
                        }
                    }
                    
                    const dateFormatted = scene.date ? new Date(scene.date).toLocaleDateString('es-ES', { 
                        weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' 
                    }) : '-';
                    
                    return `
                        <tr style="${rowBg} transition: all 0.3s ease;" 
                            onmouseover="this.style.background='rgba(232,245,233,0.9)';this.style.transform='scale(1.01)'" 
                            onmouseout="this.style.background='${rowBg.replace('background:', '').replace(';', '') || 'transparent'}';this.style.transform='scale(1)'">
                            <td style="padding:14px;border-bottom:1px solid rgba(0,0,0,0.05);font-weight:600;color:#333;">${dateFormatted}</td>
                            <td style="padding:14px;border-bottom:1px solid rgba(0,0,0,0.05);text-align:center;">
                                <div style="font-weight:600;color:#555;">${cloudText}%</div>
                                <div style="margin-top:6px;">${cloudBadge}</div>
                            </td>
                            <td style="padding:14px;border-bottom:1px solid rgba(0,0,0,0.05);text-align:center;">
                                <button class="btn btn-sm" data-ndvi-idx="${idx}" style="background:linear-gradient(135deg,#4CAF50,#2E7D32);color:white;border:none;padding:10px 18px;border-radius:12px;font-weight:600;cursor:pointer;box-shadow:0 4px 15px rgba(76,175,80,0.3);transition:all 0.3s ease;" onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(76,175,80,0.4)'" onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 15px rgba(76,175,80,0.3)'">
                                    <i class="fas fa-leaf"></i> Ver
                                </button>
                            </td>
                            <td style="padding:14px;border-bottom:1px solid rgba(0,0,0,0.05);text-align:center;">
                                <button class="btn btn-sm" data-ndmi-idx="${idx}" style="background:linear-gradient(135deg,#2196F3,#1565C0);color:white;border:none;padding:10px 18px;border-radius:12px;font-weight:600;cursor:pointer;box-shadow:0 4px 15px rgba(33,150,243,0.3);transition:all 0.3s ease;" onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(33,150,243,0.4)'" onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 15px rgba(33,150,243,0.3)'">
                                    <i class="fas fa-tint"></i> Ver
                                </button>
                            </td>
                            <td style="padding:14px;border-bottom:1px solid rgba(0,0,0,0.05);text-align:center;">
                                <button class="btn btn-sm" data-savi-idx="${idx}" style="background:linear-gradient(135deg,#8B4513,#228B22);color:white;border:none;padding:10px 18px;border-radius:12px;font-weight:600;cursor:pointer;box-shadow:0 4px 15px rgba(139,69,19,0.3);transition:all 0.3s ease;" onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(139,69,19,0.4)'" onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 15px rgba(139,69,19,0.3)'">
                                    <i class="fas fa-seedling"></i> Ver
                                </button>
                            </td>
                            <td style="padding:14px;border-bottom:1px solid rgba(0,0,0,0.05);text-align:center;">
                                <button class="btn btn-sm" onclick="obtenerAnalyticsEscena('${scene.view_id}', '${scene.date}')" style="background:linear-gradient(135deg,#FF9800,#F57C00);color:white;border:none;padding:10px 18px;border-radius:12px;font-weight:600;cursor:pointer;box-shadow:0 4px 15px rgba(255,152,0,0.3);transition:all 0.3s ease;" onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(255,152,0,0.4)'" onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 15px rgba(255,152,0,0.3)'">
                                    <i class="fas fa-chart-bar"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        `;
        tableContainer.appendChild(table);
        body.appendChild(tableContainer);

        content.appendChild(body);

        // Footer
        const footer = document.createElement("div");
        footer.style.cssText = `
            padding: 16px 28px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        `;
        footer.innerHTML = `
            <span style="font-size:12px;color:#666;">
                <i class="fas fa-info-circle"></i> Los datos provienen de satélites Sentinel-2 via EOSDA
            </span>
            <button id="closeSceneModalFooter" class="btn" style="background:#6c757d;color:white;border:none;padding:10px 24px;border-radius:8px;font-weight:500;cursor:pointer;">
                Cerrar
            </button>
        `;
        content.appendChild(footer);

        modal.appendChild(content);
        document.body.appendChild(modal);

        // Cerrar modal
        const closeModal = () => {
            modal.style.animation = 'fadeOut 0.2s ease';
            setTimeout(() => modal.remove(), 150);
            resolve({ ndvi: null, ndmi: null });
        };
        
        document.getElementById('closeSceneModal').onclick = closeModal;
        document.getElementById('closeSceneModalFooter').onclick = closeModal;
        modal.onclick = (e) => { if (e.target === modal) closeModal(); };

        // Manejar click en NDVI (usar finalScenes en lugar de scenes)
        table.querySelectorAll('button[data-ndvi-idx]').forEach(btn => {
            btn.onclick = async () => {
                const idx = btn.getAttribute('data-ndvi-idx');
                const scene = finalScenes[idx]; // Usar finalScenes filtradas
                
                // Deshabilitar todos los botones del modal durante procesamiento
                const modalButtons = modal.querySelectorAll('button');
                modalButtons.forEach(b => b.disabled = true);
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
                
                try {
                    const result = await window.verImagenEscenaEOSDA(scene.view_id || scene.id, 'ndvi', scene.date);
                    if (result && result.success) {
                        modal.remove();
                        resolve({ ndvi: true, ndmi: false, savi: false });
                    }
                } finally {
                    // Rehabilitar botones si aún existe el modal
                    if (document.body.contains(modal)) {
                        modalButtons.forEach(b => {
                            b.disabled = false;
                            if (b.getAttribute('data-ndvi-idx')) {
                                b.innerHTML = '<i class="fas fa-leaf"></i> Ver';
                            } else if (b.getAttribute('data-ndmi-idx')) {
                                b.innerHTML = '<i class="fas fa-tint"></i> Ver';
                            } else if (b.getAttribute('data-savi-idx')) {
                                b.innerHTML = '<i class="fas fa-seedling"></i> Ver';
                            }
                        });
                    }
                }
            };
        });
        // Manejar click en NDMI (usar finalScenes en lugar de scenes)
        table.querySelectorAll('button[data-ndmi-idx]').forEach(btn => {
            btn.onclick = async () => {
                const idx = btn.getAttribute('data-ndmi-idx');
                const scene = finalScenes[idx]; // Usar finalScenes filtradas
                
                // Deshabilitar todos los botones del modal durante procesamiento
                const modalButtons = modal.querySelectorAll('button');
                modalButtons.forEach(b => b.disabled = true);
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
                
                try {
                    const result = await window.verImagenEscenaEOSDA(scene.view_id || scene.id, 'ndmi', scene.date);
                    if (result && result.success) {
                        modal.remove();
                        resolve({ ndvi: false, ndmi: true, savi: false });
                    }
                } finally {
                    // Rehabilitar botones si aún existe el modal
                    if (document.body.contains(modal)) {
                        modalButtons.forEach(b => {
                            b.disabled = false;
                            if (b.getAttribute('data-ndvi-idx')) {
                                b.innerHTML = '<i class="fas fa-leaf"></i> Ver';
                            } else if (b.getAttribute('data-ndmi-idx')) {
                                b.innerHTML = '<i class="fas fa-tint"></i> Ver';
                            } else if (b.getAttribute('data-savi-idx')) {
                                b.innerHTML = '<i class="fas fa-seedling"></i> Ver';
                            }
                        });
                    }
                }
            };
        });
        
        // Manejar click en SAVI (usar finalScenes en lugar de scenes)
        table.querySelectorAll('button[data-savi-idx]').forEach(btn => {
            btn.onclick = async () => {
                const idx = btn.getAttribute('data-savi-idx');
                const scene = finalScenes[idx]; // Usar finalScenes filtradas
                
                // Deshabilitar todos los botones del modal durante procesamiento
                const modalButtons = modal.querySelectorAll('button');
                modalButtons.forEach(b => b.disabled = true);
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
                
                try {
                    const result = await window.verImagenEscenaEOSDA(scene.view_id || scene.id, 'savi', scene.date);
                    if (result && result.success) {
                        modal.remove();
                        resolve({ ndvi: false, ndmi: false, savi: true });
                    }
                } finally {
                    // Rehabilitar botones si aún existe el modal
                    if (document.body.contains(modal)) {
                        modalButtons.forEach(b => {
                            b.disabled = false;
                            if (b.getAttribute('data-ndvi-idx')) {
                                b.innerHTML = '<i class="fas fa-leaf"></i> Ver';
                            } else if (b.getAttribute('data-ndmi-idx')) {
                                b.innerHTML = '<i class="fas fa-tint"></i> Ver';
                            } else if (b.getAttribute('data-savi-idx')) {
                                b.innerHTML = '<i class="fas fa-seedling"></i> Ver';
                            }
                        });
                    }
                }
            };
        });
    });
}

// Utilidad para calcular el bounding box de un polígono GeoJSON
function getPolygonBounds(coordinates) {
    let minLon = 180, minLat = 90, maxLon = -180, maxLat = -90;
    coordinates.forEach(coord => {
        if (coord[0] < minLon) minLon = coord[0];
        if (coord[0] > maxLon) maxLon = coord[0];
        if (coord[1] < minLat) minLat = coord[1];
        if (coord[1] > maxLat) maxLat = coord[1];
    });
    return [minLon, minLat, maxLon, maxLat]; // [west, south, east, north]
}

// Botón flotante para mostrar/ocultar imagen NDVI/NDMI cacheada
function showFloatingImageToggleButton(cacheKey, bounds, mapInstance) {
    let btn = document.getElementById('floatingImageToggleBtn');
    if (!btn) {
        btn = document.createElement('button');
        btn.id = 'floatingImageToggleBtn';
        btn.className = 'btn btn-warning';
        btn.style.position = 'fixed';
        btn.style.bottom = '32px';
        btn.style.right = '32px';
        btn.style.zIndex = '99999';
        btn.style.boxShadow = '0 2px 8px rgba(0, 209, 10, 0.32)';
        document.body.appendChild(btn);
    }
    let visible = true;
    btn.textContent = 'Ocultar imagen satelital';
    btn.onclick = () => {
        visible = !visible;
        if (visible) {
            showNDVIImageOnMap(window.EOSDA_IMAGE_CACHE[cacheKey], bounds, mapInstance);
            btn.textContent = 'Ocultar imagen satelital';
        } else {
            // Elimina la capa NDVI/NDMI en Leaflet
            mapInstance.eachLayer(function (layer) {
                if (layer.options && layer.options.className === 'ndvi-layer') {
                    mapInstance.removeLayer(layer);
                }
            });
            btn.textContent = 'Mostrar imagen satelital';
        }
    };
    btn.style.display = 'block';
}
// Función para mostrar la imagen NDVI/NDMI en Leaflet sobre la parcela seleccionada
function showNDVIImageOnLeaflet(imageBase64, bounds, mapInstance) {
    // Elimina capas NDVI previas
    mapInstance.eachLayer(function (layer) {
        if (layer.options && layer.options.className === 'ndvi-layer') {
            mapInstance.removeLayer(layer);
        }
    });
    
    // Crear un pane personalizado para imágenes de índices si no existe
    // Esto asegura que la imagen se renderice sin mezcla con otras capas
    if (!mapInstance.getPane('ndviPane')) {
        const ndviPane = mapInstance.createPane('ndviPane');
        ndviPane.style.zIndex = 450; // Entre overlay (400) y marker (600)
        ndviPane.style.mixBlendMode = 'normal';
        ndviPane.style.isolation = 'isolate';
    }
    
    // Crear URL para la imagen base64
    const imageUrl = `data:image/png;base64,${imageBase64}`;
    
    // bounds: [west, south, east, north]
    // Convertir a formato Leaflet [[south, west], [north, east]]
    const leafletBounds = [[bounds[1], bounds[0]], [bounds[3], bounds[2]]];
    
    // Agregar imagen como overlay con clase identificadora y pane aislado
    // Opacidad aumentada a 0.85 para mejor visibilidad de colores reales
    const imageOverlay = L.imageOverlay(imageUrl, leafletBounds, {
        opacity: 0.85,
        className: 'ndvi-layer',
        pane: 'ndviPane',
        interactive: false // No necesita interacción del mouse
    }).addTo(mapInstance);
    
    // Forzar estilos en el elemento de imagen para evitar filtros heredados
    imageOverlay.on('load', function() {
        const imgElement = this.getElement();
        if (imgElement) {
            imgElement.style.mixBlendMode = 'normal';
            imgElement.style.filter = 'none';
            imgElement.style.isolation = 'isolate';
        }
    });
    
    console.log('[LEAFLET_NDVI] Imagen NDVI/NDMI superpuesta correctamente con pane aislado');
    
    return imageOverlay;
}

// Mantener función antigua para compatibilidad con código existente
function showNDVIImageOnMap(imageBase64, bounds, viewerOrMap) {
    // Si es mapa Leaflet, redirigir a nueva función
    if (viewerOrMap && viewerOrMap._layersMaxZoom !== undefined) {
        return showNDVIImageOnLeaflet(imageBase64, bounds, viewerOrMap);
    }
    
    // Si llegamos aquí con Cesium (no debería pasar), log de error
    console.error('[MIGRATION_ERROR] Cesium no está disponible. Usar Leaflet.');
}

// Spinner overlay con loader CSS personalizado y mensaje
function showSpinner(message = "Procesando...") {
    let spinnerContainer = document.getElementById('eosdaSpinnerContainer');
    if (!spinnerContainer) {
        spinnerContainer = document.createElement('div');
        spinnerContainer.id = 'eosdaSpinnerContainer';
        spinnerContainer.style.position = 'fixed';
        spinnerContainer.style.top = '0';
        spinnerContainer.style.left = '0';
        spinnerContainer.style.width = '100vw';
        spinnerContainer.style.height = '100vh';
        spinnerContainer.style.background = 'rgba(0,0,0,0.35)';
        spinnerContainer.style.zIndex = '99999';
        spinnerContainer.style.display = 'flex';
        spinnerContainer.style.flexDirection = 'column';
        spinnerContainer.style.alignItems = 'center';
        spinnerContainer.style.justifyContent = 'center';
        spinnerContainer.innerHTML = `
            <style id="eosdaLoaderStyle">
            .loader {
                transform: rotateZ(45deg);
                perspective: 1000px;
                border-radius: 50%;
                width: 120px;
                height: 120px;
                color: #43ea2e;
                position: relative;
                display: block;
            }
            .loader:before,
            .loader:after {
                content: '';
                display: block;
                position: absolute;
                top: 0;
                left: 0;
                width: inherit;
                height: inherit;
                border-radius: 50%;
                transform: rotateX(70deg);
                animation: 1.2s spin linear infinite;
            }
            .loader:before {
                color: #ff9800;
            }
            .loader:after {
                color: #43ea2e;
                transform: rotateY(70deg);
                animation-delay: .5s;
            }
            @keyframes spin {
                0%,100% { box-shadow: .4em 0px 0 0px currentcolor; }
                12% { box-shadow: .4em .4em 0 0 currentcolor; }
                25% { box-shadow: 0 .4em 0 0px currentcolor; }
                37% { box-shadow: -.4em .4em 0 0currentcolor; }
                50% { box-shadow: -.4em 0 0 0 currentcolor; }
                62% { box-shadow: -.4em -.4em 0 0 currentcolor; }
                75% { box-shadow: 0px -.4em 0 0 currentcolor; }
                87% { box-shadow: .4em -.4em 0 0 currentcolor; }
            }
            </style>
            <span class="loader"></span>
            <p id="eosdaSpinnerMsg" style="margin-top:32px;font-size:2rem;color:#fff;text-shadow:0 1px 4px #333;">${message}</p>
        `;
        document.body.appendChild(spinnerContainer);
    } else {
        // Actualizar solo el mensaje
        const msgElem = spinnerContainer.querySelector('#eosdaSpinnerMsg');
        if (msgElem) msgElem.textContent = message;
    }
    spinnerContainer.style.display = 'flex';
}

// Función para ocultar el spinner
function hideSpinner() {
    const spinnerContainer = document.getElementById('eosdaSpinnerContainer');
    if (spinnerContainer) {
        spinnerContainer.style.display = 'none';
    }
}

// Exponer showSpinner y hideSpinner globalmente para usar en otros módulos
window.showSpinner = showSpinner;
window.hideSpinner = hideSpinner;

// Función wrapper para manejar botones durante procesamiento de imágenes
window.procesarImagenEOSDA = async function(viewId, tipo, buttonElement = null) {
    // Deshabilitar el botón específico y todos los botones de imágenes para evitar clics múltiples
    const allImageButtons = document.querySelectorAll('button[onclick*="verImagenEscenaEOSDA"], button[onclick*="procesarImagenEOSDA"]');
    const originalTexts = new Map();
    
    allImageButtons.forEach(btn => {
        originalTexts.set(btn, btn.innerHTML);
        btn.disabled = true;
        if (btn.innerHTML.includes('Ver NDVI')) {
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
        } else if (btn.innerHTML.includes('Ver NDMI')) {
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
        } else if (btn.innerHTML.includes('Ver SAVI')) {
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
        }
    });
    
    try {
        // Llamar a la función principal
        const result = await window.verImagenEscenaEOSDA(viewId, tipo);
        return result;
    } finally {
        // Rehabilitar botones y restaurar textos originales
        allImageButtons.forEach(btn => {
            btn.disabled = false;
            btn.innerHTML = originalTexts.get(btn);
        });
    }
};

// --- IMAGEN EOSDA: Procesamiento principal ---
window.verImagenEscenaEOSDA = async function(viewId, tipo, sceneDate = null) {
    const token = localStorage.getItem("accessToken");
    const fieldId = window.AGROTECH_STATE.selectedSatelliteId;
    const parcelId = window.AGROTECH_STATE.selectedParcelId;
    
    if (!fieldId) {
        alert("No se encontró el field_id de EOSDA para la parcela seleccionada.");
        return { success: false };
    }
    
    // OPTIMIZACIÓN: Verificar cache de imagen primero
    const cacheKey = `${viewId}_${tipo}`;
    if (window.EOSDA_IMAGE_CACHE[cacheKey]) {
        console.log('[CACHE HIT] Imagen encontrada en cache frontend');
        // Obtener el polígono de la parcela seleccionada
        const parcelResp = await axiosInstance.get(`/parcel/${parcelId}/`);
        let coords = [];
        if (parcelResp.data.geometry && parcelResp.data.geometry.coordinates) {
            coords = parcelResp.data.geometry.coordinates[0];
        } else if (parcelResp.data.geom && parcelResp.data.geom.coordinates) {
            coords = parcelResp.data.geom.coordinates[0];
        }
        const bounds = getPolygonBounds(coords);
        showNDVIImageOnMap(window.EOSDA_IMAGE_CACHE[cacheKey], bounds, map);
        // Cerrar el modal
        const modal = document.getElementById('eosdaScenesModal');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) bsModal.hide();
        }
        showFloatingImageToggleButton(cacheKey, bounds, map);
        
        // NUEVO: Realizar análisis de colores automáticamente desde cache
        try {
            const imageBase64Src = `data:image/png;base64,${window.EOSDA_IMAGE_CACHE[cacheKey]}`;
            await window.mostrarImagenNDVIConAnalisis(imageBase64Src, tipo, sceneDate);
        } catch (analysisError) {
            console.warn('[IMAGE_ANALYSIS] Error en análisis desde cache:', analysisError);
        }
        
        showInfoToast(`Imagen ${tipo.toUpperCase()} cargada desde cache con análisis.`);
        return { success: true };
    }
    
    // Mostrar spinner inmediatamente antes de cualquier operación
    showSpinner(`Preparando imagen ${tipo.toUpperCase()}...`);
    
    try {
        // OPTIMIZACIÓN: Verificar cache de request_id primero
        const requestIdCacheKey = `request_${fieldId}_${viewId}_${tipo}`;
        let requestId = window.AGROTECH_STATE.requestIds[requestIdCacheKey];
        
        if (!requestId) {
            // Paso 1: Solicitar el request_id para la imagen
            showSpinner(`Solicitando procesamiento de imagen ${tipo.toUpperCase()}...`);
            
            const resp = await fetch(`${BASE_URL}/eosda-image/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({ field_id: fieldId, view_id: viewId, type: tipo, format: "png" })
            });
            
            const data = await resp.json();
            
            if (!data.request_id) {
                hideSpinner();
                if (data.error) {
                    showErrorToast(`Error: ${data.error}`);
                } else {
                    showErrorToast(`No se pudo obtener el request_id para la imagen ${tipo.toUpperCase()}.`);
                }
                return { success: false };
            }
            
            requestId = data.request_id;
            // Guardar request_id en cache
            window.AGROTECH_STATE.requestIds[requestIdCacheKey] = requestId;
            console.log('[CACHE SET] request_id guardado en cache frontend:', requestId);
        } else {
            console.log('[CACHE HIT] request_id encontrado en cache frontend:', requestId);
        }
        
        // Paso 2: Polling automático para obtener la imagen (SIN mensajes de error al usuario)
        const maxAttempts = 15; // Más intentos para imágenes que toman tiempo
        const baseInterval = 4000; // Intervalo base de 4s
        
        // Mensajes amigables que rotan durante el procesamiento
        const processingMessages = [
            `🛰️ Procesando imagen ${tipo.toUpperCase()}...`,
            `📡 Descargando datos satelitales...`,
            `🔄 El satélite está generando la imagen...`,
            `⏳ Esto puede tomar 1-2 minutos...`,
            `🌍 Procesando análisis espectral...`,
            `📊 Casi listo, preparando visualización...`
        ];
        let attempts = 0;
        
        showSpinner(processingMessages[0]);
        
        while (attempts < maxAttempts) {
            try {
                const imgResp = await fetch(`${BASE_URL}/eosda-image-result/?field_id=${fieldId}&request_id=${requestId}`, {
                    method: "GET",
                    headers: {
                        "Authorization": `Bearer ${token}`
                    }
                });
                
                const imgData = await imgResp.json();
                
                if (imgData.image_base64) {
                    // ¡ÉXITO! La imagen está lista
                    hideSpinner();
                    
                    // Obtener el polígono de la parcela seleccionada
                    const parcelResp = await axiosInstance.get(`/parcel/${parcelId}/`);
                    let coords = [];
                    if (parcelResp.data.geometry && parcelResp.data.geometry.coordinates) {
                        coords = parcelResp.data.geometry.coordinates[0];
                    } else if (parcelResp.data.geom && parcelResp.data.geom.coordinates) {
                        coords = parcelResp.data.geom.coordinates[0];
                    }
                    const bounds = getPolygonBounds(coords);
                    
                    // Guardar imagen en cache
                    window.EOSDA_IMAGE_CACHE[cacheKey] = imgData.image_base64;
                    console.log('[CACHE SET] Imagen guardada en cache frontend');
                    
                    // Mostrar imagen en Leaflet
                    showNDVIImageOnMap(imgData.image_base64, bounds, map);
                    
                    // Cerrar el modal para mostrar el mapa completo
                    const modal = document.getElementById('eosdaScenesModal');
                    if (modal) {
                        const bsModal = bootstrap.Modal.getInstance(modal);
                        if (bsModal) bsModal.hide();
                    }
                    
                    // Mostrar botón flotante para mostrar/ocultar imagen cacheada
                    showFloatingImageToggleButton(cacheKey, bounds, map);
                    
                    // Realizar análisis de colores automáticamente
                    try {
                        const imageBase64Src = `data:image/png;base64,${imgData.image_base64}`;
                        await window.mostrarImagenNDVIConAnalisis(imageBase64Src, tipo, sceneDate);
                    } catch (analysisError) {
                        console.warn('[IMAGE_ANALYSIS] Error en análisis automático:', analysisError);
                        // No interrumpir el flujo principal si falla el análisis
                    }
                    
                    showInfoToast(`✅ Imagen ${tipo.toUpperCase()} lista y superpuesta en el mapa con análisis.`);
                    return { success: true };
                    
                } else if (imgData.error) {
                    // Verificar si es un error temporal (imagen en proceso) vs error permanente
                    const errorMsg = imgData.error.toLowerCase();
                    const isTemporaryError = (
                        imgResp.status === 202 || 
                        errorMsg.includes('proceso') || 
                        errorMsg.includes('processing') ||
                        errorMsg.includes('intenta nuevamente') ||
                        errorMsg.includes('try again')
                    );
                    
                    if (isTemporaryError) {
                        // Error temporal - continuar polling sin mostrar error
                        console.log(`[POLLING] Imagen en proceso: ${imgData.error}`);
                        // Continuar con el siguiente intento
                    } else {
                        // Error permanente - mostrar al usuario
                        hideSpinner();
                        showErrorToast(`❌ Error procesando imagen: ${imgData.error}`);
                        return { success: false };
                    }
                }
                
                // La imagen aún se está procesando - continuar polling SIN molestar al usuario
                console.log(`[POLLING] Intento ${attempts + 1}/${maxAttempts} - Imagen aún procesándose...`);
                
            } catch (err) {
                console.error(`[POLLING] Error en intento ${attempts + 1}:`, err);
                // Continuar con el siguiente intento
            }
            
            attempts++;
            
            if (attempts < maxAttempts) {
                // Actualizar mensaje del spinner con mensajes amigables rotativos
                const messageIndex = Math.min(attempts, processingMessages.length - 1);
                const timeElapsed = Math.round((attempts * baseInterval) / 1000);
                showSpinner(`${processingMessages[messageIndex]} (${timeElapsed}s)`);
                
                // Intervalo progresivo: empezar rápido, luego más lento
                const currentInterval = attempts <= 3 ? baseInterval : baseInterval + (attempts * 500);
                await new Promise(resolve => setTimeout(resolve, currentInterval));
            }
        }
        
        // Si llegamos aquí, se agotaron los intentos - mostrar mensaje amigable, NO error
        hideSpinner();
        showWarningToast(
            `⏳ La imagen ${tipo.toUpperCase()} aún está siendo procesada por el satélite.\n\n` +
            `💡 Sugerencia: Espera unos segundos e intenta nuevamente. ` +
            `Las imágenes satelitales pueden tomar hasta 2-3 minutos en generarse.`
        );
        return { success: false, reason: 'timeout' };
        
    } catch (error) {
        hideSpinner();
        console.error('[EOSDA_IMAGE_ERROR] Error general:', error);
        showErrorToast(`❌ Error inesperado al procesar imagen ${tipo.toUpperCase()}: ${error.message || error}`);
        return { success: false };
    }
};

// --- NDVI/NDMI/SAVI: Visualización y análisis de porcentajes ---
window.mostrarImagenNDVIConAnalisis = async function(imageSrc, tipo = 'ndvi', sceneDate = null) {
    try {
        // Importar análisis dinámicamente (incluye nuevas funciones de interpretación)
        const { 
            analyzeImageByColor, 
            analyzeImageByColorAdvanced, 
            NDVI_COLOR_DEFINITIONS, 
            NDMI_COLOR_DEFINITIONS, 
            SAVI_COLOR_DEFINITIONS, 
            INTERPRETACIONES_INDICES, 
            updateColorLegendInDOM,
            generarInterpretacionProfesional,
            generarHTMLInterpretacion
        } = await import('./analysis.js');
        
        // Seleccionar definiciones de colores según el tipo
        let colorDefinitions;
        let title;
        switch (tipo.toLowerCase()) {
            case 'ndvi':
                colorDefinitions = NDVI_COLOR_DEFINITIONS;
                title = '🌱 Análisis NDVI';
                break;
            case 'ndmi':
                colorDefinitions = NDMI_COLOR_DEFINITIONS;
                title = '💧 Análisis NDMI';
                break;
            case 'savi':
                colorDefinitions = SAVI_COLOR_DEFINITIONS;
                title = '🌿 Análisis SAVI';
                break;
            default:
                colorDefinitions = NDVI_COLOR_DEFINITIONS;
                title = `📊 Análisis ${tipo.toUpperCase()}`;
        }
        
        // Validación: asegurarse de que colorDefinitions existe
        if (!colorDefinitions || !Array.isArray(colorDefinitions) || colorDefinitions.length === 0) {
            console.warn(`[IMAGE_ANALYSIS] colorDefinitions para ${tipo} no encontradas, usando NDVI por defecto`);
            colorDefinitions = NDVI_COLOR_DEFINITIONS;
        }
        
        console.log(`[IMAGE_ANALYSIS] Definiciones de color para ${tipo}:`, colorDefinitions);
        console.log(`[IMAGE_ANALYSIS] Iniciando análisis ${tipo.toUpperCase()}...`);
        
        // Mostrar imagen en el dashboard
        const dashboardBox = document.getElementById('ndviLegendBox') || document.getElementById('imageLegendContainer');
        if (dashboardBox) {
            let imgEl = document.getElementById('satelliteImagePreview');
            if (!imgEl) {
                imgEl = document.createElement('img');
                imgEl.id = 'satelliteImagePreview';
                imgEl.style.maxWidth = '100%';
                imgEl.style.borderRadius = '8px';
                imgEl.style.marginBottom = '12px';
                dashboardBox.insertBefore(imgEl, dashboardBox.firstChild);
            }
            imgEl.src = imageSrc;
            imgEl.alt = `Imagen ${tipo.toUpperCase()}`;
            
            // Mostrar el contenedor de análisis de imagen
            const analysisContainer = document.getElementById('imageAnalysisContainer');
            if (analysisContainer) {
                analysisContainer.style.display = 'block';
            }
        }
        
        // 3. Análisis de imagen con debugging mejorado
        console.log(`[IMAGE_ANALYSIS] Iniciando análisis ${tipo.toUpperCase()}...`);
        console.log(`[IMAGE_ANALYSIS] URL de imagen:`, imageSrc.substring(0, 100) + '...');
        console.log(`[IMAGE_ANALYSIS] Definiciones de color:`, colorDefinitions);
        
        try {
            // Primero intentar análisis avanzado que incluye fallback dinámico
            // Pasar el tipo de índice para que el análisis dinámico use nombres apropiados
            const analysisResult = await analyzeImageByColorAdvanced(imageSrc, colorDefinitions, tipo.toLowerCase());
            console.log(`[IMAGE_ANALYSIS] Resultado del análisis:`, analysisResult);
            
            if (analysisResult && analysisResult.success) {
                // Normalizar resultados para tener un formato consistente
                const resultsWithColors = analysisResult.results.map((result, index) => {
                    // Para análisis dinámico, usar el color detectado; para predefinido, usar las definiciones
                    const colorArray = result.rgb || result.color || colorDefinitions[index]?.rgb || [128, 128, 128];
                    
                    return {
                        name: result.name || `Categoría ${index + 1}`,
                        label: result.name || `Categoría ${index + 1}`, // Compatibilidad
                        color: colorArray,
                        rgb: colorArray,
                        count: result.count || 0,
                        percent: parseFloat(result.percent) || 0,
                        percentage: parseFloat(result.percent) || 0 // Compatibilidad
                    };
                });
                
                console.log(`[IMAGE_ANALYSIS] Resultados normalizados:`, resultsWithColors);
                
                // Actualizar leyenda en el contenedor principal
                if (dashboardBox) {
                    console.log(`[IMAGE_ANALYSIS] Actualizando leyenda en el dashboard...`);
                    
                    // Crear o encontrar contenedor de leyenda
                    let legendContainer = dashboardBox.querySelector('.color-analysis-legend');
                    if (!legendContainer) {
                        legendContainer = document.createElement('div');
                        legendContainer.className = 'color-analysis-legend mt-3';
                        legendContainer.id = 'dynamicLegendContainer';
                        dashboardBox.appendChild(legendContainer);
                    }
                    
                    // Actualizar leyenda directamente (sin usar función externa por ahora)
                    const analysisTypeText = analysisResult.analysisType === 'dynamic' ? 
                        '🔍 Análisis dinámico (colores detectados automáticamente)' : 
                        '📋 Análisis predefinido';
                    
                    // Formatear fecha de escena si está disponible
                    const sceneDateInfo = sceneDate ? 
                        `<br><small class="text-muted"><strong>Fecha de escena:</strong> ${new Date(sceneDate).toLocaleDateString()}</small>` : '';
                    
                    // Limpiar leyenda existente
                    legendContainer.innerHTML = '';
                    
                    // Título de análisis
                    const titleElem = document.createElement('div');
                    titleElem.style.fontSize = '1.2rem';
                    titleElem.style.fontWeight = 'bold';
                    titleElem.style.marginBottom = '8px';
                    titleElem.innerHTML = `${title} ${sceneDateInfo}`;
                    legendContainer.appendChild(titleElem);
                    
                    // Contenedor de resultados
                    const resultsContainer = document.createElement('div');
                    resultsContainer.id = 'imageAnalysisResults';
                    resultsContainer.style.display = 'grid';
                    resultsContainer.style.gridTemplateColumns = 'repeat(auto-fill, minmax(140px, 1fr))';
                    resultsContainer.style.gap = '10px';
                    legendContainer.appendChild(resultsContainer);
                    
                    // Función para determinar si el texto debe ser claro u oscuro según el fondo
                    const getContrastColor = (r, g, b) => {
                        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
                        return luminance > 0.5 ? '#333333' : '#ffffff';
                    };
                    
                    // 📚 Diccionario de explicaciones para cada categoría según el índice
                    const getCategoryExplanation = (categoryName, indexType) => {
                        // Explicaciones específicas organizadas por índice
                        const explanationsByIndex = {
                            ndvi: {
                                'Vegetación Muy Densa': {
                                    titulo: '🌳 Vegetación Muy Densa',
                                    descripcion: 'Zona con la máxima actividad de clorofila detectada. Las plantas están realizando fotosíntesis intensamente.',
                                    significado: 'Tu cultivo está en excelente estado de salud. Alta densidad de hojas verdes y activas indica óptimo desarrollo vegetativo y potencial de rendimiento máximo.'
                                },
                                'Vegetación Densa': {
                                    titulo: '🌿 Vegetación Densa',
                                    descripcion: 'Cobertura vegetal abundante con alta concentración de clorofila activa en las hojas.',
                                    significado: 'Buen estado general del cultivo. Las plantas están saludables con buena capacidad fotosintética, aunque hay margen para alcanzar el óptimo.'
                                },
                                'Vegetación Moderada': {
                                    titulo: '🌱 Vegetación Moderada',
                                    descripcion: 'Presencia vegetal media, típica de cultivos en etapa de crecimiento o con espaciamiento entre plantas.',
                                    significado: 'Si el cultivo es joven, es normal. En cultivos maduros puede indicar que las plantas no han alcanzado su máximo desarrollo o hay espacios sin vegetación.'
                                },
                                'Vegetación Escasa': {
                                    titulo: '🍂 Vegetación Escasa',
                                    descripcion: 'Poca actividad de clorofila detectada. Baja densidad o vigor de la vegetación en esta zona.',
                                    significado: 'Posible señal de alerta. Puede indicar plantas estresadas, enfermas, con deficiencia nutricional o en etapa muy temprana de desarrollo.'
                                },
                                'Estrés Severo': {
                                    titulo: '⚠️ Estrés Crítico',
                                    descripcion: 'Casi nula actividad fotosintética. La vegetación muestra signos graves de deterioro o muerte.',
                                    significado: 'Las plantas en esta zona están en peligro o ya murieron. Requiere atención urgente: puede ser sequía extrema, enfermedad, plagas o daño físico.'
                                },
                                'Suelo Desnudo': {
                                    titulo: '🟤 Suelo sin Vegetación',
                                    descripcion: 'No se detecta clorofila. El satélite ve principalmente suelo, rocas o superficies inertes.',
                                    significado: 'Área sin plantas activas. Puede ser suelo preparado para siembra, caminos, construcciones, o zonas donde falló la germinación.'
                                }
                            },
                            ndmi: {
                                'Muy Húmedo': {
                                    titulo: '💧 Saturación de Agua',
                                    descripcion: 'Alto contenido de agua en la vegetación y posiblemente en el suelo. Las hojas están completamente hidratadas.',
                                    significado: 'Indica riego reciente, lluvia o posible encharcamiento. Si persiste, podría favorecer hongos y enfermedades de raíz por exceso de humedad.'
                                },
                                'Húmedo': {
                                    titulo: '💦 Bien Hidratado',
                                    descripcion: 'Las plantas tienen buen contenido de agua en sus tejidos. Condiciones hídricas favorables.',
                                    significado: 'Estado hídrico óptimo. Las plantas tienen suficiente agua para sus funciones vitales sin estar saturadas. Condiciones ideales para el crecimiento.'
                                },
                                'Humedad Normal': {
                                    titulo: '✅ Humedad Adecuada',
                                    descripcion: 'Contenido de agua balanceado en la vegetación. Ni exceso ni déficit evidente.',
                                    significado: 'Las plantas mantienen un equilibrio hídrico saludable. Están absorbiendo y utilizando agua de manera eficiente.'
                                },
                                'Humedad Moderada': {
                                    titulo: '🌡️ Humedad Media',
                                    descripcion: 'Nivel de agua en las plantas aceptable pero no óptimo. Posible inicio de reducción hídrica.',
                                    significado: 'Las plantas aún tienen agua disponible pero conviene vigilar. En climas calurosos o secos, podrían necesitar riego preventivo pronto.'
                                },
                                'Humedad Baja': {
                                    titulo: '⚡ Inicio de Estrés Hídrico',
                                    descripcion: 'Las plantas comienzan a perder agua más rápido de lo que la absorben. Primeros signos de déficit.',
                                    significado: 'Señal de advertencia temprana. Las plantas están empezando a sufrir por falta de agua. Es el momento ideal para regar antes de que el daño sea mayor.'
                                },
                                'Seco': {
                                    titulo: '🏜️ Déficit Hídrico',
                                    descripcion: 'Bajo contenido de agua en los tejidos vegetales. Las plantas están deshidratándose.',
                                    significado: 'Estrés hídrico evidente. Las plantas están cerrando estomas y reduciendo fotosíntesis para conservar agua. Afecta directamente el rendimiento.'
                                },
                                'Muy Seco': {
                                    titulo: '🚨 Estrés Hídrico Severo',
                                    descripcion: 'Contenido de agua críticamente bajo. Las plantas están en riesgo de daño irreversible.',
                                    significado: 'Situación crítica. Las células vegetales pueden estar sufriendo daño permanente. Sin agua urgente, puede haber pérdida parcial o total del cultivo.'
                                }
                            },
                            savi: {
                                'Vegetación Muy Densa': {
                                    titulo: '🌳 Cobertura Completa',
                                    descripcion: 'El dosel vegetal cubre completamente el suelo. Análisis SAVI detecta máxima vegetación sin influencia del suelo.',
                                    significado: 'Cultivo plenamente desarrollado donde el suelo ya no es visible desde el satélite. En esta etapa, NDVI sería más preciso para evaluar salud vegetal.'
                                },
                                'Vegetación Densa': {
                                    titulo: '� Alta Cobertura',
                                    descripcion: 'Abundante vegetación con mínima exposición del suelo. SAVI indica buen desarrollo del cultivo.',
                                    significado: 'Las plantas están cubriendo bien el terreno. Buen desarrollo vegetativo con poca interferencia del suelo en la medición satelital.'
                                },
                                'Vegetación Moderada': {
                                    titulo: '🌱 Cobertura Parcial',
                                    descripcion: 'Mezcla de vegetación y suelo visible. SAVI compensa la reflectancia del suelo para dar una medición más precisa.',
                                    significado: 'Típico de cultivos en desarrollo o con espaciamiento amplio. SAVI es especialmente útil aquí porque filtra la influencia del suelo.'
                                },
                                'Vegetación Escasa': {
                                    titulo: '� Poca Cobertura',
                                    descripcion: 'Predomina la exposición del suelo con vegetación dispersa o muy joven.',
                                    significado: 'Normal en siembras recientes o cultivos de bajo porte. Si el cultivo debería estar más desarrollado, puede indicar problemas de germinación o crecimiento.'
                                },
                                'Cultivo Joven': {
                                    titulo: '🌱 Emergencia/Crecimiento Inicial',
                                    descripcion: 'Plantas pequeñas o recién emergidas donde el suelo es predominante. SAVI detecta vegetación que NDVI podría subestimar.',
                                    significado: 'Etapa inicial del cultivo. Las plantas son pequeñas pero SAVI puede detectarlas incluso con mucho suelo visible. Ideal para monitorear germinación.'
                                },
                                'Suelo Expuesto': {
                                    titulo: '🟫 Suelo Predominante',
                                    descripcion: 'Muy poca o ninguna vegetación. La señal proviene principalmente del suelo.',
                                    significado: 'Puede ser suelo preparado pre-siembra, fallas de germinación, o áreas deliberadamente sin cultivo como calles de servicio.'
                                }
                            }
                        };
                        
                        // Explicaciones comunes para todos los índices
                        const commonExplanations = {
                            'Sin Datos/Nubes': {
                                titulo: '☁️ Zona Sin Datos',
                                descripcion: 'Área cubierta por nubes o donde el satélite no pudo obtener datos válidos.',
                                significado: 'No hay información confiable para esta zona en esta imagen. Las nubes bloquean la visión del satélite hacia la superficie.'
                            },
                            'Sombra': {
                                titulo: '🌑 Área Sombreada',
                                descripcion: 'Zona oscurecida por sombras de nubes, árboles, edificaciones o relieve del terreno.',
                                significado: 'La sombra impide obtener datos precisos. No indica problema con el cultivo, solo limitación de la imagen.'
                            },
                            'Transición': {
                                titulo: '🔄 Zona de Cambio',
                                descripcion: 'Área donde se mezclan diferentes condiciones: vegetación con suelo, húmedo con seco, etc.',
                                significado: 'Representa bordes o gradientes naturales en el terreno. Puede ser límite entre zonas de diferente manejo o condición.'
                            },
                            'Mixto': {
                                titulo: '� Área Variada',
                                descripcion: 'Combinación heterogénea de diferentes coberturas o estados dentro de la misma zona.',
                                significado: 'El pixel satelital contiene mezcla de elementos: algo de vegetación, algo de suelo, posiblemente agua o estructuras.'
                            }
                        };
                        
                        // Normalizar el tipo de índice
                        const indexKey = (indexType || 'ndvi').toLowerCase().replace(/[^a-z]/g, '');
                        
                        // Buscar en explicaciones específicas del índice
                        let explanation = null;
                        const indexExplanations = explanationsByIndex[indexKey];
                        
                        if (indexExplanations) {
                            explanation = indexExplanations[categoryName];
                            
                            // Buscar coincidencia parcial si no hay exacta
                            if (!explanation) {
                                const searchTerm = categoryName.toLowerCase();
                                for (const [key, value] of Object.entries(indexExplanations)) {
                                    if (searchTerm.includes(key.toLowerCase().split(' ')[0]) || 
                                        key.toLowerCase().includes(searchTerm.split(' ')[0])) {
                                        explanation = value;
                                        break;
                                    }
                                }
                            }
                        }
                        
                        // Buscar en explicaciones comunes
                        if (!explanation) {
                            explanation = commonExplanations[categoryName];
                            if (!explanation) {
                                for (const [key, value] of Object.entries(commonExplanations)) {
                                    if (categoryName.toLowerCase().includes(key.toLowerCase().split(' ')[0])) {
                                        explanation = value;
                                        break;
                                    }
                                }
                            }
                        }
                        
                        // Generar explicación dinámica si no se encontró
                        if (!explanation) {
                            const indexNames = {
                                ndvi: 'salud vegetativa (NDVI)',
                                ndmi: 'contenido hídrico (NDMI)',
                                savi: 'vegetación ajustada al suelo (SAVI)'
                            };
                            const indexDescription = indexNames[indexKey] || indexType.toUpperCase();
                            
                            explanation = {
                                titulo: `📊 ${categoryName}`,
                                descripcion: `Categoría identificada automáticamente en el análisis de ${indexDescription}.`,
                                significado: `Esta clasificación representa una condición específica detectada por el análisis espectral de la imagen satelital para el índice ${indexType.toUpperCase()}.`
                            };
                        }
                        
                        return explanation;
                    };
                    
                    // Función para mostrar modal de explicación
                    const showCategoryExplanation = (categoryName, percent, indexType) => {
                        const explanation = getCategoryExplanation(categoryName, indexType);
                        
                        // Crear o encontrar el modal
                        let modal = document.getElementById('categoryExplanationModal');
                        if (!modal) {
                            modal = document.createElement('div');
                            modal.id = 'categoryExplanationModal';
                            modal.style.cssText = `
                                position: fixed;
                                top: 0;
                                left: 0;
                                width: 100%;
                                height: 100%;
                                background: rgba(0,0,0,0.5);
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                z-index: 10000;
                                opacity: 0;
                                transition: opacity 0.3s ease;
                            `;
                            document.body.appendChild(modal);
                        }
                        
                        modal.innerHTML = `
                            <div style="
                                background: white;
                                border-radius: 20px;
                                max-width: 420px;
                                width: 90%;
                                max-height: 80vh;
                                overflow-y: auto;
                                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                                animation: modalSlideIn 0.3s ease;
                            ">
                                <style>
                                    @keyframes modalSlideIn {
                                        from { transform: translateY(30px); opacity: 0; }
                                        to { transform: translateY(0); opacity: 1; }
                                    }
                                </style>
                                
                                <!-- Header con gradiente -->
                                <div style="
                                    background: linear-gradient(135deg, #4CAF50, #2E7D32);
                                    padding: 20px;
                                    border-radius: 20px 20px 0 0;
                                    color: white;
                                    position: relative;
                                ">
                                    <button onclick="document.getElementById('categoryExplanationModal').style.display='none'" style="
                                        position: absolute;
                                        top: 15px;
                                        right: 15px;
                                        background: rgba(255,255,255,0.2);
                                        border: none;
                                        color: white;
                                        width: 32px;
                                        height: 32px;
                                        border-radius: 50%;
                                        cursor: pointer;
                                        font-size: 18px;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                    ">✕</button>
                                    <h4 style="margin: 0 0 8px 0; font-size: 1.3rem;">${explanation.titulo}</h4>
                                    <div style="font-size: 2rem; font-weight: bold;">${parseFloat(percent).toFixed(1)}%</div>
                                    <small>del área total analizada</small>
                                </div>
                                
                                <!-- Contenido simplificado -->
                                <div style="padding: 20px;">
                                    <!-- Descripción -->
                                    <div style="margin-bottom: 20px;">
                                        <div style="font-weight: 600; color: #333; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                                            <span style="background: #E8F5E9; padding: 6px 10px; border-radius: 8px; font-size: 1.1rem;">📝</span>
                                            ¿Qué detectó el satélite?
                                        </div>
                                        <p style="color: #555; margin: 0; line-height: 1.6; font-size: 0.95rem;">${explanation.descripcion}</p>
                                    </div>
                                    
                                    <!-- Significado -->
                                    <div style="
                                        background: linear-gradient(135deg, #FFF8E1, #FFFDE7);
                                        padding: 16px;
                                        border-radius: 12px;
                                        border-left: 4px solid #FFC107;
                                    ">
                                        <div style="font-weight: 600; color: #333; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                                            <span style="font-size: 1.2rem;">💡</span>
                                            ¿Qué significa para tu cultivo?
                                        </div>
                                        <p style="color: #555; margin: 0; line-height: 1.6; font-size: 0.95rem;">${explanation.significado}</p>
                                    </div>
                                </div>
                                
                                <!-- Footer -->
                                <div style="padding: 0 20px 20px 20px;">
                                    <button onclick="document.getElementById('categoryExplanationModal').style.display='none'" style="
                                        width: 100%;
                                        background: linear-gradient(135deg, #4CAF50, #2E7D32);
                                        color: white;
                                        border: none;
                                        padding: 14px;
                                        border-radius: 12px;
                                        font-weight: 600;
                                        cursor: pointer;
                                        font-size: 1rem;
                                    ">Entendido ✓</button>
                                </div>
                            </div>
                        `;
                        
                        modal.style.display = 'flex';
                        setTimeout(() => modal.style.opacity = '1', 10);
                        
                        // Cerrar al hacer clic fuera
                        modal.onclick = (e) => {
                            if (e.target === modal) {
                                modal.style.display = 'none';
                            }
                        };
                    };
                    
                    // Añadir tarjetas de resultados con mejor diseño
                    resultsWithColors.forEach((result, index) => {
                        const [r, g, b] = result.color || [128, 128, 128];
                        const textColor = getContrastColor(r, g, b);
                        const borderColor = `rgba(${r}, ${g}, ${b}, 0.8)`;
                        
                        const card = document.createElement('div');
                        card.style.cssText = `
                            background: linear-gradient(135deg, rgba(${r}, ${g}, ${b}, 0.9), rgba(${r}, ${g}, ${b}, 1));
                            border-radius: 12px;
                            padding: 14px 10px;
                            box-shadow: 0 4px 12px rgba(${r}, ${g}, ${b}, 0.3);
                            position: relative;
                            overflow: hidden;
                            border: 2px solid ${borderColor};
                            transition: transform 0.2s ease, box-shadow 0.2s ease;
                            cursor: pointer;
                        `;
                        
                        // Icono de información
                        const infoIcon = document.createElement('div');
                        infoIcon.innerHTML = 'ⓘ';
                        infoIcon.style.cssText = `
                            position: absolute;
                            top: 6px;
                            right: 8px;
                            font-size: 0.9rem;
                            color: ${textColor};
                            opacity: 0.7;
                        `;
                        card.appendChild(infoIcon);
                        
                        // Hover effect
                        card.onmouseenter = () => {
                            card.style.transform = 'translateY(-2px)';
                            card.style.boxShadow = `0 6px 16px rgba(${r}, ${g}, ${b}, 0.4)`;
                            infoIcon.style.opacity = '1';
                        };
                        card.onmouseleave = () => {
                            card.style.transform = 'translateY(0)';
                            card.style.boxShadow = `0 4px 12px rgba(${r}, ${g}, ${b}, 0.3)`;
                            infoIcon.style.opacity = '0.7';
                        };
                        
                        // Click para mostrar explicación
                        card.onclick = () => {
                            showCategoryExplanation(result.name, result.percent || result.percentage, tipo);
                        };
                        
                        // Nombre de la categoría
                        const nameText = document.createElement('div');
                        nameText.style.cssText = `
                            font-size: 0.85rem;
                            font-weight: 600;
                            color: ${textColor};
                            text-align: center;
                            margin-bottom: 8px;
                            line-height: 1.2;
                            text-shadow: ${textColor === '#ffffff' ? '0 1px 2px rgba(0,0,0,0.3)' : 'none'};
                        `;
                        nameText.textContent = result.name || `Categoría ${index + 1}`;
                        card.appendChild(nameText);
                        
                        // Porcentaje con formato prominente
                        const percentValue = result.percent || result.percentage || 0;
                        const percentText = document.createElement('div');
                        percentText.style.cssText = `
                            font-size: 1.4rem;
                            font-weight: 800;
                            color: ${textColor};
                            text-align: center;
                            text-shadow: ${textColor === '#ffffff' ? '0 1px 3px rgba(0,0,0,0.4)' : 'none'};
                        `;
                        percentText.textContent = `${parseFloat(percentValue).toFixed(1)}%`;
                        card.appendChild(percentText);
                        
                        // Barra de progreso visual
                        const progressContainer = document.createElement('div');
                        progressContainer.style.cssText = `
                            margin-top: 8px;
                            background: rgba(255,255,255,0.3);
                            border-radius: 4px;
                            height: 6px;
                            overflow: hidden;
                        `;
                        const progressBar = document.createElement('div');
                        progressBar.style.cssText = `
                            width: ${Math.min(parseFloat(percentValue), 100)}%;
                            height: 100%;
                            background: ${textColor === '#ffffff' ? 'rgba(255,255,255,0.8)' : 'rgba(0,0,0,0.5)'};
                            border-radius: 4px;
                            transition: width 0.5s ease;
                        `;
                        progressContainer.appendChild(progressBar);
                        card.appendChild(progressContainer);
                        
                        resultsContainer.appendChild(card);
                    });
                    
                    // Agregar hint para indicar que las tarjetas son clickeables
                    const clickHint = document.createElement('div');
                    clickHint.style.cssText = `
                        margin-top: 8px;
                        padding: 6px 12px;
                        background: linear-gradient(135deg, #E8F5E9, #C8E6C9);
                        border-radius: 8px;
                        font-size: 0.75rem;
                        color: #2E7D32;
                        text-align: center;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 6px;
                    `;
                    clickHint.innerHTML = '<span style="font-size: 1rem;">👆</span> Toca cualquier tarjeta para ver qué significa';
                    legendContainer.appendChild(clickHint);
                    
                    // Agregar indicador de tipo de análisis al final
                    const analysisInfo = document.createElement('div');
                    analysisInfo.style.cssText = `
                        margin-top: 12px;
                        padding: 10px;
                        background: rgba(0,0,0,0.03);
                        border-radius: 8px;
                        font-size: 0.8rem;
                        color: #666;
                        text-align: center;
                    `;
                    const analysisIcon = analysisResult.analysisType === 'dynamic' ? '🔍' : '📋';
                    const analysisText = analysisResult.analysisType === 'dynamic' 
                        ? 'Análisis dinámico (colores detectados automáticamente)' 
                        : 'Análisis con rangos predefinidos';
                    analysisInfo.innerHTML = `${analysisIcon} <strong>${analysisText}</strong><br>
                        <small>Total píxeles analizados: ${analysisResult.totalPixels?.toLocaleString() || 'N/A'}</small>`;
                    legendContainer.appendChild(analysisInfo);
                    
                    // NUEVO: Generar y mostrar interpretación profesional
                    try {
                        const interpretacion = generarInterpretacionProfesional(resultsWithColors, tipo, analysisResult.metadata);
                        const interpretacionHTML = generarHTMLInterpretacion(interpretacion, tipo);
                        
                        // Crear contenedor de interpretación si no existe
                        let interpretacionContainer = legendContainer.querySelector('.interpretacion-profesional');
                        if (!interpretacionContainer) {
                            interpretacionContainer = document.createElement('div');
                            interpretacionContainer.className = 'interpretacion-profesional mt-3';
                            legendContainer.appendChild(interpretacionContainer);
                        }
                        interpretacionContainer.innerHTML = interpretacionHTML;
                        
                        console.log(`[IMAGE_ANALYSIS] Interpretación profesional generada para ${tipo.toUpperCase()}`);
                    } catch (interpError) {
                        console.warn('[IMAGE_ANALYSIS] Error al generar interpretación profesional:', interpError);
                    }
                    
                    // CONTEXTUALIZACIÓN CON CICLO DE CULTIVO (si existe)
                    // No modifica el análisis existente, solo agrega información adicional debajo
                    try {
                        if (window.AgrotechCropCycles && typeof window.AgrotechCropCycles.getContextualInterpretation === 'function') {
                            const parcelId = window.AGROTECH_STATE?.selectedParcelId;
                            if (parcelId) {
                                // Calcular valor promedio ponderado del índice a partir de los resultados del análisis
                                // Usar la categoría dominante para estimar un valor representativo
                                const indexRanges = {
                                    ndvi: {
                                        'Vegetación Muy Densa': 0.85, 'Vegetación Densa': 0.65,
                                        'Vegetación Moderada': 0.45, 'Vegetación Escasa': 0.25,
                                        'Estrés Severo': 0.10, 'Suelo Desnudo': 0.02
                                    },
                                    ndmi: {
                                        'Muy Húmedo': 0.50, 'Húmedo': 0.30, 'Moderado': 0.10,
                                        'Seco': -0.10, 'Muy Seco': -0.30, 'Estrés Hídrico': -0.50
                                    },
                                    savi: {
                                        'Vegetación Muy Densa': 0.75, 'Vegetación Densa': 0.55,
                                        'Vegetación Moderada': 0.35, 'Vegetación Escasa': 0.18,
                                        'Suelo con poca vegetación': 0.08, 'Suelo Desnudo': 0.02
                                    }
                                };
                                const ranges = indexRanges[tipo.toLowerCase()] || {};
                                let weightedSum = 0;
                                let totalPercent = 0;
                                for (const r of resultsWithColors) {
                                    const refValue = ranges[r.name] ?? 0.5;
                                    weightedSum += refValue * r.percent;
                                    totalPercent += r.percent;
                                }
                                const avgValue = totalPercent > 0 ? parseFloat((weightedSum / totalPercent).toFixed(3)) : 0.5;
                                
                                const contextResult = await window.AgrotechCropCycles.getContextualInterpretation(parcelId, tipo.toLowerCase(), avgValue);
                                if (contextResult && contextResult.status !== 'unknown') {
                                    let cropContextContainer = legendContainer.querySelector('.crop-context-interpretation');
                                    if (!cropContextContainer) {
                                        cropContextContainer = document.createElement('div');
                                        cropContextContainer.className = 'crop-context-interpretation mt-3';
                                        legendContainer.appendChild(cropContextContainer);
                                    }
                                    // renderContextualBadge es async y genera su propio HTML internamente
                                    const badgeHtml = await window.AgrotechCropCycles.renderContextualBadge(parcelId, tipo.toLowerCase(), avgValue);
                                    if (badgeHtml) {
                                        cropContextContainer.innerHTML = badgeHtml;
                                    }
                                    console.log(`[IMAGE_ANALYSIS] Contexto de ciclo de cultivo agregado para ${tipo.toUpperCase()} (valor estimado: ${avgValue})`);
                                }
                            }
                        }
                    } catch (cropContextError) {
                        console.warn('[IMAGE_ANALYSIS] Ciclo de cultivo no disponible (esperado si no hay ciclo activo):', cropContextError.message);
                    }
                }
                
                return;
            }
        } catch (error) {
            console.error('[IMAGE_ANALYSIS] Error en el análisis de imagen:', error);
        }
        
        // Si el análisis automático falla, usar el análisis básico
        try {
            const basicAnalysisResult = await analyzeImageByColor(imageSrc, colorDefinitions);
            console.log(`[IMAGE_ANALYSIS] Resultado del análisis básico:`, basicAnalysisResult);
            
            if (basicAnalysisResult && basicAnalysisResult.success) {
                // Mostrar resultados básicos en la leyenda
                updateColorLegendInDOM(basicAnalysisResult.results, tipo);
                
                // Mensaje de éxito
                showInfoToast(`✅ Imagen ${tipo.toUpperCase()} lista con análisis básico.`);
            }
        } catch (error) {
            console.error('[IMAGE_ANALYSIS] Error en el análisis básico:', error);
            showErrorToast(`❌ Error en el análisis de imagen: ${error.message}`);
        }
    } catch (error) {
        console.error('[IMAGE_ANALYSIS] Error inesperado:', error);
        showErrorToast(`❌ Error inesperado: ${error.message}`);
    }
};

// --- FUNCIONES DE CONTROL DE MAPA BASE ---

/**
 * Cambiar el proveedor de mapa base de Cesium
 * @param {string} provider - Tipo de proveedor: 'osm', 'esri', 'cartodb'
 */
window.changeMapProvider = function(provider) {
    if (!viewer || !viewerReady) {
        console.warn('[MAP_PROVIDER] Cesium viewer no está listo');
        showErrorToast('El visor no está listo. Intenta en unos segundos.');
        return;
    }
    
    try {
        console.log(`[MAP_PROVIDER] Cambiando a proveedor: ${provider}`);
        
        let imageryProvider;
        let providerName;
        
        switch (provider) {
            case 'osm':
                imageryProvider = new Cesium.OpenStreetMapImageryProvider({
                    url: 'https://a.tile.openstreetmap.org/',
                    credit: 'OpenStreetMap'
                });
                providerName = 'OpenStreetMap';
                break;
                
            case 'esri':
                imageryProvider = new Cesium.ArcGisMapServerImageryProvider({
                    url: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer',
                    credit: 'Esri, DigitalGlobe, GeoEye, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN, and the GIS User Community'
                });
                providerName = 'Esri World Imagery';
                break;
                
            case 'cartodb':
                imageryProvider = new Cesium.UrlTemplateImageryProvider({
                    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
                    subdomains: ['a', 'b', 'c', 'd'],
                    credit: 'CartoDB'
                });
                providerName = 'CartoDB Positron';
                break;
                
            default:
                console.warn(`[MAP_PROVIDER] Proveedor desconocido: ${provider}`);
                showErrorToast(`Proveedor de mapa desconocido: ${provider}`);
                return;
        }
        
        // Remover la capa base actual (primera capa)
        if (viewer.imageryLayers.length > 0) {
            const currentBaseLayer = viewer.imageryLayers.get(0);
            viewer.imageryLayers.remove(currentBaseLayer);
        }
        
        // Agregar nueva capa base al inicio (índice 0)
        const newBaseLayer = viewer.imageryLayers.addImageryProvider(imageryProvider, 0);
        
        console.log(`[MAP_PROVIDER] Mapa base cambiado a: ${providerName}`);
        showInfoToast(`✅ Mapa base cambiado a: ${providerName}`);
        
    } catch (error) {
        console.error('[MAP_PROVIDER] Error al cambiar proveedor de mapa:', error);
        showErrorToast(`Error al cambiar el mapa base: ${error.message}`);
    }
};

/**
 * Función alternativa para cambio de mapa (switchMapProvider)
 * Similar a changeMapProvider pero con manejo de errores mejorado
 * @param {string} providerId - ID del proveedor
 */
window.switchMapProvider = function(providerId) {
    if (!viewer || !viewerReady) {
        console.warn('[SWITCH_MAP] Cesium viewer no está listo');
        return false;
    }
    
    try {
        // Mapear IDs a nombres estándar
        const providerMap = {
            'openstreetmap': 'osm',
            'esri-imagery': 'esri',
            'cartodb-light': 'cartodb'
        };
        
        const normalizedProvider = providerMap[providerId] || providerId;
        
        // Llamar a la función principal
        changeMapProvider(normalizedProvider);
        return true;
        
    } catch (error) {
        console.error('[SWITCH_MAP] Error en switchMapProvider:', error);
        return false;
    }
};

/**
 * Reinicializar Cesium si hay problemas de visualización
 */
window.reinitializeCesium = function() {
    console.log('[CESIUM_REINIT] Reinicializando Cesium...');
    
    try {
        if (viewer) {
            viewer.destroy();
            viewer = null;
        }
        
        // Limpiar el contenedor
        const mapContainer = document.getElementById('mapContainer');
        if (mapContainer) {
            mapContainer.innerHTML = '';
        }
        
        // Mostrar mensaje de carga
        showSpinner('Reinicializando mapa...');
        
        // Reinicializar después de un pequeño delay
        setTimeout(() => {
            try {
                initializeCesium();
                hideSpinner();
                showInfoToast('✅ Mapa reinicializado correctamente');
            } catch (error) {
                hideSpinner();
                console.error('[CESIUM_REINIT] Error al reinicializar:', error);
                showErrorToast('Error al reinicializar el mapa');
            }
        }, 1000);
        
    } catch (error) {
        hideSpinner();
        console.error('[CESIUM_REINIT] Error durante reinicialización:', error);
        showErrorToast('Error durante la reinicialización del mapa');
    }
};

/**
 * Obtener información del proveedor de mapa actual
 */
window.getCurrentMapProvider = function() {
    if (!viewer || !viewerReady || viewer.imageryLayers.length === 0) {
        return null;
    }
    
    try {
        const baseLayer = viewer.imageryLayers.get(0);
        const provider = baseLayer.imageryProvider;
        
        // Identificar el proveedor basado en la URL o constructor
        if (provider.url && provider.url.includes('openstreetmap')) {
            return { id: 'osm', name: 'OpenStreetMap' };
        } else if (provider.url && provider.url.includes('arcgis')) {
            return { id: 'esri', name: 'Esri World Imagery' };
        } else if (provider.url && provider.url.includes('cartocdn')) {
            return { id: 'cartodb', name: 'CartoDB Positron' };
        } else {
            return { id: 'unknown', name: 'Proveedor desconocido' };
        }
        
    } catch (error) {
        console.error('[GET_MAP_PROVIDER] Error al obtener proveedor:', error);
        return null;
    }
};

// Exponer funciones globalmente para compatibilidad
window.changeMapProvider = changeMapProvider;
window.switchMapProvider = switchMapProvider;
window.reinitializeCesium = reinitializeCesium;
window.getCurrentMapProvider = getCurrentMapProvider;