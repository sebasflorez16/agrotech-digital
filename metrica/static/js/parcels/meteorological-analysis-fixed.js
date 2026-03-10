/**
 * Análisis Meteorológico - Datos EOSDA Reales
 * Módulo optimizado para análisis meteorológico con zoom y navegación
 * Incluye avisos de actualización y datos únicamente meteorológicos
 */

// Registrar plugin de zoom de Chart.js
Chart.register(ChartZoom);

let meteorologicalChartInstance = null;
let currentParcelId = null;
let meteorologicalData = [];

/**
 * Inicializa el módulo de análisis meteorológico
 */
function initMeteorologicalAnalysis() {
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
    window.exportMeteorologicalData = function() {
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
    };
    
    window.refreshMeteorologicalAnalysis = function() {
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
    };
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
    
    // Construir URL - usar config.js centralizado
    const baseUrl = (window.AGROTECH_CONFIG && window.AGROTECH_CONFIG.API_BASE)
        ? window.AGROTECH_CONFIG.API_BASE
        : window.location.origin;
    const endpoint = `${baseUrl}/api/parcels/parcel/${parcelId}/ndvi-weather-comparison/?refresh=${Date.now()}`;
    
    console.log(`[METEOROLOGICAL] Haciendo petición de actualización a: ${endpoint}`);
    
    fetch(endpoint, {
        method: 'GET',
        headers: window.getAuthHeaders ? window.getAuthHeaders() : {
            'Authorization': `Bearer ${getAuthToken()}`,
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
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
 * Carga el análisis meteorológico para una parcela (carga inicial)
 */
function loadMeteorologicalAnalysis(parcelId) {
    if (!parcelId) {
        console.warn('[METEOROLOGICAL] No hay parcela seleccionada');
        return;
    }
    
    currentParcelId = parcelId;
    console.log(`[METEOROLOGICAL] Cargando análisis para parcela ${parcelId}`);
    
    showMeteorologicalLoading(true);
    
    // Construir URL - usar config.js centralizado
    const baseUrl = (window.AGROTECH_CONFIG && window.AGROTECH_CONFIG.API_BASE)
        ? window.AGROTECH_CONFIG.API_BASE
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
        console.log('[METEOROLOGICAL] Datos recibidos del backend:', data);
        
        // Procesar datos reales de EOSDA
        processRealEOSDAData(data);
        
    })
    .catch(error => {
        console.error('[METEOROLOGICAL] Error cargando análisis:', error);
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
            onDoubleClick: function(event, elements) {
                // Resetear zoom y pan con doble clic
                this.resetZoom();
                if (typeof showToast === 'function') {
                    showToast('🔄 Vista restablecida', 'info');
                }
            },
            plugins: {
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true,
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'x',
                        onZoomComplete: function({chart}) {
                            if (typeof showToast === 'function') {
                                showToast('🔍 Zoom aplicado. Doble clic para resetear', 'info');
                            }
                        }
                    },
                    pan: {
                        enabled: true,
                        mode: 'x',
                        threshold: 10,
                        onPanComplete: function({chart}) {
                            if (typeof showToast === 'function') {
                                showToast('↔️ Vista desplazada. Doble clic para resetear', 'info');
                            }
                        }
                    }
                },
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
                    text: 'Análisis Comparativo Multi-Variable - Datos EOSDA Reales',
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
                            return ['', '💡 Usa la rueda del mouse para hacer zoom', '↔️ Arrastra para desplazarte', '🔄 Doble clic para resetear vista'];
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
                        text: 'Período de Análisis (Año 2025) - 🔍 Zoom disponible',
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
        setTimeout(() => {
            showToast('🔍 Gráfico cargado: Zoom con rueda del mouse, arrastra para desplazar, doble clic para resetear', 'info');
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
 * Actualiza las métricas meteorológicas útiles para la industria agrícola
 */
function updateCorrelations(meteorologicalMetrics) {
    console.log('[METEOROLOGICAL] Actualizando métricas agrícolas:', meteorologicalMetrics);
    
    if (!meteorologicalMetrics || Object.keys(meteorologicalMetrics).length === 0) {
        console.warn('[METEOROLOGICAL] No hay métricas meteorológicas disponibles');
        return;
    }
    
    // Métrica 1: Índice de Estrés por Calor
    const avgTempMax = meteorologicalMetrics.avg_temp_max || 0;
    const heatStressIndex = calculateHeatStressFromTemp(avgTempMax);
    
    const heatElem = document.getElementById('correlationPrecipitation');
    const heatStrengthElem = document.getElementById('correlationStrengthPrecip');
    const heatProgress = document.getElementById('precipitationProgressBar');
    
    if (heatElem && heatStrengthElem) {
        heatElem.textContent = avgTempMax.toFixed(1) + '°C';
        heatElem.style.color = heatStressIndex.risk === 'Alto' ? '#D32F2F' : heatStressIndex.risk === 'Medio' ? '#F57C00' : '#2E7D32';
        
        heatStrengthElem.textContent = heatStressIndex.risk;
        heatStrengthElem.className = `badge ${heatStressIndex.risk === 'Alto' ? 'bg-danger' : heatStressIndex.risk === 'Medio' ? 'bg-warning' : 'bg-success'}`;
        
        if (heatProgress) {
            const progressValue = (avgTempMax / 40) * 100;
            heatProgress.style.width = `${Math.min(progressValue, 100)}%`;
            heatProgress.className = `progress-bar ${heatStressIndex.risk === 'Alto' ? 'bg-danger' : heatStressIndex.risk === 'Medio' ? 'bg-warning' : 'bg-success'}`;
        }
    }
    
    // Métrica 2: Índice de Precipitación Total
    const totalPrecip = meteorologicalMetrics.total_precipitation || 0;
    const daysWithRain = meteorologicalMetrics.days_with_rain || 0;
    const precipIndex = calculatePrecipitationIndex(totalPrecip, daysWithRain);
    
    const precipElem = document.getElementById('correlationTemperature');
    const precipStrengthElem = document.getElementById('correlationStrengthTemp');
    const precipProgress = document.getElementById('temperatureProgressBar');
    
    if (precipElem && precipStrengthElem) {
        precipElem.textContent = totalPrecip.toFixed(1) + ' mm';
        precipElem.style.color = precipIndex.risk === 'Bajo' ? '#D32F2F' : precipIndex.risk === 'Medio' ? '#F57C00' : '#2E7D32';
        
        precipStrengthElem.textContent = precipIndex.risk;
        precipStrengthElem.className = `badge ${precipIndex.risk === 'Bajo' ? 'bg-danger' : precipIndex.risk === 'Medio' ? 'bg-warning' : 'bg-success'}`;
        
        if (precipProgress) {
            const progressValue = (totalPrecip / 1500) * 100;
            precipProgress.style.width = `${Math.min(progressValue, 100)}%`;
            precipProgress.className = `progress-bar ${precipIndex.risk === 'Bajo' ? 'bg-danger' : precipIndex.risk === 'Medio' ? 'bg-warning' : 'bg-success'}`;
        }
    }
    
    console.log('[METEOROLOGICAL] Métricas agrícolas actualizadas');
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

// Exportar funciones globales
window.initMeteorologicalAnalysis = initMeteorologicalAnalysis;
window.loadMeteorologicalAnalysis = loadMeteorologicalAnalysis;
window.exportMeteorologicalData = exportMeteorologicalData;
window.refreshMeteorologicalAnalysis = refreshMeteorologicalAnalysis;

// Inicializar módulo cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    initMeteorologicalAnalysis();
});

console.log('[METEOROLOGICAL] 🔍 Módulo de análisis meteorológico con zoom cargado correctamente');
console.log('[METEOROLOGICAL] ✅ Datos EOSDA reales confirmados');
console.log('[METEOROLOGICAL] 🔄 Funcionalidad de actualización disponible');
