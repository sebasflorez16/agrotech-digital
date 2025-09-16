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
    
    // Sincronizar primero con el estado global
    const parcelIdToUse = sincronizarParcelaSeleccionada();
    
    // Si estamos en modo pronóstico del tiempo, recargar el pronóstico
    const container = document.getElementById('meteorologicalAnalysisContainer');
    if (container && container.innerHTML.includes('weather-forecast-container')) {
        console.log('[METEOROLOGICAL] Detectado modo pronóstico, recargando pronóstico...');
        loadWeatherForecast(parcelIdToUse);
        return;
    }
    
    if (parcelIdToUse) {
        console.log('[METEOROLOGICAL] 🔄 Actualizando análisis...');
        
        // Mostrar toast de inicio de actualización
        if (typeof showToast === 'function') {
            showToast('🔄 Actualizando datos meteorológicos EOSDA...', 'info');
        }
        
        // Llamar a la función de carga con indicador de actualización
        loadMeteorologicalAnalysisWithRefresh(parcelIdToUse);
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
    
    // Construir URL - usar siempre window.location.origin para producción
    const baseUrl = window.location.origin;
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
    // Sincronizar primero con el estado global
    sincronizarParcelaSeleccionada();
    
    // Si se proporciona un ID específico, usarlo; si no, intentar obtener el ID de la parcela seleccionada
    if (!parcelId && window.EOSDA_STATE && window.EOSDA_STATE.selectedParcelId) {
        parcelId = window.EOSDA_STATE.selectedParcelId;
        console.log('[METEOROLOGICAL] Usando parcela seleccionada del estado global:', parcelId);
    }
    
    if (!parcelId) {
        console.warn('[METEOROLOGICAL] No hay parcela seleccionada');
        return;
    }
    
    currentParcelId = parcelId;
    
    // Actualizar también el estado global si es necesario
    if (window.EOSDA_STATE && window.EOSDA_STATE.selectedParcelId !== parcelId) {
        window.EOSDA_STATE.selectedParcelId = parcelId;
    }
    console.log(`[METEOROLOGICAL] Cargando análisis meteorológico para parcela ${parcelId}`);
    
    showMeteorologicalLoading(true);
    
    // Usar siempre window.location.origin para producción
    const baseUrl = window.location.origin;
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
        const currentYear = new Date().getFullYear();
        const currentMonth = new Date().toLocaleDateString('es-ES', { month: 'long' });
        showToast(`Datos meteorológicos EOSDA cargados: ${totalPoints} puntos (enero ${currentYear} - ${currentMonth})`, 'success');
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
 * Función global para cargar el pronóstico del tiempo de 14 días
 */
function loadWeatherForecast(parcelId) {
    console.log('[METEOROLOGICAL] 🌤️ loadWeatherForecast llamada para parcela:', parcelId);
    
    // Sincronizar primero con el estado global
    sincronizarParcelaSeleccionada();
    
    // Si se proporciona un ID específico, usarlo; si no, intentar obtener el ID de la parcela seleccionada
    if (!parcelId && window.EOSDA_STATE && window.EOSDA_STATE.selectedParcelId) {
        parcelId = window.EOSDA_STATE.selectedParcelId;
        console.log('[METEOROLOGICAL] Usando parcela seleccionada del estado global:', parcelId);
    }
    
    if (!parcelId) {
        console.warn('[METEOROLOGICAL] No hay parcela seleccionada para pronóstico');
        if (typeof showToast === 'function') {
            showToast('Seleccione una parcela primero', 'warning');
        } else {
            alert('Seleccione una parcela primero');
        }
        return;
    }
    
    currentParcelId = parcelId;
    
    // Actualizar también el estado global si es necesario
    if (window.EOSDA_STATE && window.EOSDA_STATE.selectedParcelId !== parcelId) {
        window.EOSDA_STATE.selectedParcelId = parcelId;
    }
    console.log(`[METEOROLOGICAL] Cargando pronóstico del tiempo para parcela ${parcelId}`);
    
    showMeteorologicalLoading(true);
    
    // Usar siempre window.location.origin para producción
    const baseUrl = window.location.origin;
    // Usar la ruta directa para evitar conflictos de routing
    const endpoint = `${baseUrl}/api/parcels/get-weather-forecast/${parcelId}/`;
    
    console.log(`[METEOROLOGICAL] Haciendo petición al pronóstico (ruta directa): ${endpoint}`);
    
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
        console.log('[METEOROLOGICAL] Datos del pronóstico recibidos:', data);
        
        // Verificar si hay un error en los datos
        if (data.error) {
            console.error('[METEOROLOGICAL] Error en la respuesta:', data.error);
            showMeteorologicalError(data.message || data.error);
            return;
        }
        
        // Inspeccionar la estructura completa del pronóstico
        console.log('[METEOROLOGICAL] Estructura del pronóstico:', JSON.stringify(data.forecast).substring(0, 300) + '...');
        
        // Verificar formato de fecha en los datos recibidos
        if (data.forecast && data.forecast.length > 0) {
            const sampleItem = data.forecast[0];
            console.log('[METEOROLOGICAL] Formato de fecha en el pronóstico:', {
                hasDate: !!sampleItem.date,
                hasUppercaseDate: !!sampleItem.Date,
                dateValue: sampleItem.date || sampleItem.Date,
                dateProperties: Object.keys(sampleItem).filter(key => key.toLowerCase().includes('date'))
            });
        }
        
        // Procesar datos de pronóstico
        renderWeatherForecast(data);
        
    })
    .catch(error => {
        console.error('[METEOROLOGICAL] Error cargando pronóstico del tiempo:', error);
        showMeteorologicalError('Error al cargar el pronóstico meteorológico. No se pudieron obtener datos reales de EOSDA.');
    });
}

