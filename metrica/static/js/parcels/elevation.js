/**
 * elevation.js
 * Módulo de visualización de elevación/topografía para parcelas.
 * Muestra mapa de calor de elevación relativa superpuesto en Leaflet.
 * 
 * NO modifica parcel.js, analysis.js ni layers.js.
 * Usa los mismos patrones de L.imageOverlay que NDVI/NDMI.
 * 
 * Depende de: 
 *   - window.AGROTECH_STATE (de parcel.js)
 *   - window.axiosInstance (de parcel.js)
 *   - Leaflet (L) global
 */

(function() {
    'use strict';

    // ── Configuración ──
    const MODULE_TAG = '[ELEVATION]';
    
    // Cache frontend de elevación (la topografía no cambia)
    window.ELEVATION_CACHE = window.ELEVATION_CACHE || {};

    // Referencia a la capa activa de elevación
    let activeElevationLayer = null;
    let elevationVisible = false;

    /**
     * Obtener la BASE_URL para el backend (mismo patrón que parcel.js)
     */
    function getBaseUrl() {
        if (window.AGROTECH_CONFIG && window.AGROTECH_CONFIG.API_BASE) {
            return window.AGROTECH_CONFIG.API_BASE + '/api/parcels';
        }
        if (window.ApiUrls) {
            return window.ApiUrls.parcels();
        }
        const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        if (isLocalhost) {
            return 'http://localhost:8000/api/parcels';
        }
        return 'https://agrotech-digital-production.up.railway.app/api/parcels';
    }

    /**
     * Solicitar elevación al backend y mostrar en el mapa
     */
    async function solicitarElevacion(parcelId) {
        const BASE_URL = getBaseUrl();
        const token = localStorage.getItem('accessToken');
        
        if (!parcelId) {
            parcelId = window.AGROTECH_STATE?.selectedParcelId;
        }

        if (!parcelId) {
            showElevationToast('Selecciona primero una parcela', 'warning');
            return;
        }

        console.log(`${MODULE_TAG} Solicitando elevación para parcela ${parcelId}`);

        // Verificar cache frontend
        const cacheKey = `elevation_${parcelId}`;
        if (window.ELEVATION_CACHE[cacheKey]) {
            console.log(`${MODULE_TAG} Cache HIT frontend`);
            const cached = window.ELEVATION_CACHE[cacheKey];
            showElevationOnLeaflet(cached.image_base64, cached.bounds);
            showElevationStats(cached.stats);
            showElevationToast('Elevación cargada desde cache', 'success');
            return;
        }

        // Mostrar spinner
        showElevationSpinner('Consultando datos de elevación...');

        try {
            const resp = await fetch(`${BASE_URL}/parcel/${parcelId}/elevation/`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!resp.ok) {
                const errorData = await resp.json().catch(() => ({}));
                throw new Error(errorData.error || `Error HTTP ${resp.status}`);
            }

            const data = await resp.json();

            if (!data.image_base64) {
                throw new Error('No se recibió imagen de elevación');
            }

            // Guardar en cache frontend
            window.ELEVATION_CACHE[cacheKey] = data;
            console.log(`${MODULE_TAG} Datos guardados en cache frontend`);

            // Mostrar en el mapa
            hideElevationSpinner();
            showElevationOnLeaflet(data.image_base64, data.bounds);
            showElevationStats(data.stats);
            showElevationToggleButton(data.image_base64, data.bounds);
            showElevationToast(
                `Elevación cargada: ${data.stats.min_elevation}m - ${data.stats.max_elevation}m (dif: ${data.stats.difference}m)`, 
                'success'
            );

        } catch (error) {
            hideElevationSpinner();
            console.error(`${MODULE_TAG} Error:`, error);
            showElevationToast(`Error: ${error.message}`, 'error');
        }
    }

    /**
     * Mostrar la imagen de elevación en Leaflet 
     * (mismo patrón que showNDVIImageOnLeaflet en parcel.js)
     */
    function showElevationOnLeaflet(imageBase64, bounds) {
        // Obtener referencia al mapa Leaflet
        const mapInstance = getMapInstance();
        if (!mapInstance) {
            console.error(`${MODULE_TAG} No se encontró instancia del mapa Leaflet`);
            return;
        }

        // Eliminar capa de elevación previa si existe
        removeElevationLayer(mapInstance);

        // Crear pane personalizado para elevación si no existe
        if (!mapInstance.getPane('elevationPane')) {
            const pane = mapInstance.createPane('elevationPane');
            pane.style.zIndex = 440; // Debajo del ndviPane (450) para no tapar NDVI
            pane.style.mixBlendMode = 'normal';
            pane.style.isolation = 'isolate';
        }

        // Crear URL para la imagen base64
        const imageUrl = `data:image/png;base64,${imageBase64}`;

        // bounds: [west, south, east, north]
        // Convertir a formato Leaflet [[south, west], [north, east]]
        const leafletBounds = [[bounds[1], bounds[0]], [bounds[3], bounds[2]]];

        // Agregar imagen como overlay
        activeElevationLayer = L.imageOverlay(imageUrl, leafletBounds, {
            opacity: 0.75,
            className: 'elevation-layer',
            pane: 'elevationPane',
            interactive: false
        }).addTo(mapInstance);

        // Forzar estilos limpios
        activeElevationLayer.on('load', function() {
            const imgElement = this.getElement();
            if (imgElement) {
                imgElement.style.mixBlendMode = 'normal';
                imgElement.style.filter = 'none';
                imgElement.style.isolation = 'isolate';
            }
        });

        elevationVisible = true;
        console.log(`${MODULE_TAG} Imagen de elevación superpuesta en el mapa`);
    }

    /**
     * Remover capa de elevación del mapa
     */
    function removeElevationLayer(mapInstance) {
        if (!mapInstance) mapInstance = getMapInstance();
        if (!mapInstance) return;

        if (activeElevationLayer) {
            mapInstance.removeLayer(activeElevationLayer);
            activeElevationLayer = null;
        }

        // También buscar por className como respaldo
        mapInstance.eachLayer(function(layer) {
            if (layer.options && layer.options.className === 'elevation-layer') {
                mapInstance.removeLayer(layer);
            }
        });

        elevationVisible = false;
    }

    /**
     * Obtener referencia al mapa Leaflet (buscar en variables globales)
     */
    function getMapInstance() {
        // Intentar obtener de variable global directa
        if (window.map && window.map._leaflet_id) return window.map;
        
        // Buscar en el contenedor del mapa
        const container = document.getElementById('mapContainer');
        if (container && container._leaflet_id) {
            // Leaflet almacena la instancia en _leaflet
            return container._leaflet;
        }

        return null;
    }

    /**
     * Mostrar panel de estadísticas de elevación
     */
    function showElevationStats(stats) {
        // Remover panel previo si existe
        let panel = document.getElementById('elevationStatsPanel');
        if (panel) panel.remove();

        const diff = stats.difference;
        let interpretation = '';
        let interpretColor = '';

        if (diff < 1) {
            interpretation = 'Terreno prácticamente plano';
            interpretColor = '#4CAF50';
        } else if (diff < 3) {
            interpretation = 'Desnivel suave — variaciones menores';
            interpretColor = '#8BC34A';
        } else if (diff < 5) {
            interpretation = 'Desnivel moderado — posible acumulación de agua en zonas bajas';
            interpretColor = '#FF9800';
        } else if (diff < 10) {
            interpretation = 'Desnivel significativo — zonas bajas propensas a encharcamiento';
            interpretColor = '#F44336';
        } else {
            interpretation = 'Desnivel alto — considerar drenaje y manejo de pendientes';
            interpretColor = '#D32F2F';
        }

        panel = document.createElement('div');
        panel.id = 'elevationStatsPanel';
        panel.style.cssText = `
            position: fixed;
            bottom: 80px;
            left: 20px;
            z-index: 10000;
            background: rgba(255, 255, 255, 0.96);
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            font-family: 'Inter', sans-serif;
            max-width: 320px;
            border-left: 4px solid ${interpretColor};
            backdrop-filter: blur(10px);
        `;

        panel.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <strong style="color:#333;font-size:14px;">
                    <i class="fas fa-mountain" style="color:#8B4513;margin-right:6px;"></i>
                    Elevación del Terreno
                </strong>
                <button onclick="document.getElementById('elevationStatsPanel').remove()" 
                        style="border:none;background:none;cursor:pointer;font-size:16px;color:#999;padding:0;">✕</button>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
                <div style="background:#E3F2FD;border-radius:8px;padding:8px;text-align:center;">
                    <div style="font-size:11px;color:#666;">Punto más bajo</div>
                    <div style="font-size:16px;font-weight:600;color:#1565C0;">${stats.min_elevation}m</div>
                </div>
                <div style="background:#EFEBE9;border-radius:8px;padding:8px;text-align:center;">
                    <div style="font-size:11px;color:#666;">Punto más alto</div>
                    <div style="font-size:16px;font-weight:600;color:#5D4037;">${stats.max_elevation}m</div>
                </div>
                <div style="background:#FFF3E0;border-radius:8px;padding:8px;text-align:center;">
                    <div style="font-size:11px;color:#666;">Diferencia</div>
                    <div style="font-size:16px;font-weight:600;color:#E65100;">${stats.difference}m</div>
                </div>
                <div style="background:#F1F8E9;border-radius:8px;padding:8px;text-align:center;">
                    <div style="font-size:11px;color:#666;">Promedio</div>
                    <div style="font-size:16px;font-weight:600;color:#33691E;">${stats.avg_elevation}m</div>
                </div>
            </div>
            <div style="background:${interpretColor}15;border-radius:8px;padding:8px 10px;margin-bottom:8px;">
                <div style="font-size:12px;color:${interpretColor};font-weight:500;">
                    📋 ${interpretation}
                </div>
            </div>
            <div style="font-size:10px;color:#999;text-align:center;">
                Resolución: ~${stats.resolution_m}m | Puntos: ${stats.grid_points} | Grilla: ${stats.grid_size}
            </div>
            <div style="margin-top:8px;padding-top:8px;border-top:1px solid #eee;">
                <div style="display:flex;align-items:center;gap:4px;justify-content:center;">
                    <div style="width:16px;height:10px;background:linear-gradient(to right, #1E50AA, #46B4FF);border-radius:2px;"></div>
                    <span style="font-size:10px;color:#666;">Bajo</span>
                    <div style="width:16px;height:10px;background:linear-gradient(to right, #64F064, #DCC840);border-radius:2px;margin-left:4px;"></div>
                    <span style="font-size:10px;color:#666;">Medio</span>
                    <div style="width:16px;height:10px;background:linear-gradient(to right, #DCA028, #8C6428);border-radius:2px;margin-left:4px;"></div>
                    <span style="font-size:10px;color:#666;">Alto</span>
                </div>
            </div>
        `;

        document.body.appendChild(panel);
    }

    /**
     * Botón flotante para mostrar/ocultar elevación
     */
    function showElevationToggleButton(imageBase64, bounds) {
        let btn = document.getElementById('elevationToggleBtn');
        if (!btn) {
            btn = document.createElement('button');
            btn.id = 'elevationToggleBtn';
            btn.className = 'btn';
            btn.style.cssText = `
                position: fixed;
                bottom: 32px;
                left: 20px;
                z-index: 10001;
                box-shadow: 0 2px 10px rgba(139, 69, 19, 0.4);
                background: linear-gradient(135deg, #8B4513, #2E7D32);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                cursor: pointer;
            `;
            document.body.appendChild(btn);
        }

        btn.innerHTML = '<i class="fas fa-mountain me-1"></i> Ocultar Elevación';
        btn.style.display = 'block';

        btn.onclick = () => {
            const mapInstance = getMapInstance();
            if (elevationVisible) {
                removeElevationLayer(mapInstance);
                btn.innerHTML = '<i class="fas fa-mountain me-1"></i> Mostrar Elevación';
                // Ocultar panel de stats
                const panel = document.getElementById('elevationStatsPanel');
                if (panel) panel.style.display = 'none';
            } else {
                showElevationOnLeaflet(imageBase64, bounds);
                btn.innerHTML = '<i class="fas fa-mountain me-1"></i> Ocultar Elevación';
                // Mostrar panel de stats
                const panel = document.getElementById('elevationStatsPanel');
                if (panel) panel.style.display = 'block';
            }
        };
    }

    /**
     * Spinner de carga para elevación
     */
    function showElevationSpinner(message) {
        let spinner = document.getElementById('elevationSpinner');
        if (!spinner) {
            spinner = document.createElement('div');
            spinner.id = 'elevationSpinner';
            spinner.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                z-index: 100000;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 16px;
                padding: 30px 40px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.2);
                text-align: center;
                font-family: 'Inter', sans-serif;
            `;
            document.body.appendChild(spinner);
        }

        spinner.innerHTML = `
            <div style="margin-bottom:12px;">
                <i class="fas fa-mountain fa-2x" style="color:#8B4513;animation:pulse 1.5s infinite;"></i>
            </div>
            <div style="font-size:14px;color:#333;font-weight:500;">${message}</div>
            <div style="font-size:11px;color:#999;margin-top:6px;">Los datos de elevación se cachean — solo tarda la primera vez</div>
            <style>
                @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
            </style>
        `;
        spinner.style.display = 'block';
    }

    function hideElevationSpinner() {
        const spinner = document.getElementById('elevationSpinner');
        if (spinner) spinner.style.display = 'none';
    }

    /**
     * Toast de notificación (usa el sistema existente si está disponible)
     */
    function showElevationToast(message, type) {
        // Intentar usar el sistema de toasts existente
        if (type === 'error' && typeof window.showErrorToast === 'function') {
            window.showErrorToast(message);
            return;
        }
        if (type === 'success' && typeof window.showInfoToast === 'function') {
            window.showInfoToast(message);
            return;
        }
        if (type === 'warning' && typeof window.showWarningToast === 'function') {
            window.showWarningToast(message);
            return;
        }
        // Fallback: console
        console.log(`${MODULE_TAG} [${type}] ${message}`);
    }

    // ── Exponer funciones globales ──
    window.solicitarElevacion = solicitarElevacion;
    window.removeElevationLayer = removeElevationLayer;
    window.ELEVATION_CACHE = window.ELEVATION_CACHE;

    console.log(`${MODULE_TAG} Módulo de elevación cargado correctamente`);

})();
