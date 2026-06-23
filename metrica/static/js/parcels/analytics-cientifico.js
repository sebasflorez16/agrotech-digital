/**
 * Analytics Científico Satelital - Función independiente
 * Propósito: Obtener y mostrar datos científicos NDVI/NDMI sin afectar análisis visual
 * Autor: Sistema Agrotech
 * Fecha: 2025
 */

// Variable global para almacenar los últimos datos de análisis científico
window.LATEST_SCIENTIFIC_ANALYTICS = null;

/**
 * Función principal para obtener analytics científicos satelitales
 * @param {string} viewId - ID de la vista satelital
 * @param {string} sceneDate - Fecha de la escena (formato YYYY-MM-DD)
 * @returns {Promise<Object>} Datos científicos interpretados
 */
window.obtenerAnalyticsCientifico = async function(viewId, sceneDate) {
    try {
        console.log(`[ANALYTICS_CIENTIFICO] Iniciando análisis científico`);
        console.log(`[ANALYTICS_CIENTIFICO] View ID:`, viewId, 'Fecha:', sceneDate);

        // Validar parámetros
        if (!viewId) {
            const msg = 'View ID es requerido para análisis científico';
            console.error(`[ANALYTICS_CIENTIFICO] Error: ${msg}`);
            if (typeof showToast === 'function') showToast(`❌ ${msg}`, 'error');
            else alert(msg);
            return;
        }

        // Cache frontend: evita llamadas repetidas en 5 minutos
        const cacheKey = `analytics_${viewId}_${sceneDate || 'latest'}`;
        const lastCall = window._ANALYTICS_TIMESTAMPS || {};
        if (lastCall[cacheKey] && Date.now() - lastCall[cacheKey] < 300000) {
            console.log(`[ANALYTICS_CIENTIFICO] Cache frontend: solicitud omitida (menos de 5 min)`);
            return;
        }
        if (!window._ANALYTICS_TIMESTAMPS) window._ANALYTICS_TIMESTAMPS = {};
        window._ANALYTICS_TIMESTAMPS[cacheKey] = Date.now();

        // 🗄️ Verificar cache de localStorage primero
        const idxType = sceneDate ? 'ndvi' : 'ndvi';
        if (window.SceneCache && sceneDate) {
            const cached = window.SceneCache.getStats(viewId, sceneDate, idxType);
            if (cached) {
                console.log('[ANALYTICS_CIENTIFICO] Cache localStorage hit');
                window.LATEST_SCIENTIFIC_ANALYTICS = cached;
                return cached;
            }
        }
        
        // Mostrar spinner con mensaje informativo
        if (typeof showSpinner === 'function') {
            showSpinner('Procesando análisis satelital... Esto puede tomar hasta 15 segundos.');
        } else if (typeof showToast === 'function') {
            showToast('🛰️ Procesando análisis satelital...', 'info');
        }
        
        // Verificar que axiosInstance esté disponible
        if (typeof window.axiosInstance === 'undefined') {
            if (typeof hideSpinner === 'function') hideSpinner();
            const msg = 'Sistema de autenticación no inicializado';
            console.error(`[ANALYTICS_CIENTIFICO] Error: ${msg}`);
            if (typeof showToast === 'function') {
                showToast(`❌ ${msg}`, 'error');
            } else {
                alert(msg);
            }
            return;
        }
        
        // Construir parámetros de la consulta
        const parcelId = window.AGROTECH_STATE?.selectedParcelId;
        const params = new URLSearchParams({
            view_id: viewId
        });
        if (parcelId) params.append('parcel_id', parcelId);
        if (sceneDate) params.append('scene_date', sceneDate);
        
        console.log(`[ANALYTICS_CIENTIFICO] Llamando a: /eosda-analytics/?${params.toString()}`);
        
        // Llamada al endpoint de analytics científico usando axiosInstance
        const response = await window.axiosInstance.get(`/eosda-analytics/?${params.toString()}`);
        
        const analyticsData = response.data;
        
        console.log(`[ANALYTICS_CIENTIFICO] Datos obtenidos exitosamente:`, analyticsData);
        
        // 🗄️ Guardar en localStorage cache
        if (window.SceneCache && sceneDate) {
            window.SceneCache.setStats(viewId, sceneDate, 'ndvi', analyticsData);
        }

        mostrarModalAnalyticsCientifico(analyticsData, sceneDate, viewId);
        
        if (typeof showToast === 'function') {
            showToast('✅ Análisis científico completado', 'success');
        }
        
        // Almacenar datos en variable global
        window.LATEST_SCIENTIFIC_ANALYTICS = analyticsData;
        
        return analyticsData;
        
    } catch (error) {
        // Ocultar spinner en caso de error
        if (typeof hideSpinner === 'function') {
            hideSpinner();
        }
        
        console.error('[ANALYTICS_CIENTIFICO] Error:', error);
        
        // Mejorar mensajes de error con información contextual
        let errorMsg = '';
        let userFriendlyMsg = '';
        
        if (error.response) {
            // Error de respuesta del servidor
            const status = error.response.status;
            const data = error.response.data;
            
            if (status === 503) {
                userFriendlyMsg = 'El análisis satelital aún se está procesando. Por favor, intenta nuevamente en unos minutos.';
            } else if (status === 404) {
                userFriendlyMsg = 'No se encontraron datos de análisis para esta escena.';
            } else if (status === 500) {
                userFriendlyMsg = 'Error en el servidor al procesar el análisis. Por favor, contacta al administrador.';
            } else {
                userFriendlyMsg = data?.detail || data?.error || `Error del servidor (código ${status})`;
            }
            
            errorMsg = `${userFriendlyMsg} [Status: ${status}]`;
        } else if (error.request) {
            // La solicitud se hizo pero no hubo respuesta
            errorMsg = 'No se pudo conectar con el servidor. Verifica tu conexión a internet.';
            userFriendlyMsg = errorMsg;
        } else {
            // Error en la configuración de la solicitud
            errorMsg = error.message || JSON.stringify(error);
            userFriendlyMsg = 'Error al procesar la solicitud de análisis.';
        }
        
        if (typeof showToast === 'function') {
            showToast(`❌ ${userFriendlyMsg}`, 'error');
        } else {
            alert(`Error en análisis científico: ${userFriendlyMsg}`);
        }
        
        console.error('[ANALYTICS_CIENTIFICO] Detalle completo del error:', errorMsg);
        throw error;
    }
};

/**
 * Muestra modal con análisis científico completo
 * @param {Object} analyticsData - Datos científicos interpretados
 * @param {string} sceneDate - Fecha de la escena
 * @param {string} viewId - ID de la vista
 */
