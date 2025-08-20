/**
 * Analytics Científico EOSDA - Función independiente
 * Propósito: Obtener y mostrar datos científicos NDVI/NDMI sin afectar análisis visual
 * Autor: Sistema Agrotech
 * Fecha: 2025
 */

// Variable global para almacenar los últimos datos de análisis científico
window.LATEST_SCIENTIFIC_ANALYTICS = null;

/**
 * Función principal para obtener analytics científicos de EOSDA
 * @param {string} viewId - ID de la vista EOSDA
 * @param {string} sceneDate - Fecha de la escena (formato YYYY-MM-DD)
 * @returns {Promise<Object>} Datos científicos interpretados
 */
window.obtenerAnalyticsCientifico = async function(viewId, sceneDate) {
    try {
        console.log(`[ANALYTICS_CIENTIFICO] Iniciando análisis científico`);
        console.log(`[ANALYTICS_CIENTIFICO] View ID: ${viewId}, Fecha: ${sceneDate}`);
        
        // Validar parámetros
        if (!viewId) {
            throw new Error('View ID es requerido para análisis científico');
        }
        
        // Mostrar indicador de carga
        if (typeof showToast === 'function') {
            showToast('🔬 Obteniendo análisis científico EOSDA...', 'info');
        }
        
        // Verificar que axiosInstance esté disponible
        if (typeof window.axiosInstance === 'undefined') {
            throw new Error('Sistema de autenticación no inicializado');
        }
        
        // Construir parámetros de la consulta
        const params = new URLSearchParams({
            view_id: viewId
        });
        
        if (sceneDate) {
            params.append('scene_date', sceneDate);
        }
        
        console.log(`[ANALYTICS_CIENTIFICO] Llamando a: /eosda-analytics/?${params.toString()}`);
        
        // Llamada al endpoint de analytics científico usando axiosInstance
        const response = await window.axiosInstance.get(`/eosda-analytics/?${params.toString()}`);
        
        const analyticsData = response.data;
        
        console.log(`[ANALYTICS_CIENTIFICO] Datos obtenidos exitosamente:`, analyticsData);
        
        // Mostrar modal con análisis científico
        mostrarModalAnalyticsCientifico(analyticsData, sceneDate, viewId);
        
        if (typeof showToast === 'function') {
            showToast('✅ Análisis científico completado', 'success');
        }
        
        // Almacenar datos en variable global
        window.LATEST_SCIENTIFIC_ANALYTICS = analyticsData;
        
        return analyticsData;
        
    } catch (error) {
        console.error('[ANALYTICS_CIENTIFICO] Error:', error);
        
        if (typeof showToast === 'function') {
            showToast(`❌ Error en análisis científico: ${error.message}`, 'error');
        } else {
            alert(`Error en análisis científico: ${error.message}`);
        }
        
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
        // Fallback: mostrar como alert si Bootstrap no está disponible
        alert('Análisis científico completado. Ver consola para detalles.');
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
                            🔬 Análisis Científico EOSDA
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        ${generateScientificAnalysisHTML(analyticsData, sceneDate, viewId)}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-success" onclick="exportarAnalyticsCientificoData('${viewId}', '${sceneDate}')">
                            📥 Exportar Datos CSV
                        </button>
                        <button type="button" class="btn btn-info" onclick="imprimirAnalyticsCientifico('${viewId}', '${sceneDate}')">
                            🖨️ Imprimir Reporte
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
            <!-- Explicación de Índices Satelitales -->
            <div class="analysis-section mb-4" style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                <h6 class="section-title" style="color: #2c5aa0;">📚 ¿Qué significan estos análisis?</h6>
                <div class="row">
                    <div class="col-md-4">
                        <div class="index-explanation">
                            <h6 style="color: #28a745;">🌱 NDVI</h6>
                            <p><strong>Índice de Vegetación:</strong> Mide qué tan verde y saludable está su cultivo.</p>
                            <small><strong>Rango:</strong> -1 (sin vegetación) a +1 (vegetación muy densa)</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="index-explanation">
                            <h6 style="color: #007bff;">💧 NDMI</h6>
                            <p><strong>Índice de Humedad:</strong> Detecta si las plantas tienen suficiente agua.</p>
                            <small><strong>Rango:</strong> -1 (muy seco) a +1 (muy húmedo)</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="index-explanation">
                            <h6 style="color: #ff6b35;">🌿 EVI</h6>
                            <p><strong>Índice Mejorado:</strong> Versión más precisa del NDVI para zonas densas.</p>
                            <small><strong>Rango:</strong> 0 (sin vegetación) a +1 (vegetación óptima)</small>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Explicación de Términos Estadísticos -->
            <div class="analysis-section mb-4" style="background: #fff3cd; padding: 15px; border-radius: 8px;">
                <h6 class="section-title" style="color: #856404;">📈 ¿Qué significan las estadísticas?</h6>
                <div class="row">
                    <div class="col-md-6">
                        <ul style="font-size: 14px; margin: 0;">
                            <li><strong>Promedio:</strong> Valor típico en todo el campo</li>
                            <li><strong>Mediana:</strong> Valor del centro (elimina valores extremos)</li>
                            <li><strong>Mínimo/Máximo:</strong> Zonas con peor/mejor condición</li>
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <ul style="font-size: 14px; margin: 0;">
                            <li><strong>Desviación:</strong> Qué tan uniforme está el campo</li>
                            <li><strong>Píxeles:</strong> Puntos analizados (más = mayor precisión)</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <!-- Información general -->
            <div class="analysis-section mb-4">
                <h6 class="section-title">📊 Información General</h6>
                <div class="row">
                    <div class="col-md-3">
                        <div class="info-item">
                            <small class="text-muted">View ID:</small><br>
                            <code>${viewId}</code>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="info-item">
                            <small class="text-muted">Fecha de escena:</small><br>
                            <strong>${formatSceneDate(sceneDate)}</strong>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="info-item">
                            <small class="text-muted">Tipo de análisis:</small><br>
                            <span class="badge bg-primary">Científico EOSDA</span>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="info-item">
                            <small class="text-muted">Confiabilidad:</small><br>
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
    
    // Métricas NDVI
    if (raw_data.ndvi) {
        html += generateNDVIMetricsHTML(raw_data.ndvi, interpretation.ndvi);
    }
    
    // Métricas NDMI
    if (raw_data.ndmi) {
        html += generateNDMIMetricsHTML(raw_data.ndmi, interpretation.ndmi);
    }
    
    // Métricas EVI si están disponibles
    if (raw_data.evi) {
        html += generateEVIMetricsHTML(raw_data.evi, interpretation.evi);
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
    if (!ndviData || !interpretation) return '';
    
    const metrics = interpretation.metrics || {};
    
    return `
        <div class="analysis-section mb-4">
            <h6 class="section-title">🌱 Análisis NDVI (Índice de Vegetación)</h6>
            <div class="row">
                <div class="col-md-8">
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-value">${metrics.mean_value || 'N/A'}</div>
                            <div class="metric-label">Promedio</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${ndviData.median?.toFixed(3) || 'N/A'}</div>
                            <div class="metric-label">Mediana</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${metrics.variability || 'N/A'}</div>
                            <div class="metric-label">Desviación</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${metrics.min_value || 'N/A'}</div>
                            <div class="metric-label">Mínimo</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${metrics.max_value || 'N/A'}</div>
                            <div class="metric-label">Máximo</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${ndviData.count?.toLocaleString() || 'N/A'}</div>
                            <div class="metric-label">Pixels</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="interpretation-panel">
                        <div class="status-badge ${getStatusClass(interpretation.priority)}">${interpretation.health_status || ''}</div>
                        <p class="interpretation-text">${interpretation.description || ''}</p>
                        <div class="uniformity-info">
                            <strong>Uniformidad:</strong> ${interpretation.uniformity || ''}
                            <br><small class="text-muted">${interpretation.uniformity_description || ''}</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Genera HTML para métricas NDMI científicas
 * @param {Object} ndmiData - Datos NDMI brutos
 * @param {Object} interpretation - Interpretación NDMI
 * @returns {string} HTML de métricas NDMI
 */
function generateNDMIMetricsHTML(ndmiData, interpretation) {
    if (!ndmiData || !interpretation) return '';
    
    const metrics = interpretation.metrics || {};
    
    return `
        <div class="analysis-section mb-4">
            <h6 class="section-title">💧 Análisis NDMI (Índice de Humedad)</h6>
            <div class="row">
                <div class="col-md-8">
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-value">${metrics.mean_value || 'N/A'}</div>
                            <div class="metric-label">Promedio</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${ndmiData.median?.toFixed(3) || 'N/A'}</div>
                            <div class="metric-label">Mediana</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${metrics.variability || 'N/A'}</div>
                            <div class="metric-label">Desviación</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${metrics.min_value || 'N/A'}</div>
                            <div class="metric-label">Mínimo</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${metrics.max_value || 'N/A'}</div>
                            <div class="metric-label">Máximo</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">${ndmiData.count?.toLocaleString() || 'N/A'}</div>
                            <div class="metric-label">Pixels</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="interpretation-panel">
                        <div class="status-badge ${getStatusClass(interpretation.priority)}">${interpretation.moisture_status || ''}</div>
                        <p class="interpretation-text">${interpretation.description || ''}</p>
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
    if (!eviData || !interpretation) return '';
    
    return `
        <div class="analysis-section mb-4">
            <h6 class="section-title">🌿 Análisis EVI (Índice de Vegetación Mejorado)</h6>
            <div class="row">
                <div class="col-md-6">
                    <div class="metric-card">
                        <div class="metric-value">${interpretation.mean_value || 'N/A'}</div>
                        <div class="metric-label">EVI Promedio</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="interpretation-panel">
                        <div class="status-badge">${interpretation.status || ''}</div>
                        <p class="interpretation-text">${interpretation.description || ''}</p>
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
        
        return `
            <div class="alert ${alertClass} mb-2">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <strong>${alert.title}</strong>${priorityBadge}
                        <p class="mb-1">${alert.message}</p>
                        <small><em>Acción recomendada: ${alert.action}</em></small>
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
    if (!recommendations || recommendations.length === 0) return '';
    
    const recHTML = recommendations.map((rec, index) => {
        const priorityColor = getPriorityColor(rec.priority);
        const actionsHTML = rec.actions ? rec.actions.map(action => `<li>${action}</li>`).join('') : '';
        
        return `
            <div class="recommendation-card mb-3">
                <div class="card h-100">
                    <div class="card-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="mb-0">${rec.title}</h6>
                            <span class="badge bg-${priorityColor}">${rec.priority.toUpperCase()}</span>
                        </div>
                        <small class="text-muted">${rec.category}</small>
                    </div>
                    <div class="card-body">
                        <p class="card-text">${rec.description}</p>
                        ${actionsHTML ? `
                            <h6>Acciones recomendadas:</h6>
                            <ul class="list-unstyled">
                                ${actionsHTML}
                            </ul>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    return `
        <div class="analysis-section mb-4">
            <h6 class="section-title">💡 Recomendaciones Agronómicas</h6>
            <div class="row">
                ${recommendations.map((rec, index) => `
                    <div class="col-md-${recommendations.length > 2 ? '4' : '6'} mb-3">
                        ${recHTML}
                    </div>
                `).join('')}
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
    
    let csv = `Análisis Científico EOSDA\n`;
    csv += `View ID,${viewId}\n`;
    csv += `Fecha de Escena,${sceneDate}\n`;
    csv += `Fecha de Análisis,${new Date().toISOString().split('T')[0]}\n`;
    csv += `Tipo,Científico EOSDA\n\n`;
    
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

console.log('[ANALYTICS_CIENTIFICO] Módulo de Analytics Científico cargado exitosamente');
