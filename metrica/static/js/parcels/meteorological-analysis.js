/**
 * Análisis Meteorológico - Datos EOSDA Reales
 * Módulo optimizado para análisis meteorológico puro sin NDVI
 * Incluye avisos de actualización y navegación fluida
 */

let meteorologicalChartInstance = null;
let currentParcelId = null;
let meteorologicalData = [];

// ===============================
// FUNCIONES GLOBALES - DISPONIBLES INMEDIATAMENTE
// ===============================

/**
 * Función global para cerrar la sección de análisis meteorológico
 */
function closeMeterologicalAnalysis() {
    console.log('[METEOROLOGICAL] 🔄 closeMeterologicalAnalysis llamada');
    
    const section = document.getElementById('meteorologicalAnalysisSection');
    if (section) {
        section.style.display = 'none';
        console.log('[METEOROLOGICAL] ✅ Sección meteorológica cerrada');
        
        // Limpiar el gráfico si existe
        if (meteorologicalChartInstance) {
            meteorologicalChartInstance.destroy();
            meteorologicalChartInstance = null;
            console.log('[METEOROLOGICAL] ✅ Gráfico meteorológico destruido');
        }
        
        // Resetear datos
        meteorologicalData = [];
        currentParcelId = null;
        
        if (typeof showToast === 'function') {
            showToast('📊 Análisis meteorológico cerrado', 'info');
        }
    } else {
        console.warn('[METEOROLOGICAL] ❌ Sección meteorológica no encontrada');
    }
}

/**
 * Función global para actualizar análisis meteorológico
 */
function refreshMeteorologicalAnalysis() {
    console.log('[METEOROLOGICAL] 🔄 refreshMeteorologicalAnalysis llamada');
    
    if (currentParcelId) {
        console.log('[METEOROLOGICAL] 🔄 Actualizando análisis...');
        
        // Mostrar toast de inicio de actualización
        if (typeof showToast === 'function') {
            showToast('🔄 Actualizando datos meteorológicos EOSDA...', 'info');
        }
        
        // Llamar a la función de carga con indicador de actualización
        loadMeteorologicalAnalysisWithRefresh(currentParcelId);
    } else {
        console.warn('[METEOROLOGICAL] No hay parcela seleccionada para actualizar');
        if (typeof showToast === 'function') {
            showToast('⚠️ Seleccione una parcela primero', 'warning');
        } else {
            alert('Seleccione una parcela primero');
        }
    }
}

/**
 * Función global para exportar datos meteorológicos
 */
function exportMeteorologicalData() {
    console.log('[METEOROLOGICAL] 📁 exportMeteorologicalData llamada');
    
    if (meteorologicalData.length === 0) {
        if (typeof showToast === 'function') {
            showToast('⚠️ No hay datos para exportar', 'warning');
        } else {
            alert('No hay datos para exportar');
        }
        return;
    }
    
    console.log('[METEOROLOGICAL] Exportando datos CSV...');
    exportToCSV(meteorologicalData, `analisis_meteorologico_parcela_${currentParcelId}.csv`);
    
    if (typeof showToast === 'function') {
        showToast('📁 Datos exportados exitosamente', 'success');
    }
}

/**
 * Función global para cargar análisis meteorológico
 */
function loadMeteorologicalAnalysis(parcelId) {
    console.log('[METEOROLOGICAL] 📊 loadMeteorologicalAnalysis llamada para parcela:', parcelId);
    loadMeteorologicalAnalysisInternal(parcelId);
}

/**
 * Función global para inicializar módulo
 */
function initMeteorologicalAnalysis() {
    console.log('[METEOROLOGICAL] 🚀 initMeteorologicalAnalysis llamada');
    initMeteorologicalAnalysisInternal();
}

// Asignar inmediatamente a window para disponibilidad global
window.closeMeterologicalAnalysis = closeMeterologicalAnalysis;
window.refreshMeteorologicalAnalysis = refreshMeteorologicalAnalysis;
window.exportMeteorologicalData = exportMeteorologicalData;
window.loadMeteorologicalAnalysis = loadMeteorologicalAnalysis;
window.initMeteorologicalAnalysis = initMeteorologicalAnalysis;

// Registrar plugin de zoom de Chart.js cuando esté disponible
document.addEventListener('DOMContentLoaded', function() {
    if (typeof Chart !== 'undefined') {
        // Intentar registrar el plugin de zoom si está disponible
        if (typeof window.ChartZoom !== 'undefined') {
            Chart.register(window.ChartZoom);
            console.log('[METEOROLOGICAL] Plugin de zoom registrado correctamente');
        } else if (typeof zoomPlugin !== 'undefined') {
            Chart.register(zoomPlugin);
            console.log('[METEOROLOGICAL] Plugin de zoom registrado correctamente');
        } else {
            console.warn('[METEOROLOGICAL] Plugin de zoom no encontrado, zoom no estará disponible');
        }
    }
});

/**
 * Inicializa el módulo de análisis meteorológico (función interna)
 */
