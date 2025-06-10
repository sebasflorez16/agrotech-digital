let ndviLayer = null;
let ndviEnabled = false;

// Elimina los import
// import axios from "axios";
// import qs from "qs";

const client_id = "98424e68-8d91-4fe4-be6e-b527648e330a";
const client_secret = "vwLbyJ149nmvHEPGyKoSbUWWjkWRJIWd";
const instance_id = "204da595-1d83-4f8e-9c9d-cf2a94759e7c";

window.SENTINEL_NDVI_WMTS = null;
let tokenPromise = null;

const body = Qs.stringify({
  client_id,
  client_secret,
  grant_type: "client_credentials"
});

tokenPromise = axios.post("https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token", body, {
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'
  }
}).then(resp => {
  const access_token = resp.data.access_token;
  window.SENTINEL_ACCESS_TOKEN = access_token; // <-- Guardar el token globalmente
  window.SENTINEL_NDVI_WMTS = `https://services.sentinel-hub.com/ogc/wmts/204da595-1d83-4f8e-9c9d-cf2a94759e7c?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=NDVI&STYLE=default&TILEMATRIXSET=PopularWebMercator512&FORMAT=image/png&token=${access_token}`;
  console.log("Token obtenido y URL WMTS lista:", window.SENTINEL_NDVI_WMTS);
}).catch(err => {
  console.error("Error obteniendo token Sentinel Hub:", err);
});

// ...el resto de tu código igual...

/**
 * Utilidad: Determina si un punto [lon, lat] está dentro de un polígono (array de [lon, lat])
 * Algoritmo: Ray-casting
 */
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

/**
 * Alterna la capa NDVI y la recorta al polígono dibujado (usando Process API de Sentinel Hub)
 */
export async function toggleNDVILayer(viewer) {
    if (!viewer) {
        console.warn("Viewer no está definido.");
        return;
    }
    if (tokenPromise) {
        await tokenPromise;
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
    // Obtener token de acceso
    const access_token = window.SENTINEL_ACCESS_TOKEN;
    let token = access_token;
    if (!token && tokenPromise) {
        try {
            const resp = await tokenPromise;
            token = resp.data.access_token;
        } catch (e) {
            alert("No se pudo obtener el token de Sentinel Hub");
            return;
        }
    }
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
                    timeRange: {
                        from: "2023-11-01T00:00:00Z",
                        to: "2025-05-22T23:59:59Z"
                    },
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
    // Mostrar el payload para depuración
    console.log("Payload enviado a Sentinel Hub Process API:", JSON.stringify(payload, null, 2));
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

// El resto de tu código permanece igual...
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
        btn.style.position = "absolute";
        btn.style.top = "20px";
        btn.style.left = "20px";
        btn.style.zIndex = 1000;
        btn.style.padding = "10px";
        btn.style.background = "#2c7a7b";
        btn.style.color = "white";
        btn.style.border = "none";
        btn.style.borderRadius = "8px";
        btn.style.cursor = "pointer";
        document.body.appendChild(btn);
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