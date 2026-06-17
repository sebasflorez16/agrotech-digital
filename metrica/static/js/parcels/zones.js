/**
 * Zonas de manejo (precision farming) — UI para el dashboard de parcelas.
 *
 * Depende de:
 *  - Leaflet (window.L)
 *  - Axios (window.axios) o fetch nativo
 *  - getBackendUrl() de /static/js/utils/api-utils.js
 *  - localStorage.accessToken para JWT
 *
 * Engancha el panel #zonesPanel cuando hay una parcela seleccionada
 * (vía wrap de window.updateSelectedParcelBanner).
 */
(function () {
    'use strict';

    const state = {
        currentParcelId: null,
        currentZonification: null,
        map: null,
        layer: null,
    };

    const CATEGORY_COLORS = {
        low: '#d73027',
        mid_low: '#fc8d59',
        mid: '#fee08b',
        mid_high: '#91cf60',
        high: '#1a9850',
    };

    function apiBase() {
        if (typeof getBackendUrl === 'function') {
            return getBackendUrl();
        }
        return `${window.location.protocol}//${window.location.hostname}:8000`;
    }

    function authHeader() {
        const t = localStorage.getItem('accessToken') || localStorage.getItem('access');
        return t ? { Authorization: `Bearer ${t}` } : {};
    }

    async function api(path, opts = {}) {
        const url = `${apiBase()}${path}`;
        const headers = Object.assign(
            { 'Content-Type': 'application/json' },
            authHeader(),
            opts.headers || {}
        );
        const res = await fetch(url, Object.assign({}, opts, { headers }));
        const text = await res.text();
        let data;
        try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
        if (!res.ok) {
            const err = new Error(data?.detail || `HTTP ${res.status}`);
            err.status = res.status;
            err.data = data;
            throw err;
        }
        return data;
    }

    function ensureMap() {
        if (state.map || !window.L) return state.map;
        const el = document.getElementById('zonesMap');
        if (!el) return null;
        state.map = L.map(el, { zoomControl: true }).setView([4.6, -74.1], 12);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap',
            maxZoom: 19,
        }).addTo(state.map);
        return state.map;
    }

    function setStatus(html, color) {
        const el = document.getElementById('zonesStatus');
        if (!el) return;
        el.style.color = color || '#666';
        el.innerHTML = html;
    }

    function renderZonesList(zonification) {
        const container = document.getElementById('zonesList');
        if (!container) return;
        const zones = zonification?.zones || [];
        if (!zones.length) {
            container.innerHTML = '<div style="color:#888;font-style:italic;">Sin zonas todavía.</div>';
            return;
        }
        container.innerHTML = zones.map(z => {
            const color = CATEGORY_COLORS[z.category] || '#666';
            return `
            <div style="border-left:5px solid ${color};background:#fafafa;border-radius:8px;padding:10px 12px;margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <strong style="color:${color};">${z.label}</strong>
                    <span style="font-size:12px;color:#555;">${(z.area_ha || 0).toFixed(2)} ha · ${z.pixel_count} px</span>
                </div>
                <div style="font-size:12px;color:#444;margin-top:4px;">
                    NDVI ${z.ndvi_mean ?? '-'} · NDMI ${z.ndmi_mean ?? '-'} · SAVI ${z.savi_mean ?? '-'} · NDRE ${z.ndre_mean ?? '-'}
                </div>
                <div style="font-size:12px;color:#333;margin-top:6px;">${z.recomendacion || ''}</div>
            </div>`;
        }).join('');
    }

    function renderZonesOnMap(zonification) {
        const map = ensureMap();
        if (!map) return;
        if (state.layer) {
            map.removeLayer(state.layer);
            state.layer = null;
        }
        const features = (zonification?.zones || [])
            .filter(z => z.geometry_geojson)
            .map(z => ({
                type: 'Feature',
                geometry: z.geometry_geojson,
                properties: {
                    label: z.label,
                    category: z.category,
                    ndvi_mean: z.ndvi_mean,
                    area_ha: z.area_ha,
                    recomendacion: z.recomendacion,
                },
            }));
        if (!features.length) return;
        state.layer = L.geoJSON({ type: 'FeatureCollection', features }, {
            style: f => ({
                color: '#222',
                weight: 1,
                fillColor: CATEGORY_COLORS[f.properties.category] || '#888',
                fillOpacity: 0.65,
            }),
            onEachFeature: (f, lyr) => {
                lyr.bindPopup(`
                    <strong>${f.properties.label}</strong><br/>
                    NDVI: ${f.properties.ndvi_mean ?? '-'}<br/>
                    Área: ${(f.properties.area_ha || 0).toFixed(2)} ha<br/>
                    <small>${f.properties.recomendacion || ''}</small>
                `);
            },
        }).addTo(state.map);
        try { state.map.fitBounds(state.layer.getBounds(), { padding: [10, 10] }); } catch (_) {}
    }

    async function loadLatestZonification(parcelId) {
        if (!parcelId) return;
        setStatus('Cargando zonificaciones existentes…');
        try {
            const list = await api(`/api/parcels/parcel-zonifications/?parcel=${parcelId}`);
            const items = Array.isArray(list) ? list : (list.results || []);
            if (items.length) {
                const latest = items[0];
                state.currentZonification = latest;
                renderZonesList(latest);
                renderZonesOnMap(latest);
                setStatus(
                    `Última zonificación: ${latest.scene_date} · ${latest.method_display || latest.method} · k=${latest.k_zones} · status=${latest.status_display || latest.status}`
                );
            } else {
                setStatus('No hay zonificaciones aún. Haz clic en "Generar zonificación".');
                renderZonesList({ zones: [] });
            }
        } catch (e) {
            setStatus(`Error cargando zonificaciones: ${e.message}`, '#c0392b');
        }
    }

    async function generateZonification() {
        const parcelId = state.currentParcelId;
        if (!parcelId) {
            setStatus('Primero selecciona una parcela.', '#c0392b');
            return;
        }
        const k = parseInt(document.getElementById('zonesKSelect').value, 10) || 5;
        const idx = document.getElementById('zonesIndexSelect').value || 'ndvi';
        const btn = document.getElementById('btnGenerateZones');
        if (btn) { btn.disabled = true; btn.textContent = 'Procesando…'; }
        setStatus('Generando zonificación (K-means)…');
        try {
            const data = await api('/api/parcels/parcel-zonifications/generate-for-parcel/', {
                method: 'POST',
                body: JSON.stringify({ parcel: parcelId, k_zones: k, index_base: idx }),
            });
            state.currentZonification = data;
            renderZonesList(data);
            renderZonesOnMap(data);
            setStatus(
                `✅ Zonificación lista · ${data.zones?.length || 0} zonas · ${data.total_pixels} pixeles · ${data.scene_date}`,
                '#27ae60'
            );
        } catch (e) {
            setStatus(`❌ Error: ${e.message}`, '#c0392b');
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = '⚙️ Generar zonificación'; }
        }
    }

    function showPanelFor(parcel) {
        const panel = document.getElementById('zonesPanel');
        if (!panel) return;
        if (!parcel || !parcel.id) {
            panel.style.display = 'none';
            state.currentParcelId = null;
            return;
        }
        panel.style.display = 'block';
        if (parcel.id === state.currentParcelId) return;
        state.currentParcelId = parcel.id;
        // Esperar al próximo frame para que Leaflet calcule tamaños correctos
        setTimeout(() => {
            const m = ensureMap();
            if (m) m.invalidateSize();
            loadLatestZonification(parcel.id);
        }, 100);
    }

    function wireBanner() {
        const original = window.updateSelectedParcelBanner;
        window.updateSelectedParcelBanner = function (parcel) {
            try { if (typeof original === 'function') original(parcel); } catch (_) {}
            showPanelFor(parcel);
        };
    }

    function init() {
        const btn = document.getElementById('btnGenerateZones');
        if (btn) btn.addEventListener('click', generateZonification);
        wireBanner();
        // Si ya hay una parcela seleccionada al cargar el script
        const id = window.AGROTECH_STATE && window.AGROTECH_STATE.selectedParcelId;
        if (id) showPanelFor({ id });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
