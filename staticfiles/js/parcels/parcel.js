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

            // Asignar el token de Cesium
            const cesiumToken = data.cesium_token || CESIUM_ACCESS_TOKEN;
            Cesium.Ion.defaultAccessToken = cesiumToken;

            // Asignar el token de OpenWeather
            const weatherApiKey = data.weather_api_key;

            //Guardar en una variable global
            window.WEATHER_API_KEY = weatherApiKey;

            window.SENTINEL_NDVI_WMTS = data.sentinel_ndvi_wmts;

            // Inicializar el visor de Cesium
            viewer = new Cesium.Viewer('cesiumContainer', {
                terrainProvider: Cesium.createWorldTerrain(), // Agrega relieve
                baseLayerPicker: false, // Evita cambiar capas
                shouldAnimate: true, // Habilita animaciones
                sceneMode: Cesium.SceneMode.SCENE2D // Mostrar en 2D por defecto
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
                        material: Cesium.Color.TRANSPARENT, // Solo borde
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

    // Enviar los datos al backend
    axiosInstance.post("/parcel/", {
        name: name,
        description: description,
        field_type: fieldType,
        soil_type: soilType,
        topography: topography,
        geom: geojson
    })
    .then(response => {
        alert("Parcela guardada con éxito");
        closeModal(); // Cerrar el modal
        location.reload(); // Recargar la página para mostrar la nueva parcela
    })
    .catch(error => {
        console.error("Error al guardar la parcela:", error);
        alert("Hubo un error al guardar la parcela. Revisa la consola para más detalles.");
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
            const data = response.data.parcels.features || []; // Acceder a "features" dentro de "parcels"
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
                const row = document.createElement("tr");
                row.innerHTML = `
                    <td>${parcel.properties.name || "Sin nombre"}</td>
                    <td>${parcel.properties.description || "Sin descripción"}</td>
                    <td>${parcel.properties.field_type || "N/A"}</td>
                    <td>${parcel.properties.soil_type || "N/A"}</td>
                    <td>${parcel.properties.topography || "N/A"}</td>
                    <td>
                        <button class="btn btn-info btn-sm" onclick="flyToParcel(${parcel.id})" title="Ver Parcela">
                            <i class="bi bi-eye"></i> Ver
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

import { showNDVIToggleButton } from "./layers.js"; // Importar la función para mostrar el botón NDVI

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
            // Amarillo (ancho 4) o verde oscuro (ancho 2 y color #145A32)
            if (
                (width === 4 && color === Cesium.Color.YELLOW.toCssColorString()) ||
                (width === 2 && color === Cesium.Color.fromCssColorString('#145A32').toCssColorString())
            ) {
                entitiesToRemove.push(entity);
            }
        }
    });
    entitiesToRemove.forEach(entity => viewer.entities.remove(entity));

    axiosInstance.get(`/parcel/${parcelId}/`)
        .then(response => {
            const feature = response.data;

            if (!feature.geometry || !feature.geometry.coordinates) {
                throw new Error("La geometría de la parcela no es válida.");
            }

            // Obtener las coordenadas del centro de la parcela
            const center = feature.geometry.coordinates[0][0];
            const lat = center[1];
            const lon = center[0];

            const coordinates = feature.geometry.coordinates[0].map(coord =>
                Cesium.Cartesian3.fromDegrees(coord[0], coord[1])
            );

            // Actualizar window.positions con los vértices de la parcela seleccionada
            window.positions = coordinates;

            // Calcular área en hectáreas y mostrar en el cuadro de datos
            const areaHect = polygonAreaHectares(feature.geometry.coordinates[0]);
            const areaCell = document.getElementById("parcelAreaCell");
            if (areaCell) {
                areaCell.textContent = `${areaHect.toLocaleString(undefined, {maximumFractionDigits: 2})} ha`;
            }

            // Mover el botón NDVI al pie del área, dentro del cuadro de datos (asegura que esté visible y bien posicionado)
            setTimeout(() => {
                const ndviBtn = document.getElementById("ndviToggle");
                const ndviContainer = document.getElementById("ndviBtnContainer");
                if (ndviBtn && ndviContainer) {
                    ndviBtn.style.position = "static";
                    ndviBtn.style.margin = "0 0 0 12px";
                    ndviBtn.style.display = "inline-block";
                    ndviBtn.style.verticalAlign = "middle";
                    ndviContainer.innerHTML = "";
                    ndviContainer.appendChild(ndviBtn);
                }
            }, 100);

            // Volar al bounding sphere de la parcela
            const boundingSphere = Cesium.BoundingSphere.fromPoints(coordinates);
            viewer.camera.flyToBoundingSphere(boundingSphere, {
                duration: 2,
                complete: () => {
                    console.log("Animación completada. Habilitando eventos de entrada.");
                    viewer.scene.screenSpaceCameraController.enableInputs = true;
                }
            });

            // Obtener datos meteorológicos promedio
            fetchWeatherData(lat, lon);

            // Resaltar en amarillo temporalmente (borde amarillo grueso)
            const highlighted = viewer.entities.add({
                polyline: {
                    positions: coordinates.concat([coordinates[0]]),
                    width: 4,
                    material: Cesium.Color.YELLOW
                }
            });

            // Restaurar a solo borde verde oscuro después de 3 segundos
            setTimeout(() => {
                viewer.entities.remove(highlighted);
                viewer.entities.add({
                    polyline: {
                        positions: coordinates.concat([coordinates[0]]),
                        width: 2,
                        material: Cesium.Color.fromCssColorString('#145A32') // Verde oscuro
                    }
                });
            }, 3000);
            
            // Mostrar el botón NDVI y conectar el flujo EOSDA
            showNDVIToggleButton(viewer);
            // Reemplazar el evento del botón NDVI para abrir el modal EOSDA
            setTimeout(() => {
                const ndviBtn = document.getElementById("ndviToggle");
                if (ndviBtn) {
                    ndviBtn.onclick = function() {
                        window.showEOSDAScenesModal(parcelId);
                    };
                }
            }, 150);
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

let weatherChart; // Variable global para mantener la instancia Chart.js

function fetchWeatherData(lat, lon) {
    const apiKey = window.WEATHER_API_KEY; // Clave de API desde el backend
    if (!apiKey) {
        console.error("La clave de API meteorológica no está definida.");
        return;
    }

    const url = `https://api.openweathermap.org/data/2.5/onecall?lat=${lat}&lon=${lon}&units=metric&lang=es&appid=${apiKey}`;

    console.log("URL de la solicitud:", url);

    axios.get(url)
        .then(response => {
            const data = response.data;

            if (!data || !data.hourly) {
                console.error("La respuesta de la API no contiene datos válidos.");
                return;
            }

            // Mostrar ubicación
            document.getElementById("weatherLocation").textContent = `Predicción para las próximas horas`;

            // Preparar datos para el gráfico
            const labels = [];
            const temps = [];
            const humidity = [];

            // Obtener predicciones por hora (hasta 12 horas)
            data.hourly.slice(0, 12).forEach(hour => {
                const date = new Date(hour.dt * 1000);
                const hourLabel = `${date.getHours()}:00`;
                labels.push(hourLabel);
                temps.push(hour.temp);
                humidity.push(hour.humidity);
            });

            // Actualizar el gráfico
            updateWeatherChart(labels, temps, humidity);

            // Mostrar el dashboard
            document.getElementById("weatherDashboard").style.display = "block";
        })
        .catch(error => {
            console.error("Error al obtener datos meteorológicos:", error);
            document.getElementById("weatherDashboard").style.display = "none";
        });
}


function updateWeatherChart(labels, temps, humidity) {
    if (window.weatherChartInstance) {
        window.weatherChartInstance.destroy(); // Destruir el gráfico anterior si existe
    }

    const ctx = document.getElementById("weatherChart").getContext("2d");
    window.weatherChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Temperatura (°C)",
                    data: temps,
                    borderColor: "rgba(255,99,132,1)",
                    backgroundColor: "rgba(255,99,132,0.2)",
                    fill: true,
                    tension: 0.4
                },
                {
                    label: "Humedad (%)",
                    data: humidity,
                    borderColor: "rgba(54,162,235,1)",
                    backgroundColor: "rgba(54,162,235,0.2)",
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: "bottom" },
                title: { display: true, text: "Predicción Meteorológica por Hora" }
            }
        }
    });
}