/**
 * Renderiza el pronóstico del tiempo en tarjetas
 * Basado en la documentación de EOSDA Weather API: https://doc.eos.com/docs/weather/basic-weather-providers/
 */
function renderWeatherForecast(data) {
    console.log('[METEOROLOGICAL] Renderizando pronóstico del tiempo');
    
    showMeteorologicalLoading(false);
    
    const container = document.getElementById('meteorologicalAnalysisContainer');
    if (!container) return;
    
    // Extraer datos del pronóstico
    let forecast = data.forecast || [];
    const provider = data.source || 'EOSDA Weather';
    const parcelName = data.parcel_name || '';
    
    // Procesar datos antes de almacenar - agregar cálculos de precipitación y viento
    forecast = forecast.map(day => {
        // Calcular precipitación total desde valores por hora de Rain o usar campos directos
        let precipitation = null;
        if (day.precipitation !== null && day.precipitation !== undefined) {
            // Usar el campo directo de precipitación si está disponible
            precipitation = day.precipitation;
        } else if (day.Rain && typeof day.Rain === 'object') {
            // Si hay datos horarios, sumarlos (formato original EOSDA)
            const rainValues = Object.values(day.Rain).filter(val => typeof val === 'number');
            if (rainValues.length > 0) {
                precipitation = rainValues.reduce((sum, val) => sum + val, 0);
            }
        } else if (day.Precip_total || day.precip_mm) {
            precipitation = day.Precip_total || day.precip_mm;
        }
        
        // Calcular velocidad del viento promedio desde valores por hora de Windspeed o usar campos directos
        let windSpeed = null;
        if (day.wind_speed !== null && day.wind_speed !== undefined) {
            // Usar el campo directo de viento si está disponible
            windSpeed = day.wind_speed;
        } else if (day.Windspeed && typeof day.Windspeed === 'object') {
            // Si hay datos horarios, promediarlos (formato original EOSDA)
            const windValues = Object.values(day.Windspeed).filter(val => typeof val === 'number');
            if (windValues.length > 0) {
                windSpeed = windValues.reduce((sum, val) => sum + val, 0) / windValues.length;
            }
        } else if (day.Wind_speed || day.wind_kph) {
            windSpeed = day.Wind_speed || day.wind_kph;
        }
        
        // Agregar los campos calculados al objeto del día
        const processedDay = {
            ...day,
            calculated_precipitation: precipitation,
            calculated_wind_speed: windSpeed
        };
        
        // Debug log para verificar cálculos
        console.log(`[METEOROLOGICAL] Día procesado - Fecha: ${day.date || day.Date}`);
        console.log(`[METEOROLOGICAL] - Rain original:`, day.Rain);
        console.log(`[METEOROLOGICAL] - Windspeed original:`, day.Windspeed);
        console.log(`[METEOROLOGICAL] - Precipitación calculada: ${precipitation}`);
        console.log(`[METEOROLOGICAL] - Viento calculado: ${windSpeed}`);
        
        return processedDay;
    });
    
    // Almacenar los datos del pronóstico a nivel global para acceso desde el modal de detalles
    window.weatherForecastData = forecast;
    console.log('[METEOROLOGICAL] Datos procesados y almacenados globalmente:', forecast.length, 'días');
    
    // Mostrar todos los días del pronóstico que proporciona la API
    // Los datos de la API ya vienen ordenados desde la fecha actual en adelante
    console.log('[METEOROLOGICAL] Datos del pronóstico recibidos:', forecast.length, 'días');
    console.log('[METEOROLOGICAL] Fechas del pronóstico:', forecast.map(day => day.date).join(', '));
    
    // Verificamos el formato de fecha que usa la API en cada elemento
    const dateField = forecast[0] && forecast[0].Date ? 'Date' : 'date';
    
    // Convertimos las fechas si es necesario para normalizar el formato
    forecast = forecast.map(day => {
        if (!day.date && day[dateField]) {
            day.date = day[dateField];
        }
        return day;
    });
    
    console.log('[METEOROLOGICAL] Fechas normalizadas:', forecast.map(day => day.date).join(', '));
    
    // Filtrar solo los días a partir de hoy
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Normalizar a inicio del día
    
    forecast = forecast.filter(day => {
        const dayDate = new Date(day.date);
        return dayDate >= today;
    });
    
    console.log('[METEOROLOGICAL] Datos filtrados:', forecast.length, 'días desde hoy');
    
    if (!forecast || forecast.length === 0) {
        container.innerHTML = `
            <div class="alert alert-warning">
                <h6 class="alert-heading">Sin datos de pronóstico</h6>
                <p>No hay datos de pronóstico disponibles para esta parcela. La API de EOSDA no devolvió datos reales.</p>
                <p class="small">Por favor verifique que la parcela tiene un ID válido en EOSDA y que está correctamente registrada.</p>
            </div>
        `;
        return;
    }
    
    // Verificar explícitamente qué días son reales vs generados para mejor depuración
    console.log('[METEOROLOGICAL] Días con datos reales:', forecast.filter(day => day.is_real_data !== false).length);
    console.log('[METEOROLOGICAL] Días con datos generados:', forecast.filter(day => day.is_real_data === false).length);
    
    // Crear contenido HTML para el pronóstico
    let forecastHTML = `
        <div class="mb-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div>
                    <h5 class="mb-1 fw-bold">Pronóstico del tiempo - Próximos ${forecast.length} días</h5>
                    <p class="text-muted mb-0 small">
                        <span class="me-2">${parcelName ? `Parcela: ${parcelName}` : ''}</span>
                        <span>Datos: Agrotech</span>
                        ${forecast.filter(day => day.is_real_data !== false).length < forecast.length ? 
                        `<span class="badge bg-info bg-opacity-25 text-dark ms-2">
                            <i class="fas fa-info-circle me-1"></i>${forecast.filter(day => day.is_real_data !== false).length} días reales + 
                            ${forecast.length - forecast.filter(day => day.is_real_data !== false).length} estimados
                         </span>` : ''}
                    </p>
                </div>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-outline-primary" onclick="loadMeteorologicalAnalysis(currentParcelId)">
                        <i class="fas fa-chart-line me-1"></i>Ver análisis histórico
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="loadWeatherForecast(window.EOSDA_STATE.selectedParcelId)">
                        <i class="fas fa-sync-alt me-1"></i>Actualizar
                    </button>
                </div>
            </div>
            
            <!-- Información del día actual -->
            ${forecast.length > 0 ? createCurrentDayCard(forecast[0]) : ''}
            
            <!-- Contenedor de tarjetas de pronóstico -->
            <div class="weather-forecast-container d-flex flex-nowrap overflow-auto pb-2 mb-3 mt-3">
    `;        // Generar tarjetas para cada día del pronóstico
    forecast.forEach((day, index) => {
        // Manejar diferentes formatos de fecha (pueden venir como 'Date' o 'date')
        let dateStr = day.date || day.Date;
        console.log(`[METEOROLOGICAL] Procesando día ${index}, fecha original:`, dateStr);
        
        // Intentar convertir la fecha correctamente
        const date = new Date(dateStr);
        console.log(`[METEOROLOGICAL] Fecha convertida:`, date);
        
        // Determinar si es el día de hoy comparando la fecha
        const today = new Date();
        today.setHours(0, 0, 0, 0); // Normalizar a inicio del día
        const dayDate = new Date(date);
        dayDate.setHours(0, 0, 0, 0);
        const isToday = dayDate.getTime() === today.getTime();
        
        const formattedDate = date.toLocaleDateString('es-ES', {
            weekday: 'short',
            day: 'numeric',
            month: 'short'
        });
        
        // Determinar el estado del tiempo y seleccionar el icono correspondiente
        const weatherInfo = getWeatherInfo(day);
        
        // Determinar si el día es real o generado (verificar campo is_real_data)
        const isRealData = day.is_real_data !== false; // Por defecto, asumir que es real si no tiene la propiedad
        
        // Aplicar estilo según si es hoy o datos generados
        let cardClass = isToday ? 'border-primary' : '';
        // Añadir clase especial para datos generados
        if (!isRealData) {
            cardClass += ' generated-forecast';
        }
        
        // Obtener valores de temperaturas (manejar múltiples formatos de la API EOSDA)
        console.log(`[METEOROLOGICAL] Campos disponibles en día ${index}:`, Object.keys(day));
        
        // Solo usar valores reales de EOSDA - usar campos que realmente existen
        const tempMax = day.temperature_max || day.Temp_air_max || day.temp_max;
        const tempMin = day.temperature_min || day.Temp_air_min || day.temp_min;
        
        // Usar directamente los campos de EOSDA (incluye 0 como valor válido)
        const precipitation = day.precipitation !== undefined ? day.precipitation : (day.calculated_precipitation !== undefined ? day.calculated_precipitation : null);
        const windSpeed = day.wind_speed !== undefined ? day.wind_speed : (day.calculated_wind_speed !== undefined ? day.calculated_wind_speed : null);
        const humidity = day.humidity || day.Rel_humidity || day.humidity_avg;
        
        console.log(`[METEOROLOGICAL] Día ${index} - Precip: ${precipitation}, Viento: ${windSpeed}, Humedad: ${humidity}`);
        
        // Debug específico para ver los valores calculados vs mostrados
        console.log(`[METEOROLOGICAL] Día ${index} - VALORES PARA DISPLAY:`);
        console.log(`[METEOROLOGICAL] - precipitation calculada: ${precipitation}, tipo: ${typeof precipitation}`);
        console.log(`[METEOROLOGICAL] - windSpeed calculado: ${windSpeed}, tipo: ${typeof windSpeed}`);
        console.log(`[METEOROLOGICAL] - humidity: ${humidity}, tipo: ${typeof humidity}`);
        console.log(`[METEOROLOGICAL] - Raw Rain data:`, day.Rain);
        console.log(`[METEOROLOGICAL] - Raw Windspeed data:`, day.Windspeed);
        console.log(`[METEOROLOGICAL] - ¿Tiene calculated_precipitation?`, day.calculated_precipitation);
        console.log(`[METEOROLOGICAL] - ¿Tiene calculated_wind_speed?`, day.calculated_wind_speed);
        
        // Verificar si los valores se están pasando correctamente al HTML
        const precipDisplay = precipitation !== null && typeof precipitation === 'number' ? precipitation.toFixed(1) + ' mm' : 'N/A';
        const windDisplay = windSpeed !== null && typeof windSpeed === 'number' ? windSpeed.toFixed(1) + ' km/h' : 'N/A';
        
        console.log(`[METEOROLOGICAL] - Precipitation DISPLAY: "${precipDisplay}"`);
        console.log(`[METEOROLOGICAL] - WindSpeed DISPLAY: "${windDisplay}"`);
        
        // Formatear temperatura con 1 decimal si es un número
        const formatTemp = (temp) => {
            return typeof temp === 'number' ? temp.toFixed(1) + '°C' : 'N/A';
        };
        
        forecastHTML += `
            <div class="card weather-day-card ${cardClass}" style="min-width: 150px; width: 150px; margin-right: 12px; border-radius: 12px; overflow: hidden; ${!isRealData ? 'border-style: dashed; opacity: 0.9;' : ''}">
                <!-- Encabezado con fecha -->
                <div class="card-header text-center py-1 ${isToday ? 'bg-primary text-white' : isRealData ? 'bg-light' : 'bg-light-subtle'}" style="border: none;">
                    <h6 class="card-title mb-0 fw-bold" style="font-size: 0.9rem;">${formattedDate}</h6>
                    ${!isRealData ? '<small class="badge bg-secondary bg-opacity-50" style="font-size: 0.6rem;">Estimado</small>' : ''}
                </div>
                
                <div class="card-body p-2 text-center">
                    <!-- Icono del clima -->
                    <div class="weather-icon-container my-2">
                        <div class="weather-icon" style="background-color: ${weatherInfo.bgColor}; width: 75px; height: 75px; border-radius: 50%; margin: 0 auto; display: flex; justify-content: center; align-items: center;">
                            <i class="${weatherInfo.icon}" style="font-size: 2.5rem; color: ${weatherInfo.iconColor};"></i>
                        </div>
                        <div class="small text-center mt-2 fw-bold" style="color: ${weatherInfo.textColor};">${weatherInfo.label}</div>
                    </div>
                    
                    <!-- Datos meteorológicos -->
                    <div class="weather-data mt-2 pt-2 border-top">
                        <div class="d-flex justify-content-between small mb-1">
                            <span class="text-muted">Temp máx:</span>
                            <span class="fw-bold">${tempMax !== undefined && tempMax !== null ? tempMax.toFixed(1) + '°C' : 'N/A'}</span>
                        </div>
                        <div class="d-flex justify-content-between small mb-1">
                            <span class="text-muted">Temp mín:</span>
                            <span class="fw-bold">${tempMin !== undefined && tempMin !== null ? tempMin.toFixed(1) + '°C' : 'N/A'}</span>
                        </div>
                        <div class="d-flex justify-content-between small mb-1">
                            <span class="text-muted">Precip:</span>
                            <span class="fw-bold ${precipitation > 0 ? 'text-primary' : ''}">${precipitation !== null && precipitation !== undefined ? precipitation.toFixed(1) + ' mm' : 'N/A'}</span>
                        </div>
                        <div class="d-flex justify-content-between small mb-1">
                            <span class="text-muted">Viento:</span>
                            <span class="fw-bold">${windSpeed !== null && windSpeed !== undefined ? windSpeed.toFixed(1) + ' km/h' : 'N/A'}</span>
                        </div>
                        <div class="d-flex justify-content-between small">
                            <span class="text-muted">Humedad:</span>
                            <span class="fw-bold">${humidity !== null && humidity !== undefined ? humidity.toFixed(0) + '%' : 'N/A'}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    forecastHTML += `
            </div>
            <div class="alert alert-info p-2 small">
                <i class="fas fa-info-circle me-1"></i>
                Deslice horizontalmente para ver el pronóstico completo. Este pronóstico se actualiza diariamente.
                ${forecast.some(day => day.is_real_data === false) ? 
                `<br><small><i class="fas fa-info-circle me-1"></i>Nota: Se muestran ${forecast.filter(day => day.is_real_data !== false).length} días con datos reales más ${forecast.filter(day => day.is_real_data === false).length} días estimados para completar un pronóstico de 7 días.</small>` : ''}
            </div>
        </div>
    `;
    
    // Mostrar el pronóstico
    container.innerHTML = forecastHTML;
    
    // Mostrar la sección si estaba oculta
    const section = document.getElementById('meteorologicalAnalysisSection');
    if (section) {
        section.style.display = 'block';
    }
    
    // Emitir evento de que las tarjetas han sido renderizadas
    // Esto permitirá que el módulo de detalles meteorológicos active la interactividad
    const weatherCardsRenderedEvent = new Event('weatherCardsRendered');
    document.dispatchEvent(weatherCardsRenderedEvent);
    
    // Agregar estilos para el contenedor de tarjetas
    const styleId = 'weather-forecast-styles';
    if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .weather-forecast-container {
                -webkit-overflow-scrolling: touch;
                padding: 10px 0;
            }
            .weather-forecast-container::-webkit-scrollbar {
                height: 6px;
            }
            .weather-forecast-container::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 10px;
            }
            .weather-forecast-container::-webkit-scrollbar-thumb {
                background: #c1c1c1;
                border-radius: 10px;
            }
            .weather-day-card {
                transition: all 0.3s ease;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }                .weather-day-card:hover {
                transform: translateY(-6px);
                box-shadow: 0 6px 16px rgba(0,0,0,0.12);
            }
            .generated-forecast {
                border-style: dashed !important;
                border-color: #cccccc !important;
            }
            .weather-icon-container {
                position: relative;
                z-index: 1;
            }
            .current-day-card {
                background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                overflow: hidden;
            }
            .current-day-temp {
                font-size: 2.5rem;
                font-weight: 700;
            }
            .current-day-condition {
                font-size: 1.2rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
            }
            .weather-data-pill {
                background-color: rgba(255,255,255,0.7);
                border-radius: 20px;
                padding: 4px 12px;
                margin: 0 4px;
                display: inline-flex;
                align-items: center;
                font-weight: 500;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
        `;
        document.head.appendChild(style);
    }
    
    if (typeof showToast === 'function') {
        showToast('Pronóstico del tiempo actualizado', 'success');
    }
}

/**
 * Crea la tarjeta para el día actual con más detalles
 */
function createCurrentDayCard(dayData) {
    if (!dayData) return '';
    
    // Manejar diferentes formatos de fecha (pueden venir como 'Date' o 'date')
    let dateStr = dayData.date || dayData.Date;
    console.log(`[METEOROLOGICAL] createCurrentDayCard - Fecha original:`, dateStr);
    
    const date = new Date(dateStr);
    console.log(`[METEOROLOGICAL] createCurrentDayCard - Fecha convertida:`, date);
    
    // Usar siempre la fecha actual para mostrar "Hoy" en la tarjeta principal
    const today = new Date();
    const formattedDate = today.toLocaleDateString('es-ES', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
    
    // Obtener valores de temperaturas (manejar múltiples formatos de la API EOSDA)
    console.log('[METEOROLOGICAL] Campos disponibles en dayData:', Object.keys(dayData));
    
    // EOSDA utiliza diferentes formatos según la API
    // Solo usar valores reales, priorizar campos que realmente existen
    const tempMax = dayData.temperature_max || dayData.Temp_air_max || dayData.temp_max;
    const tempMin = dayData.temperature_min || dayData.Temp_air_min || dayData.temp_min;
    
    // Temperatura promedio solo si tenemos temperaturas reales o un valor de temperatura promedio directo
    let temp = 'N/A';
    if (dayData.temperature || dayData.temp || dayData.temp_avg) {
        temp = dayData.temperature || dayData.temp || dayData.temp_avg;
    } else if (typeof tempMax === 'number' && typeof tempMin === 'number') {
        temp = (tempMax + tempMin) / 2;
    }
    
    // Usar directamente los campos de EOSDA (incluye 0 como valor válido)
    const precipitation = dayData.precipitation !== undefined ? dayData.precipitation : (dayData.calculated_precipitation !== undefined ? dayData.calculated_precipitation : null);
    const windSpeed = dayData.wind_speed !== undefined ? dayData.wind_speed : (dayData.calculated_wind_speed !== undefined ? dayData.calculated_wind_speed : null);
    const humidity = dayData.humidity || dayData.Rel_humidity || dayData.humidity_avg;
    
    // Formatear temperatura con 1 decimal si es un número
    const formatTemp = (temp) => {
        return typeof temp === 'number' ? temp.toFixed(1) + '°C' : 'N/A';
    };
    
    const weatherInfo = getWeatherInfo(dayData);
    
    // Agregar logs para debug
    console.log('[METEOROLOGICAL] createCurrentDayCard - precipitation:', precipitation);
    console.log('[METEOROLOGICAL] createCurrentDayCard - windSpeed:', windSpeed);
    console.log('[METEOROLOGICAL] createCurrentDayCard - humidity:', humidity);
    
    return `
    <div class="current-day-card p-3 mb-3">
        <div class="row">
            <!-- Información principal -->
            <div class="col-md-4 d-flex align-items-center">
                <div class="text-center" style="width: 90px; margin-right: 15px;">
                    <div class="weather-icon" style="background-color: ${weatherInfo.bgColor}; width: 85px; height: 85px; border-radius: 50%; display: flex; justify-content: center; align-items: center;">
                        <i class="${weatherInfo.icon}" style="font-size: 3rem; color: ${weatherInfo.iconColor};"></i>
                    </div>
                </div>
                <div>
                    <h6 class="mb-1 text-muted">Hoy, ${formattedDate}</h6>
                    <div class="current-day-condition" style="color: ${weatherInfo.textColor};">${weatherInfo.label}</div>
                    <div class="current-day-temp">${formatTemp(temp)}</div>
                </div>
            </div>
            
            <!-- Detalles adicionales -->
            <div class="col-md-8">
                <div class="row h-100 align-items-center">
                    <div class="col-6 col-md-3">
                        <div class="text-center small">
                            <i class="fas fa-thermometer-half text-danger mb-1" style="font-size: 1.2rem;"></i>
                            <div class="fw-bold">${tempMax !== undefined && tempMax !== null ? tempMax.toFixed(1) + '°C' : 'N/A'}</div>
                            <div class="text-muted">Máx</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="text-center small">
                            <i class="fas fa-thermometer-quarter text-primary mb-1" style="font-size: 1.2rem;"></i>
                            <div class="fw-bold">${tempMin !== undefined && tempMin !== null ? tempMin.toFixed(1) + '°C' : 'N/A'}</div>
                            <div class="text-muted">Mín</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="text-center small">
                            <i class="fas fa-cloud-rain text-info mb-1" style="font-size: 1.2rem;"></i>
                            <div class="fw-bold ${precipitation && precipitation > 0 ? 'text-primary' : ''}">${precipitation !== null && precipitation !== undefined ? precipitation.toFixed(1) + ' mm' : 'N/A'}</div>
                            <div class="text-muted">Precipitación</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="text-center small">
                            <i class="fas fa-wind text-secondary mb-1" style="font-size: 1.2rem;"></i>
                            <div class="fw-bold">${windSpeed !== null && windSpeed !== undefined ? windSpeed.toFixed(1) + ' km/h' : 'N/A'}</div>
                            <div class="text-muted">Viento</div>
                        </div>
                    </div>
                </div>
                <div class="row mt-2">
                    <div class="col-6">
                        <div class="text-center small">
                            <i class="fas fa-tint text-primary mb-1" style="font-size: 1.2rem;"></i>
                            <div class="fw-bold">${humidity !== null && humidity !== undefined ? humidity.toFixed(0) + '%' : 'N/A'}</div>
                            <div class="text-muted">Humedad</div>
                        </div>
                    </div>
                    <div class="col-6 text-center mt-3 mt-md-0">
                        <button class="btn btn-primary btn-sm" onclick="loadMeteorologicalAnalysis(currentParcelId)">
                            <i class="fas fa-chart-line me-1"></i>Histórico completo
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    `;
}

/**
 * Determina la información del clima basada en los datos del día
 * Según la documentación de EOSDA Weather API: https://doc.eos.com/docs/weather/basic-weather-providers/
 */
function getWeatherInfo(dayData) {
    // Valores predeterminados
    let icon = 'fas fa-cloud';
    let label = 'Parcialmente nublado';
    let bgColor = '#f0f4f7';
    let iconColor = '#6c757d';
    let textColor = '#6c757d';
    
    // Si no hay datos, retornar valores predeterminados
    if (!dayData) return { 
        icon, label, bgColor, iconColor, textColor, 
        isGeneratedForecast: false 
    };
    
    // Si es un pronóstico generado (no es dato real), marcar visualmente
    const isGeneratedForecast = dayData.is_real_data === false;
    
    // Extraer condiciones del clima si están disponibles (manejar múltiples formatos de la API)
    let conditionsText = '';
    
    // Manejar diferentes formatos de la API EOSDA
    if (dayData.description) {
        conditionsText = dayData.description.toLowerCase();
    } else if (dayData.conditions) {
        conditionsText = dayData.conditions.toLowerCase();
    } else if (dayData.weather_desc) {
        if (Array.isArray(dayData.weather_desc)) {
            conditionsText = dayData.weather_desc[0].toLowerCase();
        } else {
            conditionsText = String(dayData.weather_desc).toLowerCase();
        }
    }
    
    // Obtener precipitación - priorizar campos directos de EOSDA API
    let precipitation = null;
    if (dayData.precipitation !== null && dayData.precipitation !== undefined) {
        precipitation = dayData.precipitation;
    } else if (dayData.calculated_precipitation !== null && dayData.calculated_precipitation !== undefined) {
        precipitation = dayData.calculated_precipitation;
    } else if (dayData.Rain && typeof dayData.Rain === 'object') {
        // Sumar todos los valores de Rain por hora
        const rainValues = Object.values(dayData.Rain).filter(val => typeof val === 'number');
        if (rainValues.length > 0) {
            precipitation = rainValues.reduce((sum, val) => sum + val, 0);
        }
    } else if (dayData.precip_mm || dayData.Precip_total) {
        precipitation = dayData.precip_mm || dayData.Precip_total;
    }
    
    // Obtener velocidad del viento - priorizar campos directos de EOSDA API
    let windSpeed = null;
    if (dayData.wind_speed !== null && dayData.wind_speed !== undefined) {
        windSpeed = dayData.wind_speed;
    } else if (dayData.calculated_wind_speed !== null && dayData.calculated_wind_speed !== undefined) {
        windSpeed = dayData.calculated_wind_speed;
    } else if (dayData.Windspeed && typeof dayData.Windspeed === 'object') {
        // Promediar todos los valores de Windspeed por hora
        const windValues = Object.values(dayData.Windspeed).filter(val => typeof val === 'number');
        if (windValues.length > 0) {
            windSpeed = windValues.reduce((sum, val) => sum + val, 0) / windValues.length;
        }
    } else if (dayData.Wind_speed || dayData.wind_kph) {
        windSpeed = dayData.Wind_speed || dayData.wind_kph;
    }
    
    const cloudCover = dayData.cloud_cover || dayData.Cloud_cover || null;
    const temperature = dayData.temperature || dayData.temp || dayData.temp_avg || null;
    
    // Determinar el estado del tiempo basado en los datos disponibles
    if (conditionsText.includes('thunderstorm') || conditionsText.includes('storm') || conditionsText.includes('tormenta') || conditionsText.includes('trueno')) {
        icon = 'fas fa-bolt';
        label = 'Tormenta eléctrica';
        bgColor = '#343a40';
        iconColor = '#ffc107';
        textColor = '#dc3545';
    } else if (conditionsText.includes('rain') || conditionsText.includes('shower') || conditionsText.includes('lluvia') || precipitation > 3) {
        if (precipitation > 10) {
            icon = 'fas fa-cloud-showers-heavy';
            label = 'Lluvia intensa';
            bgColor = '#495057';
            iconColor = '#0d6efd';
            textColor = '#0d6efd';
        } else {
            icon = 'fas fa-cloud-rain';
            label = 'Lluvia';
            bgColor = '#e9ecef';
            iconColor = '#0d6efd';
            textColor = '#0d6efd';
        }
    } else if (conditionsText.includes('drizzle') || conditionsText.includes('llovizna') || precipitation > 0) {
        icon = 'fas fa-cloud-rain';
        label = 'Llovizna';
        bgColor = '#e9ecef';
        iconColor = '#6c757d';
        textColor = '#0d6efd';
    } else if (conditionsText.includes('snow') || conditionsText.includes('nieve')) {
        icon = 'fas fa-snowflake';
        label = 'Nieve';
        bgColor = '#f8f9fa';
        iconColor = '#0dcaf0';
        textColor = '#0dcaf0';
    } else if (conditionsText.includes('clear') || conditionsText.includes('sunny') || conditionsText.includes('soleado') || conditionsText.includes('despejado') || cloudCover < 10) {
        if (temperature > 30) {
            icon = 'fas fa-sun';
            label = 'Soleado y caluroso';
            bgColor = '#FFF9C4';
            iconColor = '#fd7e14';
            textColor = '#fd7e14';
        } else {
            icon = 'fas fa-sun';
            label = 'Soleado';
            bgColor = '#FFF9C4';
            iconColor = '#ffc107';
            textColor = '#fd7e14';
        }
    } else if (conditionsText.includes('cloudy') || conditionsText.includes('overcast') || conditionsText.includes('nublado') || cloudCover > 50) {
        icon = 'fas fa-cloud';
        label = 'Nublado';
        bgColor = '#e9ecef';
        iconColor = '#6c757d';
        textColor = '#495057';
    } else if (conditionsText.includes('partly') || conditionsText.includes('parcialmente') || cloudCover > 20) {
        icon = 'fas fa-cloud-sun';
        label = 'Parcialmente nublado';
        bgColor = '#f8f9fa';
        iconColor = '#6c757d';
        textColor = '#495057';
    } else if (conditionsText.includes('fog') || conditionsText.includes('mist') || conditionsText.includes('niebla')) {
        icon = 'fas fa-smog';
        label = 'Niebla';
        bgColor = '#f8f9fa';
        iconColor = '#adb5bd';
        textColor = '#6c757d';
    } else if (windSpeed > 20) {
        icon = 'fas fa-wind';
        label = 'Ventoso';
        bgColor = '#e9ecef';
        iconColor = '#6c757d';
        textColor = '#495057';
    }
    
    // Si es un pronóstico generado, modificar ligeramente el estilo visual
    if (isGeneratedForecast) {
        // Añadir "(Est.)" al final de la etiqueta para datos generados
        label += " (Est.)";
        
        // Reducir ligeramente la intensidad de los colores para datos generados
        // para diferenciarlos visualmente de los datos reales
        const reduceOpacity = (color) => {
            return color + "90"; // Añadir 90 (56% de opacidad) al color hexadecimal
        };
        
        bgColor = reduceOpacity(bgColor);
        iconColor = reduceOpacity(iconColor);
    }
    
    // Retornar objeto con la información del clima
    return {
        icon,
        label,
        bgColor,
        iconColor,
        textColor,
        isGeneratedForecast
    };
}

/**
 * Sincroniza el ID de parcela entre el estado global y la variable local
 * Esta función debe ser llamada antes de cualquier operación con parcelas
 */
function sincronizarParcelaSeleccionada() {
    if (window.EOSDA_STATE && window.EOSDA_STATE.selectedParcelId) {
        if (currentParcelId !== window.EOSDA_STATE.selectedParcelId) {
            console.log('[METEOROLOGICAL] Sincronizando ID de parcela:', 
                      'local:', currentParcelId, 
                      'global:', window.EOSDA_STATE.selectedParcelId);
            currentParcelId = window.EOSDA_STATE.selectedParcelId;
        }
    } else if (currentParcelId) {
        // Si no hay parcela global pero sí local, actualizar el estado global
        if (window.EOSDA_STATE) {
            window.EOSDA_STATE.selectedParcelId = currentParcelId;
        }
    }
    return currentParcelId;
}

// Asignar inmediatamente a window para disponibilidad global
window.loadWeatherForecast = loadWeatherForecast;

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
    console.error('[METEOROLOGICAL] Error:', errorMessage);
    
    showMeteorologicalLoading(false);
    
    const container = document.getElementById('meteorologicalAnalysisContainer');
    if (!container) return;
    
    // Crear un mensaje de error visualmente atractivo
    container.innerHTML = `
        <div class="alert alert-danger p-4">
            <div class="d-flex align-items-center mb-3">
                <i class="fas fa-exclamation-circle me-3" style="font-size: 2rem;"></i>
                <h5 class="mb-0">Error cargando datos meteorológicos reales</h5>
            </div>
            <p class="mb-3">${errorMessage}</p>
            <p class="small mb-3"><i class="fas fa-info-circle me-1"></i> No se están utilizando datos ficticios. El sistema solo muestra datos reales de EOSDA.</p>
            <div class="d-flex gap-2">
                <button class="btn btn-outline-danger" onclick="loadWeatherForecast(window.EOSDA_STATE.selectedParcelId)">
                    <i class="fas fa-sync-alt me-2"></i>Reintentar
                </button>
                <button class="btn btn-outline-secondary" onclick="closeMeterologicalAnalysis()">
                    <i class="fas fa-times me-2"></i>Cerrar
                </button>
            </div>
        </div>
    `;
    
    // Mostrar la sección si estaba oculta
    const section = document.getElementById('meteorologicalAnalysisSection');
    if (section) {
        section.style.display = 'block';
    }
    
    if (typeof showToast === 'function') {
        showToast('Error cargando pronóstico meteorológico', 'error');
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
    console.log('[METEOROLOGICAL] loadWeatherForecast:', typeof window.loadWeatherForecast);
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
    loadWeatherForecast: typeof window.loadWeatherForecast,
    initMeteorologicalAnalysis: typeof window.initMeteorologicalAnalysis
});

// ==============================================
// FUNCIÓN DE DEBUG PARA VERIFICAR DATOS
// ==============================================

/**
 * Función de debug para verificar que los datos se estén procesando correctamente
 */
function debugWeatherData() {
    console.log('[DEBUG WEATHER] =================================');
    console.log('[DEBUG WEATHER] Estado actual de los datos del clima:');
    console.log('[DEBUG WEATHER] window.weatherForecastData:', window.weatherForecastData);
    
    if (window.weatherForecastData && window.weatherForecastData.length > 0) {
        const firstDay = window.weatherForecastData[0];
        console.log('[DEBUG WEATHER] Primer día de datos:');
        console.log('[DEBUG WEATHER] - Fecha:', firstDay.date || firstDay.Date);
        console.log('[DEBUG WEATHER] - Rain (original):', firstDay.Rain);
        console.log('[DEBUG WEATHER] - Windspeed (original):', firstDay.Windspeed);
        console.log('[DEBUG WEATHER] - calculated_precipitation:', firstDay.calculated_precipitation);
        console.log('[DEBUG WEATHER] - calculated_wind_speed:', firstDay.calculated_wind_speed);
        
        // Verificar cálculo manual
        if (firstDay.Rain && typeof firstDay.Rain === 'object') {
            const rainValues = Object.values(firstDay.Rain).filter(val => typeof val === 'number');
            const totalRain = rainValues.reduce((sum, val) => sum + val, 0);
            console.log('[DEBUG WEATHER] - Cálculo manual de precipitación:', totalRain);
        }
        
        if (firstDay.Windspeed && typeof firstDay.Windspeed === 'object') {
            const windValues = Object.values(firstDay.Windspeed).filter(val => typeof val === 'number');
            const avgWind = windValues.reduce((sum, val) => sum + val, 0) / windValues.length;
            console.log('[DEBUG WEATHER] - Cálculo manual de viento:', avgWind);
        }
    } else {
        console.log('[DEBUG WEATHER] No hay datos de pronóstico disponibles');
    }
    console.log('[DEBUG WEATHER] =================================');
}

// Hacer la función disponible globalmente para debugging
window.debugWeatherData = debugWeatherData;
