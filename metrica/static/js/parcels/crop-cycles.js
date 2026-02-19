/**
 * =========================================================================
 * MÓDULO: CICLOS DE CULTIVO - Agrotech Digital
 * =========================================================================
 * Integra ciclos de cultivo con análisis satelital (NDVI, NDMI, SAVI).
 * Permite asociar opcionalmente un cultivo del catálogo a una parcela,
 * y contextualizar los índices satelitales según la etapa fenológica.
 * 
 * Endpoints consumidos:
 *   GET  /api/crop/catalog/                   -> Catálogo de cultivos
 *   GET  /api/crop/catalog/<id>/stages/       -> Etapas fenológicas
 *   GET  /api/crop/cycles/by-parcel/?parcel_id=X -> Ciclos de una parcela
 *   GET  /api/crop/cycles/active/?parcel_id=X -> Ciclo activo de parcela
 *   POST /api/crop/cycles/                    -> Crear ciclo
 *   POST /api/crop/cycles/<id>/interpret/     -> Interpretar índice
 * 
 * NO modifica flujos existentes. Es 100% aditivo.
 * =========================================================================
 */

(function () {
    'use strict';

    // =====================================================================
    // CONFIGURACIÓN
    // =====================================================================

    function getCropApiBase() {
        if (window.ApiUrls && typeof window.ApiUrls.base === 'function') {
            return window.ApiUrls.base() + '/crop';
        }
        const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        if (isLocalhost) {
            return 'http://localhost:8000/api/crop';
        }
        return '/api/crop';
    }

    const CROP_API = getCropApiBase();

    // Cache local para catálogo (no cambia frecuentemente)
    let catalogCache = null;
    let catalogCacheTimestamp = 0;
    const CATALOG_CACHE_TTL = 5 * 60 * 1000; // 5 minutos

    // =====================================================================
    // UTILIDADES HTTP
    // =====================================================================

    function getAuthHeaders() {
        const token = localStorage.getItem('accessToken');
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        };
    }

    async function cropFetch(endpoint, options = {}) {
        const url = `${CROP_API}${endpoint}`;
        const response = await fetch(url, {
            headers: getAuthHeaders(),
            ...options
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || errorData.error || `Error ${response.status}`);
        }
        return response.json();
    }

    // =====================================================================
    // API: CATÁLOGO DE CULTIVOS
    // =====================================================================

    /**
     * Obtiene el catálogo de cultivos (con cache).
     */
    async function getCropCatalog() {
        const now = Date.now();
        if (catalogCache && (now - catalogCacheTimestamp) < CATALOG_CACHE_TTL) {
            return catalogCache;
        }
        try {
            const data = await cropFetch('/catalog/');
            catalogCache = data.results || data;
            catalogCacheTimestamp = now;
            console.log('[CROP_CYCLES] Catálogo cargado:', catalogCache.length, 'cultivos');
            return catalogCache;
        } catch (err) {
            console.error('[CROP_CYCLES] Error cargando catálogo:', err);
            return catalogCache || [];
        }
    }

    /**
     * Obtiene las etapas fenológicas de un cultivo del catálogo.
     */
    async function getCropStages(catalogId) {
        try {
            return await cropFetch(`/catalog/${catalogId}/stages/`);
        } catch (err) {
            console.error('[CROP_CYCLES] Error cargando etapas:', err);
            return [];
        }
    }

    // =====================================================================
    // API: CICLOS DE CULTIVO
    // =====================================================================

    /**
     * Obtiene los ciclos de cultivo de una parcela.
     */
    async function getCyclesByParcel(parcelId) {
        try {
            return await cropFetch(`/cycles/by-parcel/?parcel_id=${parcelId}`);
        } catch (err) {
            console.error('[CROP_CYCLES] Error cargando ciclos:', err);
            return [];
        }
    }

    /**
     * Obtiene el ciclo activo de una parcela (si existe).
     */
    async function getActiveCycle(parcelId) {
        try {
            const cycles = await cropFetch(`/cycles/active/?parcel_id=${parcelId}`);
            const data = cycles.results || cycles;
            return Array.isArray(data) && data.length > 0 ? data[0] : null;
        } catch (err) {
            console.warn('[CROP_CYCLES] Sin ciclo activo para parcela:', parcelId);
            return null;
        }
    }

    /**
     * Crea un nuevo ciclo de cultivo.
     */
    async function createCropCycle(cycleData) {
        try {
            return await cropFetch('/cycles/', {
                method: 'POST',
                body: JSON.stringify(cycleData)
            });
        } catch (err) {
            console.error('[CROP_CYCLES] Error creando ciclo:', err);
            throw err;
        }
    }

    /**
     * Interpreta un valor de índice satelital según el ciclo activo.
     */
    async function interpretIndex(cycleId, indexType, value) {
        try {
            return await cropFetch(`/cycles/${cycleId}/interpret/`, {
                method: 'POST',
                body: JSON.stringify({ index_type: indexType, value: value })
            });
        } catch (err) {
            console.error('[CROP_CYCLES] Error interpretando índice:', err);
            return null;
        }
    }

    // =====================================================================
    // UI: BADGE DE CICLO ACTIVO EN PARCELA
    // =====================================================================

    /**
     * Muestra un badge de ciclo de cultivo activo en el panel de parcela.
     * Se llama cuando se selecciona una parcela. NO modifica flujos existentes.
     */
    async function showCropCycleBadge(parcelId) {
        // Buscar o crear contenedor del badge
        let container = document.getElementById('cropCycleBadgeContainer');
        if (!container) {
            // Intentar insertar después del banner de parcela seleccionada
            const banner = document.getElementById('selectedParcelBanner');
            if (!banner) return; // No hay banner, no mostrar badge

            container = document.createElement('div');
            container.id = 'cropCycleBadgeContainer';
            container.style.cssText = 'margin-top: 8px;';
            banner.parentNode.insertBefore(container, banner.nextSibling);
        }

        try {
            const cycle = await getActiveCycle(parcelId);

            if (!cycle) {
                container.innerHTML = `
                    <div style="display:inline-flex;align-items:center;gap:8px;padding:8px 16px;border-radius:10px;
                        background:#f8f9fa;color:#555;font-size:13px;cursor:pointer;
                        border:1px dashed #ccc;transition:all 0.2s ease;"
                        onmouseover="this.style.borderColor='#4CAF50';this.style.color='#2E7D32'"
                        onmouseout="this.style.borderColor='#ccc';this.style.color='#555'"
                        onclick="window.AgrotechCropCycles.openAssignCycleModal(${parcelId})">
                        <i class="fas fa-seedling"></i>
                        <span>+ Asignar cultivo</span>
                    </div>
                    <div style="font-size:11px;color:#999;margin-top:4px;padding-left:4px;">
                        Opcional: permite contextualizar NDVI, NDMI y SAVI según la etapa del cultivo.
                    </div>
                `;
                return;
            }

            // Hay un ciclo activo
            const stage = cycle.current_stage;
            const stageName = stage ? stage.name : 'Sin etapa';
            const progress = cycle.progress_percent || 0;

            // Color simple según progreso
            let progressColor = '#4CAF50';
            if (progress > 80) progressColor = '#FF9800';
            if (progress > 95) progressColor = '#f44336';

            container.innerHTML = `
                <div style="display:flex;align-items:center;gap:12px;padding:10px 16px;border-radius:10px;
                    background:#f8f9fa;border:1px solid #e0e0e0;font-size:13px;cursor:pointer;"
                    onclick="window.AgrotechCropCycles.openCycleDetailModal(${cycle.id})">
                    <div style="width:36px;height:36px;position:relative;flex-shrink:0;">
                        <svg viewBox="0 0 36 36" style="width:36px;height:36px;transform:rotate(-90deg);">
                            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                fill="none" stroke="#e8e8e8" stroke-width="3" />
                            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                fill="none" stroke="${progressColor}" stroke-width="3"
                                stroke-dasharray="${progress}, 100" stroke-linecap="round" />
                        </svg>
                        <span style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:9px;font-weight:700;color:#333;">${Math.round(progress)}%</span>
                    </div>
                    <div>
                        <div style="font-weight:600;color:#333;">
                            ${cycle.crop_catalog_name}${cycle.variety ? ` · ${cycle.variety}` : ''}
                        </div>
                        <div style="font-size:11px;color:#888;">
                            ${stageName} · Día ${cycle.days_since_planting}${stage && stage.is_critical ? ' · ⚠️ Etapa crítica' : ''}
                        </div>
                    </div>
                </div>
            `;
        } catch (err) {
            console.error('[CROP_CYCLES] Error mostrando badge:', err);
            container.innerHTML = '';
        }
    }

    /**
     * Limpia el badge de ciclo cuando se deselecciona la parcela.
     */
    function clearCropCycleBadge() {
        const container = document.getElementById('cropCycleBadgeContainer');
        if (container) container.innerHTML = '';
    }

    // =====================================================================
    // UI: MODAL PARA ASIGNAR CICLO DE CULTIVO
    // =====================================================================

    async function openAssignCycleModal(parcelId) {
        // Remover modal previo si existe
        let oldModal = document.getElementById('cropCycleAssignModal');
        if (oldModal) oldModal.remove();

        const catalog = await getCropCatalog();

        const modal = document.createElement('div');
        modal.id = 'cropCycleAssignModal';
        modal.style.cssText = `
            position:fixed;top:0;left:0;width:100vw;height:100vh;
            background:rgba(0,0,0,0.5);backdrop-filter:blur(4px);z-index:10000;
            display:flex;align-items:center;justify-content:center;animation:fadeIn 0.2s ease;
        `;

        // Generar opciones del catálogo agrupadas por categoría
        const categories = {};
        catalog.forEach(crop => {
            const cat = crop.category_display || crop.category || 'Otros';
            if (!categories[cat]) categories[cat] = [];
            categories[cat].push(crop);
        });

        let optionsHtml = '<option value="">Selecciona un cultivo...</option>';
        Object.entries(categories).forEach(([catName, crops]) => {
            optionsHtml += `<optgroup label="${catName}">`;
            crops.forEach(crop => {
                optionsHtml += `<option value="${crop.id}" data-cycle-min="${crop.cycle_days_min}" data-cycle-max="${crop.cycle_days_max}">${crop.name} (${crop.scientific_name || ''})</option>`;
            });
            optionsHtml += '</optgroup>';
        });

        const today = new Date().toISOString().split('T')[0];

        modal.innerHTML = `
            <div style="background:white;border-radius:16px;max-width:520px;width:95%;
                box-shadow:0 20px 40px rgba(0,0,0,0.2);overflow:hidden;">
                <div style="background:#2E7D32;padding:18px 24px;color:white;">
                    <h4 style="margin:0;font-weight:700;font-size:17px;">🌱 Asignar Ciclo de Cultivo</h4>
                    <p style="margin:4px 0 0;font-size:13px;opacity:0.85;">Vincula un cultivo a esta parcela para contextualizar el análisis satelital</p>
                </div>
                <div style="padding:24px;">
                    <form id="cropCycleForm">
                        <div style="margin-bottom:16px;">
                            <label style="display:block;font-weight:600;margin-bottom:6px;color:#333;font-size:14px;">
                                Cultivo del catálogo *
                            </label>
                            <select id="ccCropCatalog" required style="width:100%;padding:10px 14px;border:1.5px solid #ddd;
                                border-radius:10px;font-size:14px;outline:none;transition:border-color 0.3s;"
                                onfocus="this.style.borderColor='#4CAF50'" onblur="this.style.borderColor='#ddd'">
                                ${optionsHtml}
                            </select>
                        </div>
                        <div id="ccStagesPreview" style="display:none;margin-bottom:16px;padding:12px;border-radius:10px;
                            background:linear-gradient(135deg,#e8f5e9,#f1f8e9);font-size:12px;"></div>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">
                            <div>
                                <label style="display:block;font-weight:600;margin-bottom:6px;color:#333;font-size:14px;">
                                    Fecha de siembra *
                                </label>
                                <input type="date" id="ccPlantingDate" value="${today}" required 
                                    style="width:100%;padding:10px 14px;border:1.5px solid #ddd;border-radius:10px;font-size:14px;outline:none;"
                                    onfocus="this.style.borderColor='#4CAF50'" onblur="this.style.borderColor='#ddd'" />
                            </div>
                            <div>
                                <label style="display:block;font-weight:600;margin-bottom:6px;color:#333;font-size:14px;">
                                    Variedad <span style="color:#999;">(opcional)</span>
                                </label>
                                <input type="text" id="ccVariety" placeholder="Ej: ICA V-305"
                                    style="width:100%;padding:10px 14px;border:1.5px solid #ddd;border-radius:10px;font-size:14px;outline:none;"
                                    onfocus="this.style.borderColor='#4CAF50'" onblur="this.style.borderColor='#ddd'" />
                            </div>
                        </div>
                        <div style="margin-bottom:16px;">
                            <label style="display:block;font-weight:600;margin-bottom:6px;color:#333;font-size:14px;">
                                Notas <span style="color:#999;">(opcional)</span>
                            </label>
                            <textarea id="ccNotes" rows="2" placeholder="Observaciones del ciclo..."
                                style="width:100%;padding:10px 14px;border:1.5px solid #ddd;border-radius:10px;font-size:14px;
                                outline:none;resize:vertical;font-family:inherit;"
                                onfocus="this.style.borderColor='#4CAF50'" onblur="this.style.borderColor='#ddd'"></textarea>
                        </div>
                        <div id="ccFormError" style="display:none;padding:10px;border-radius:8px;background:#ffebee;
                            color:#c62828;font-size:13px;margin-bottom:12px;"></div>
                        <div style="display:flex;gap:12px;justify-content:flex-end;">
                            <button type="button" id="ccCancelBtn" style="padding:10px 24px;border:1.5px solid #ddd;
                                background:white;border-radius:10px;cursor:pointer;font-weight:500;font-size:14px;">
                                Cancelar
                            </button>
                            <button type="submit" id="ccSubmitBtn" style="padding:10px 24px;border:none;
                                background:linear-gradient(135deg,#2E7D32,#4CAF50);color:white;border-radius:10px;
                                cursor:pointer;font-weight:600;font-size:14px;box-shadow:0 4px 12px rgba(76,175,80,0.3);">
                                🌱 Asignar Ciclo
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Cerrar al hacer clic fuera
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        document.getElementById('ccCancelBtn').addEventListener('click', () => modal.remove());

        // Preview de etapas al seleccionar cultivo
        document.getElementById('ccCropCatalog').addEventListener('change', async function () {
            const preview = document.getElementById('ccStagesPreview');
            if (!this.value) {
                preview.style.display = 'none';
                return;
            }

            preview.style.display = 'block';
            preview.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Cargando etapas...';

            try {
                const stages = await getCropStages(this.value);
                if (stages.length === 0) {
                    preview.innerHTML = '<span style="color:#999;">Sin etapas fenológicas definidas</span>';
                    return;
                }

                const selected = this.options[this.selectedIndex];
                const cycleMin = selected.getAttribute('data-cycle-min');
                const cycleMax = selected.getAttribute('data-cycle-max');

                // Auto-calcular fecha estimada de cosecha
                if (cycleMin) {
                    const plantDate = document.getElementById('ccPlantingDate').value;
                    if (plantDate) {
                        const avgDays = Math.round((parseInt(cycleMin) + parseInt(cycleMax)) / 2);
                        const harvestDate = new Date(plantDate);
                        harvestDate.setDate(harvestDate.getDate() + avgDays);
                        // Info visual
                        preview.innerHTML = `
                            <div style="margin-bottom:8px;">
                                <strong>📅 Ciclo estimado:</strong> ${cycleMin}-${cycleMax} días
                                <span style="color:#2E7D32;"> → Cosecha aprox: ${harvestDate.toLocaleDateString('es-ES')}</span>
                            </div>
                            <div style="display:flex;flex-wrap:wrap;gap:6px;">
                                ${stages.map(s => `
                                    <span style="padding:3px 10px;border-radius:20px;font-size:11px;
                                        background:${s.is_critical ? 'rgba(255,152,0,0.15)' : 'rgba(76,175,80,0.1)'};
                                        color:${s.is_critical ? '#E65100' : '#2E7D32'};
                                        border:1px solid ${s.is_critical ? 'rgba(255,152,0,0.3)' : 'rgba(76,175,80,0.2)'};">
                                        ${s.is_critical ? '⚠️' : '🌿'} ${s.name} (D${s.day_start}-${s.day_end})
                                    </span>
                                `).join('')}
                            </div>
                        `;
                    }
                }
            } catch (err) {
                preview.innerHTML = '<span style="color:#dc3545;">Error cargando etapas</span>';
            }
        });

        // Submit del formulario
        document.getElementById('cropCycleForm').addEventListener('submit', async function (e) {
            e.preventDefault();
            const errorEl = document.getElementById('ccFormError');
            const submitBtn = document.getElementById('ccSubmitBtn');

            const cropCatalogId = document.getElementById('ccCropCatalog').value;
            const plantingDate = document.getElementById('ccPlantingDate').value;
            const variety = document.getElementById('ccVariety').value.trim();
            const notes = document.getElementById('ccNotes').value.trim();

            if (!cropCatalogId || !plantingDate) {
                errorEl.textContent = 'Selecciona un cultivo y fecha de siembra.';
                errorEl.style.display = 'block';
                return;
            }

            // Calcular fecha estimada de cosecha
            const selected = document.getElementById('ccCropCatalog').options[document.getElementById('ccCropCatalog').selectedIndex];
            const cycleMax = parseInt(selected.getAttribute('data-cycle-max')) || 150;
            const harvestDate = new Date(plantingDate);
            harvestDate.setDate(harvestDate.getDate() + cycleMax);

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';

            try {
                await createCropCycle({
                    parcel: parcelId,
                    crop_catalog: parseInt(cropCatalogId),
                    planting_date: plantingDate,
                    estimated_harvest_date: harvestDate.toISOString().split('T')[0],
                    variety: variety || null,
                    notes: notes || null,
                    status: 'active'
                });

                modal.remove();
                if (typeof showInfoToast === 'function') {
                    showInfoToast('🌱 Ciclo de cultivo asignado correctamente');
                }

                // Refrescar badge
                showCropCycleBadge(parcelId);

            } catch (err) {
                errorEl.textContent = `Error: ${err.message}`;
                errorEl.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.innerHTML = '🌱 Asignar Ciclo';
            }
        });
    }

    // =====================================================================
    // UI: MODAL DETALLE DE CICLO DE CULTIVO
    // =====================================================================

    async function openCycleDetailModal(cycleId) {
        let oldModal = document.getElementById('cropCycleDetailModal');
        if (oldModal) oldModal.remove();

        const modal = document.createElement('div');
        modal.id = 'cropCycleDetailModal';
        modal.style.cssText = `
            position:fixed;top:0;left:0;width:100vw;height:100vh;
            background:rgba(0,0,0,0.5);backdrop-filter:blur(4px);z-index:10000;
            display:flex;align-items:center;justify-content:center;
        `;
        modal.innerHTML = `
            <div style="background:white;border-radius:16px;max-width:600px;width:95%;
                box-shadow:0 20px 40px rgba(0,0,0,0.2);overflow:hidden;max-height:90vh;display:flex;flex-direction:column;">
                <div style="background:#2E7D32;padding:18px 24px;color:white;display:flex;justify-content:space-between;align-items:center;">
                    <h4 style="margin:0;font-size:17px;" id="ccDetailTitle"><i class="fas fa-spinner fa-spin"></i> Cargando...</h4>
                    <button id="ccDetailCloseX" style="background:rgba(255,255,255,0.2);border:none;color:white;width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:16px;">✕</button>
                </div>
                <div id="ccDetailBody" style="padding:24px;overflow-y:auto;flex:1;">
                    <div style="text-align:center;padding:40px;color:#888;">
                        <i class="fas fa-spinner fa-spin" style="font-size:20px;"></i>
                        <p style="margin-top:8px;font-size:13px;">Cargando información del ciclo...</p>
                    </div>
                </div>
                <div style="padding:12px 24px;background:#f8f9fa;border-top:1px solid #eee;text-align:right;">
                    <button id="ccDetailClose" style="padding:8px 20px;border:none;background:#6c757d;color:white;
                        border-radius:8px;cursor:pointer;font-size:13px;">Cerrar</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
        document.getElementById('ccDetailClose').addEventListener('click', () => modal.remove());
        document.getElementById('ccDetailCloseX').addEventListener('click', () => modal.remove());

        try {
            const cycle = await cropFetch(`/cycles/${cycleId}/`);
            const stage = cycle.current_stage;

            document.getElementById('ccDetailTitle').innerHTML = `🌱 ${cycle.crop_catalog_name}${cycle.variety ? ` · ${cycle.variety}` : ''}`;

            const stages = await getCropStages(cycle.crop_catalog);

            document.getElementById('ccDetailBody').innerHTML = `
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px;">
                    <div style="padding:12px;border-radius:10px;background:#f5f5f5;text-align:center;">
                        <div style="font-size:11px;color:#888;">Estado</div>
                        <div style="font-weight:700;color:#2E7D32;font-size:14px;">${cycle.status_display || cycle.status}</div>
                    </div>
                    <div style="padding:12px;border-radius:10px;background:#f5f5f5;text-align:center;">
                        <div style="font-size:11px;color:#888;">Día</div>
                        <div style="font-weight:700;color:#333;font-size:18px;">${cycle.days_since_planting}</div>
                    </div>
                    <div style="padding:12px;border-radius:10px;background:#f5f5f5;text-align:center;">
                        <div style="font-size:11px;color:#888;">Progreso</div>
                        <div style="font-weight:700;color:#333;font-size:14px;">${cycle.progress_percent || 0}%</div>
                    </div>
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;font-size:13px;">
                    <div><span style="color:#888;">Siembra:</span> <strong>${new Date(cycle.planting_date).toLocaleDateString('es-ES')}</strong></div>
                    <div><span style="color:#888;">Cosecha est.:</span> <strong>${cycle.estimated_harvest_date ? new Date(cycle.estimated_harvest_date).toLocaleDateString('es-ES') : 'N/A'}</strong></div>
                    <div><span style="color:#888;">Etapa actual:</span> <strong style="color:${stage && stage.is_critical ? '#E65100' : '#2E7D32'};">${stage ? stage.name : 'Sin etapa'}${stage && stage.is_critical ? ' ⚠️' : ''}</strong></div>
                    <div><span style="color:#888;">Parcela:</span> <strong>${cycle.parcel_name || '-'}</strong></div>
                </div>

                ${stage ? `
                <div style="margin-bottom:20px;">
                    <h6 style="font-weight:600;margin-bottom:10px;font-size:14px;color:#333;">Rangos óptimos de índices — ${stage.name}</h6>
                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;">
                        <div style="padding:10px;border-radius:8px;background:#e8f5e9;text-align:center;">
                            <div style="font-size:11px;color:#2E7D32;font-weight:600;">NDVI</div>
                            <div style="font-weight:700;font-size:16px;color:#1B5E20;">${stage.ndvi_optimal}</div>
                            <div style="font-size:10px;color:#666;">${stage.ndvi_min} — ${stage.ndvi_max}</div>
                        </div>
                        <div style="padding:10px;border-radius:8px;background:#e3f2fd;text-align:center;">
                            <div style="font-size:11px;color:#1565C0;font-weight:600;">NDMI</div>
                            <div style="font-weight:700;font-size:16px;color:#0D47A1;">${stage.ndmi_optimal}</div>
                            <div style="font-size:10px;color:#666;">${stage.ndmi_min} — ${stage.ndmi_max}</div>
                        </div>
                        <div style="padding:10px;border-radius:8px;background:#efebe9;text-align:center;">
                            <div style="font-size:11px;color:#4E342E;font-weight:600;">SAVI</div>
                            <div style="font-weight:700;font-size:16px;color:#3E2723;">${stage.savi_optimal}</div>
                            <div style="font-size:10px;color:#666;">${stage.savi_min} — ${stage.savi_max}</div>
                        </div>
                    </div>
                    ${stage.is_critical ? `
                        <div style="margin-top:10px;padding:10px 12px;border-radius:8px;background:#fff3e0;
                            border-left:3px solid #FF9800;font-size:12px;color:#E65100;">
                            ⚠️ <strong>Etapa crítica</strong> — ${stage.critical_alert || 'Monitorear de cerca. Los problemas ahora impactan significativamente el rendimiento.'}
                        </div>
                    ` : ''}
                </div>
                ` : ''}

                ${stages.length > 0 ? `
                <div>
                    <h6 style="font-weight:600;margin-bottom:8px;font-size:14px;color:#333;">Etapas del ciclo</h6>
                    <div style="display:flex;flex-direction:column;gap:3px;">
                        ${stages.map(s => {
                            const isCurrent = stage && s.id === stage.id;
                            const isPast = cycle.days_since_planting > s.day_end;
                            return `
                                <div style="display:flex;align-items:center;gap:8px;padding:7px 10px;border-radius:6px;
                                    background:${isCurrent ? '#e8f5e9' : 'transparent'};
                                    border:1px solid ${isCurrent ? '#4CAF50' : '#f0f0f0'};
                                    opacity:${isPast && !isCurrent ? '0.5' : '1'};font-size:13px;">
                                    <span style="width:20px;text-align:center;font-size:12px;">
                                        ${isCurrent ? '▶' : isPast ? '✓' : '○'}
                                    </span>
                                    <span style="flex:1;font-weight:${isCurrent ? '600' : '400'};">${s.name}</span>
                                    <span style="font-size:11px;color:#999;">D${s.day_start}–${s.day_end}</span>
                                    ${s.is_critical ? '<span style="font-size:10px;color:#FF9800;">⚠️</span>' : ''}
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
                ` : ''}

                ${cycle.notes ? `
                    <div style="margin-top:14px;padding:10px 12px;border-radius:8px;background:#fafafa;font-size:12px;color:#666;">
                        📝 ${cycle.notes}
                    </div>
                ` : ''}
            `;
        } catch (err) {
            document.getElementById('ccDetailBody').innerHTML = `
                <div style="text-align:center;padding:40px;color:#dc3545;">
                    <i class="fas fa-exclamation-triangle" style="font-size:24px;"></i>
                    <p>Error al cargar detalles del ciclo</p>
                </div>
            `;
        }
    }

    // =====================================================================
    // INTEGRACIÓN: INTERPRETACIÓN CONTEXTUAL DE ÍNDICES
    // =====================================================================

    /**
     * Función principal para obtener interpretación contextual.
     * Se puede llamar desde analytics-cientifico.js o cualquier módulo.
     * 
     * @param {number} parcelId - ID de la parcela
     * @param {string} indexType - 'ndvi', 'ndmi' o 'savi'
     * @param {number} value - Valor del índice (-1 a 1)
     * @returns {Object|null} Interpretación contextual o null si no hay ciclo activo
     */
    async function getContextualInterpretation(parcelId, indexType, value) {
        try {
            const cycle = await getActiveCycle(parcelId);
            if (!cycle) return null;

            const interpretation = await interpretIndex(cycle.id, indexType, value);
            return interpretation;
        } catch (err) {
            console.warn('[CROP_CYCLES] Error en interpretación contextual:', err);
            return null;
        }
    }

    /**
     * Genera HTML con la interpretación contextual para insertar en modales de analytics.
     */
    async function renderContextualBadge(parcelId, indexType, value) {
        const interp = await getContextualInterpretation(parcelId, indexType, value);
        if (!interp || interp.status === 'unknown') return '';

        const statusColors = {
            optimal: { bg: '#e8f5e9', border: '#4CAF50', text: '#1B5E20', icon: '✅' },
            normal: { bg: '#f1f8e9', border: '#8BC34A', text: '#33691E', icon: '👍' },
            warning: { bg: '#fff3e0', border: '#FF9800', text: '#E65100', icon: '⚠️' },
            critical: { bg: '#ffebee', border: '#f44336', text: '#B71C1C', icon: '🚨' },
            high: { bg: '#e3f2fd', border: '#2196F3', text: '#0D47A1', icon: 'ℹ️' },
        };
        const colors = statusColors[interp.status] || statusColors.normal;

        return `
            <div style="margin-top:12px;padding:14px;border-radius:12px;background:${colors.bg};
                border-left:4px solid ${colors.border};font-size:13px;">
                <div style="font-weight:700;color:${colors.text};margin-bottom:6px;">
                    ${colors.icon} ${interp.message}
                </div>
                ${interp.stage ? `
                    <div style="color:#555;font-size:12px;">
                        🌱 <strong>${interp.crop.name}</strong> · Etapa: ${interp.stage.name}
                        (Día ${interp.days_since_planting}) · Progreso: ${interp.progress_percent}%
                    </div>
                    <div style="color:#666;font-size:11px;margin-top:4px;">
                        Rango esperado: [${interp.index.range[0]} - ${interp.index.range[1]}] · 
                        Óptimo: ${interp.index.optimal} · Desviación: ${interp.index.deviation_percent}%
                    </div>
                ` : ''}
                ${interp.critical_alert ? `
                    <div style="margin-top:8px;padding:8px;border-radius:8px;background:rgba(255,152,0,0.1);
                        color:#E65100;font-size:12px;">
                        <strong>⚠️ Alerta:</strong> ${interp.critical_alert}
                    </div>
                ` : ''}
            </div>
        `;
    }

    // =====================================================================
    // HOOKS: INTEGRACIÓN CON FLUJOS EXISTENTES (NO MODIFICA NADA)
    // =====================================================================

    /**
     * Hook que se ejecuta cuando se selecciona una parcela.
     * Escucha cambios en AGROTECH_STATE sin modificar el flujo original.
     */
    function initCropCyclesHook() {
        let lastParcelId = null;

        setInterval(() => {
            const currentId = window.AGROTECH_STATE?.selectedParcelId;
            if (currentId && currentId !== lastParcelId) {
                lastParcelId = currentId;
                showCropCycleBadge(currentId);
                console.log('[CROP_CYCLES] Badge actualizado para parcela:', currentId);
            } else if (!currentId && lastParcelId) {
                lastParcelId = null;
                clearCropCycleBadge();
            }
        }, 800);

        console.log('[CROP_CYCLES] ✅ Módulo de ciclos de cultivo inicializado');
    }

    // =====================================================================
    // INICIALIZACIÓN
    // =====================================================================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCropCyclesHook);
    } else {
        initCropCyclesHook();
    }

    // =====================================================================
    // API PÚBLICA
    // =====================================================================

    window.AgrotechCropCycles = {
        getCropCatalog,
        getCropStages,
        getCyclesByParcel,
        getActiveCycle,
        createCropCycle,
        interpretIndex,
        getContextualInterpretation,
        renderContextualBadge,
        showCropCycleBadge,
        clearCropCycleBadge,
        openAssignCycleModal,
        openCycleDetailModal,
    };

})();