// Función para obtener el request_id de EOSDA usando el eosda_id de la parcela
async function getEOSDARequestId(eosda_id) {
    try {
        const token = localStorage.getItem("accessToken");
        const response = await axios.post(
            `${BASE_URL}/eosda-request-id/`,
            { eosda_id },
            { headers: { "Authorization": `Bearer ${token}` } }
        );
        console.log("Request_id obtenido:", response.data.request_id);
        return response.data.request_id;
    } catch (error) {
        console.error("Error obteniendo request_id de EOSDA:", error);
        return null;
    }
}

// Función para obtener la imagen NDVI usando eosda_id y view_id
async function getEOSDANDVIImage(eosda_id, view_id) {
    try {
        const token = localStorage.getItem("accessToken");
        const response = await axios.post(
            `${BASE_URL}/eosda-ndvi-image/`,
            { eosda_id, view_id },
            { headers: { "Authorization": `Bearer ${token}` } }
        );
        console.log("URL imagen NDVI:", response.data.image_url);
        return response.data.image_url;
    } catch (error) {
        console.error("Error obteniendo imagen NDVI de EOSDA:", error);
        return null;
    }
}

// Función para obtener las escenas disponibles usando field_id y request_id
async function getEOSDAScenesWithRequest(field_id, request_id) {
    try {
        const token = localStorage.getItem("accessToken");
        const response = await axios.post(
            `${BASE_URL}/eosda-scenes-with-request/`,
            { field_id, request_id },
            { headers: { "Authorization": `Bearer ${token}` } }
        );
        console.log("Escenas disponibles:", response.data.scenes);
        return response.data.scenes;
    } catch (error) {
        console.error("Error obteniendo escenas de EOSDA:", error);
        return [];
    }
}

