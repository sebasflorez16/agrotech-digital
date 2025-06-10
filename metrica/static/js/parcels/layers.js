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
async function fetchSentinelWMTS() {
    try {
        const resp = await fetch("/parcels/sentinel-wmts-urls/", {
            headers: {
                'Accept': 'application/json',
                // Si usas JWT, agrega el token aquí
                // 'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            },
            credentials: 'include' // Si usas sesión/cookies
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
 * Alterna la capa NDVI y la recorta al polígono dibujado (usando Process API de Sentinel Hub)
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
    // Obtener el polígono actual
    const polygonLonLat = getCurrentPolygonLonLat();
    if (!polygonLonLat) {
        alert("Dibuja o selecciona una parcela para visualizar NDVI.");
        return;
    }
    // Ocultar los bordes de las parcelas
    viewer.entities.values.forEach(entity => {
        if (entity.polyline && entity.polyline.material && entity.polyline.material.color && entity.polyline.material.color.getValue().toCssColorString() === '#145a32') {
            entity.show = false;
        }
    });
    // Construir GeoJSON del polígono (cerrado)
    const geojson = {
        type: "Polygon",
        coordinates: [polygonLonLat.concat([polygonLonLat[0]])]
    };
    // Calcular bounding box del polígono
    const lons = polygonLonLat.map(c => c[0]);
    const lats = polygonLonLat.map(c => c[1]);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    // Definir parámetros de la imagen
    const width = 512;
    const height = 512;
    // Payload para Process API (rango de fechas extendido y comentarios)
    // Evalscript NDVI estándar: rojo (bajo), amarillo, verde claro, verde oscuro (alto), sin azul
    const evalscript = `//VERSION=3
function setup() {
  return {
    input: ["B04", "B08", "dataMask"],
    output: { bands: 4 }
  };
}
function evaluatePixel(sample) {
  if (sample.dataMask === 0) {
    return [0, 0, 0, 0];
  }
  let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
  let r = 0, g = 0, b = 0;
  if (ndvi < 0.2) {
    // Rojo
    r = 1.0; g = 0.0; b = 0.0;
  } else if (ndvi < 0.4) {
    // Amarillo
    r = 1.0; g = 1.0; b = 0.0;
  } else if (ndvi < 0.6) {
    // Verde claro
    r = 0.6; g = 1.0; b = 0.2;
  } else {
    // Verde oscuro
    r = 0.0; g = 0.5; b = 0.0;
  }
  return [r, g, b, 1];
}`;
    const payload = {
        input: {
            bounds: {
                bbox: [minLon, minLat, maxLon, maxLat],
                geometry: geojson
            },
            data: [{
                type: "sentinel-2-l2a",
                dataFilter: {
                    mosaickingOrder: "mostRecent"
                }
            }]
        },
        output: {
            width: width,
            height: height,
            responses: [{identifier: "default", format: {type: "image/png"}}]
        },
        evalscript: evalscript
    };

    // Llamar a la Process API
    let imageBlob;
    try {
        const response = await axios.post(
            "https://services.sentinel-hub.com/api/v1/process",
            payload,
            {
                responseType: "blob",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json",
                    "Accept": "image/png" // <-- Solución al error 400 por mime type
                }
            }
        );
        imageBlob = response.data;
    } catch (error) {
        // Mostrar error detallado
        console.error("Error al obtener imagen NDVI de Sentinel Hub Process API:", error);
        if (error.response && error.response.data) {
            // Intentar leer el mensaje de error del backend
            error.response.data.text().then(msg => {
                console.error("Detalle del error 400:", msg);
            });
        }
        alert("No se pudo obtener la imagen NDVI recortada a la parcela. Revisa la consola para detalles del error 400.");
        return;
    }
    // Crear URL de la imagen
    const imageUrl = URL.createObjectURL(imageBlob);
    // Agregar la imagen como capa en Cesium
    ndviLayer = viewer.imageryLayers.addImageryProvider(
        new Cesium.SingleTileImageryProvider({
            url: imageUrl,
            rectangle: Cesium.Rectangle.fromDegrees(minLon, minLat, maxLon, maxLat)
        })
    );
    ndviEnabled = true;
    viewer.scene.screenSpaceCameraController.enableZoom = false;
    updateNDVIButtonText(true);
    console.log("NDVI recortado a la parcela y mostrado como imagen estática. Zoom bloqueado.");
}

/**
 * Alterna la capa NDMI (Índice de Humedad de Diferencia Normalizada) y la recorta al polígono dibujado
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
    const polygonLonLat = getCurrentPolygonLonLat();
    if (!polygonLonLat) {
        alert("Dibuja o selecciona una parcela para visualizar NDMI.");
        return;
    }
    const geojson = {
        type: "Polygon",
        coordinates: [polygonLonLat.concat([polygonLonLat[0]])]
    };
    const lons = polygonLonLat.map(c => c[0]);
    const lats = polygonLonLat.map(c => c[1]);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const width = 512;
    const height = 512;
    let token = window.SENTINEL_ACCESS_TOKEN;
    if (!token && tokenPromise) {
        try {
            const resp = await tokenPromise;
            token = resp.data.access_token;
        } catch (e) {
            alert("No se pudo obtener el token de Sentinel Hub");
            return;
        }
    }
    // Evalscript NDMI
    const evalscript = `//VERSION=3
function setup() {
  return {
    input: ["B08", "B11", "dataMask"],
    output: { bands: 4 }
  };
}
function evaluatePixel(sample) {
  if (sample.dataMask === 0) {
    return [0, 0, 0, 0];
  }
  let ndmi = (sample.B08 - sample.B11) / (sample.B08 + sample.B11);
  let r = 0, g = 0, b = 0;
  if (ndmi < 0.1) {
    r = 0.8; g = 0.2; b = 0.2; // seco: rojo
  } else if (ndmi < 0.3) {
    r = 1.0; g = 1.0; b = 0.0; // intermedio: amarillo
  } else {
    r = 0.0; g = 0.6; b = 1.0; // húmedo: azul verdoso
  }
  return [r, g, b, 1];
}`;
    const payload = {
        input: {
            bounds: {
                bbox: [minLon, minLat, maxLon, maxLat],
                geometry: geojson
            },
            data: [{
                type: "sentinel-2-l2a",
                dataFilter: {
                    mosaickingOrder: "mostRecent"
                }
            }]
        },
        output: {
            width: width,
            height: height,
            responses: [{identifier: "default", format: {type: "image/png"}}]
        },
        evalscript: evalscript
    };
    let imageBlob;
    try {
        const response = await axios.post(
            "https://services.sentinel-hub.com/api/v1/process",
            payload,
            {
                responseType: "blob",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json",
                    "Accept": "image/png"
                }
            }
        );
        imageBlob = response.data;
    } catch (error) {
        alert("No se pudo obtener la imagen NDMI recortada a la parcela.");
        return;
    }
    const imageUrl = URL.createObjectURL(imageBlob);
    ndmiLayer = viewer.imageryLayers.addImageryProvider(
        new Cesium.SingleTileImageryProvider({
            url: imageUrl,
            rectangle: Cesium.Rectangle.fromDegrees(minLon, minLat, maxLon, maxLat)
        })
    );
    ndmiEnabled = true;
    updateNDMIButtonText(true);
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