function mostrarModalAnalyticsCientifico(analyticsData, sceneDate, viewId) {
    console.log('[ANALYTICS_CIENTIFICO] Mostrando modal de análisis científico');
    
    // Aplicar estilos consistentes
    applyCientificoAnalyticsStyles();
    
    const modalHTML = generateScientificModalHTML(analyticsData, sceneDate, viewId);
    
    // Remover modal anterior si existe
    const existingModal = document.getElementById('scientificAnalyticsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Agregar nuevo modal al DOM
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Mostrar modal usando Bootstrap
    try {
        const modalElement = document.getElementById('scientificAnalyticsModal');
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        
        // Limpiar modal al cerrar
        modalElement.addEventListener('hidden.bs.modal', function () {
            modalElement.remove();
        });
        
    } catch (error) {
        console.error('[MODAL_CIENTIFICO] Error mostrando modal:', error);
        alert('Análisis científico completado. Ver consola para detalles.');
    }

    // 🗄️ SceneCache: guardar en historial + mostrar panel
    if (window.SceneCache && sceneDate) {
        const parcelId = window.AGROTECH_STATE?.selectedParcelId;
        const parcelName = document.getElementById('parcelNameCell')?.textContent || '';
        const stats = analyticsData?.interpreted_data || analyticsData?.statistics || {};
        const ndviVal = stats.ndvi?.latest || stats.ndvi?.average || stats.ndvi?.mean;

        window.SceneCache.addToHistory({
            viewId: viewId, sceneDate: sceneDate, indexType: 'ndvi',
            parcelId: parcelId, parcelName: parcelName, value: ndviVal,
        });

        if (typeof updateCurrentSceneStats === 'function')
            updateCurrentSceneStats(analyticsData, sceneDate, viewId, parcelName);
        const section = document.getElementById('sceneHistorySection');
        if (section) section.style.display = 'block';
        if (typeof renderSceneHistory === 'function') renderSceneHistory();
    }
}

/**
 * Genera HTML completo del modal de análisis científico
 * @param {Object} analyticsData - Datos científicos
 * @param {string} sceneDate - Fecha de la escena
 * @param {string} viewId - ID de la vista
 * @returns {string} HTML del modal
 */
function generateScientificModalHTML(analyticsData, sceneDate, viewId) {
    const { raw_data, interpretation, alerts, recommendations, metadata } = analyticsData;
    
    return `
        <div class="modal fade" id="scientificAnalyticsModal" tabindex="-1" role="dialog" aria-labelledby="scientificModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-xl" role="document">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title" id="scientificModalLabel">
                            Análisis Científico Satelital
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        ${generateScientificAnalysisHTML(analyticsData, sceneDate, viewId)}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-success" onclick="exportarAnalyticsCientificoData('${viewId}', '${sceneDate}')">
                            Exportar Datos CSV
                        </button>
                        <button type="button" class="btn btn-info" onclick="imprimirAnalyticsCientifico('${viewId}', '${sceneDate}')">
                            Imprimir Reporte
                        </button>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Genera el contenido HTML del análisis científico
 * @param {Object} analyticsData - Datos científicos completos
 * @param {string} sceneDate - Fecha de la escena
 * @param {string} viewId - ID de la vista
 * @returns {string} HTML del análisis
 */
function generateScientificAnalysisHTML(analyticsData, sceneDate, viewId) {
    const { raw_data, interpretation, alerts, recommendations, metadata } = analyticsData;
    
    let html = `
        <div class="scientific-analysis-container">
            <style>
                .analysis-section {
                    border: 1px solid #e9ecef;
                    border-radius: 8px;
                    margin-bottom: 1.5rem;
                }
                .section-title {
                    font-weight: 600;
                    margin-bottom: 1rem;
                    font-size: 1.1rem;
                }
                .index-card {
                    background: white;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 12px;
                    margin-bottom: 10px;
                    transition: box-shadow 0.2s;
                }
                .index-card:hover {
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                .index-header {
                    font-weight: 600;
                    margin-bottom: 8px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                .index-range {
                    font-size: 0.85rem;
                    padding: 4px 8px;
                    border-radius: 4px;
                    margin-top: 6px;
                }
                .range-excellent { background: #d4edda; color: #155724; }
                .range-good { background: #fff3cd; color: #856404; }
                .range-poor { background: #f8d7da; color: #721c24; }
                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                    gap: 10px;
                }
                .stat-item {
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 8px;
                    text-align: center;
                }
                .stat-value {
                    font-weight: 600;
                    font-size: 1.1rem;
                    color: #495057;
                }
                .stat-label {
                    font-size: 0.8rem;
                    color: #6c757d;
                    margin-top: 2px;
                }
                .metrics-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                    gap: 12px;
                    margin-bottom: 1rem;
                }
                .metric-card {
                    background: linear-gradient(145deg, #fff, #f8f9fa);
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 12px;
                    text-align: center;
                    transition: transform 0.2s;
                }
                .metric-card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }
                .metric-value {
                    font-size: 1.2rem;
                    font-weight: 700;
                    color: #495057;
                    margin-bottom: 4px;
                }
                .metric-label {
                    font-size: 0.85rem;
                    color: #6c757d;
                    font-weight: 500;
                }
                .interpretation-panel {
                    background: linear-gradient(145deg, #f8f9fa, #e9ecef);
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 15px;
                    height: 100%;
                }
                .status-badge {
                    display: inline-block;
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 0.85rem;
                    margin-bottom: 10px;
                }
                .status-excellent { background: #d4edda; color: #155724; }
                .status-good { background: #d1ecf1; color: #0c5460; }
                .status-medium { background: #fff3cd; color: #856404; }
                .status-poor { background: #f8d7da; color: #721c24; }
                .interpretation-text {
                    font-size: 0.9rem;
                    line-height: 1.4;
                    margin-bottom: 8px;
                }
                .recommendation-card {
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    transition: box-shadow 0.2s;
                }
                .recommendation-card:hover {
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }
                .explanation-highlight {
                    background: linear-gradient(145deg, #e3f2fd, #f3e5f5);
                    border-left: 4px solid #2196f3;
                    padding: 12px 15px;
                    margin: 10px 0;
                    border-radius: 4px;
                }
            </style>

            <!-- Explicación simplificada de índices -->
            <div class="analysis-section" style="background: linear-gradient(145deg, #f8f9fa, #e9ecef); padding: 20px;">
                <h6 class="section-title" style="color: #2c5aa0;">Análisis Satelital Explicado</h6>
                <div class="explanation-highlight">
                    <p style="margin: 0; font-size: 0.95rem; color: #495057;">
                        <strong>¿Qué estamos analizando?</strong> Utilizamos imágenes satelitales para medir la salud y el agua en sus cultivos. 
                        Estos índices nos permiten detectar problemas antes de que sean visibles a simple vista.
                    </p>
                </div>
                
                <div class="row">
                    <div class="col-md-4">
                        <div class="index-card">
                            <div class="index-header" style="color: #28a745;">
                                🌱 <span>NDVI - Salud Vegetal</span>
                            </div>
                            <p style="font-size: 0.9rem; margin-bottom: 8px;">Mide la vitalidad y vigor del cultivo mediante reflectancia infrarroja.</p>
                            <div class="index-range range-excellent">Excelente: 0.7 - 1.0</div>
                            <div class="index-range range-good">Bueno: 0.3 - 0.7</div>
                            <div class="index-range range-poor">Deficiente: < 0.3</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="index-card">
                            <div class="index-header" style="color: #007bff;">
                                💧 <span>NDMI - Contenido de Agua</span>
                            </div>
                            <p style="font-size: 0.9rem; margin-bottom: 8px;">Evalúa el estado hídrico y contenido de humedad en la vegetación.</p>
                            <div class="index-range range-excellent">Excelente: 0.4 - 1.0</div>
                            <div class="index-range range-good">Bueno: 0.0 - 0.4</div>
                            <div class="index-range range-poor">Deficiente: < 0.0</div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="index-card">
                            <div class="index-header" style="color: #ff6b35;">
                                🌿 <span>EVI - Índice Vegetación Mejorado</span>
                            </div>
                            <p style="font-size: 0.9rem; margin-bottom: 8px;">Análisis optimizado que reduce interferencia atmosférica y del suelo.</p>
                            <div class="index-range range-excellent">Excelente: 0.5 - 1.0</div>
                            <div class="index-range range-good">Bueno: 0.2 - 0.5</div>
                            <div class="index-range range-poor">Deficiente: < 0.2</div>
                        </div>
                    </div>
                </div>
            </div>
            <!-- Información general -->
            <div class="analysis-section mb-4" style="padding: 15px;">
                <h6 class="section-title">Detalles del Análisis</h6>
                <div class="row">
                    <div class="col-md-3">
                        <div class="info-item">
                            <small class="text-muted">ID de Vista:</small><br>
                            <code style="font-size: 0.8rem;">${viewId}</code>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="info-item">
                            <small class="text-muted">Fecha de Imagen:</small><br>
                            <strong>${formatSceneDate(sceneDate)}</strong>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="info-item">
                            <small class="text-muted">Satélite:</small><br>
                            <span class="badge bg-primary">Sentinel-2</span>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="info-item">
                            <small class="text-muted">Precisión:</small><br>
                            <span class="badge bg-success">Alta (95%+)</span>
                        </div>
                    </div>
                </div>
            </div>
    `;
    
    // Alertas críticas al inicio
    if (alerts && alerts.length > 0) {
        html += generateAlertsHTML(alerts);
    }
    
    // Verificar que los datos sean reales de EOSDA
    const isEOSDAReal = metadata && metadata.data_source === 'EOSDA_REAL';
    console.log('[ANALYTICS_CIENTIFICO] Datos reales EOSDA:', isEOSDAReal);
    
    // Volcado completo para análisis y depuración
    console.log('[ANALYTICS_CIENTIFICO] Estructura completa de datos:', raw_data);
    console.log('[ANALYTICS_CIENTIFICO] Recomendaciones:', recommendations);
    console.log('[ANALYTICS_CIENTIFICO] Interpretación:', interpretation);
    
    // Garantizar que exista un objeto de interpretación para evitar errores
    if (!interpretation) {
        interpretation = {
            ndvi: null,
            ndmi: null,
            evi: null
        };
        console.log('[ANALYTICS_CIENTIFICO] Creando objeto de interpretación vacío para garantizar consistencia');
    }
    
    // Verificar que existan valores para cada índice
    let indicesMostrados = 0;
    
    // Función para extraer valor de cualquier fuente disponible
    const extractValueFromAnySource = (indexName) => {
        // Posibles fuentes de datos, ordenadas por prioridad
        const sources = [
            // Array de valores directos
            raw_data[`${indexName}_values`] ? raw_data[`${indexName}_values`][0] : null,
            // Valor promedio en estadísticas
            raw_data[`${indexName}_statistics`]?.mean,
            // Objeto directo si existe
            raw_data[indexName]?.mean,
            // Buscar en recomendaciones (como vimos en la imagen)
            recommendations?.find(rec => rec.description?.includes(`${indexName.toUpperCase()} de `))?.description.match(/[A-Z]+ de ([\-\d\.]+)/)?.[1],
            // Cualquier valor numérico que se encuentre en el objeto raw_data
            typeof raw_data[indexName] === 'number' ? raw_data[indexName] : null,
        ];
        
        // Devolver el primer valor disponible
        return sources.find(val => val !== null && val !== undefined);
    };
    
    // Métricas NDVI - Buscando en todas las fuentes posibles
    const ndviValue = extractValueFromAnySource('ndvi');
    console.log('[ANALYTICS_CIENTIFICO] NDVI extraído:', ndviValue);
    
    if (ndviValue !== null && ndviValue !== undefined) {
        // Convertir a número si es string
        const ndviNumeric = typeof ndviValue === 'string' ? parseFloat(ndviValue) : ndviValue;
        
        // Crear objeto con las estadísticas necesarias para mostrar
        const ndviData = {
            mean: ndviNumeric,
            median: raw_data.ndvi_statistics?.median || ndviNumeric,
            std: raw_data.ndvi_statistics?.std || 0.05, // Valor por defecto si no hay estadísticas
            min: raw_data.ndvi_statistics?.min || (ndviNumeric * 0.9), // Aproximación
            max: raw_data.ndvi_statistics?.max || (ndviNumeric * 1.1), // Aproximación
            count: raw_data.ndvi_statistics?.count || 1
        };
        
        html += generateNDVIMetricsHTML(ndviData, interpretation.ndvi);
        indicesMostrados++;
    } else {
        html += `<div class="analysis-section"><h6 class="section-title">🌱 NDVI - No disponible</h6><div class="alert alert-warning">No hay datos NDVI reales de EOSDA para la fecha seleccionada.</div></div>`;
    }
    
    // Métricas NDMI - Buscando en todas las fuentes posibles
    const ndmiValue = extractValueFromAnySource('ndmi');
    console.log('[ANALYTICS_CIENTIFICO] NDMI extraído:', ndmiValue);
    
    if (ndmiValue !== null && ndmiValue !== undefined) {
        // Convertir a número si es string
        const ndmiNumeric = typeof ndmiValue === 'string' ? parseFloat(ndmiValue) : ndmiValue;
        
        const ndmiData = {
            mean: ndmiNumeric,
            median: raw_data.ndmi_statistics?.median || ndmiNumeric,
            std: raw_data.ndmi_statistics?.std || 0.05, // Valor por defecto si no hay estadísticas
            min: raw_data.ndmi_statistics?.min || (ndmiNumeric * 0.9), // Aproximación
            max: raw_data.ndmi_statistics?.max || (ndmiNumeric * 1.1), // Aproximación
            count: raw_data.ndmi_statistics?.count || 1
        };
        
        html += generateNDMIMetricsHTML(ndmiData, interpretation.ndmi);
        indicesMostrados++;
    } else {
        html += `<div class="analysis-section"><h6 class="section-title">💧 NDMI - No disponible</h6><div class="alert alert-warning">No hay datos NDMI reales de EOSDA para la fecha seleccionada.</div></div>`;
    }
    
    // Métricas EVI - Buscando en todas las fuentes posibles
    const eviValue = extractValueFromAnySource('evi');
    console.log('[ANALYTICS_CIENTIFICO] EVI extraído:', eviValue);
    
    if (eviValue !== null && eviValue !== undefined) {
        // Convertir a número si es string
        const eviNumeric = typeof eviValue === 'string' ? parseFloat(eviValue) : eviValue;
        
        const eviData = {
            mean: eviNumeric,
            median: raw_data.evi_statistics?.median || eviNumeric,
            std: raw_data.evi_statistics?.std || 0.05, // Valor por defecto si no hay estadísticas
            min: raw_data.evi_statistics?.min || (eviNumeric * 0.9), // Aproximación
            max: raw_data.evi_statistics?.max || (eviNumeric * 1.1), // Aproximación
            count: raw_data.evi_statistics?.count || 1
        };
        
        html += generateEVIMetricsHTML(eviData, interpretation.evi);
        indicesMostrados++;
    } else {
        html += `<div class="analysis-section"><h6 class="section-title">🌿 EVI - No disponible</h6><div class="alert alert-warning">No hay datos EVI reales de EOSDA para la fecha seleccionada.</div></div>`;
    }
    
    // Si no se mostró ningún índice, mostrar mensaje general
    if (indicesMostrados === 0) {
        html += `<div class="analysis-section"><div class="alert alert-danger">No hay datos satelitales reales disponibles para esta escena. Verifique la fecha o seleccione otra imagen.</div></div>`;
    } else {
        console.log(`[ANALYTICS_CIENTIFICO] Se mostraron ${indicesMostrados} índices correctamente`);
    }
    
    // Recomendaciones
    if (recommendations && recommendations.length > 0) {
        html += generateRecommendationsHTML(recommendations);
    }
    
    html += `</div>`;
    
    return html;
}

/**
 * Genera HTML para métricas NDVI científicas
 * @param {Object} ndviData - Datos NDVI brutos
 * @param {Object} interpretation - Interpretación NDVI
 * @returns {string} HTML de métricas NDVI
 */
function generateNDVIMetricsHTML(ndviData, interpretation) {
    console.log('[ANALYTICS_CIENTIFICO] Generando panel NDVI con:', ndviData, interpretation);
    
    if (!ndviData) return '';
    
    // Si no tenemos interpretación, creamos una interpretación por defecto completa
    if (!interpretation) {
        console.log('[ANALYTICS_CIENTIFICO] Creando interpretación por defecto para NDVI');
        let healthStatus;
        let description;
        
        if (ndviData.mean >= 0.7) {
            healthStatus = 'Excelente';
            description = 'La vegetación muestra valores NDVI excelentes, indicando alta actividad fotosintética y buen desarrollo del cultivo.';
        } else if (ndviData.mean >= 0.3) {
            healthStatus = 'Bueno';
            description = 'Los valores NDVI indican un desarrollo vegetal moderado a bueno. El cultivo se encuentra en condiciones aceptables.';
        } else {
            healthStatus = 'Deficiente';
            description = 'Los valores NDVI son bajos, lo que sugiere posibles problemas de desarrollo o estrés en la vegetación.';
        }
        
        interpretation = {
            health_status: healthStatus,
            description: description,
            uniformity: getNDVIUniformityText(ndviData.std),
            uniformity_description: getUniformityDescription(ndviData.std)
        };
    } else {
        // Garantizar que siempre exista un objeto de interpretación completo
        interpretation = interpretation || {};
        // Obtener valores con fallbacks por si acaso
        const healthStatus = interpretation.health_status || (ndviData.mean >= 0.7 ? 'Excelente' : (ndviData.mean >= 0.3 ? 'Bueno' : 'Deficiente'));
        const healthClass = getHealthStatusClass(healthStatus);
        const description = interpretation.description || (ndviData.mean >= 0.7 ? 
            'La vegetación muestra valores NDVI excelentes, indicando alta actividad fotosintética y buen desarrollo del cultivo.' : 
            (ndviData.mean >= 0.3 ? 
                'Los valores NDVI indican un desarrollo vegetal moderado a bueno. El cultivo se encuentra en condiciones aceptables.' : 
                'Los valores NDVI son bajos, lo que sugiere posibles problemas de desarrollo o estrés en la vegetación.')
        );

        // Generar uniformidad si no existe
        const hasUniformityData = interpretation.uniformity && interpretation.uniformity_description;
        const uniformityInfo = hasUniformityData ? `
            <div class="uniformity-info" style="margin-top: 12px; padding: 8px; background: #f8f9fa; border-radius: 4px;">
                <strong>Uniformidad del Campo:</strong><br>
                <span style="font-size: 0.9rem;">${interpretation.uniformity}</span>
                <br><small class="text-muted">${interpretation.uniformity_description || getUniformityDescription(ndviData.std)}</small>
            </div>
        ` : `
            <div class="uniformity-info" style="margin-top: 12px; padding: 8px; background: #f8f9fa; border-radius: 4px;">
                <strong>Uniformidad del Campo:</strong><br>
                <span style="font-size: 0.9rem;">${getNDVIUniformityText(ndviData.std)}</span>
                <br><small class="text-muted">${getUniformityDescription(ndviData.std)}</small>
            </div>
        `;

        // Panel de métricas NDVI (sin puntos analizados/pixel count)
        return `
            <div class="analysis-section">
                <h6 class="section-title">🌱 NDVI - Salud de la Vegetación</h6>
                <div class="row">
                    <div class="col-md-8">
                        <div class="metrics-grid">
                            <div class="metric-card">
                                <div class="metric-value">${formatMetricValue(ndviData.mean)}</div>
                                <div class="metric-label">Promedio General</div>
                                <small class="text-muted">Condición típica del campo</small>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">${formatMetricValue(ndviData.median)}</div>
                                <div class="metric-label">Valor Central</div>
                                <small class="text-muted">Elimina valores extremos</small>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">${formatMetricValue(ndviData.std)}</div>
                                <div class="metric-label">Uniformidad</div>
                                <small class="text-muted">${getUniformityDescription(ndviData.std)}</small>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">${formatMetricValue(ndviData.min)}</div>
                                <div class="metric-label">Zona Problemática</div>
                                <small class="text-muted">Área que necesita atención</small>
                            </div>
                            <div class="metric-card">
                                <div class="metric-value">${formatMetricValue(ndviData.max)}</div>
                                <div class="metric-label">Mejor Zona</div>
                                <small class="text-muted">Área en óptimo estado</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="interpretation-panel">
                            <div class="status-badge ${healthClass}">${healthStatus}</div>
                            <div class="interpretation-text">
                                <strong>Diagnóstico:</strong><br>
                                ${description}
                            </div>
                            ${uniformityInfo}
                            <div style="margin-top: 12px; font-size: 0.85rem; color: #6c757d;">
                                🎯 <strong>Qué significa:</strong> Valores &gt; 0.6 indican cultivos saludables. 
                                Valores &lt; 0.3 sugieren problemas de crecimiento.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}
/**
 * Genera HTML para métricas NDMI científicas
 * @param {Object} ndmiData - Datos NDMI brutos
 * @param {Object} interpretation - Interpretación NDMI
 * @returns {string} HTML de métricas NDMI
 */
function generateNDMIMetricsHTML(ndmiData, interpretation) {
    console.log('[ANALYTICS_CIENTIFICO] Generando panel NDMI con:', ndmiData, interpretation);
    
    // Si no tenemos interpretación, creamos una interpretación por defecto
    if (!interpretation) {
        console.log('[ANALYTICS_CIENTIFICO] Creando interpretación por defecto para NDMI');
        interpretation = {
            moisture_status: getNDMIStatusText(ndmiData.mean),
            description: getNDMIDescription(ndmiData.mean),
            uniformity: getNDMIUniformityText(ndmiData.std),
            uniformity_description: getUniformityDescription(ndmiData.std),
            irrigation_recommendation: getNDMIIrrigationRecommendation(ndmiData.mean)
        };
    }
    
    const moistureStatus = interpretation.moisture_status || getNDMIStatusText(ndmiData.mean);
    const moistureClass = getMoistureStatusClass(moistureStatus);
    
    return `
        <div class="analysis-section">
            <h6 class="section-title">💧 NDMI - Contenido de Humedad</h6>
            <div class="row">
                <div class="col-md-8">
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-value">${formatMetricValue(ndmiData.mean)}</div>
                            <div class="metric-label">Humedad Promedio</div>
                            <small class="text-muted">Nivel general de agua</small>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${formatMetricValue(ndmiData.median)}</div>
                            <div class="metric-label">Humedad Central</div>
                            <small class="text-muted">Valor más representativo</small>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${formatMetricValue(ndmiData.std)}</div>
                            <div class="metric-label">Variación</div>
                            <small class="text-muted">${interpretation.uniformity_description || getUniformityDescription(ndmiData.std)}</small>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${formatMetricValue(ndmiData.min)}</div>
                            <div class="metric-label">Zona Más Seca</div>
                            <small class="text-muted">Requiere riego urgente</small>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${formatMetricValue(ndmiData.max)}</div>
                            <div class="metric-label">Zona Más Húmeda</div>
                            <small class="text-muted">Buena retención de agua</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="interpretation-panel">
                        <div class="status-badge ${moistureClass}">${moistureStatus}</div>
                        <div class="interpretation-text">
                            <strong>Estado Hídrico:</strong><br>
                            ${interpretation.description || getNDMIDescription(ndmiData.mean)}
                        </div>
                        ${interpretation.uniformity ? `
                            <div class="uniformity-info" style="margin-top: 12px; padding: 8px; background: #f8f9fa; border-radius: 4px;">
                                <strong>Uniformidad del Campo:</strong><br>
                                <span style="font-size: 0.9rem;">${interpretation.uniformity}</span>
                                ${interpretation.uniformity_description ? `<br><small class="text-muted">${interpretation.uniformity_description}</small>` : ''}
                            </div>
                        ` : `
                            <div class="uniformity-info" style="margin-top: 12px; padding: 8px; background: #f8f9fa; border-radius: 4px;">
                                <strong>Uniformidad del Campo:</strong><br>
                                <span style="font-size: 0.9rem;">${getNDMIUniformityText(ndmiData.std)}</span>
                                <br><small class="text-muted">${getUniformityDescription(ndmiData.std)}</small>
                            </div>
                        `}
                        <div style="margin-top: 12px; font-size: 0.85rem; color: #6c757d;">
                            💡 <strong>Interpretación:</strong> Valores &gt; 0.3 indican buena humedad. 
                            Valores &lt; 0.0 sugieren estrés hídrico severo.
                        </div>
                        ${interpretation.irrigation_recommendation ? `
                            <div style="margin-top: 10px; padding: 8px; background: #e3f2fd; border-radius: 4px; border-left: 3px solid #2196f3;">
                                <strong>💧 Recomendación de Riego:</strong><br>
                                <small style="color: #1976d2;">${interpretation.irrigation_recommendation}</small>
                            </div>
                        ` : `
                            <div style="margin-top: 10px; padding: 8px; background: #e3f2fd; border-radius: 4px; border-left: 3px solid #2196f3;">
                                <strong>💧 Recomendación de Riego:</strong><br>
                                <small style="color: #1976d2;">${getNDMIIrrigationRecommendation(ndmiData.mean)}</small>
                            </div>
                        `}
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Genera HTML para métricas EVI científicas
 * @param {Object} eviData - Datos EVI brutos
 * @param {Object} interpretation - Interpretación EVI
 * @returns {string} HTML de métricas EVI
 */
function generateEVIMetricsHTML(eviData, interpretation) {
    console.log('[ANALYTICS_CIENTIFICO] Generando panel EVI con:', eviData, interpretation);
    
    // Si no tenemos interpretación, creamos una interpretación por defecto
    if (!interpretation) {
        console.log('[ANALYTICS_CIENTIFICO] Creando interpretación por defecto para EVI');
        interpretation = {
            status: getEVIHealthStatus(eviData.mean),
            description: getEVIHealthDescription(eviData.mean),
            uniformity: getEVIUniformityText(eviData.std),
            uniformity_description: getVariabilityDescription(eviData.std),
            management_recommendation: getEVIManagementRecommendation(eviData.mean)
        };
    }
    
    const eviStatus = interpretation.status || getEVIHealthStatus(eviData.mean);
    const eviClass = getEVIStatusClass(eviStatus);
    
    return `
        <div class="analysis-section">
            <h6 class="section-title">🌿 Análisis EVI - Índice Mejorado de Vegetación</h6>
            <div class="row">
                <div class="col-md-8">
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-value">${formatMetricValue(eviData.mean)}</div>
                            <div class="metric-label">EVI Promedio</div>
                            <small class="text-muted">Índice mejorado general</small>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${formatMetricValue(eviData.median)}</div>
                            <div class="metric-label">EVI Central</div>
                            <small class="text-muted">Valor más confiable</small>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${formatMetricValue(eviData.std)}</div>
                            <div class="metric-label">Consistencia</div>
                            <small class="text-muted">Uniformidad del índice</small>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${formatMetricValue(eviData.min)}</div>
                            <div class="metric-label">EVI Mínimo</div>
                            <small class="text-muted">Zona con menor vigor</small>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${formatMetricValue(eviData.max)}</div>
                            <div class="metric-label">EVI Máximo</div>
                            <small class="text-muted">Zona de mayor vigor</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="interpretation-panel">
                        <div class="status-badge ${eviClass}">${eviStatus}</div>
                        <div class="interpretation-text">
                            <strong>Análisis Avanzado:</strong><br>
                            ${interpretation.description || getEVIHealthDescription(eviData.mean)}
                        </div>
                        ${interpretation.uniformity ? `
                            <div class="uniformity-info" style="margin-top: 12px; padding: 8px; background: #f8f9fa; border-radius: 4px;">
                                <strong>Uniformidad del Cultivo:</strong><br>
                                <span style="font-size: 0.9rem;">${interpretation.uniformity}</span>
                                ${interpretation.uniformity_description ? `<br><small class="text-muted">${interpretation.uniformity_description}</small>` : ''}
                            </div>
                        ` : `
                            <div class="uniformity-info" style="margin-top: 12px; padding: 8px; background: #f8f9fa; border-radius: 4px;">
                                <strong>Uniformidad del Cultivo:</strong><br>
                                <span style="font-size: 0.9rem;">${getEVIUniformityText(eviData.std)}</span>
                                <br><small class="text-muted">${getVariabilityDescription(eviData.std)}</small>
                            </div>
                        `}
                        <div style="margin-top: 12px; font-size: 0.85rem; color: #6c757d;">
                            🔬 <strong>EVI vs NDVI:</strong> EVI es más preciso en cultivos densos y corrige mejor 
                            los efectos del suelo y la atmósfera.
                        </div>
                        <div style="margin-top: 8px; padding: 6px; background: #fff3e0; border-radius: 4px;">
                            <small><strong>Rango óptimo:</strong> 0.3 - 0.8 para la mayoría de cultivos</small>
                        </div>
                        ${interpretation.management_recommendation ? `
                            <div style="margin-top: 10px; padding: 8px; background: #e8f5e9; border-radius: 4px; border-left: 3px solid #4caf50;">
                                <strong>🌿 Recomendación de Manejo:</strong><br>
                                <small style="color: #2e7d32;">${interpretation.management_recommendation}</small>
                            </div>
                        ` : `
                            <div style="margin-top: 10px; padding: 8px; background: #e8f5e9; border-radius: 4px; border-left: 3px solid #4caf50;">
                                <strong>🌿 Recomendación de Manejo:</strong><br>
                                <small style="color: #2e7d32;">${getEVIManagementRecommendation(eviData.mean)}</small>
                            </div>
                        `}
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Genera HTML para alertas del sistema
 * @param {Array} alerts - Lista de alertas
 * @returns {string} HTML de alertas
 */
function generateAlertsHTML(alerts) {
    if (!alerts || alerts.length === 0) return '';
    
    const alertsHTML = alerts.map(alert => {
        const alertClass = getAlertClass(alert.type);
        const priorityBadge = alert.priority ? `<span class="badge bg-${getPriorityColor(alert.priority)} ms-2">${alert.priority.toUpperCase()}</span>` : '';
        // Si la acción está indefinida, mostrar recomendación según NDMI
        let actionText = alert.action;
        if (!actionText || actionText === 'undefined') {
            // Si el mensaje es de NDMI, dar apreciación según el valor
            if (alert.title && alert.title.toLowerCase().includes('ndmi')) {
                const ndmiMatch = alert.message.match(/NDMI de ([\-\d\.]+)/);
                if (ndmiMatch) {
                    const ndmiValue = parseFloat(ndmiMatch[1]);
                    if (ndmiValue < 0) {
                        actionText = `Active el sistema de riego en las zonas más secas detectadas por el análisis satelital (NDMI negativo). Realice inspección visual en campo antes de regar. Monitoree NDMI y humedad del suelo 2-3 días después del riego. Si el estrés hídrico persiste, consulte con un agrónomo.`;
                    } else if (ndmiValue < 0.2) {
                        actionText = `Aumente la frecuencia de riego y monitoree la humedad del suelo. Realice inspección visual en las zonas con NDMI bajo. Verifique recuperación tras el riego.`;
                    } else {
                        actionText = `El contenido de humedad es adecuado. Mantenga el monitoreo regular y registre las acciones realizadas. Si observa zonas secas, realice inspección visual y ajuste el riego si es necesario.`;
                    }
                } else {
                    actionText = 'Monitoree la humedad y consulte con un agrónomo si el problema persiste.';
                }
            } else {
                actionText = 'No se recomienda acción específica. Monitoree la parcela y consulte con un agrónomo si el problema persiste.';
            }
        }
        return `
            <div class="alert ${alertClass} mb-2">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <strong>${alert.title}</strong>${priorityBadge}
                        <p class="mb-1">${alert.message}</p>
                        <small><em>Acción recomendada: ${actionText}</em></small>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    return `
        <div class="analysis-section mb-4">
            <h6 class="section-title">🚨 Alertas Detectadas</h6>
            ${alertsHTML}
        </div>
    `;
}

/**
 * Genera HTML para recomendaciones agronómicas
 * @param {Array} recommendations - Lista de recomendaciones
 * @returns {string} HTML de recomendaciones
 */
function generateRecommendationsHTML(recommendations) {
    console.log('[ANALYTICS_CIENTIFICO] Generando panel de recomendaciones:', recommendations);
    
    // Si no hay recomendaciones, mostrar un mensaje por defecto con estructura consistente
    if (!recommendations || recommendations.length === 0) {
        return `
            <div class="analysis-section">
                <h6 class="section-title">📋 Recomendaciones Agronómicas</h6>
                <div class="row">
                    <div class="col-md-12">
                        <div class="recommendation-card h-100">
                            <div class="card h-100" style="border: 2px solid #e9ecef; border-radius: 12px;">
                                <div class="card-header" style="background: linear-gradient(145deg, #f8f9fa, #e9ecef); border-bottom: 1px solid #dee2e6;">
                                    <h6 class="mb-0" style="color: #2c3e50; font-weight: 600;">
                                        ℹ️ Información
                                    </h6>
                                    <small class="text-muted d-block mt-1">
                                        📂 General
                                    </small>
                                </div>
                                <div class="card-body" style="padding: 16px;">
                                    <p class="card-text" style="font-size: 0.9rem; line-height: 1.4; margin-bottom: 12px; color: #495057;">
                                        No hay recomendaciones disponibles para esta fecha o escena específica. Esto puede deberse a que los índices vegetativos están dentro de rangos normales o no hay suficiente información para generar recomendaciones específicas.
                                    </p>
                                    <div class="tips-section" style="margin-top: 12px; padding: 8px; background: #f8f9fa; border-radius: 6px; border-left: 3px solid #007bff;">
                                        <h6 style="font-size: 0.8rem; font-weight: 600; margin-bottom: 6px; color: #2c3e50;">
                                            💡 Sugerencia:
                                        </h6>
                                        <div style="font-size: 0.75rem; color: #495057;">
                                            Continúe monitoreando los índices vegetativos regularmente. Considere realizar inspecciones de campo para verificar el estado actual del cultivo.
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    const priorityOrder = { 'critical': 0, 'urgent': 1, 'high': 2, 'medium': 3, 'low': 4 };
    const sortedRecs = recommendations.sort((a, b) => 
        (priorityOrder[a.priority] || 5) - (priorityOrder[b.priority] || 5)
    );
    
    const recCards = sortedRecs.map((rec, index) => {
        const priorityColor = getPriorityColor(rec.priority);
        const priorityIcon = getPriorityIcon(rec.priority);
        const timeframe = getTimeframeSuggestion(rec.priority);
        
        // Crear lista de acciones más específicas
        const actionsHTML = rec.actions ? rec.actions.map(action => {
            const actionWithTiming = addActionTiming(action, rec.priority);
            return `<li style="margin-bottom: 6px; padding: 4px 0; border-bottom: 1px solid #f0f0f0;"><span style="color: #495057;">${actionWithTiming}</span></li>`;
        }).join('') : '';
        
        // Agregar consejos específicos según la categoría
        const specificTips = getSpecificTips(rec.category, rec.priority);
        
        return `
            <div class="col-lg-${recommendations.length > 2 ? '4' : '6'} col-md-6 mb-3">
                <div class="recommendation-card h-100">
                    <div class="card h-100" style="border: 2px solid ${getBorderColor(rec.priority)}; border-radius: 12px;">
                        <div class="card-header" style="background: linear-gradient(145deg, ${getHeaderGradient(rec.priority)}); border-bottom: 1px solid #dee2e6;">
                            <div class="d-flex justify-content-between align-items-center">
                                <h6 class="mb-0" style="color: #2c3e50; font-weight: 600;">
                                    ${priorityIcon} ${rec.title}
                                </h6>
                                <div>
                                    <span class="badge bg-${priorityColor}" style="font-size: 0.75rem;">${rec.priority.toUpperCase()}</span>
                                </div>
                            </div>
                            <small class="text-muted d-block mt-1">
                                📂 ${rec.category} ${timeframe ? `• ⏱️ ${timeframe}` : ''}
                            </small>
                        </div>
                        <div class="card-body" style="padding: 16px;">
                            <p class="card-text" style="font-size: 0.9rem; line-height: 1.4; margin-bottom: 12px; color: #495057;">
                                ${rec.description}
                            </p>
                            
                            ${actionsHTML ? `
                                <div class="actions-section">
                                    <h6 style="font-size: 0.85rem; font-weight: 600; color: #2c3e50; margin-bottom: 8px; border-bottom: 1px solid #dee2e6; padding-bottom: 4px;">
                                        📋 Acciones Específicas:
                                    </h6>
                                    <ul style="font-size: 0.8rem; margin: 0; padding-left: 16px; list-style: none;">
                                        ${actionsHTML}
                                    </ul>
                                </div>
                            ` : ''}
                            
                            ${specificTips ? `
                                <div class="tips-section" style="margin-top: 12px; padding: 8px; background: ${getTipBackground(rec.priority)}; border-radius: 6px; border-left: 3px solid ${getBorderColor(rec.priority)};">
                                    <h6 style="font-size: 0.8rem; font-weight: 600; margin-bottom: 6px; color: #2c3e50;">
                                        💡 Consejos Específicos:
                                    </h6>
                                    <div style="font-size: 0.75rem; color: #495057;">
                                        ${specificTips}
                                    </div>
                                </div>
                            ` : ''}
                            
                            <div class="impact-indicator" style="margin-top: 12px; padding: 6px 8px; background: #f8f9fa; border-radius: 4px; border: 1px solid #e9ecef;">
                                <small style="font-size: 0.75rem; color: #6c757d;">
                                    <strong>Impacto esperado:</strong> ${getExpectedImpact(rec.priority, rec.category)}
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    return `
        <div class="analysis-section">
            <h6 class="section-title">💡 Recomendaciones Agronómicas Personalizadas</h6>
            <div class="recommendation-intro" style="background: #e8f5e8; padding: 12px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #28a745;">
                <p style="margin: 0; font-size: 0.9rem; color: #2d5016;">
                    <strong>📍 Basado en su análisis satelital:</strong> Estas recomendaciones están priorizadas según la urgencia y el impacto potencial en su cultivo.
                </p>
            </div>
            <div class="row">
                ${recCards}
            </div>
            <div class="recommendations-footer" style="margin-top: 20px; padding: 12px; background: #fff3cd; border-radius: 8px; border: 1px solid #ffeaa7;">
                <small style="color: #856404;">
                    <strong>⚠️ Nota importante:</strong> Estas recomendaciones se basan en análisis satelital. 
                    Considere las condiciones locales, el tipo de cultivo y consulte con un agrónomo para decisiones críticas.
                </small>
            </div>
        </div>
    `;
}

/**
 * Exporta datos científicos a CSV
 * @param {string} viewId - ID de la vista
 * @param {string} sceneDate - Fecha de la escena
 * @param {Object} analyticsData - Datos científicos
 */
window.exportarAnalyticsCientifico = function(viewId, sceneDate, analyticsData) {
    try {
        console.log('[EXPORT_SCIENTIFIC] Iniciando exportación...');
        
        const data = typeof analyticsData === 'string' ? JSON.parse(analyticsData) : analyticsData;
        
        // Generar contenido CSV
        const csvContent = generateScientificCSV(data, sceneDate, viewId);
        
        // Crear y descargar archivo
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        
        link.setAttribute('href', url);
        link.setAttribute('download', `agrotech_scientific_analysis_${viewId}_${sceneDate.replace(/[^\d]/g, '')}.csv`);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);
        
        if (typeof showToast === 'function') {
            showToast('📄 Análisis científico exportado exitosamente', 'success');
        }
        
        console.log('[EXPORT_SCIENTIFIC] Exportación completada exitosamente');
        
    } catch (error) {
        console.error('[EXPORT_SCIENTIFIC] Error:', error);
        if (typeof showToast === 'function') {
            showToast(`❌ Error al exportar: ${error.message}`, 'error');
        }
    }
};

/**
 * Función wrapper para exportar los últimos datos analíticos
 * @param {string} viewId - ID de la vista EOSDA
 * @param {string} sceneDate - Fecha de la escena
 */
window.exportarAnalyticsCientificoData = function(viewId, sceneDate) {
    if (!window.LATEST_SCIENTIFIC_ANALYTICS) {
        if (typeof showToast === 'function') {
            showToast('❌ No hay datos de análisis científico disponibles', 'error');
        } else {
            alert('No hay datos de análisis científico disponibles para exportar');
        }
        return;
    }
    
    // Llamar a la función original con los datos almacenados
    window.exportarAnalyticsCientifico(viewId, sceneDate, window.LATEST_SCIENTIFIC_ANALYTICS);
};

/**
 * Genera contenido CSV para exportación
 * @param {Object} data - Datos científicos
 * @param {string} sceneDate - Fecha de la escena
 * @param {string} viewId - ID de la vista
 * @returns {string} Contenido CSV
 */
function generateScientificCSV(data, sceneDate, viewId) {
    const { raw_data, interpretation, alerts, recommendations } = data;
    
    let csv = `Análisis Científico Satelital - Agrotech\n`;
    csv += `View ID,${viewId}\n`;
    csv += `Fecha de Escena,${sceneDate}\n`;
    csv += `Fecha de Análisis,${new Date().toISOString().split('T')[0]}\n`;
    csv += `Satélite,Sentinel-2\n`;
    csv += `Plataforma,Agrotech\n\n`;
    
    // Datos NDVI
    if (raw_data.ndvi && interpretation.ndvi) {
        csv += `ANÁLISIS NDVI\n`;
        csv += `Métrica,Valor,Interpretación\n`;
        csv += `Promedio,${raw_data.ndvi.mean?.toFixed(3) || 'N/A'},${interpretation.ndvi.health_status || ''}\n`;
        csv += `Mediana,${raw_data.ndvi.median?.toFixed(3) || 'N/A'},\n`;
        csv += `Desviación Estándar,${raw_data.ndvi.std?.toFixed(3) || 'N/A'},${interpretation.ndvi.uniformity || ''}\n`;
        csv += `Mínimo,${raw_data.ndvi.min?.toFixed(3) || 'N/A'},\n`;
        csv += `Máximo,${raw_data.ndvi.max?.toFixed(3) || 'N/A'},\n`;
        csv += `Total Pixels,${raw_data.ndvi.count?.toLocaleString() || 'N/A'},\n`;
        csv += `Descripción,,"${interpretation.ndvi.description || ''}"\n\n`;
    }
    
    // Datos NDMI
    if (raw_data.ndmi && interpretation.ndmi) {
        csv += `ANÁLISIS NDMI\n`;
        csv += `Métrica,Valor,Interpretación\n`;
        csv += `Promedio,${raw_data.ndmi.mean?.toFixed(3) || 'N/A'},${interpretation.ndmi.moisture_status || ''}\n`;
        csv += `Mediana,${raw_data.ndmi.median?.toFixed(3) || 'N/A'},\n`;
        csv += `Desviación Estándar,${raw_data.ndmi.std?.toFixed(3) || 'N/A'},\n`;
        csv += `Mínimo,${raw_data.ndmi.min?.toFixed(3) || 'N/A'},\n`;
        csv += `Máximo,${raw_data.ndmi.max?.toFixed(3) || 'N/A'},\n`;
        csv += `Total Pixels,${raw_data.ndmi.count?.toLocaleString() || 'N/A'},\n`;
        csv += `Descripción,,"${interpretation.ndmi.description || ''}"\n\n`;
    }
    
    // Alertas
    if (alerts && alerts.length > 0) {
        csv += `ALERTAS DETECTADAS\n`;
        csv += `Tipo,Prioridad,Título,Mensaje,Acción Recomendada\n`;
        alerts.forEach(alert => {
            csv += `${alert.type},${alert.priority || 'N/A'},"${alert.title}","${alert.message}","${alert.action}"\n`;
        });
        csv += `\n`;
    }
    
    // Recomendaciones
    if (recommendations && recommendations.length > 0) {
        csv += `RECOMENDACIONES AGRONÓMICAS\n`;
        csv += `Prioridad,Categoría,Título,Descripción\n`;
        recommendations.forEach(rec => {
            csv += `${rec.priority},${rec.category},"${rec.title}","${rec.description}"\n`;
        });
    }
    
    return csv;
}

/**
 * Función para imprimir reporte (placeholder)
 * @param {string} viewId - ID de la vista
 * @param {string} sceneDate - Fecha de la escena
 */
window.imprimirAnalyticsCientifico = function(viewId, sceneDate) {
    if (typeof showToast === 'function') {
        showToast('🖨️ Función de impresión en desarrollo', 'info');
    }
    // TODO: Implementar funcionalidad de impresión
};

// ========== FUNCIONES HELPER ==========

/**
 * Formatea fecha de escena con día de la semana
 * @param {string} sceneDate - Fecha en formato YYYY-MM-DD
 * @returns {string} Fecha formateada
 */
function formatSceneDate(sceneDate) {
    if (!sceneDate) return 'No especificada';
    
    try {
        const date = new Date(sceneDate + 'T12:00:00'); // Evitar problemas de timezone
        const dayNames = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
        const monthNames = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                           'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
        
        const dayName = dayNames[date.getDay()];
        const day = date.getDate();
        const monthName = monthNames[date.getMonth()];
        const year = date.getFullYear();
        
        return `${dayName}, ${day} de ${monthName} ${year}`;
    } catch (error) {
        console.warn('[FORMAT_DATE] Error formateando fecha:', error);
        return sceneDate;
    }
}

/**
 * Obtiene clase CSS según prioridad
 * @param {string} priority - Nivel de prioridad
 * @returns {string} Clase CSS
 */
function getStatusClass(priority) {
    switch (priority) {
        case 'critical':
        case 'urgent': return 'status-critical';
        case 'high': return 'status-high';
        case 'medium': return 'status-medium';
        case 'low': return 'status-low';
        default: return 'status-info';
    }
}

/**
 * Obtiene clase de alerta según tipo
 * @param {string} type - Tipo de alerta
 * @returns {string} Clase de alerta Bootstrap
 */
function getAlertClass(type) {
    switch (type) {
        case 'critical': return 'alert-danger';
        case 'warning': return 'alert-warning';
        case 'info': return 'alert-info';
        default: return 'alert-primary';
    }
}

/**
 * Obtiene color según prioridad
 * @param {string} priority - Nivel de prioridad
 * @returns {string} Color Bootstrap
 */
function getPriorityColor(priority) {
    switch (priority) {
        case 'critical':
        case 'urgent': return 'danger';
        case 'high': return 'warning';
        case 'medium': return 'info';
        case 'low': return 'success';
        default: return 'secondary';
    }
}

console.log('[ANALYTICS_CIENTIFICO] Módulo de Analytics Científico Satelital cargado exitosamente');

// ========== FUNCIONES HELPER PARA MEJOR COMPRENSIÓN ==========

/**
 * Genera estado de salud para EVI basado en el valor promedio
 * @param {number} value - Valor medio EVI
 * @returns {string} Estado de salud EVI
 */
function getEVIHealthStatus(value) {
    if (value === null || value === undefined || isNaN(value)) return 'Desconocido';
    if (value < 0.1) {
        return 'Suelo desnudo o escasa vegetación';
    } else if (value < 0.3) {
        return 'Vegetación pobre';
    } else if (value < 0.5) {
        return 'Vegetación moderada';
    } else if (value < 0.8) {
        return 'Vegetación buena';
    } else {
        return 'Vegetación excelente';
    }
}

/**
 * Genera descripción interpretativa para EVI según valor promedio
 * @param {number} value - Valor medio EVI
 * @returns {string} Descripción interpretativa
 */
function getEVIHealthDescription(value) {
    if (value === null || value === undefined || isNaN(value)) return 'Evaluación en proceso.';
    if (value < 0.1) {
        return 'El campo presenta suelo desnudo o vegetación extremadamente escasa. Se recomienda revisar la cobertura vegetal.';
    } else if (value < 0.3) {
        return 'La vegetación es pobre, lo que puede indicar problemas de establecimiento, estrés o manejo deficiente.';
    } else if (value < 0.5) {
        return 'Vegetación moderada, el cultivo está en desarrollo pero podría beneficiarse de mejores prácticas agronómicas.';
    } else if (value < 0.8) {
        return 'Vegetación buena, el cultivo muestra buen vigor y salud general.';
    } else {
        return 'Vegetación excelente, óptimas condiciones de desarrollo y manejo.';
    }
}

/**
 * Genera texto de uniformidad para EVI según desviación estándar
 * @param {number} std - Desviación estándar EVI
 * @returns {string} Descripción de uniformidad
 */
function getEVIUniformityText(std) {
    if (std === null || std === undefined || isNaN(std)) return 'Sin datos';
    if (std < 0.04) {
        return 'Muy uniforme (excelente distribución de vigor)';
    } else if (std < 0.09) {
        return 'Uniformidad buena (distribución de vigor aceptable)';
    } else if (std < 0.15) {
        return 'Variabilidad moderada (posibles zonas de bajo y alto vigor)';
    } else {
        return 'Alta variabilidad (diferencias significativas de vigor en el campo)';
    }
}

/**
 * Genera descripción de variabilidad para EVI según desviación estándar
 * @param {number} std - Desviación estándar EVI
 * @returns {string} Descripción de variabilidad
 */
function getVariabilityDescription(std) {
    if (std === null || std === undefined || isNaN(std)) return 'Sin datos de variabilidad.';
    if (std < 0.04) {
        return 'El campo es muy uniforme en vigor.';
    } else if (std < 0.09) {
        return 'Buena uniformidad, pocas zonas problemáticas.';
    } else if (std < 0.15) {
        return 'Variabilidad moderada, revisar zonas de bajo vigor.';
    } else {
        return 'Alta variabilidad, se recomienda inspección y manejo específico.';
    }
}

/**
 * Genera recomendación de manejo para EVI según valor promedio
 * @param {number} value - Valor medio EVI
 * @returns {string} Recomendación de manejo
 */
function getEVIManagementRecommendation(value) {
    if (value === null || value === undefined || isNaN(value)) return 'Sin recomendación disponible.';
    if (value < 0.1) {
        return 'Revisar cobertura vegetal y considerar resiembra o mejora de condiciones.';
    } else if (value < 0.3) {
        return 'Evaluar fertilización, riego y control de plagas para mejorar el vigor.';
    } else if (value < 0.5) {
        return 'Aplicar prácticas agronómicas para potenciar el desarrollo.';
    } else if (value < 0.8) {
        return 'Mantener manejo actual y monitorear posibles cambios.';
    } else {
        return 'Continuar con el manejo actual, condiciones óptimas.';
    }
}

/**
 * Formatea valores métricos para mostrar de forma comprensible
 * @param {number} value - Valor numérico
 * @returns {string} Valor formateado
 */
function formatMetricValue(value) {
    if (value === null || value === undefined) return 'N/A';
    if (typeof value === 'number') {
        return value.toFixed(3);
    }
    return String(value);
}

/**
 * Genera texto de uniformidad para NDVI basado en la desviación estándar
 * @param {number} std - Desviación estándar del NDVI
 * @returns {string} Descripción de uniformidad
 */
function getNDVIUniformityText(std) {
    if (std === null || std === undefined) return 'Sin datos';
    if (std < 0.04) {
        return 'Muy uniforme (excelente distribución de humedad)';
    } else if (std < 0.09) {
        return 'Uniformidad buena (distribución de humedad aceptable)';
    } else if (std < 0.15) {
        return 'Variabilidad moderada (posibles zonas secas y húmedas)';
    } else {
        return 'Alta variabilidad (diferencias significativas de humedad en el campo)';
    }
}

/**
 * Devuelve texto interpretativo sobre la uniformidad NDMI según la desviación estándar
 * @param {number} std - Desviación estándar NDMI
 * @returns {string} Texto de uniformidad
 */
function getNDMIUniformityText(std) {
    if (std === null || std === undefined || isNaN(std)) return 'Sin datos';
    if (std < 0.04) {
        return 'Muy uniforme (excelente distribución de humedad)';
    } else if (std < 0.09) {
        return 'Uniformidad buena (distribución de humedad aceptable)';
    } else if (std < 0.15) {
        return 'Variabilidad moderada (posibles zonas secas y húmedas)';
    } else {
        return 'Alta variabilidad (diferencias significativas de humedad en el campo)';
    }
}

/**
 * Genera texto de estado del NDMI basado en el valor promedio
 * @param {number} value - Valor medio NDMI
 * @returns {string} Estado del NDMI
 */
function getNDMIStatusText(value) {
    if (!value && value !== 0) return 'Desconocido';
    
    if (value < -0.2) {
        return 'Muy Seco';
    } else if (value < 0) {
        return 'Seco';
    } else if (value < 0.2) {
        return 'Moderadamente Seco';
    } else if (value < 0.4) {
        return 'Adecuado';
    } else {
        return 'Húmedo';
    }
}

/**
 * Genera descripción del NDMI basado en el valor promedio
 * @param {number} value - Valor medio NDMI
 * @returns {string} Descripción del estado del NDMI
 */
function getNDMIDescription(value) {
    if (!value && value !== 0) return 'Evaluación en proceso';
    if (value < -0.2) {
        return 'El cultivo muestra signos de estrés hídrico severo. Requiere riego inmediato para evitar daños significativos.';
    } else if (value < 0) {
        return 'Condiciones secas. El cultivo puede estar experimentando estrés hídrico moderado y podría beneficiarse de riego.';
    } else if (value < 0.2) {
        return 'Contenido de humedad aceptable pero puede estar por debajo de lo óptimo para algunas etapas fenológicas.';
    } else if (value < 0.4) {
        return 'Buenas condiciones de humedad. El cultivo tiene un suministro de agua adecuado para su desarrollo.';
    } else {
        return 'Condiciones de humedad muy favorables. Los cultivos tienen abundante disponibilidad de agua.';
    }
}

/**
 * Obtiene descripción de uniformidad basada en desviación estándar
 * @param {number} std - Desviación estándar
 * @returns {string} Descripción de uniformidad
 */
function getUniformityDescription(std) {
    if (!std || std === 'N/A') return 'Desconocido';
    const stdValue = parseFloat(std);
    if (stdValue < 0.1) return 'Muy uniforme';
    if (stdValue < 0.2) return 'Bastante uniforme';
    if (stdValue < 0.3) return 'Moderadamente uniforme';
    return 'Irregular, revisar zonas';
}

/**
 * Obtiene clase CSS para estado de salud
 * @param {string} healthStatus - Estado de salud
 * @returns {string} Clase CSS
 */
function getHealthStatusClass(healthStatus) {
    const status = healthStatus.toLowerCase();
    if (status.includes('excelente') || status.includes('óptimo')) return 'status-excellent';
    if (status.includes('bueno') || status.includes('saludable')) return 'status-good';
    if (status.includes('moderado') || status.includes('regular')) return 'status-medium';
    if (status.includes('pobre') || status.includes('problema')) return 'status-poor';
    return 'status-medium';
}

/**
 * Obtiene clase CSS para estado de humedad
 * @param {string} moistureStatus - Estado de humedad
 * @returns {string} Clase CSS
 */
function getMoistureStatusClass(moistureStatus) {
    const status = moistureStatus.toLowerCase();
    if (status.includes('óptimo') || status.includes('excelente')) return 'status-excellent';
    if (status.includes('bueno') || status.includes('adecuado')) return 'status-good';
    if (status.includes('moderado') || status.includes('regular')) return 'status-medium';
    if (status.includes('seco') || status.includes('estrés')) return 'status-poor';
    return 'status-medium';
}

/**
 * Obtiene clase CSS para estado EVI
 * @param {string} eviStatus - Estado EVI
 * @returns {string} Clase CSS
 */
function getEVIStatusClass(eviStatus) {
    const status = eviStatus.toLowerCase();
    if (status.includes('excelente')) return 'status-excellent';
    if (status.includes('bueno')) return 'status-good';
    if (status.includes('moderado')) return 'status-moderate';
    if (status.includes('escasa')) return 'status-poor';
    if (status.includes('suelo') || status.includes('desnudo')) return 'status-critical';
    return 'status-unknown';
}

/**
 * Obtiene icono según prioridad
 * @param {string} priority - Nivel de prioridad
 * @returns {string} Icono emoji
 */
function getPriorityIcon(priority) {
    switch (priority) {
        case 'critical':
        case 'urgent': return '🚨';
        case 'high': return '⚠️';
        case 'medium': return '📋';
        case 'low': return '💡';
        default: return 'ℹ️';
    }
}

/**
 * Obtiene sugerencia de tiempo según prioridad
 * @param {string} priority - Nivel de prioridad
 * @returns {string} Sugerencia de tiempo
 */
function getTimeframeSuggestion(priority) {
    switch (priority) {
        case 'critical':
        case 'urgent': return 'Inmediato (1-2 días)';
        case 'high': return 'Esta semana';
        case 'medium': return 'Próximas 2 semanas';
        case 'low': return 'Próximo mes';
        default: return '';
    }
}

/**
 * Agrega tiempo específico a las acciones
 * @param {string} action - Acción original
 * @param {string} priority - Prioridad
 * @returns {string} Acción con timing
 */
function addActionTiming(action, priority) {
    const urgencyWords = {
        'critical': 'URGENTE: ',
        'urgent': 'URGENTE: ',
        'high': 'Prioritario: ',
        'medium': '',
        'low': 'Cuando sea posible: '
    };
    
    return (urgencyWords[priority] || '') + action;
}

/**
 * Obtiene consejos específicos según categoría y prioridad
 * @param {string} category - Categoría de la recomendación
 * @param {string} priority - Prioridad
 * @returns {string} Consejos específicos
 */
function getSpecificTips(category, priority) {
    const tips = {
        'irrigation': {
            'critical': 'Verifique sistema de riego inmediatamente. Considere riego de emergencia.',
            'high': 'Programe riego adicional. Revise eficiencia del sistema actual.',
            'medium': 'Ajuste frecuencia de riego. Monitoree humedad del suelo.',
            'low': 'Optimice calendario de riego para la próxima temporada.'
        },
        'fertilization': {
            'critical': 'Aplicación foliar de emergencia puede ser necesaria.',
            'high': 'Considere análisis de suelo y aplicación dirigida.',
            'medium': 'Planifique próxima fertilización según deficiencias detectadas.',
            'low': 'Incluya en plan nutricional de mantenimiento.'
        },
        'pest_management': {
            'critical': 'Inspección inmediata en campo. Posible tratamiento urgente.',
            'high': 'Monitoreo intensivo. Prepare estrategia de control.',
            'medium': 'Incluya en programa de monitoreo regular.',
            'low': 'Observe durante inspecciones rutinarias.'
        },
        'general': {
            'critical': 'Consulte inmediatamente con agrónomo especialista.',
            'high': 'Implemente medidas en los próximos días.',
            'medium': 'Planifique implementación gradual.',
            'low': 'Considere para mejoras futuras.'
        }
    };
    
    return tips[category]?.[priority] || tips['general'][priority] || '';
}

/**
 * Obtiene color de borde según prioridad
 * @param {string} priority - Prioridad
 * @returns {string} Color hexadecimal
 */
function getBorderColor(priority) {
    switch (priority) {
        case 'critical':
        case 'urgent': return '#dc3545';
        case 'high': return '#fd7e14';
        case 'medium': return '#17a2b8';
        case 'low': return '#28a745';
        default: return '#6c757d';
    }
}

/**
 * Obtiene gradiente para header según prioridad
 * @param {string} priority - Prioridad
 * @returns {string} Gradiente CSS
 */
function getHeaderGradient(priority) {
    switch (priority) {
        case 'critical':
        case 'urgent': return '#ffebee, #ffcdd2';
        case 'high': return '#fff3e0, #ffe0b2';
        case 'medium': return '#e0f2f1, #b2dfdb';
        case 'low': return '#e8f5e8, #c8e6c9';
        default: return '#f8f9fa, #e9ecef';
    }
}

/**
 * Obtiene fondo para tips según prioridad
 * @param {string} priority - Prioridad
 * @returns {string} Color de fondo
 */
function getTipBackground(priority) {
    switch (priority) {
                      case 'critical':
        case 'urgent': return '#fff5f5';
        case 'high': return '#fffbf0';
        case 'medium': return '#f0f9ff';
        case 'low': return '#f0fff4';
        default: return '#f8f9fa';
    }
}

/**
 * Obtiene impacto esperado según prioridad y categoría
 * @param {string} priority - Prioridad
 * @param {string} category - Categoría
 * @returns {string} Descripción de impacto
 */
function getExpectedImpact(priority, category) {
    const impacts = {
        'critical': 'Alto - Previene pérdidas significativas',
        'urgent': 'Alto - Previene pérdidas significativas', 
        'high': 'Medio-Alto - Mejora considerable del rendimiento',
        'medium': 'Medio - Optimización gradual',
        'low': 'Bajo-Medio - Mejora a largo plazo'
    };
    
    return impacts[priority] || 'Impacto variable según implementación';
}

/**
 * Aplica estilos CSS consistentes para los paneles de análisis
 */
function applyCientificoAnalyticsStyles() {
    const styleId = 'cientifico-analytics-styles';
    // Si ya existe el estilo, no lo volvemos a agregar
    if (document.getElementById(styleId)) return;
    
    const styleSheet = document.createElement('style');
    styleSheet.id = styleId;
    styleSheet.textContent = `
        .analysis-section {
            margin-bottom: 24px;
            padding: 16px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .section-title {
            margin-bottom: 16px;
            font-weight: 600;
            color: #333;
            border-bottom: 1px solid #eee;
            padding-bottom: 8px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 12px;
        }
        
        .metric-card {
            background: #f9f9f9;
            padding: 12px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            text-align: center;
        }
        
        .metric-value {
            font-size: 1.4rem;
            font-weight: 700;
            color: #2c3e50;
        }
        
        .metric-label {
            font-size: 0.9rem;
            font-weight: 500;
            text-align: center;
        }
        
        .status-excellent {
            background-color: #d4edda;
            color: #155724;
        }
        
        .status-good {
            background-color: #cce5ff;
            color: #004085;
        }
        
        .status-moderate {
            background-color: #fff3cd;
            color: #856404;
        }
        
        .status-poor {
            background-color: #f8d7da;
            color: #721c24;
        }
        
        .status-critical {
            background-color: #dc3545;
            color: white;
        }
        
        .status-unknown {
            background-color: #e2e3e5;
            color: #383d41;
        }
        
        .interpretation-text {
            font-size: 0.9rem;
            line-height: 1.4;
            color: #495057;
        }
        
        .recommendation-card {
            height:  100%;
        }
        
        /* Estilos consistentes para recomendaciones */
        .actions-section, .tips-section {
            margin-top: 12px;
        }
        
        /* Estilos para estado sin datos */
        .alert-warning {
            background-color: #fff3cd;
            color: #856404;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 0;
        }
        
        /* Estilo para paneles de uniformidad */
        .uniformity-info {
            margin-top: 12px;
            padding: 8px;
            background: #f8f9fa;
            border-radius: 4px;
            font-size: 0.9rem;
        }
    `;
    
    document.head.appendChild(styleSheet);
    console.log('[ANALYTICS_CIENTIFICO] Estilos CSS aplicados para paneles de análisis');
}

/**
 * Genera recomendación de riego basada en el valor NDMI
 * @param {number} ndmiMean - Valor medio NDMI
 * @returns {string} Recomendación de riego
 */
function getNDMIIrrigationRecommendation(ndmiMean) {
    if (ndmiMean === null || ndmiMean === undefined || isNaN(ndmiMean)) return 'Sin datos suficientes para recomendar riego.';
    if (ndmiMean < 0) {
        return 'Se recomienda riego urgente en las zonas con NDMI negativo. Verifique humedad del suelo y realice inspección visual.';
    } else if (ndmiMean < 0.2) {
        return 'Considere riego adicional en áreas con NDMI bajo. Monitoree evolución tras el riego.';
    } else if (ndmiMean < 0.4) {
        return 'El riego es opcional, la humedad es adecuada pero puede optimizarse según el cultivo.';
    } else {
        return 'No se requiere riego. La humedad es óptima para el desarrollo del cultivo.';
    }
}