// Ejemplo de flujo completo para mostrar fechas y obtener NDVI
import { showSceneSelectionModal } from "../../metrica/static/js/parcels/layers.js";

window.showEOSDAScenesModal = async function(parcelId) {
    console.log('[NDVI] showEOSDAScenesModal INICIO', { parcelId });
    // 1. Obtener la parcela y su eosda_id
    const parcelResp = await axiosInstance.get(`/parcel/${parcelId}/`);
    const eosda_id = parcelResp.data.eosda_id;
    console.log('[NDVI] eosda_id obtenido:', eosda_id);
    if (!eosda_id) {
        // Mostrar error profesional en toast y en consola
        showErrorToast("No se pudo determinar eosda_id para la petición NDVI. Verifica que la parcela tenga configurado el campo EOSDA.");
        console.error('[NDVI] Error: eosda_id no encontrado. parcel:', parcelResp.data);
        return;
    }
    // 2. Consultar las escenas disponibles
    const scenesResp = await axios.post(
        `${BASE_URL}/eosda-scenes-with-request/`,
        { field_id: eosda_id },
        { headers: { "Authorization": `Bearer ${localStorage.getItem("accessToken")}` } }
    );
    const scenes = scenesResp.data.scenes || [];
    console.log('[NDVI] escenas obtenidas:', scenes);
    if (!scenes.length) {
        showErrorToast("No hay escenas satelitales disponibles para este campo.");
        return;
    }
    // Guardar el eosda_id globalmente para que layers.js lo use correctamente
    window.SELECTED_EOSDA_ID = eosda_id; // <-- Ajuste para integración NDVI
    // 3. Mostrar el modal profesional para selección de escena
    showSceneSelectionModal(scenes, async (scene) => {
        console.log('[NDVI] callback selección escena ejecutado', scene);
        // Al seleccionar una escena, obtener la imagen NDVI y mostrarla
        const view_id = scene.view_id || scene.id;
        // Validar ambos parámetros antes de enviar
        if (!view_id) {
            showErrorToast("No se pudo obtener el view_id de la escena seleccionada.");
            console.error('[NDVI] view_id inválido:', scene);
            return;
        }
        if (!eosda_id) {
            showErrorToast("No se pudo obtener el eosda_id de la parcela.");
            console.error('[NDVI] eosda_id inválido:', eosda_id);
            return;
        }
        // Enviar ambos parámetros correctamente en el body
        let image_url = null;
        let isPng = false;
        try {
            const token = localStorage.getItem("accessToken");
            const resp = await fetch(
                `${BASE_URL}/eosda-ndvi-image/`,
                {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ eosda_id, view_id })
                }
            );
            const contentType = resp.headers.get("Content-Type") || "";
            if (contentType.includes("image/png")) {
                // Recibimos la imagen binaria
                const blob = await resp.blob();
                image_url = URL.createObjectURL(blob);
                isPng = true;
            } else {
                // Recibimos JSON
                const data = await resp.json();
                image_url = data.image_url;
            }
            console.log('[NDVI] Respuesta image_url:', image_url);
        } catch (err) {
            showErrorToast("No se pudo obtener la imagen NDVI de EOSDA. Verifica la escena seleccionada y los parámetros enviados.");
            console.error('[NDVI] Error al obtener imagen NDVI:', { eosda_id, view_id, error: err });
            return;
        }
        if (!image_url) {
            showErrorToast("No se pudo obtener la imagen NDVI de EOSDA. La respuesta no contiene una URL válida.");
            console.error('[NDVI] Error al obtener imagen NDVI:', { eosda_id, view_id });
            return;
        }
        // Mostrar la imagen NDVI en un modal profesional
        const ndviModal = document.createElement("div");
        ndviModal.style.position = "fixed";
        ndviModal.style.top = "0";
        ndviModal.style.left = "0";
        ndviModal.style.width = "100vw";
        ndviModal.style.height = "100vh";
        ndviModal.style.background = "rgba(0,0,0,0.7)";
        ndviModal.style.zIndex = "10000";
        ndviModal.style.display = "flex";
        ndviModal.style.alignItems = "center";
        ndviModal.style.justifyContent = "center";
        ndviModal.innerHTML = `
            <div style="background:#fff;padding:32px 24px;border-radius:16px;max-width:650px;box-shadow:0 8px 32px rgba(0,0,0,0.22);text-align:center;position:relative;">
                <button style="position:absolute;top:16px;right:16px;font-size:22px;background:none;border:none;color:#145A32;cursor:pointer;" onclick="this.closest('div').parentNode.remove()">&times;</button>
                <h3 style="color:#145A32;margin-bottom:18px;">Imagen NDVI</h3>
                <img src="${image_url}" alt="NDVI" style="max-width:100%;border-radius:10px;box-shadow:0 2px 12px rgba(0,0,0,0.14);margin-bottom:18px;" onerror="showErrorToast('Error al cargar la imagen NDVI. Puede que la URL esté vacía o el formato no sea válido.');this.style.display='none';" />
                <div style="margin-top:10px;font-size:15px;color:#555;">Esta imagen NDVI fue generada por EOSDA para la escena seleccionada.</div>
                ${isPng ? '<div style="margin-top:8px;font-size:13px;color:#888;">Imagen recibida directamente como PNG</div>' : ''}
            </div>
        `;
        document.body.appendChild(ndviModal);
    }, 'NDVI', viewer);
}
