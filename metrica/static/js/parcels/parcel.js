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
        window.EOSDA_STATE.selectedParcelId = parcelId;
        window.EOSDA_STATE.selectedEosdaId = eosda_id;
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
window.EOSDA_STATE = {
  selectedParcelId: null,
  selectedEosdaId: null,
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
    window.EOSDA_STATE.requestIds = {};
    console.log('[CACHE CLEARED] Cache de EOSDA limpiado');
};

// BASE_URL usa rutas relativas para aprovechar los redirects de Netlify
// Netlify redirige /api/* → https://agrotechcolombia.com/api/* preservando el tenant
const BASE_URL = window.ApiUrls ? window.ApiUrls.parcels() : '/api/parcels';

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

        // Inicializar el mapa Leaflet centrado en Colombia
        map = L.map('cesiumContainer', {
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
        const mapContainer = document.getElementById('cesiumContainer');
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
                        
                    } catch (error) {
                        console.error("Error dibujando parcela en el mapa:", error);
                    }
                }
            });
        })
        .catch(error => {
            console.error("Error al cargar las parcelas:", error);
            showErrorToast("Error al cargar las parcelas: " + (error.message || error));
        });
}

import { showErrorToast, showInfoToast, showNDVIToggleButton, showNDMIToggleButton, showSceneSelectionModal } from "./layers.js";

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
            window.EOSDA_STATE.selectedParcelId = parcelId;
            window.EOSDA_STATE.selectedEosdaId = feature.eosda_id || null;
            window.EOSDA_STATE.selectedScene = null;
            window.EOSDA_STATE.ndviActive = false;
            window.EOSDA_STATE.requestIds = {};

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
    // PRIMERO: Verificar que Leaflet exista
    if (typeof L === 'undefined') {
        console.error('[LEAFLET] Leaflet no está disponible. Verifica la importación del script.');
        
        // Mostrar mensaje al usuario
        const mapContainer = document.getElementById('cesiumContainer');
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
        const parcelaSeleccionada = !!window.EOSDA_STATE.selectedParcelId;
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
            const parcelaSeleccionada = !!window.EOSDA_STATE.selectedParcelId;
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
            const parcelId = window.EOSDA_STATE.selectedParcelId;
            const startDate = fechaInicio.value;
            const endDate = fechaFin.value;
            await buscarEscenasPorRango(parcelId, startDate, endDate);
        };
    }

    // Configurar evento para botón de análisis meteorológico
    const btnAnalisisMeteorologico = document.getElementById("analisisMeteorologicoBtn");
    if (btnAnalisisMeteorologico) {
        btnAnalisisMeteorologico.onclick = function() {
            const parcelaSeleccionada = !!window.EOSDA_STATE.selectedParcelId;
            
            if (!parcelaSeleccionada) {
                showErrorToast("Selecciona primero una parcela para ver el análisis meteorológico.");
                return;
            }
            
            const parcelId = window.EOSDA_STATE.selectedParcelId;
            
            // Mostrar la sección de análisis meteorológico
            const meteorologicalSection = document.getElementById("meteorologicalAnalysisSection");
            if (meteorologicalSection) {
                meteorologicalSection.style.display = "block";
                
                // Actualizar explícitamente el estado global antes de llamar a la función
            window.EOSDA_STATE.selectedParcelId = parcelId;
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
                "⚠️ EOSDA API: Límite de consultas excedido. " +
                "Se ha alcanzado el límite mensual de la API de imágenes satelitales. " +
                "Contacte al administrador del sistema.",
                { duration: 10000 } // Toast más largo para este error crítico
            );
            
            // Mostrar modal con más información
            if (confirm(
                "❌ LÍMITE DE API EOSDA EXCEDIDO\n\n" +
                "Se ha alcanzado el límite mensual de consultas a EOSDA API Connect.\n" +
                "• Límite: 1000 requests/mes\n" +
                "• Estado: Excedido\n\n" +
                "¿Desea contactar al administrador?"
            )) {
                window.open('mailto:admin@agrotech.com?subject=Límite EOSDA API Excedido&body=Se necesita renovar el plan de EOSDA API Connect');
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
                `El campo con ID ${errorData.field_id} no existe en EOSDA API Connect.\n\n` +
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

        // Crear modal
        const modal = document.createElement("div");
        modal.id = "sceneSelectionModal";
        modal.style.position = "fixed";
        modal.style.top = "0";
        modal.style.left = "0";
        modal.style.width = "100vw";
        modal.style.height = "100vh";
        modal.style.background = "rgba(79, 227, 5, 0.05)";
        modal.style.zIndex = "9999";
        modal.style.display = "flex";
        modal.style.alignItems = "center";
        modal.style.justifyContent = "center";

        // Contenido del modal
        const content = document.createElement("div");
        content.style.background = "#fff";
        content.style.padding = "32px";
        content.style.borderRadius = "12px";
        content.style.boxShadow = "0 2px 16px rgba(0,0,0,0.2)";
        content.style.maxWidth = "600px";
        content.style.width = "100%";

        // Título
        const title = document.createElement("h3");
        title.textContent = "Selecciona la escena satelital a visualizar";
        title.style.marginBottom = "12px";
        content.appendChild(title);

        // Mensaje explicativo sobre nubosidad
        const infoBox = document.createElement("div");
        infoBox.style.marginBottom = "18px";
        infoBox.style.padding = "10px 12px";
        infoBox.style.borderRadius = "6px";
        infoBox.style.backgroundColor = "#e7f3ff";
        infoBox.style.border = "1px solid #b3d9ff";
        infoBox.style.fontSize = "13px";
        infoBox.style.lineHeight = "1.5";
        infoBox.innerHTML = `
            <strong>💡 Importante sobre la nubosidad:</strong><br>
            Las nubes bloquean la vista del satélite y hacen que los análisis (NDVI, NDMI) sean inexactos.<br>
            <strong>Recomendación:</strong> Selecciona escenas con <strong>menos del 30% de nubes</strong> para obtener datos precisos.
        `;
        content.appendChild(infoBox);

        // Mensaje informativo sobre filtrado - explicación clara para usuarios
        if (filteredCount > 0) {
            const filterMessage = document.createElement("div");
            filterMessage.style.marginBottom = "15px";
            filterMessage.style.padding = "12px 15px";
            filterMessage.style.borderRadius = "8px";
            filterMessage.style.fontSize = "14px";
            filterMessage.style.lineHeight = "1.5";
            
            if (lowCloudScenes.length > 0) {
                filterMessage.style.backgroundColor = "#d1ecf1";
                filterMessage.style.color = "#0c5460";
                filterMessage.style.border = "1px solid #bee5eb";
                filterMessage.innerHTML = `
                    <div style="display:flex;align-items:flex-start;gap:10px;">
                        <i class="fas fa-info-circle" style="font-size:20px;margin-top:2px;"></i>
                        <div>
                            <strong>Filtro aplicado:</strong> Se ocultaron ${filteredCount} imagen(es) porque tenían más del 75% del cielo cubierto por nubes.
                            <br><small>Mostramos solo las imágenes con cielo más despejado para obtener análisis más precisos.</small>
                        </div>
                    </div>`;
            } else {
                filterMessage.style.backgroundColor = "#fff3cd";
                filterMessage.style.color = "#856404";
                filterMessage.style.border = "1px solid #ffeeba";
                filterMessage.innerHTML = `
                    <div style="display:flex;align-items:flex-start;gap:10px;">
                        <i class="fas fa-exclamation-triangle" style="font-size:20px;margin-top:2px;"></i>
                        <div>
                            <strong>⚠️ Atención:</strong> No hay imágenes satelitales con cielo despejado en este período.
                            <br>Todas las imágenes disponibles tienen más del 75% del cielo cubierto por nubes, lo que <strong>afectará significativamente</strong> la precisión del análisis.
                            <br><small>💡 <strong>Recomendación:</strong> Intenta seleccionar otro rango de fechas con mejor clima. Las escenas con más del 50% de nubes tienen datos poco confiables.</small>
                        </div>
                    </div>`;
            }
            content.appendChild(filterMessage);
        }

        // Tabla con botones NDVI y NDMI y porcentaje de nubosidad
        const table = document.createElement("table");
        table.style.width = "100%";
        table.style.borderCollapse = "collapse";
        table.innerHTML = `
            <thead>
                <tr style="background:#f5f5f5">
                    <th style="padding:8px;border-bottom:1px solid #ccc">Fecha</th>
                    <th style="padding:8px;border-bottom:1px solid #ccc">Cobertura de nubes (%)</th>
                    <th style="padding:8px;border-bottom:1px solid #ccc">NDVI</th>
                    <th style="padding:8px;border-bottom:1px solid #ccc">NDMI</th>
                    <th style="padding:8px;border-bottom:1px solid #ccc">Analytics</th>
                </tr>
            </thead>
            <tbody>
                ${finalScenes.map((scene, idx) => {
                    let cloud = scene.cloudCoverage ?? scene.cloud ?? scene.nubosidad;
                    let cloudText = (typeof cloud === 'number') ? cloud.toFixed(1) : (cloud ? cloud : '-');
                    
                    // Badge visual por nivel de nubosidad
                    let cloudBadge = '';
                    let rowStyle = '';
                    if (typeof cloud === 'number') {
                        if (cloud <= 30) {
                            cloudBadge = ' <span class="badge" style="background:#28a745;color:#fff;padding:3px 8px;border-radius:12px;font-size:11px;font-weight:600;">✓ Óptima</span>';
                            rowStyle = 'background:#f0fff4;'; // Verde claro
                        } else if (cloud <= 50) {
                            cloudBadge = ' <span class="badge" style="background:#ffc107;color:#000;padding:3px 8px;border-radius:12px;font-size:11px;font-weight:600;">⚠ Aceptable</span>';
                            rowStyle = 'background:#fffbf0;'; // Amarillo claro
                        } else {
                            cloudBadge = ' <span class="badge" style="background:#dc3545;color:#fff;padding:3px 8px;border-radius:12px;font-size:11px;font-weight:600;">✗ No recomendada</span>';
                            rowStyle = 'background:#fff5f5;'; // Rojo claro
                        }
                    }
                    
                    console.log('[SCENE_ROW]', { scene, viewId: scene.view_id, date: scene.date, idx });
                    return `
                        <tr style="${rowStyle}">
                            <td style="padding:8px;border-bottom:1px solid #eee">${scene.date ? scene.date.split('T')[0] : '-'}</td>
                            <td style="padding:8px;border-bottom:1px solid #eee">${cloudText}%${cloudBadge}</td>
                            <td style="padding:8px;border-bottom:1px solid #eee">
                                <button class="btn btn-sm btn-success" data-ndvi-idx="${idx}">Ver NDVI</button>
                            </td>
                            <td style="padding:8px;border-bottom:1px solid #eee">
                                <button class="btn btn-sm btn-info" data-ndmi-idx="${idx}">Ver NDMI</button>
                            </td>
                            <td style="padding:8px;border-bottom:1px solid #eee">
                                <button class="btn btn-sm btn-warning" onclick="obtenerAnalyticsEscena('${scene.view_id}', '${scene.date}')">📊 Stats</button>
                            </td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        `;
        content.appendChild(table);

        // Botón cerrar
        const closeBtn = document.createElement("button");
        closeBtn.textContent = "Cerrar";
        closeBtn.className = "btn btn-secondary";
        closeBtn.style.marginTop = "18px";
        closeBtn.onclick = () => {
            modal.remove();
            resolve({ ndvi: null, ndmi: null });
        };
        content.appendChild(closeBtn);

        modal.appendChild(content);
        document.body.appendChild(modal);

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
                        resolve({ ndvi: true, ndmi: false });
                    }
                } finally {
                    // Rehabilitar botones si aún existe el modal
                    if (document.body.contains(modal)) {
                        modalButtons.forEach(b => {
                            b.disabled = false;
                            if (b.getAttribute('data-ndvi-idx')) {
                                b.innerHTML = 'Ver NDVI';
                            } else if (b.getAttribute('data-ndmi-idx')) {
                                b.innerHTML = 'Ver NDMI';
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
                        resolve({ ndvi: false, ndmi: true });
                    }
                } finally {
                    // Rehabilitar botones si aún existe el modal
                    if (document.body.contains(modal)) {
                        modalButtons.forEach(b => {
                            b.disabled = false;
                            if (b.getAttribute('data-ndvi-idx')) {
                                b.innerHTML = 'Ver NDVI';
                            } else if (b.getAttribute('data-ndmi-idx')) {
                                b.innerHTML = 'Ver NDMI';
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
            showNDVIImageOnCesium(window.EOSDA_IMAGE_CACHE[cacheKey], bounds, mapInstance);
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
    
    // Crear URL para la imagen base64
    const imageUrl = `data:image/png;base64,${imageBase64}`;
    
    // bounds: [west, south, east, north]
    // Convertir a formato Leaflet [[south, west], [north, east]]
    const leafletBounds = [[bounds[1], bounds[0]], [bounds[3], bounds[2]]];
    
    // Agregar imagen como overlay con clase identificadora
    const imageOverlay = L.imageOverlay(imageUrl, leafletBounds, {
        opacity: 0.7,
        className: 'ndvi-layer'
    }).addTo(mapInstance);
    
    console.log('[LEAFLET_NDVI] Imagen NDVI/NDMI superpuesta correctamente');
    
    return imageOverlay;
}

// Mantener función antigua para compatibilidad con código existente
function showNDVIImageOnCesium(imageBase64, bounds, viewerOrMap) {
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
    const fieldId = window.EOSDA_STATE.selectedEosdaId;
    const parcelId = window.EOSDA_STATE.selectedParcelId;
    
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
        showNDVIImageOnCesium(window.EOSDA_IMAGE_CACHE[cacheKey], bounds, map);
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
        let requestId = window.EOSDA_STATE.requestIds[requestIdCacheKey];
        
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
            window.EOSDA_STATE.requestIds[requestIdCacheKey] = requestId;
            console.log('[CACHE SET] request_id guardado en cache frontend:', requestId);
        } else {
            console.log('[CACHE HIT] request_id encontrado en cache frontend:', requestId);
        }
        
        // Paso 2: Polling automático para obtener la imagen (SIN mensajes al usuario)
        const maxAttempts = 10; // Aumentar intentos para mejor experiencia
        const baseInterval = 3000; // Intervalo base de 3s
        let attempts = 0;
        
        showSpinner(`Procesando imagen ${tipo.toUpperCase()}... (puede tomar 1-2 minutos)`);
        
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
                    showNDVIImageOnCesium(imgData.image_base64, bounds, map);
                    
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
                    // Error específico del backend
                    hideSpinner();
                    showErrorToast(`❌ Error procesando imagen: ${imgData.error}`);
                    return { success: false };
                }
                
                // La imagen aún se está procesando - continuar polling SIN molestar al usuario
                console.log(`[POLLING] Intento ${attempts + 1}/${maxAttempts} - Imagen aún procesándose...`);
                
            } catch (err) {
                console.error(`[POLLING] Error en intento ${attempts + 1}:`, err);
                // Continuar con el siguiente intento
            }
            
            attempts++;
            
            if (attempts < maxAttempts) {
                // Actualizar mensaje del spinner para mostrar progreso
                const progress = Math.round((attempts / maxAttempts) * 100);
                showSpinner(`Procesando imagen ${tipo.toUpperCase()}... ${progress}% (${attempts}/${maxAttempts})`);
                
                // Intervalo progresivo: empezar rápido, luego más lento
                const currentInterval = attempts <= 3 ? baseInterval : baseInterval + (attempts * 1000);
                await new Promise(resolve => setTimeout(resolve, currentInterval));
                       }
        }
        
        // Si llegamos aquí, se agotaron los intentos
        hideSpinner();
        showErrorToast(
            `⏰ La imagen ${tipo.toUpperCase()} está tomando más tiempo del esperado.\n` +
            `Esto puede deberse a:\n` +
            `• Alta demanda en el servidor EOSDA\n` +
            `• Imagen de alta resolución\n` +
            `• Problemas temporales de conectividad\n\n` +
            `💡 Sugerencia: Intenta nuevamente en unos minutos.`
        );
        return { success: false };
        
    } catch (error) {
        hideSpinner();
        console.error('[EOSDA_IMAGE_ERROR] Error general:', error);
        showErrorToast(`❌ Error inesperado al procesar imagen ${tipo.toUpperCase()}: ${error.message || error}`);
        return { success: false };
    }
};

// --- NDVI/NDMI: Visualización y análisis de porcentajes ---
window.mostrarImagenNDVIConAnalisis = async function(imageSrc, tipo = 'ndvi', sceneDate = null) {
    try {
        // Importar análisis dinámicamente
        const { analyzeImageByColor, analyzeImageByColorAdvanced, NDVI_COLOR_DEFINITIONS, NDMI_COLOR_DEFINITIONS, updateColorLegendInDOM } = await import('./analysis.js');
        
        // Seleccionar definiciones de colores según el tipo
        const colorDefinitions = tipo === 'ndvi' ? NDVI_COLOR_DEFINITIONS : NDMI_COLOR_DEFINITIONS;
        const title = tipo === 'ndvi' ? '🌱 Análisis NDVI' : '💧 Análisis NDMI';
        
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
            const analysisResult = await analyzeImageByColorAdvanced(imageSrc, colorDefinitions);
            console.log(`[IMAGE_ANALYSIS] Resultado del análisis:`, analysisResult);
            
            if (analysisResult && analysisResult.success) {
                // Añadir información de color a los resultados
                const resultsWithColors = analysisResult.results.map((result, index) => ({
                    ...result,
                    color: colorDefinitions[index]?.rgb || [128, 128, 128]
                }));
                
                console.log(`[IMAGE_ANALYSIS] Resultados con colores:`, resultsWithColors);
                
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
                    resultsContainer.style.gridTemplateColumns = 'repeat(auto-fill, minmax(120px, 1fr))';
                    resultsContainer.style.gap = '8px';
                    legendContainer.appendChild(resultsContainer);
                    
                    // Añadir tarjetas de resultados
                    resultsWithColors.forEach((result, index) => {
                        const card = document.createElement('div');
                        card.style.background = 'rgba(255, 255, 255, 0.8)';
                        card.style.borderRadius = '8px';
                        card.style.padding = '12px';
                        card.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
                        card.style.position = 'relative';
                        card.style.overflow = 'hidden';
                        
                        // Color de fondo según el resultado
                        card.style.backgroundColor = `rgb(${result.color.join(',')})`;
                        
                        // Texto del resultado
                        const text = document.createElement('div');
                        text.style.fontSize = '1rem';
                        text.style.fontWeight = 'bold';
                        text.style.color = '#fff';
                        text.style.textAlign = 'center';
                        text.style.marginBottom = '4px';
                        text.textContent = result.label;
                        card.appendChild(text);
                        
                        // Porcentaje (si aplica)
                        if (result.percentage != null) {
                            const percentage = document.createElement('div');
                            percentage.style.fontSize = '0.9rem';
                            percentage.style.color = '#fff';
                            percentage.style.textAlign = 'center';
                            percentage.textContent = `${result.percentage.toFixed(1)}%`;
                            card.appendChild(percentage);
                        }
                        
                        // Indicador de análisis dinámico (si aplica)
                        if (analysisResult.analysisType === 'dynamic') {
                            const dynamicIndicator = document.createElement('div');
                            dynamicIndicator.style.position = 'absolute';
                            dynamicIndicator.style.top = '8px';
                            dynamicIndicator.style.right = '8px';
                            dynamicIndicator.style.background = 'rgba(255, 255, 255, 0.9)';
                            dynamicIndicator.style.color = '#333';
                            dynamicIndicator.style.fontSize = '0.8rem';
                            dynamicIndicator.style.padding = '4px 8px';
                            dynamicIndicator.style.borderRadius = '12px';
                            dynamicIndicator.textContent = 'Análisis dinámico';
                            card.appendChild(dynamicIndicator);
                        }
                        
                        resultsContainer.appendChild(card);
                    });
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
        const cesiumContainer = document.getElementById('cesiumContainer');
        if (cesiumContainer) {
            cesiumContainer.innerHTML = '';
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