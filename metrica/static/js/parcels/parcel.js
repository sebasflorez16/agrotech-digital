// Modal Bootstrap para mostrar escenas EOSDA
function crearModalEscenasEOSDA() {
    let modal = document.getElementById('eosdaScenesModal');
    if (modal) return modal; // Ya existe
    modal = document.createElement('div');
    modal.id = 'eosdaScenesModal';
    modal.className = 'modal fade';
    modal.tabIndex = -1;
    modal.innerHTML = `
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Escenas satelitales EOSDA</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
          </div>
          <div class="modal-body">
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
    // Consultar escenas
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
        if (!scenes.length) {
            document.getElementById('eosdaScenesTableContainer').innerHTML = '<div class="alert alert-warning">No hay escenas disponibles para este campo.</div>';
            return;
        }
        // Renderizar tabla Bootstrap con botón Ver imagen
        let html = `<table class="table table-striped table-bordered">
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>View ID</th>
                    <th>Nubosidad (%)</th>
                    <th>NDVI</th>
                    <th>NDMI</th>
                </tr>
            </thead>
            <tbody>
                ${scenes.map(scene => `
                    <tr>
                        <td>${scene.date}</td>
                        <td>${scene.view_id}</td>
                        <td>${scene.cloud != null ? scene.cloud.toFixed(2) : 'N/A'}</td>
                        <td><button class="btn btn-success btn-sm" onclick="verImagenEscenaEOSDA('${scene.view_id}', 'ndvi')">Ver NDVI</button></td>
                        <td><button class="btn btn-info btn-sm" onclick="verImagenEscenaEOSDA('${scene.view_id}', 'ndmi')">Ver NDMI</button></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>`;
        document.getElementById('eosdaScenesTableContainer').innerHTML = html;
    } catch (err) {
        document.getElementById('eosdaScenesTableContainer').innerHTML = '<div class="alert alert-danger">Error al consultar escenas EOSDA.</div>';
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
  requestIds: {}
};

const BASE_URL = `http://${window.location.hostname}:8000/api/parcels`;

// Inicializar el mapa de Cesium
// Variables globales
let axiosInstance; // Declarar axiosInstance como global
let positions = []; // Almacena las posiciones del polígono
let polygonEntity = null; // Referencia al polígono dibujado

let viewer; // Declarar viewer como global
let viewerReady = true;



// Inicializar el mapa de Cesium
function initializeCesium() {
    const token = localStorage.getItem("accessToken");

    if (!token) {
        console.error("No se encontró el token. Redirigiendo...");
        window.location.href = "/templates/authentication/login.html";
        return;
    }

    // Configurar axios
    axiosInstance = axios.create({ // Asignar axiosInstance a la variable global
        baseURL: BASE_URL,
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        }
    });

    loadParcels(); // Llamar a loadParcels después de configurar axiosInstance y inicializar el mapa de Cesium

    // Obtener datos del backend
    axiosInstance.get("/parcel/")
        .then(response => {
            const data = response.data;
            const cesiumToken = data.cesium_token;
            if (!cesiumToken) {
                alert("No se recibió el token Cesium del backend. Contacta al administrador.");
                console.error("Token Cesium faltante en la respuesta del backend.");
                return;
            }
            Cesium.Ion.defaultAccessToken = cesiumToken;

            // Las URLs WMTS/TMS de EOSDA ahora deben apuntar al proxy backend para evitar CORS y proteger el token
            // Inicializar el visor de Cesium

            // Inicializar el visor de Cesium ocultando controles nativos innecesarios
            viewer = new Cesium.Viewer('cesiumContainer', {
                terrainProvider: Cesium.createWorldTerrain(), // Agrega relieve
                baseLayerPicker: true, // Evita cambiar capas
                shouldAnimate: true, // Habilita animaciones
                sceneMode: Cesium.SceneMode.SCENE2D, // Mostrar en 2D por defecto
                timeline: false, // Oculta el timeline
                animation: false, // muestra el widget de animación
                geocoder: true, // muestra la búsqueda
                homeButton: false, // Oculta el botón home
                infoBox: false, // Oculta el infoBox
                sceneModePicker: true, // Muestra el selector de modo
                selectionIndicator: false, // Oculta el indicador de selección
                navigationHelpButton: false, // Oculta el botón de ayuda
                navigationInstructionsInitiallyVisible: false, // Oculta instrucciones
                fullscreenButton: false, // Oculta el botón fullscreen
                vrButton: false, // Oculta el botón VR
                creditContainer: document.createElement('div') // Oculta el logo de Cesium
            });

            // Asegurarse de que los controles de cámara estén habilitados
            const controller = viewer.scene.screenSpaceCameraController;
            controller.enableZoom = true;
            controller.enableRotate = true;
            controller.enableTranslate = true;
            controller.enableTilt = true;
            controller.enableLook = true;

            // Centrar el mapa en Colombia
            viewer.scene.camera.setView({
                destination: Cesium.Cartesian3.fromDegrees(-74.0817, 4.6097, 1000000)
            });

            console.log("Cesium cargado correctamente. Esperando datos...");

            // 🔹 Dibujar parcelas guardadas
            if (data.features) {
                data.features.forEach(parcel => {
                    const coordinates = parcel.geometry.coordinates[0].map(coord =>
                        Cesium.Cartesian3.fromDegrees(coord[0], coord[1])
                    );
                    // Polígono transparente (solo borde)
                    viewer.entities.add({
                        name: parcel.properties.name || "Parcela sin nombre",
                        polygon: {
                            hierarchy: new Cesium.PolygonHierarchy(coordinates),
                            material: Cesium.Color.TRANSPARENT,
                            outline: true,
                            outlineColor: Cesium.Color.BLACK
                        }
                    });
                    // Polyline para borde visible (verde oscuro, grosor 2)
                    viewer.entities.add({
                        polyline: {
                            positions: coordinates.concat([coordinates[0]]),
                            width: 2,
                            material: Cesium.Color.fromCssColorString('#145A32') // Verde oscuro
                        }
                    });
                });
            }
            // 🔹 Agregar controles de dibujo
            setupDrawingTools(viewer);
        })
        .catch(error => console.error("Error al obtener datos:", error));
}

// 🔹 Función separada para manejar el dibujo
function setupDrawingTools(viewer) {
    let isDrawing = false;

    // Referencia al botón
    const cancelBtn = document.getElementById("cancel-button");

    window.startDrawing = function () {
        isDrawing = true;
        positions = []; // Reiniciar las posiciones al iniciar un nuevo dibujo
        polygonEntity = null;
        cancelBtn.style.display = "none";
        console.log("Dibujo iniciado.");
    };

    window.cancelDrawing = function () {
        isDrawing = false;
        positions = []; // Limpiar las posiciones al cancelar el dibujo
        if (polygonEntity) {
            viewer.entities.remove(polygonEntity);
            polygonEntity = null;
        }
        cancelBtn.style.display = "none";
        console.log("Dibujo cancelado.");
    };

    viewer.screenSpaceEventHandler.setInputAction((click) => {
        if (!isDrawing) return;

        let cartesian = viewer.scene.pickPosition(click.position);
        if (!cartesian) {
            cartesian = viewer.camera.pickEllipsoid(click.position, viewer.scene.globe.ellipsoid);
        }

        if (cartesian) {
            positions.push(cartesian);

            // Mostrar botón cancelar si hay al menos 1 punto
            if (positions.length > 0) {
                cancelBtn.style.display = "block";
            }

            if (!polygonEntity) {
                polygonEntity = viewer.entities.add({
                    polygon: {
                        hierarchy: new Cesium.CallbackProperty(() => {
                            return new Cesium.PolygonHierarchy(positions);
                        }, false),
                        material: Cesium.Color.RED.withAlpha(0.5), // Pintar de rojo con transparencia
                        outline: true,
                        outlineColor: Cesium.Color.RED
                    }
                });
            }
        }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    viewer.screenSpaceEventHandler.setInputAction(() => {
        isDrawing = false;
        console.log("Dibujo finalizado.");
    }, Cesium.ScreenSpaceEventType.RIGHT_CLICK);
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

    // Convertir las posiciones a coordenadas GeoJSON
    const coordinates = positions.map(pos => {
        const cartographic = Cesium.Cartographic.fromCartesian(pos);
        return [Cesium.Math.toDegrees(cartographic.longitude), Cesium.Math.toDegrees(cartographic.latitude)];
    });

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
            console.log("Respuesta del servidor:", response);
            const data = response.data.parcels || []; // Acceder directamente al array de parcelas
            console.log("Datos de parcelas:", data);

            const tableBody = document.getElementById("parcelTable").querySelector("tbody");
            tableBody.innerHTML = ""; // Limpiar la tabla

            if (data.length === 0) {
                // Mostrar mensaje si no hay parcelas
                tableBody.innerHTML = `
                    <tr id="no-parcels-row">
                        <td colspan="6" class="text-center">No hay parcelas registradas.</td>
                    </tr>
                `;
                return;
            }

            // Llenar la tabla con las parcelas
            data.forEach(parcel => {
                // Si el backend envía propiedades directamente en el objeto
                const props = parcel.properties || parcel; // Soporta ambos formatos
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
    <button class="btn btn-warning btn-sm" onclick="mostrarModalEscenasEOSDA(${parcel.id})" title="Escenas Satelitales">
        <i class="bi bi-cloud"></i> Escenas Satelitales
    </button>
</td>
                    <td>
                        <button class="btn btn-primary btn-sm" onclick="editParcel('${parcel.id}')">Editar</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteParcel('${parcel.id}')">Eliminar</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error("Error al cargar las parcelas:", error);
            const tableBody = document.getElementById("parcelTable").querySelector("tbody");
            tableBody.innerHTML = `
                <tr id="no-parcels-row">
                    <td colspan="6" class="text-center text-danger">Error al cargar las parcelas.</td>
                </tr>
            `;
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
    if (!viewerReady || !viewer) {
        alert("El visor Cesium aún no está listo. Intenta en unos segundos.");
        return;
    }

    // Eliminar resaltados previos (polylines amarillas de ancho 4 y verdes de ancho 2)
    const entitiesToRemove = [];
    viewer.entities.values.forEach(entity => {
        if (entity.polyline && entity.polyline.width && entity.polyline.width.getValue) {
            const width = entity.polyline.width.getValue();
            let color = null;
            if (entity.polyline.material && entity.polyline.material.color) {
                color = entity.polyline.material.color.getValue().toCssColorString();
            }
            if (
                (width === 4 && color === Cesium.Color.YELLOW.toCssColorString()) ||
                (width === 2 && color === Cesium.Color.fromCssColorString('#145A32').toCssColorString())
            ) {
                entitiesToRemove.push(entity);
            }
        }
    });
    entitiesToRemove.forEach(entity => viewer.entities.remove(entity));

    // 1. Obtener la geometría y centrar el mapa como antes
    axiosInstance.get(`/parcel/${parcelId}/`)
        .then(async response => {
            const feature = response.data;
            let coordinates = [];
            if (feature.geometry && feature.geometry.coordinates) {
                coordinates = feature.geometry.coordinates[0].map(coord =>
                    Cesium.Cartesian3.fromDegrees(coord[0], coord[1])
                );
            } else if (feature.geom && feature.geom.coordinates) {
                coordinates = feature.geom.coordinates[0].map(coord =>
                    Cesium.Cartesian3.fromDegrees(coord[0], coord[1])
                );
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
            // Centrar el mapa en la parcela
            const boundingSphere = Cesium.BoundingSphere.fromPoints(coordinates);
            viewer.camera.flyToBoundingSphere(boundingSphere, {
                duration: 2,
                complete: () => {
                    viewer.scene.screenSpaceCameraController.enableInputs = true;
                }
            });
            // Resaltar en amarillo temporalmente
            const highlighted = viewer.entities.add({
                polyline: {
                    positions: coordinates.concat([coordinates[0]]),
                    width: 4,
                    material: Cesium.Color.YELLOW
                }
            });
            setTimeout(() => {
                viewer.entities.remove(highlighted);
                viewer.entities.add({
                    polyline: {
                        positions: coordinates.concat([coordinates[0]]),
                        width: 2,
                        material: Cesium.Color.fromCssColorString('#145A32')
                    }
                });
            }, 3000);

            // Actualizar estado global EOSDA
            window.EOSDA_STATE.selectedParcelId = parcelId;
            window.EOSDA_STATE.selectedEosdaId = feature.eosda_id || null;
            window.EOSDA_STATE.selectedScene = null;
            window.EOSDA_STATE.ndviActive = false;
            window.EOSDA_STATE.requestIds = {};

            // Actualizar el botón NDVI
            import('./layers.js').then(mod => {
                mod.showNDVIToggleButton(viewer);
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
    // Inicializar Cesium
    initializeCesium();
});

// Las URLs WMTS/TMS de EOSDA ahora deben apuntar al proxy backend para evitar CORS y proteger el token.
// Función profesional para buscar escenas y construir URLs WMTS usando el nuevo endpoint de búsqueda
async function fetchEosdaWmtsUrls(polygonGeoJson) {
    // Buscar la fecha más reciente disponible (por ejemplo, hace 10 días)
    const today = new Date();
    const daysAgo = 10;
    const fechaNDVI = new Date(today.getFullYear(), today.getMonth(), today.getDate() - daysAgo)
        .toISOString().split('T')[0];
    // Siempre usar prueba.localhost para el proxy WMTS
    const baseProxy = `http://prueba.localhost:8000/api/parcels/eosda-wmts-tile/`;
    // const ndviUrl = ...; const ndmiUrl = ...; Eliminado. Usar Render API.
    return { ndvi: ndviUrl, ndmi: ndmiUrl };
}

// Tabla/modal profesional para que el usuario elija la escena satelital a visualizar
async function showSceneSelectionTable(scenes) {
    return new Promise((resolve) => {
        // Si ya existe el modal, elimínalo
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
        modal.style.background = "rgba(0,0,0,0.4)";
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
        title.style.marginBottom = "18px";
        content.appendChild(title);

        // Tabla
        const table = document.createElement("table");
        table.style.width = "100%";
        table.style.borderCollapse = "collapse";
        table.innerHTML = `
            <thead>
                <tr style="background:#f5f5f5">
                    <th style="padding:8px;border-bottom:1px solid #ccc">Fecha</th>
                    <th style="padding:8px;border-bottom:1px solid #ccc">Cobertura de nubes (%)</th>
                    <th style="padding:8px;border-bottom:1px solid #ccc">Acción</th>
                </tr>
            </thead>
            <tbody>
                ${scenes.map((scene, idx) => `
                    <tr>
                        <td style="padding:8px;border-bottom:1px solid #eee">${scene.date ? scene.date.split('T')[0] : '-'}</td>
                        <td style="padding:8px;border-bottom:1px solid #eee">${scene.cloudCoverage != null ? scene.cloudCoverage : '-'}</td>
                        <td style="padding:8px;border-bottom:1px solid #eee">
                            <button class="btn btn-sm btn-success" data-idx="${idx}">Visualizar</button>
                        </td>
                    </tr>
                `).join('')}
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

        // Manejar click en visualizar
        table.querySelectorAll('button[data-idx]').forEach(btn => {
            btn.onclick = async () => {
                const idx = btn.getAttribute('data-idx');
                const scene = scenes[idx];
                // Usar el nuevo endpoint y lógica NDVI
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
                    // Mostrar la imagen NDVI en Cesium (puedes adaptar esto a tu flujo)
                    showNDVIImageOnCesium(data.image_url, viewer);
                } catch (err) {
                    showErrorToast('Error al renderizar la imagen NDVI: ' + err.message);
                }
                modal.remove();
                resolve({ ndvi: null, ndmi: null });
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

// Función para mostrar la imagen NDVI/NDMI en Cesium sobre la parcela seleccionada
function showNDVIImageOnCesium(imageBase64, bounds, viewer) {
    // Elimina capas NDVI previas
    const layers = viewer.imageryLayers;
    for (let i = layers.length - 1; i >= 0; i--) {
        const layer = layers.get(i);
        if (layer._layerName === 'NDVI_RENDERED') {
            layers.remove(layer);
        }
    }
    // Crear un objeto URL para la imagen base64
    const imageUrl = `data:image/png;base64,${imageBase64}`;
    // bounds: [west, south, east, north]
    const ndviLayer = layers.addImageryProvider(new Cesium.SingleTileImageryProvider({
        url: imageUrl,
        rectangle: Cesium.Rectangle.fromDegrees(bounds[0], bounds[1], bounds[2], bounds[3])
    }));
    ndviLayer._layerName = 'NDVI_RENDERED';
}

// Función para mostrar un spinner mientras se realiza el polling
function showSpinner() {
    let spinnerContainer = document.getElementById('eosdaSpinnerContainer');
    if (!spinnerContainer) {
        spinnerContainer = document.createElement('div');
        spinnerContainer.id = 'eosdaSpinnerContainer';
        spinnerContainer.className = 'text-center mt-3';
        spinnerContainer.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Cargando...</span>
            </div>
            <p>Procesando imagen, por favor espera...</p>
        `;
        document.body.appendChild(spinnerContainer);
    }
    spinnerContainer.style.display = 'block';
}

// Función para ocultar el spinner
function hideSpinner() {
    const spinnerContainer = document.getElementById('eosdaSpinnerContainer');
    if (spinnerContainer) {
        spinnerContainer.style.display = 'none';
    }
}

// Modificar el flujo para mostrar la imagen en el mapa y cerrar el modal
window.verImagenEscenaEOSDA = async function(viewId, tipo) {
    const token = localStorage.getItem("accessToken");
    const fieldId = window.EOSDA_STATE.selectedEosdaId;
    const parcelId = window.EOSDA_STATE.selectedParcelId;
    if (!fieldId) {
        alert("No se encontró el field_id de EOSDA para la parcela seleccionada.");
        return;
    }
    try {
        // Paso 1: Solicitar el request_id para la imagen
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
            alert(`No se pudo obtener el request_id para la imagen ${tipo.toUpperCase()}.`);
            return;
        }
        // Paso 2: Polling para obtener la imagen y superponerla en el mapa
        let attempts = 0;
        const maxAttempts = 10;
        const interval = 3000;
        showSpinner();
        while (attempts < maxAttempts) {
            try {
                const imgResp = await fetch(`${BASE_URL}/eosda-image-result/?field_id=${fieldId}&request_id=${data.request_id}`, {
                    method: "GET",
                    headers: {
                        "Authorization": `Bearer ${token}`
                    }
                });
                const imgData = await imgResp.json();
                if (imgData.image_base64) {
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
                    showNDVIImageOnCesium(imgData.image_base64, bounds, viewer);
                    // Cerrar el modal para mostrar el mapa completo
                    const modal = document.getElementById('eosdaScenesModal');
                    if (modal) {
                        const bsModal = bootstrap.Modal.getInstance(modal);
                        if (bsModal) bsModal.hide();
                    }
                    showInfoToast(`Imagen ${tipo.toUpperCase()} superpuesta en el mapa.`);
                    return;
                } else if (imgData.error) {
                    hideSpinner();
                    showErrorToast(imgData.error);
                    return;
                }
            } catch (err) {
                console.error("Error durante el polling de la imagen EOSDA:", err);
            }
            attempts++;
            await new Promise(resolve => setTimeout(resolve, interval));
        }
        hideSpinner();
        showErrorToast(`No se pudo obtener la imagen ${tipo.toUpperCase()} después de varios intentos.`);
    } catch (err) {
        hideSpinner();
        showErrorToast(`Error al consultar la imagen ${tipo.toUpperCase()} de la escena.`);
    }
};

//prueba de que se fueron todos los cambios a github