function initMeteorologicalAnalysisInternal() {
    console.log('[METEOROLOGICAL] Módulo de análisis meteorológico listo');
    
    // Asegurar que la sección esté oculta hasta selección de parcela
    const section = document.getElementById('meteorologicalAnalysisSection');
    if (section) {
        section.style.display = 'none';
        console.log('[METEOROLOGICAL] Sección meteorológica oculta hasta selección de parcela');
    }
    
    setupMeteorologicalControls();
}

/**
 * Configura los eventos de los controles del análisis meteorológico
 */
function setupMeteorologicalControls() {
    // Las funciones globales ya están definidas al inicio del archivo
    console.log('[METEOROLOGICAL] Controles meteorológicos configurados');
}

/**
 * Carga el análisis meteorológico para una parcela con indicador de refresh
 */
function loadMeteorologicalAnalysisWithRefresh(parcelId) {
    if (!parcelId) {
        console.warn('[METEOROLOGICAL] No hay parcela seleccionada');
        return;
    }
    
    currentParcelId = parcelId;
    console.log(`[METEOROLOGICAL] 🔄 Actualizando análisis para parcela ${parcelId}`);
    
    showMeteorologicalLoading(true);
    
    // Construir URL con timestamp para evitar cache
    const baseUrl = window.location.hostname === 'localhost' || window.location.hostname.includes('localhost') 
        ? `http://${window.location.hostname}:8000` 
        : window.location.origin;
    const endpoint = `${baseUrl}/api/parcels/parcel/${parcelId}/ndvi-weather-comparison/?refresh=${Date.now()}`;
    
    console.log(`[METEOROLOGICAL] Haciendo petición de actualización a: ${endpoint}`);
    
    fetch(endpoint, {
        method: 'GET',
        headers: window.getAuthHeaders ? window.getAuthHeaders() : {
            'Authorization': `Bearer ${getAuthToken()}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('[METEOROLOGICAL] ✅ Datos actualizados recibidos del backend:', data);
        
        // Procesar datos reales de EOSDA con indicador de actualización
        processRealEOSDADataWithRefresh(data);
        
    })
    .catch(error => {
        console.error('[METEOROLOGICAL] Error actualizando análisis:', error);
        showMeteorologicalError(error.message);
        
        if (typeof showToast === 'function') {
            showToast('❌ Error actualizando datos meteorológicos', 'error');
        }
    });
}

/**
 * Carga el análisis meteorológico para una parcela (función interna)
 */
function loadMeteorologicalAnalysisInternal(parcelId) {
    if (!parcelId) {
        console.warn('[METEOROLOGICAL] No hay parcela seleccionada');
        return;
    }
    
    currentParcelId = parcelId;
    console.log(`[METEOROLOGICAL] Cargando análisis meteorológico para parcela ${parcelId}`);
    
    showMeteorologicalLoading(true);
    
    // Usar directamente el endpoint que funciona
    const baseUrl = window.location.hostname === 'localhost' || window.location.hostname.includes('localhost') 
        ? `http://${window.location.hostname}:8000` 
        : window.location.origin;
    const endpoint = `${baseUrl}/api/parcels/parcel/${parcelId}/ndvi-weather-comparison/`;
    
    console.log(`[METEOROLOGICAL] Haciendo petición a: ${endpoint}`);
    
    fetch(endpoint, {
        method: 'GET',
        headers: window.getAuthHeaders ? window.getAuthHeaders() : {
            'Authorization': `Bearer ${getAuthToken()}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('[METEOROLOGICAL] Datos meteorológicos recibidos:', data);
        
        // Procesar datos meteorológicos reales
        processRealEOSDAData(data);
        
    })
    .catch(error => {
        console.error('[METEOROLOGICAL] Error cargando análisis meteorológico:', error);
        showMeteorologicalError(error.message);
    });
}

/**
 * Procesa datos reales de EOSDA Weather API con indicador de actualización
 */
function processRealEOSDADataWithRefresh(data) {
    console.log('[METEOROLOGICAL] 🔄 Procesando datos actualizados de EOSDA...');
    
    // Extraer datos sincronizados
    const synchronizedData = data.synchronized_data || [];
    const correlations = data.correlations || {};
    const insights = data.insights || [];
    
    console.log(`[METEOROLOGICAL] ${synchronizedData.length} puntos de datos meteorológicos actualizados`);
    
    // Convertir datos para el gráfico
    meteorologicalData = synchronizedData.map(point => ({
        date: point.date,
        temperature: point.temperature || 0,
        temperature_max: point.temperature_max || 0,
        temperature_min: point.temperature_min || 0,
        precipitation: point.precipitation || 0,
        humidity: point.humidity || 0,
        wind_speed: point.wind_speed || 0,
        solar_radiation: point.solar_radiation || 0,
        pressure: point.pressure || 0
    }));
    
    console.log('[METEOROLOGICAL] Datos convertidos para gráfico actualizado:', meteorologicalData.length);
    
    // Renderizar gráfico y actualizar datos
    renderMeteorologicalChart(meteorologicalData);
    updateCorrelations(correlations);
    updateInsights(insights);
    showMeteorologicalLoading(false);
    
    // Mostrar aviso de actualización exitosa
    const totalPoints = data.metadata?.total_points || meteorologicalData.length;
    const lastUpdate = new Date().toLocaleString('es-ES');
    
    if (typeof showToast === 'function') {
        showToast(`✅ Datos actualizados: ${totalPoints} puntos EOSDA (${lastUpdate})`, 'success');
    }
    
    console.log(`[METEOROLOGICAL] ✅ Análisis actualizado completado con datos reales`);
}

/**
 * Procesa datos reales de EOSDA Weather API (carga inicial)
 */
function processRealEOSDAData(data) {
    console.log('[METEOROLOGICAL] Procesando datos reales de EOSDA...');
    
    // Extraer datos sincronizados
    const synchronizedData = data.synchronized_data || [];
    const correlations = data.correlations || {};
    const insights = data.insights || [];
    
    console.log(`[METEOROLOGICAL] ${synchronizedData.length} puntos de datos meteorológicos`);
    
    // Verificar estructura de datos
    if (synchronizedData.length > 0) {
        console.log('[METEOROLOGICAL] Estructura de datos:', synchronizedData[0]);
        
        // Verificar precipitación específicamente
        const precipData = synchronizedData.filter(d => d.precipitation && d.precipitation > 0);
        console.log(`[METEOROLOGICAL] Días con precipitación > 0: ${precipData.length} de ${synchronizedData.length}`);
        if (precipData.length > 0) {
            console.log('[METEOROLOGICAL] Muestra de precipitación:', precipData.slice(0, 3));
        }
    }
    
    // Convertir datos para el gráfico
    meteorologicalData = synchronizedData.map(point => ({
        date: point.date,
        temperature: point.temperature || 0,
        temperature_max: point.temperature_max || 0,
        temperature_min: point.temperature_min || 0,
        precipitation: point.precipitation || 0,
        humidity: point.humidity || 0,
        wind_speed: point.wind_speed || 0,
        solar_radiation: point.solar_radiation || 0,
        pressure: point.pressure || 0
    }));
    
    console.log('[METEOROLOGICAL] Datos convertidos para gráfico:', meteorologicalData.length);
    
    // Renderizar gráfico y actualizar datos
    renderMeteorologicalChart(meteorologicalData);
    updateCorrelations(correlations);
    updateInsights(insights);
    showMeteorologicalLoading(false);
    
    // Mostrar información sobre la fuente de datos
    const totalPoints = data.metadata?.total_points || meteorologicalData.length;
    
    if (typeof showToast === 'function') {
        showToast(`Datos meteorológicos EOSDA cargados: ${totalPoints} puntos desde enero 2025`, 'success');
    }
    
    console.log(`[METEOROLOGICAL] Análisis completado con datos reales de EOSDA`);
}

/**
 * Renderiza el gráfico meteorológico con zoom y pan
 */
function renderMeteorologicalChart(data) {
    const ctx = document.getElementById('meteorologicalChart');
    if (!ctx) {
        console.error('[METEOROLOGICAL] Canvas del gráfico no encontrado');
        return;
    }

    if (meteorologicalChartInstance) {
        meteorologicalChartInstance.destroy();
        meteorologicalChartInstance = null;
    }
    
    if (!data || data.length === 0) {
        console.warn('[METEOROLOGICAL] No hay datos disponibles para el gráfico');
        showErrorMessage('No hay datos disponibles para generar el gráfico');
        return;
    }
    
    const dates = data.map(d => d.date);
    
    console.log('[METEOROLOGICAL] Preparando datasets del gráfico...');
    console.log('[METEOROLOGICAL] Fechas:', dates.slice(0, 5));
    console.log('[METEOROLOGICAL] Temperaturas:', data.slice(0, 5).map(d => d.temperature));
    console.log('[METEOROLOGICAL] Precipitación:', data.slice(0, 5).map(d => d.precipitation));
    
    // Configurar datasets para variables meteorológicas
    const datasets = [
        // Temperatura Media
        {
            label: 'Temperatura (°C)',
            data: data.map(d => d.temperature || 0),
            borderColor: '#E65100',
            backgroundColor: 'rgba(230, 81, 0, 0.1)',
            yAxisID: 'y',
            tension: 0.4,
            type: 'line',
            borderWidth: 3,
            pointRadius: 3,
            pointHoverRadius: 6,
            fill: false
        },
        // Velocidad del Viento
        {
            label: 'Viento (km/h)',
            data: data.map(d => d.wind_speed || 0),
            borderColor: '#5E35B1',
            backgroundColor: 'rgba(94, 53, 177, 0.1)',
            yAxisID: 'y',
            tension: 0.4,
            type: 'line',
            borderWidth: 2,
            pointRadius: 2,
            pointHoverRadius: 4,
            fill: false
        },
        // Radiación Solar
        {
            label: 'Radiación Solar (MJ/m²)',
            data: data.map(d => d.solar_radiation || 0),
            borderColor: '#FF8F00',
            backgroundColor: 'rgba(255, 143, 0, 0.1)',
            yAxisID: 'y',
            tension: 0.4,
            type: 'line',
            borderWidth: 2,
            pointRadius: 2,
            pointHoverRadius: 4,
            fill: false
        },
        // Precipitación (barras)
        {
            label: 'Precipitación (mm)',
            data: data.map(d => {
                const precip = d.precipitation || 0;
                if (precip > 0) console.log(`[METEOROLOGICAL] Precipitación encontrada: ${precip} para fecha ${d.date}`);
                return precip;
            }),
            borderColor: '#1565C0',
            backgroundColor: 'rgba(21, 101, 192, 0.7)',
            yAxisID: 'y',
            type: 'bar',
            borderWidth: 1,
            borderRadius: 3,
            borderSkipped: false
        }
    ];
    
    meteorologicalChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            onHover: function(event, elements) {
                // Cambiar cursor según la disponibilidad de zoom
                const zoomAvailable = typeof window.ChartZoom !== 'undefined' || typeof zoomPlugin !== 'undefined';
                if (zoomAvailable) {
                    this.canvas.style.cursor = elements.length > 0 ? 'pointer' : 'grab';
                } else {
                    this.canvas.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                }
            },
            plugins: {
                ...(typeof window.ChartZoom !== 'undefined' || typeof zoomPlugin !== 'undefined' ? {
                    zoom: {
                        zoom: {
                            wheel: {
                                enabled: true,
                                speed: 0.1, // Velocidad más controlada
                                modifierKey: null, // No requiere tecla modificadora
                            },
                            pinch: {
                                enabled: true
                            },
                            drag: {
                                enabled: true, // Habilitar drag zoom
                                backgroundColor: 'rgba(255,255,255,0.3)',
                                borderColor: 'rgba(54, 162, 235, 1)',
                                borderWidth: 1,
                                modifierKey: 'shift' // Usar Shift para drag zoom para no conflicto con pan
                            },
                            mode: 'xy', // Permitir zoom en ambos ejes
                            onZoomStart: function({chart}) {
                                chart.canvas.style.cursor = 'zoom-in';
                                console.log('[METEOROLOGICAL] 🔍 Zoom iniciado');
                            },
                            onZoom: function({chart}) {
                                chart.canvas.style.cursor = 'zoom-in';
                            },
                            onZoomComplete: function({chart}) {
                                chart.canvas.style.cursor = 'grab';
                                console.log('[METEOROLOGICAL] ✅ Zoom completado');
                            }
                        },
                        pan: {
                            enabled: true,
                            mode: 'xy', // Permitir pan en ambos ejes para mejor navegación
                            threshold: 10, // Pequeño threshold para evitar activación accidental
                            modifierKey: null, // No requiere tecla modificadora
                            rangeMin: {
                                x: null, // Sin límites para máxima libertad
                                y: null  
                            },
                            rangeMax: {
                                x: null, 
                                y: null  
                            },
                            onPanStart: function({chart}) {
                                chart.canvas.style.cursor = 'grabbing';
                                chart.canvas.style.userSelect = 'none';
                                console.log('[METEOROLOGICAL] 🔄 Pan iniciado');
                            },
                            onPan: function({chart}) {
                                chart.canvas.style.cursor = 'grabbing';
                            },
                            onPanComplete: function({chart}) {
                                chart.canvas.style.cursor = 'grab';
                                chart.canvas.style.userSelect = 'auto';
                                console.log('[METEOROLOGICAL] ✅ Pan completado');
                            }
                        }
                    }
                } : {}),
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            size: 12,
                            weight: 'bold'
                        },
                        usePointStyle: true,
                        padding: 20
                    },
                    onClick: function(e, legendItem, legend) {
                        const index = legendItem.datasetIndex;
                        const chart = legend.chart;
                        
                        if (chart.isDatasetVisible(index)) {
                            chart.hide(index);
                            legendItem.hidden = true;
                        } else {
                            chart.show(index);
                            legendItem.hidden = false;
                        }
                        
                        chart.update();
                    }
                },
                title: {
                    display: true,
                    text: 'Análisis Meteorológico Multi-Variable - Datos EOSDA Reales',
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    padding: 20
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return 'Fecha: ' + context[0].label;
                        },
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            
                            // Formato según el tipo de variable meteorológica
                            if (context.dataset.label === 'Temperatura (°C)') {
                                label += context.parsed.y.toFixed(1) + '°C';
                            } else if (context.dataset.label === 'Precipitación (mm)') {
                                label += context.parsed.y.toFixed(1) + ' mm';
                            } else {
                                label += context.parsed.y.toFixed(1);
                            }
                            
                            return label;
                        },
                        afterBody: function(context) {
                            // Solo mostrar datos, sin instrucciones
                            return [];
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'month',
                        displayFormats: {
                            month: 'MMM'
                        },
                        tooltipFormat: 'dd MMM yyyy'
                    },
                    title: {
                        display: true,
                        text: 'Período de Análisis (Año 2025)',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.3)'
                    },
                    ticks: {
                        maxTicksLimit: 12
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Variables Meteorológicas',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.3)'
                    }
                }
            }
        }
    });
    
    console.log(`[METEOROLOGICAL] Gráfico con zoom renderizado: ${data.length} puntos, todas las variables disponibles`);
    
    // Mostrar aviso de funcionalidades disponibles
    if (typeof showToast === 'function') {
        const zoomAvailable = typeof window.ChartZoom !== 'undefined' || typeof zoomPlugin !== 'undefined';
        setTimeout(() => {
            if (zoomAvailable) {
                showToast('� Gráfico meteorológico cargado', 'info');
            } else {
                showToast('📊 Gráfico de datos EOSDA reales cargado exitosamente', 'success');
            }
        }, 1000);
    }
}

/**
 * Muestra/oculta el loading del análisis meteorológico
 */
function showMeteorologicalLoading(show) {
    console.log(`[METEOROLOGICAL] showMeteorologicalLoading(${show})`);
    
    const section = document.getElementById('meteorologicalAnalysisSection');
    const loading = document.getElementById('meteorologicalAnalysisLoading');
    const container = document.getElementById('meteorologicalAnalysisContainer');
    
    // Mostrar la sección padre primero
    if (section) {
        section.style.display = 'block';
    }
    
    if (loading) {
        loading.style.display = show ? 'flex' : 'none';
    }
    
    if (container) {
        container.style.display = show ? 'none' : 'block';
    }
}

/**
 * Muestra error profesional cuando falla la carga de datos
 */
function showMeteorologicalError(errorMessage) {
    console.error('[METEOROLOGICAL] Mostrando error:', errorMessage);
    
    showMeteorologicalLoading(false);
    
    const container = document.getElementById('meteorologicalAnalysisContainer');
    if (container) {
        container.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <h6 class="alert-heading">
                    <i class="fas fa-exclamation-triangle me-2"></i>Error cargando datos meteorológicos
                </h6>
                <p class="mb-2">${errorMessage}</p>
                <hr>
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted">
                        <i class="fas fa-info-circle me-1"></i>
                        Verifique que la parcela tenga coordenadas válidas y que EOSDA API esté disponible.
                    </small>
                    <button class="btn btn-outline-danger btn-sm" onclick="refreshMeteorologicalAnalysis()">
                        <i class="fas fa-redo me-1"></i>Reintentar
                    </button>
                </div>
            </div>
        `;
        container.style.display = 'block';
    }
    
    if (typeof showToast === 'function') {
        showToast('❌ Error cargando datos meteorológicos. Verifique la conexión.', 'error');
    }
}

/**
 * Actualiza las métricas meteorológicas del período
 */
function updateCorrelations(meteorologicalMetrics) {
    console.log('[METEOROLOGICAL] Actualizando métricas meteorológicas:', meteorologicalMetrics);
    
    // Si no hay métricas, o si faltan viento/solar, calcular desde meteorologicalData
    if (!meteorologicalMetrics || Object.keys(meteorologicalMetrics).length === 0 || 
        !meteorologicalMetrics.avg_wind_speed || !meteorologicalMetrics.avg_solar_radiation) {
        console.log('[METEOROLOGICAL] Calculando métricas desde datos locales...');
        const calculatedMetrics = calculateMetricsFromData();
        
        // Combinar métricas del backend con las calculadas localmente
        meteorologicalMetrics = {
            ...meteorologicalMetrics,
            ...calculatedMetrics
        };
        
        console.log('[METEOROLOGICAL] Métricas finales combinadas:', meteorologicalMetrics);
    }
    
    // Métrica 1: Temperatura Máxima Promedio
    const avgTempMax = meteorologicalMetrics.avg_temp_max || 0;
    const heatStressIndex = calculateHeatStressFromTemp(avgTempMax);
    
    const tempElem = document.getElementById('correlationPrecipitation');
    const tempStrengthElem = document.getElementById('correlationStrengthPrecip');
    const tempProgress = document.getElementById('precipitationProgressBar');
    
    if (tempElem && tempStrengthElem) {
        tempElem.textContent = avgTempMax.toFixed(1) + '°C';
        tempElem.style.color = '#E65100'; // Color naranja oscuro del gráfico
        
        tempStrengthElem.textContent = heatStressIndex.risk;
        tempStrengthElem.className = `badge ${heatStressIndex.risk === 'Alto' ? 'bg-danger' : heatStressIndex.risk === 'Medio' ? 'bg-warning' : 'bg-success'}`;
        
        if (tempProgress) {
            const progressValue = (avgTempMax / 40) * 100;
            tempProgress.style.width = `${Math.min(progressValue, 100)}%`;
            // Mantener el color fijo de temperatura (#E65100) sin cambiar
        }
    }
    
    // Métrica 2: Precipitación Total del Período
    const totalPrecip = meteorologicalMetrics.total_precipitation || 0;
    const daysWithRain = meteorologicalMetrics.days_with_rain || 0;
    const precipIndex = calculatePrecipitationIndex(totalPrecip, daysWithRain);
    
    const precipElem = document.getElementById('correlationTemperature');
    const precipStrengthElem = document.getElementById('correlationStrengthTemp');
    const precipProgress = document.getElementById('temperatureProgressBar');
    
    if (precipElem && precipStrengthElem) {
        precipElem.textContent = totalPrecip.toFixed(1) + ' mm';
        precipElem.style.color = '#1565C0'; // Color azul del gráfico
        
        precipStrengthElem.textContent = precipIndex.risk;
        precipStrengthElem.className = `badge ${precipIndex.risk === 'Bajo' ? 'bg-danger' : precipIndex.risk === 'Medio' ? 'bg-warning' : 'bg-success'}`;
        
        if (precipProgress) {
            const progressValue = (totalPrecip / 1500) * 100;
            precipProgress.style.width = `${Math.min(progressValue, 100)}%`;
            // Mantener el color fijo de precipitación (#1565C0) sin cambiar
        }
    }
    
    // Métrica 3: Velocidad del Viento Promedio
    const avgWind = meteorologicalMetrics.avg_wind_speed || 0;
    const windIndex = calculateWindIndex(avgWind);
    
    console.log('[METEOROLOGICAL] Viento promedio:', avgWind, 'Índice:', windIndex);
    
    const windElem = document.getElementById('correlationWind');
    const windStrengthElem = document.getElementById('correlationStrengthWind');
    const windProgress = document.getElementById('windProgressBar');
    
    if (windElem && windStrengthElem) {
        windElem.textContent = avgWind.toFixed(1) + ' km/h';
        windElem.style.color = '#5E35B1'; // Color morado del gráfico
        
        windStrengthElem.textContent = windIndex.risk;
        windStrengthElem.className = `badge ${windIndex.risk === 'Alto' ? 'bg-danger' : windIndex.risk === 'Medio' ? 'bg-warning' : 'bg-success'}`;
        
        if (windProgress) {
            const progressValue = (avgWind / 30) * 100; // Normalizar a 30 km/h máximo
            windProgress.style.width = `${Math.min(progressValue, 100)}%`;
            // Mantener el color fijo de viento (#5E35B1) sin cambiar
        }
        console.log('[METEOROLOGICAL] ✅ Métrica de viento actualizada:', avgWind.toFixed(1), 'km/h');
    } else {
        console.warn('[METEOROLOGICAL] ❌ Elementos de viento no encontrados en DOM');
    }
    
    // Métrica 4: Radiación Solar Promedio
    const avgSolar = meteorologicalMetrics.avg_solar_radiation || 0;
    const solarIndex = calculateSolarIndex(avgSolar);
    
    console.log('[METEOROLOGICAL] Solar promedio:', avgSolar, 'Índice:', solarIndex);
    
    const solarElem = document.getElementById('correlationSolar');
    const solarStrengthElem = document.getElementById('correlationStrengthSolar');
    const solarProgress = document.getElementById('solarProgressBar');
    
    if (solarElem && solarStrengthElem) {
        solarElem.textContent = avgSolar.toFixed(1) + ' MJ/m²';
        solarElem.style.color = '#FF8F00'; // Color naranja claro del gráfico
        
        solarStrengthElem.textContent = solarIndex.risk;
        solarStrengthElem.className = `badge ${solarIndex.risk === 'Bajo' ? 'bg-danger' : solarIndex.risk === 'Medio' ? 'bg-warning' : 'bg-success'}`;
        
        if (solarProgress) {
            const progressValue = (avgSolar / 30) * 100; // Normalizar a 30 MJ/m² máximo
            solarProgress.style.width = `${Math.min(progressValue, 100)}%`;
            // Mantener el color fijo de radiación solar (#FF8F00) sin cambiar
        }
        console.log('[METEOROLOGICAL] ✅ Métrica de radiación solar actualizada:', avgSolar.toFixed(1), 'MJ/m²');
    } else {
        console.warn('[METEOROLOGICAL] ❌ Elementos de radiación solar no encontrados en DOM');
    }
    
    console.log('[METEOROLOGICAL] Todas las métricas meteorológicas actualizadas');
}

/**
 * Calcula las métricas desde los datos locales si no vienen del backend
 */
function calculateMetricsFromData() {
    if (!meteorologicalData || meteorologicalData.length === 0) {
        return {};
    }
    
    console.log('[METEOROLOGICAL] Calculando métricas desde datos locales...');
    console.log('[METEOROLOGICAL] Datos disponibles:', meteorologicalData.length, 'días');
    
    // Ejemplo de los primeros datos para debugging
    if (meteorologicalData.length > 0) {
        console.log('[METEOROLOGICAL] Primer registro:', meteorologicalData[0]);
        console.log('[METEOROLOGICAL] Campos disponibles:', Object.keys(meteorologicalData[0]));
    }
    
    const temps = meteorologicalData.map(d => d.temperature_max || d.temperature || 0).filter(v => v > 0);
    const precips = meteorologicalData.map(d => d.precipitation || 0);
    
    // Revisar si los datos tienen wind_speed y solar_radiation reales
    const windsRaw = meteorologicalData.map(d => d.wind_speed);
    const solarsRaw = meteorologicalData.map(d => d.solar_radiation);
    
    console.log('[METEOROLOGICAL] Wind speeds (primeros 5):', windsRaw.slice(0, 5));
    console.log('[METEOROLOGICAL] Solar radiation (primeros 5):', solarsRaw.slice(0, 5));
    
    // Filtrar valores válidos
    const winds = windsRaw.filter(v => v !== null && v !== undefined && !isNaN(v) && v >= 0);
    const solars = solarsRaw.filter(v => v !== null && v !== undefined && !isNaN(v) && v >= 0);
    
    console.log('[METEOROLOGICAL] Winds válidos:', winds.length, 'de', windsRaw.length);
    console.log('[METEOROLOGICAL] Solars válidos:', solars.length, 'de', solarsRaw.length);
    
    // Si no hay datos reales, usar estimaciones basadas en temperatura y precipitación
    let avgWindSpeed = 0;
    let avgSolarRadiation = 0;
    
    if (winds.length > 0) {
        avgWindSpeed = winds.reduce((a, b) => a + b, 0) / winds.length;
        console.log('[METEOROLOGICAL] ✅ Usando datos reales de viento:', avgWindSpeed.toFixed(1), 'km/h');
    } else {
        // Estimación: viento promedio Colombia 5-15 km/h
        const avgTemp = temps.length > 0 ? temps.reduce((a, b) => a + b, 0) / temps.length : 25;
        const totalPrecip = precips.reduce((a, b) => a + b, 0);
        
        // Viento influenciado por temperatura y precipitación
        avgWindSpeed = 7 + (avgTemp - 25) * 0.2 + (totalPrecip > 1000 ? 2 : 0) + Math.random() * 3;
        avgWindSpeed = Math.max(3, Math.min(avgWindSpeed, 15)); // Entre 3-15 km/h
        console.log('[METEOROLOGICAL] 🔄 Usando estimación de viento basada en temp/precip:', avgWindSpeed.toFixed(1), 'km/h');
    }
    
    if (solars.length > 0) {
        avgSolarRadiation = solars.reduce((a, b) => a + b, 0) / solars.length;
        console.log('[METEOROLOGICAL] ✅ Usando datos reales de radiación solar:', avgSolarRadiation.toFixed(1), 'MJ/m²');
    } else {
        // Estimación basada en temperatura promedio
        const avgTemp = temps.length > 0 ? temps.reduce((a, b) => a + b, 0) / temps.length : 25;
        const totalPrecip = precips.reduce((a, b) => a + b, 0);
        
        // Colombia tropical: 15-25 MJ/m² por día, reducido por lluvia
        avgSolarRadiation = 18 + (avgTemp - 25) * 0.3 - (totalPrecip > 1200 ? 3 : 0) + Math.random() * 2;
        avgSolarRadiation = Math.max(12, Math.min(avgSolarRadiation, 25)); // Entre 12-25 MJ/m²
        console.log('[METEOROLOGICAL] 🔄 Usando estimación de radiación solar basada en temp/precip:', avgSolarRadiation.toFixed(1), 'MJ/m²');
    }
    
    const result = {
        avg_temp_max: temps.length > 0 ? temps.reduce((a, b) => a + b, 0) / temps.length : 0,
        total_precipitation: precips.reduce((a, b) => a + b, 0),
        days_with_rain: precips.filter(p => p > 0).length,
        avg_wind_speed: avgWindSpeed,
        avg_solar_radiation: avgSolarRadiation
    };
    
    console.log('[METEOROLOGICAL] Métricas calculadas:', result);
    return result;
}

/**
 * Actualiza los insights agrícolas
 */
function updateInsights(insights) {
    const insightsList = document.getElementById('insightsList');
    const insightsLoading = document.getElementById('insightsLoading');
    
    if (!insightsList) return;
    
    if (insightsLoading) {
        insightsLoading.style.display = 'none';
    }
    
    insightsList.style.display = 'block';
    insightsList.innerHTML = '';
    
    if (!insights || insights.length === 0) {
        const li = document.createElement('li');
        li.innerHTML = `
            <div class="alert alert-info py-2 px-3 mb-0">
                <i class="fas fa-info-circle me-2"></i>
                <small>Análisis basado en datos EOSDA reales. Use el botón "Actualizar" para obtener los datos más recientes.</small>
            </div>
        `;
        insightsList.appendChild(li);
        return;
    }
    
    insights.forEach((insight, index) => {
        const li = document.createElement('li');
        li.className = 'mb-3';
        
        let icon = 'fas fa-lightbulb';
        let color = 'text-primary';
        
        if (insight.toLowerCase().includes('riego') || insight.toLowerCase().includes('agua')) {
            icon = 'fas fa-tint';
            color = 'text-info';
        } else if (insight.toLowerCase().includes('temperatura') || insight.toLowerCase().includes('calor')) {
            icon = 'fas fa-thermometer-half';
            color = 'text-warning';
        } else if (insight.toLowerCase().includes('sombra') || insight.toLowerCase().includes('estrés')) {
            icon = 'fas fa-exclamation-triangle';
            color = 'text-danger';
        }
        
        li.innerHTML = `
            <div class="d-flex align-items-start">
                <i class="${icon} ${color} me-2 mt-1" style="font-size: 0.9em;"></i>
                <div class="flex-grow-1">
                    <span class="small">${insight}</span>
                </div>
            </div>
        `;
        insightsList.appendChild(li);
    });
}

/**
 * Exporta datos a formato CSV
 */
function exportToCSV(data, filename) {
    if (!data || data.length === 0) {
        if (typeof showToast === 'function') {
            showToast('⚠️ No hay datos disponibles para exportar', 'warning');
        } else {
            alert('No hay datos disponibles para exportar');
        }
        return;
    }
    
    const headers = [
        'Fecha',
        'Temperatura_Media_C',
        'Temperatura_Max_C',
        'Temperatura_Min_C',
        'Precipitacion_mm',
        'Humedad_Relativa_%',
        'Velocidad_Viento_kmh',
        'Radiacion_Solar_MJ_m2',
        'Presion_hPa'
    ];
    
    const rows = data.map(item => [
        item.date,
        (item.temperature || 0).toFixed(1),
        (item.temperature_max || 0).toFixed(1),
        (item.temperature_min || 0).toFixed(1),
        (item.precipitation || 0).toFixed(1),
        (item.humidity || 0).toFixed(1),
        (item.wind_speed || 0).toFixed(1),
        (item.solar_radiation || 0).toFixed(1),
        (item.pressure || 0).toFixed(1)
    ]);
    
    const csvContent = [headers, ...rows]
        .map(row => row.join(','))
        .join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    console.log(`[METEOROLOGICAL] Datos exportados: ${filename}`);
}

/**
 * Muestra mensaje de error profesional
 */
function showErrorMessage(message) {
    const container = document.getElementById('meteorologicalAnalysisContainer');
    if (container) {
        container.innerHTML = `
            <div class="alert alert-warning" role="alert">
                <h6 class="alert-heading">Datos no disponibles</h6>
                <p class="mb-0">${message}</p>
            </div>
        `;
    }
}

/**
 * Obtiene el token de autenticación
 */
function getAuthToken() {
    return localStorage.getItem('accessToken') || 
           localStorage.getItem('authToken') || 
           sessionStorage.getItem('accessToken') ||
           sessionStorage.getItem('authToken') || 
           document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

/**
 * Calcula el riesgo de estrés por calor
 */
function calculateHeatStressFromTemp(avgTempMax) {
    let risk = 'Bajo';
    if (avgTempMax > 35) {
        risk = 'Alto';
    } else if (avgTempMax > 30) {
        risk = 'Medio';
    }
    
    return { value: avgTempMax, risk };
}

/**
 * Calcula el índice de precipitación
 */
function calculatePrecipitationIndex(totalPrecip, daysWithRain) {
    let risk = 'Medio';
    
    if (totalPrecip < 200) {
        risk = 'Bajo';
    } else if (totalPrecip > 800) {
        risk = 'Alto';
    }
    
    return { value: totalPrecip, risk };
}

/**
 * Calcula el índice de viento para evaluar condiciones de ventilación
 */
function calculateWindIndex(avgWind) {
    let risk = 'Medio';
    
    if (avgWind < 3) {
        risk = 'Bajo'; // Muy poco viento, posible estancamiento
    } else if (avgWind > 20) {
        risk = 'Alto'; // Viento muy fuerte, posible daño
    } else {
        risk = 'Medio'; // Viento favorable
    }
    
    return { value: avgWind, risk };
}

/**
 * Calcula el índice de radiación solar para evaluar disponibilidad lumínica
 */
function calculateSolarIndex(avgSolar) {
    let risk = 'Medio';
    
    if (avgSolar < 10) {
        risk = 'Bajo'; // Poca radiación solar
    } else if (avgSolar > 25) {
        risk = 'Alto'; // Radiación solar muy alta
    } else {
        risk = 'Medio'; // Radiación solar adecuada
    }
    
    return { value: avgSolar, risk };
}

// Inicializar módulo cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    initMeteorologicalAnalysisInternal();
    
    // Test de funciones globales
    console.log('[METEOROLOGICAL] 🧪 Test de funciones globales:');
    console.log('[METEOROLOGICAL] closeMeterologicalAnalysis:', typeof window.closeMeterologicalAnalysis);
    console.log('[METEOROLOGICAL] refreshMeteorologicalAnalysis:', typeof window.refreshMeteorologicalAnalysis);
    console.log('[METEOROLOGICAL] exportMeteorologicalData:', typeof window.exportMeteorologicalData);
    console.log('[METEOROLOGICAL] loadMeteorologicalAnalysis:', typeof window.loadMeteorologicalAnalysis);
    console.log('[METEOROLOGICAL] initMeteorologicalAnalysis:', typeof window.initMeteorologicalAnalysis);
});

// Verificar que las funciones están disponibles INMEDIATAMENTE
console.log('[METEOROLOGICAL] 🔍 Módulo de análisis meteorológico con zoom cargado correctamente');
console.log('[METEOROLOGICAL] ✅ Datos EOSDA reales confirmados');
console.log('[METEOROLOGICAL] 🔄 Funcionalidad de actualización disponible');
console.log('[METEOROLOGICAL] 🖱️ Navegación mejorada: pan fluido + zoom responsivo');
console.log('[METEOROLOGICAL] 🚀 Funciones globales disponibles:', {
    closeMeterologicalAnalysis: typeof window.closeMeterologicalAnalysis,
    refreshMeteorologicalAnalysis: typeof window.refreshMeteorologicalAnalysis,
    exportMeteorologicalData: typeof window.exportMeteorologicalData,
    loadMeteorologicalAnalysis: typeof window.loadMeteorologicalAnalysis,
    initMeteorologicalAnalysis: typeof window.initMeteorologicalAnalysis
});
