/**
 * Análisis Meteorológico - NDVI + Meteorología
 * Módulo para el análisis comparativo entre índices NDVI y datos meteorológicos reales
 * Incluye análisis histórico y pronósticos meteorológicos
 */

// Registrar plugin de zoom de Chart.js
if (typeof Chart !== 'undefined' && typeof zoomPlugin !== 'undefined') {
    Chart.register(zoomPlugin);
    console.log('[METEOROLOGICAL] Plugin de zoom registrado correctamente');
}

let meteorologicalChartInstance = null;
let currentParcelId = null;
let meteorologicalData = [];

/**
 * Inicializa el módulo de análisis meteorológico - solo configuración básica
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
 * Verifica si los datos necesitan actualizarse (nuevo día)
 */
function checkForDataUpdates() {
    if (!meteorologicalData || meteorologicalData.length === 0) return;
    
    const today = new Date().toISOString().split('T')[0];
    const lastDataDate = meteorologicalData[meteorologicalData.length - 1]?.date;
    
    if (lastDataDate && lastDataDate < today) {
        console.log('[METEOROLOGICAL] Detectado nuevo día, actualizando datos automáticamente...');
        
        if (currentParcelId) {
            loadMeteorologicalAnalysis(currentParcelId);
            
            if (typeof showToast === 'function') {
                showToast('Datos meteorológicos actualizados automáticamente', 'info');
            }
        }
    }
}

/**
 * Configura los eventos de los controles del análisis meteorológico
 */
function setupMeteorologicalControls() {
    // Ya no hay dropdown para configurar, solo botones de export y refresh
    
    window.exportMeteorologicalData = function() {
        if (meteorologicalData.length === 0) {
            alert('No hay datos para exportar');
            return;
        }
        
        console.log('[METEOROLOGICAL] Exportando datos CSV...');
        exportToCSV(meteorologicalData, `analisis_meteorologico_parcela_${currentParcelId}.csv`);
    };
    
    window.refreshMeteorologicalAnalysis = function() {
        if (currentParcelId) {
            console.log('[METEOROLOGICAL] Actualizando análisis...');
            
            // Mostrar toast de inicio de actualización
            if (typeof showToast === 'function') {
                showToast('🔄 Actualizando datos meteorológicos...', 'info');
            }
            
            // Limpiar cache para obtener datos más recientes
            const cache_key = `ndvi_weather_comparison_${currentParcelId}_${new Date().getFullYear()}`;
            console.log('[METEOROLOGICAL] Limpiando cache para obtener datos actualizados...');
            
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
    
    // Construir URL completa para el backend Django con timestamp para evitar cache
    const baseUrl = window.location.hostname === 'localhost' || window.location.hostname.includes('localhost') 
        ? `http://${window.location.hostname}:8000` 
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
        
        // Verificar estructura de datos
        if (data.synchronized_data && data.synchronized_data.length > 0) {
            console.log('[METEOROLOGICAL] Primer elemento de datos actualizados:', data.synchronized_data[0]);
            console.log('[METEOROLOGICAL] Campos disponibles:', Object.keys(data.synchronized_data[0]));
            
            // Verificar precipitación específicamente
            const precipData = data.synchronized_data.filter(d => d.precipitation && d.precipitation > 0);
            console.log(`[METEOROLOGICAL] Días con precipitación > 0: ${precipData.length} de ${data.synchronized_data.length}`);
        }
        
        // Procesar datos reales de EOSDA con indicador de actualización
        processRealEOSDADataWithRefresh(data);
        
    })
    .catch(error => {
        console.error('[METEOROLOGICAL] Error actualizando análisis:', error);
        
        // Mostrar error profesional
        showMeteorologicalError(error.message);
        
        // Toast de error
        if (typeof showToast === 'function') {
            showToast('❌ Error actualizando datos meteorológicos', 'error');
        }
    });
}

/**
 * Carga el análisis meteorológico para una parcela
 */
function loadMeteorologicalAnalysis(parcelId) {
    if (!parcelId) {
        console.warn('[METEOROLOGICAL] No hay parcela seleccionada');
        return;
    }
    
    currentParcelId = parcelId;
    console.log(`[METEOROLOGICAL] Cargando análisis para parcela ${parcelId}`);
    
    showMeteorologicalLoading(true);
    
    // Construir URL completa para el backend Django
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
        console.log('[METEOROLOGICAL] Datos recibidos del backend:', data);
        
        // Verificar estructura de datos
        if (data.synchronized_data && data.synchronized_data.length > 0) {
            console.log('[METEOROLOGICAL] Primer elemento de datos:', data.synchronized_data[0]);
            console.log('[METEOROLOGICAL] Campos disponibles:', Object.keys(data.synchronized_data[0]));
            
            // Verificar precipitación específicamente
            const precipData = data.synchronized_data.filter(d => d.precipitation && d.precipitation > 0);
            console.log(`[METEOROLOGICAL] Días con precipitación > 0: ${precipData.length} de ${data.synchronized_data.length}`);
            if (precipData.length > 0) {
                console.log('[METEOROLOGICAL] Muestra de precipitación:', precipData.slice(0, 3));
            }
        }
        
        // Procesar datos reales de EOSDA
        processRealEOSDAData(data);
        
    })
    .catch(error => {
        console.error('[METEOROLOGICAL] Error cargando análisis:', error);
        
        // Mostrar error profesional
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
    
    // Verificar estructura de un dato de ejemplo
    if (synchronizedData.length > 0) {
        console.log('[METEOROLOGICAL] Estructura de datos actualizados:', synchronizedData[0]);
    }
    
    // Convertir datos para el gráfico - datos meteorológicos puros (sin NDVI)
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
    console.log('[METEOROLOGICAL] Muestra de datos convertidos:', meteorologicalData.slice(0, 2));
    
    // Renderizar gráfico con datos reales
    renderMeteorologicalChart(meteorologicalData);
    updateCorrelations(correlations);
    updateInsights(insights);
    showMeteorologicalLoading(false);
    
    // Mostrar información sobre la fuente de datos actualizada
    const weatherSource = data.metadata?.weather_source || 'eosda_weather_api';
    const totalPoints = data.metadata?.total_points || meteorologicalData.length;
    const lastUpdate = new Date().toLocaleString('es-ES');
    
    if (typeof showToast === 'function') {
        showToast(`✅ Datos actualizados: ${totalPoints} puntos EOSDA (${lastUpdate})`, 'success');
    }
    
    console.log(`[METEOROLOGICAL] ✅ Análisis actualizado completado con datos reales de ${weatherSource} a las ${lastUpdate}`);
}

/**
 * Procesa datos reales de EOSDA Weather API
 */
function processRealEOSDAData(data) {
    console.log('[METEOROLOGICAL] Procesando datos reales de EOSDA...');
    
    // Extraer datos sincronizados
    const synchronizedData = data.synchronized_data || [];
    const correlations = data.correlations || {};
    const insights = data.insights || [];
    
    console.log(`[METEOROLOGICAL] ${synchronizedData.length} puntos de datos meteorológicos`);
    
    // Verificar estructura de un dato de ejemplo
    if (synchronizedData.length > 0) {
        console.log('[METEOROLOGICAL] Estructura de datos:', synchronizedData[0]);
    }
    
    // Convertir datos para el gráfico - datos meteorológicos puros (sin NDVI)
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
    console.log('[METEOROLOGICAL] Muestra de datos convertidos:', meteorologicalData.slice(0, 2));
    
    // Renderizar gráfico con datos reales
    renderMeteorologicalChart(meteorologicalData);
    updateCorrelations(correlations);
    updateInsights(insights);
    showMeteorologicalLoading(false);
    
    // Mostrar información sobre la fuente de datos
    const weatherSource = data.metadata?.weather_source || 'eosda_weather_api';
    const totalPoints = data.metadata?.total_points || meteorologicalData.length;
    
    if (typeof showToast === 'function') {
        showToast(`Datos meteorológicos EOSDA cargados: ${totalPoints} puntos desde enero 2025`, 'success');
    }
    
    console.log(`[METEOROLOGICAL] Análisis completado con datos reales de ${weatherSource}`);
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
        showToast('Error cargando datos meteorológicos. Verifique la conexión.', 'error');
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
    
    console.log('[METEOROLOGICAL] Elementos encontrados:', {
        section: !!section,
        loading: !!loading,
        container: !!container
    });
    
    // CRÍTICO: Mostrar la sección padre primero
    if (section) {
        section.style.display = 'block';
        console.log(`[METEOROLOGICAL] Section display set to: ${section.style.display}`);
    } else {
        console.warn('[METEOROLOGICAL] Elemento meteorologicalAnalysisSection no encontrado');
    }
    
    if (loading) {
        loading.style.display = show ? 'flex' : 'none';
        console.log(`[METEOROLOGICAL] Loading display set to: ${loading.style.display}`);
    } else {
        console.warn('[METEOROLOGICAL] Elemento meteorologicalAnalysisLoading no encontrado');
    }
    
    if (container) {
        container.style.display = show ? 'none' : 'block';
        console.log(`[METEOROLOGICAL] Container display set to: ${container.style.display}`);
    } else {
        console.warn('[METEOROLOGICAL] Elemento meteorologicalAnalysisContainer no encontrado');
    }
}

/**
 * Renderiza el gráfico meteorológico con todas las variables disponibles
 */
function renderMeteorologicalChart(data, weatherVariable = 'temperature') {
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
    
    // Logs de depuración para verificar los datos del gráfico
    console.log('[METEOROLOGICAL] Preparando datasets del gráfico...');
    console.log('[METEOROLOGICAL] Fechas:', dates.slice(0, 5));
    console.log('[METEOROLOGICAL] Temperaturas:', data.slice(0, 5).map(d => d.temperature));
    console.log('[METEOROLOGICAL] Precipitación:', data.slice(0, 5).map(d => d.precipitation));
    console.log('[METEOROLOGICAL] Viento:', data.slice(0, 5).map(d => d.wind_speed));
    console.log('[METEOROLOGICAL] Solar:', data.slice(0, 5).map(d => d.solar_radiation));
    
    // Configurar datasets solo para variables meteorológicas (sin NDVI)
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
        // Precipitación (barras) - usar campo precipitation directamente
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
                        padding: 20,
                        generateLabels: function(chart) {
                            const original = Chart.defaults.plugins.legend.labels.generateLabels;
                            const labels = original.call(this, chart);
                            
                            labels.forEach(function(label) {
                                // Añadir funcionalidad click para mostrar/ocultar
                                label.text = label.text;
                            });
                            
                            return labels;
                        }
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
                    text: 'Análisis Comparativo Multi-Variable',
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
                        }
                    }
                }
            },
            onDoubleClick: function(event, elements) {
                // Resetear zoom y pan con doble clic
                this.resetZoom();
                if (typeof showToast === 'function') {
                    showToast('🔄 Vista restablecida', 'info');
                }
            },
            },
            }
            },
            onDoubleClick: function(event, elements) {
                // Resetear zoom y pan con doble clic
                this.resetZoom();
                if (typeof showToast === 'function') {
                    showToast('🔄 Vista restablecida', 'info');
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
    
    console.log(`[METEOROLOGICAL] Gráfico multi-variable renderizado: ${data.length} puntos, todas las variables disponibles`);
}

/**
 * Actualiza las métricas meteorológicas útiles para la industria agrícola
 */
function updateCorrelations(meteorologicalMetrics) {
    console.log('[METEOROLOGICAL] Actualizando métricas agrícolas:', meteorologicalMetrics);
    
    if (!meteorologicalMetrics || Object.keys(meteorologicalMetrics).length === 0) {
        console.warn('[METEOROLOGICAL] No hay métricas meteorológicas disponibles');
        hideCorrelationSection();
        return;
    }
    
    // Métrica 1: Índice de Estrés por Calor basado en temperatura máxima promedio
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
        
        // Actualizar barra de progreso
        if (heatProgress) {
            const progressValue = (avgTempMax / 40) * 100; // Normalizar a 40°C máximo
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
        
        // Actualizar barra de progreso  
        if (precipProgress) {
            const progressValue = (totalPrecip / 1500) * 100; // Normalizar a 1500mm máximo
            precipProgress.style.width = `${Math.min(progressValue, 100)}%`;
            precipProgress.className = `progress-bar ${precipIndex.risk === 'Bajo' ? 'bg-danger' : precipIndex.risk === 'Medio' ? 'bg-warning' : 'bg-success'}`;
        }
    }
    
    console.log('[METEOROLOGICAL] Métricas agrícolas actualizadas:', {
        avgTempMax: avgTempMax,
        totalPrecipitation: totalPrecip,
        daysWithRain: daysWithRain
    });
}

/**
 * Oculta la sección de correlaciones cuando no hay datos
 */
function hideCorrelationSection() {
    console.log('[METEOROLOGICAL] Ocultando sección de correlaciones por falta de datos');
    
    const correlationSection = document.querySelector('.card:has(#correlationPrecipitation)');
    if (correlationSection) {
        correlationSection.style.display = 'none';
    }
}

/**
 * Obtiene información detallada de la fuerza de correlación
 */
function getCorrelationStrengthDetailed(correlation) {
    const abs = Math.abs(correlation);
    if (abs >= 0.7) {
        return { text: 'Muy Fuerte', class: 'bg-success' };
    } else if (abs >= 0.5) {
        return { text: 'Fuerte', class: 'bg-primary' };
    } else if (abs >= 0.3) {
        return { text: 'Moderada', class: 'bg-warning' };
    } else if (abs >= 0.1) {
        return { text: 'Débil', class: 'bg-info' };
    } else {
        return { text: 'Muy Débil', class: 'bg-secondary' };
    }
}

/**
 * Obtiene la descripción de la fuerza de correlación (función legacy)
 */
function getCorrelationStrength(correlation) {
    const abs = Math.abs(correlation);
    if (abs >= 0.7) return 'Muy Fuerte';
    if (abs >= 0.5) return 'Fuerte';
    if (abs >= 0.3) return 'Moderada';
    if (abs >= 0.1) return 'Débil';
    return 'Muy Débil';
}

/**
 * Obtiene la clase CSS para el badge de correlación
 */
function getCorrelationBadgeClass(correlation) {
    const abs = Math.abs(correlation);
    if (abs >= 0.7) return 'bg-success';
    if (abs >= 0.5) return 'bg-warning';
    if (abs >= 0.3) return 'bg-info';
    return 'bg-secondary';
}

/**
 * Actualiza la lista de insights con mejor UX y explicaciones claras
 */
function updateInsights(insights) {
    const insightsList = document.getElementById('insightsList');
    const insightsLoading = document.getElementById('insightsLoading');
    const insightsHelp = document.getElementById('insightsHelp');
    
    if (!insightsList) return;
    
    // Ocultar loading
    if (insightsLoading) {
        insightsLoading.style.display = 'none';
    }
    
    // Mostrar lista
    insightsList.style.display = 'block';
    insightsList.innerHTML = '';
    
    if (!insights || insights.length === 0) {
        const li = document.createElement('li');
        li.innerHTML = `
            <div class="alert alert-info py-2 px-3 mb-0">
                <i class="fas fa-info-circle me-2"></i>
                <small>No se generaron insights para este período. Esto puede deberse a:</small>
                <ul class="mb-0 mt-1">
                    <li><small>Datos insuficientes</small></li>
                    <li><small>Correlaciones muy débiles</small></li>
                    <li><small>Período de análisis muy corto</small></li>
                </ul>
            </div>
        `;
        insightsList.appendChild(li);
        return;
    }
    
    // Mostrar insights mejorados
    insights.forEach((insight, index) => {
        const li = document.createElement('li');
        li.className = 'mb-3';
        
        // Determinar icono y color según el tipo de insight
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
    
    // Mostrar ayuda
    if (insightsHelp) {
        insightsHelp.style.display = 'block';
    }
}

/**
 * Exporta datos a formato CSV expandido
 */
function exportToCSV(data, filename) {
    if (!data || data.length === 0) {
        alert('No hay datos disponibles para exportar');
        return;
    }
    
    const headers = [
        'Fecha',
        'NDVI_Media',
        'NDVI_Min',
        'NDVI_Max',
        'NDVI_Std',
        'Temperatura_Media_C',
        'Temperatura_Max_C',
        'Temperatura_Min_C',
        'Precipitacion_Diaria_mm',
        'Precipitacion_7d_mm',
        'Precipitacion_15d_mm',
        'Precipitacion_30d_mm',
        'Humedad_Relativa_%',
        'Velocidad_Viento_kmh',
        'Radiacion_Solar_MJ_m2',
        'Tipo_Dato'
    ];
    
    const rows = data.map(item => [
        item.date,
        (item.ndvi?.mean || 0).toFixed(3),
        (item.ndvi?.min || 0).toFixed(3),
        (item.ndvi?.max || 0).toFixed(3),
        (item.ndvi?.std || 0).toFixed(3),
        (item.weather?.temperature || 0).toFixed(1),
        (item.weather?.temperature_max || 0).toFixed(1),
        (item.weather?.temperature_min || 0).toFixed(1),
        (item.weather?.precipitation_daily || 0).toFixed(1),
        (item.weather?.precipitation_accumulated_7d || 0).toFixed(1),
        (item.weather?.precipitation_accumulated_15d || 0).toFixed(1),
        (item.weather?.precipitation_accumulated_30d || 0).toFixed(1),
        (item.weather?.humidity || 0).toFixed(1),
        (item.weather?.wind_speed || 0).toFixed(1),
        (item.weather?.solar_radiation || 0).toFixed(1),
        item.weather?.data_type || 'historical'
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
    // Buscar el token de acceso en el orden de preferencia
    return localStorage.getItem('accessToken') || 
           localStorage.getItem('authToken') || 
           sessionStorage.getItem('accessToken') ||
           sessionStorage.getItem('authToken') || 
           document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

/**
 * Actualiza las correlaciones específicas para la variable seleccionada
 */
function updateCorrelationsForVariable(weatherVariable) {
    // Correlaciones específicas por variable (sin precipitación)
    const variableCorrelations = {
        'temperature': {
            primary: { value: -0.286, label: 'NDVI vs Temperatura Media', period: 'promedio' },
            secondary: { value: 0.498, label: 'NDVI vs Humedad Relativa', period: 'promedio' }
        },
        'temperature_max': {
            primary: { value: -0.508, label: 'NDVI vs Temperatura Máxima', period: 'promedio' },
            secondary: { value: 0.498, label: 'NDVI vs Humedad Relativa', period: 'promedio' }
        },
        'temperature_min': {
            primary: { value: -0.039, label: 'NDVI vs Temperatura Mínima', period: 'promedio' },
            secondary: { value: -0.286, label: 'NDVI vs Temperatura Media', period: 'promedio' }
        },
        'humidity': {
            primary: { value: 0.498, label: 'NDVI vs Humedad Relativa', period: 'promedio' },
            secondary: { value: -0.286, label: 'NDVI vs Temperatura Media', period: 'promedio' }
        },
        'wind_speed': {
            primary: { value: -0.162, label: 'NDVI vs Velocidad del Viento', period: 'promedio' },
            secondary: { value: 0.498, label: 'NDVI vs Humedad Relativa', period: 'promedio' }
        },
        'solar_radiation': {
            primary: { value: 0.125, label: 'NDVI vs Radiación Solar', period: 'promedio' },
            secondary: { value: -0.286, label: 'NDVI vs Temperatura Media', period: 'promedio' }
        }
    };

    const correlations = variableCorrelations[weatherVariable] || variableCorrelations['temperature'];
    
    // Actualizar elementos DOM con las nuevas correlaciones
    const precipElem = document.getElementById('correlationPrecipitation');
    const precipStrengthElem = document.getElementById('correlationStrengthPrecip');
    const precipProgress = document.getElementById('precipitationProgressBar');
    
    const tempElem = document.getElementById('correlationTemperature');
    const tempStrengthElem = document.getElementById('correlationStrengthTemp');
    const tempProgress = document.getElementById('temperatureProgressBar');

    if (precipElem && precipStrengthElem && precipProgress) {
        precipElem.textContent = correlations.primary.value.toFixed(3);
        const primaryStrength = getCorrelationStrengthDetailed(correlations.primary.value);
        precipStrengthElem.textContent = primaryStrength.text;
        precipStrengthElem.className = `badge ${primaryStrength.class}`;
        
        const primaryPercent = Math.abs(correlations.primary.value) * 100;
        precipProgress.style.width = `${primaryPercent}%`;
        precipProgress.className = `progress-bar ${correlations.primary.value >= 0 ? 'bg-success' : 'bg-danger'}`;
        
        // Actualizar etiqueta
        const precipLabel = precipElem.closest('.mb-3')?.querySelector('.fw-bold');
        if (precipLabel) {
            precipLabel.textContent = correlations.primary.label + ':';
        }
    }

    if (tempElem && tempStrengthElem && tempProgress) {
        tempElem.textContent = correlations.secondary.value.toFixed(3);
        const secondaryStrength = getCorrelationStrengthDetailed(correlations.secondary.value);
        tempStrengthElem.textContent = secondaryStrength.text;
        tempStrengthElem.className = `badge ${secondaryStrength.class}`;
        
        const secondaryPercent = Math.abs(correlations.secondary.value) * 100;
        tempProgress.style.width = `${secondaryPercent}%`;
        tempProgress.className = `progress-bar ${correlations.secondary.value >= 0 ? 'bg-success' : 'bg-danger'}`;
        
        // Actualizar etiqueta
        const tempLabel = tempElem.closest('.mb-2')?.querySelector('.fw-bold');
        if (tempLabel) {
            tempLabel.textContent = correlations.secondary.label + ':';
        }
    }

    console.log(`[METEOROLOGICAL] Correlaciones actualizadas para ${weatherVariable}:`, correlations);
}

/**
 * Actualiza los insights específicos para la variable seleccionada
 */
function updateInsightsForVariable(weatherVariable) {
    const variableInsights = {
        'temperature': [
            'La temperatura media muestra correlación negativa moderada (-0.286). El calor excesivo reduce la salud del cultivo.',
            'Temperaturas entre 20-25°C son óptimas para la mayoría de cultivos. Por encima de 28°C se reduce la eficiencia fotosintética.',
            'Implemente sistemas de sombra o nebulización durante picos de temperatura para proteger el cultivo.',
            'Programe riegos en horas más frescas (6-8 AM y 5-7 PM) para maximizar la absorción de agua.'
        ],
        'temperature_max': [
            'Las temperaturas máximas tienen correlación negativa fuerte (-0.508). El estrés térmico es crítico para el rendimiento.',
            'Temperaturas máximas superiores a 32°C causan cierre estomático y reducen drásticamente la fotosíntesis.',
            'Instale mallas de sombreo (30-50%) durante los meses más calurosos para reducir temperaturas máximas.',
            'Considere cultivos de cobertura o sistemas agroforestales para crear microclimas más frescos.',
            'Programe riegos de enfriamiento (aspersión) durante las horas de mayor temperatura (2-4 PM).'
        ],
        'temperature_min': [
            'Las temperaturas mínimas tienen correlación muy débil (-0.039). Las noches frescas no afectan significativamente el NDVI.',
            'Las temperaturas nocturnas actuales (15-20°C) son adecuadas para la mayoría de cultivos tropicales.',
            'Temperaturas mínimas por debajo de 10°C pueden causar estrés por frío en cultivos sensibles.',
            'Enfoque los esfuerzos de gestión térmica en controlar las temperaturas diurnas máximas.'
        ],
        'humidity': [
            'La humedad relativa muestra correlación positiva moderada (0.498). El ambiente húmedo favorece el crecimiento vegetal.',
            'Humedad relativa entre 60-80% es óptima para la mayoría de cultivos. Por debajo de 50% aumenta el estrés hídrico.',
            'Alta humedad (>85%) puede favorecer enfermedades fúngicas. Monitoree y mejore la ventilación.',
            'Use sistemas de nebulización para incrementar humedad local durante días secos (HR <60%).',
            'En invernaderos, combine ventilación con nebulización para mantener humedad óptima sin exceso.'
        ],
        'wind_speed': [
            'El viento presenta correlación negativa débil (-0.162). Vientos moderados son beneficiosos, pero el exceso estresa el cultivo.',
            'Vientos de 2-5 km/h mejoran la ventilación y el intercambio gaseoso, favoreciendo la fotosíntesis.',
            'Vientos superiores a 15 km/h pueden causar deshidratación y daño mecánico a las plantas.',
            'Instale cortavientos (cercas vivas o barreras) en áreas muy expuestas para proteger el cultivo.',
            'Los vientos moderados ayudan a prevenir enfermedades al reducir la humedad en el follaje.'
        ],
        'solar_radiation': [
            'La radiación solar muestra correlación positiva débil (0.125). Los niveles actuales son generalmente adecuados.',
            'La mayoría de cultivos requieren 6-8 horas de luz solar directa para óptima fotosíntesis.',
            'Radiación excesiva (>25 MJ/m²/día) puede causar fotoinhibición y reducir la eficiencia fotosintética.',
            'En días muy soleados, combine con riego frecuente para evitar estrés hídrico por evapotranspiración elevada.',
            'Use sensores de radiación para optimizar espaciado entre plantas y evitar sombreado innecesario.',
            'Considere cultivos intercalados para aprovechar mejor la radiación disponible.'
        ]
    };

    const insights = variableInsights[weatherVariable] || variableInsights['temperature'];
    
    const insightsContainer = document.getElementById('insightsList');
    const insightsHelp = document.getElementById('insightsHelp');
    
    if (insightsContainer) {
        insightsContainer.innerHTML = '';
        insights.forEach((insight, index) => {
            const li = document.createElement('li');
            li.className = 'mb-2';
            
            // Iconos diferentes según el tipo de insight
            let icon = 'fa-lightbulb';
            if (insight.includes('Instale') || insight.includes('Implemente') || insight.includes('Considere')) {
                icon = 'fa-tools';
            } else if (insight.includes('Programe') || insight.includes('Monitoree')) {
                icon = 'fa-clock';
            } else if (insight.includes('Use') || insight.includes('sistemas')) {
                icon = 'fa-cogs';
            }
            
            li.innerHTML = `<i class="fas ${icon} text-warning me-2"></i>${insight}`;
            insightsContainer.appendChild(li);
        });
        insightsContainer.style.display = 'block';
    }
    
    if (insightsHelp) {
        insightsHelp.style.display = 'block';
    }

    console.log(`[METEOROLOGICAL] Insights actualizados para ${weatherVariable}`);
}

// Exportar funciones globales
window.initMeteorologicalAnalysis = initMeteorologicalAnalysis;
window.loadMeteorologicalAnalysis = loadMeteorologicalAnalysis;
window.exportMeteorologicalData = exportMeteorologicalData;
window.refreshMeteorologicalAnalysis = refreshMeteorologicalAnalysis;

// Función de debug para testing
window.debugMeteorologicalAnalysis = function() {
    console.log('[DEBUG] Estado actual del análisis meteorológico:');
    console.log('- currentParcelId:', currentParcelId);
    console.log('- meteorologicalData length:', meteorologicalData?.length || 0);
    
    // Verificar elementos DOM
    const elementos = {
        section: document.getElementById('meteorologicalAnalysisSection'),
        loading: document.getElementById('meteorologicalAnalysisLoading'),
        container: document.getElementById('meteorologicalAnalysisContainer'),
        precipElem: document.getElementById('correlationPrecipitation'),
        tempElem: document.getElementById('correlationTemperature'),
        chart: document.getElementById('meteorologicalChart')
    };
    
    console.log('[DEBUG] Elementos DOM encontrados:');
    Object.entries(elementos).forEach(([key, elem]) => {
        console.log(`- ${key}: ${elem ? 'ENCONTRADO' : 'NO ENCONTRADO'}`);
        if (elem) {
            console.log(`  - display: ${elem.style.display || 'default'}`);
            if (elem.textContent) console.log(`  - textContent: ${elem.textContent.substring(0, 50)}`);
        }
    });
    
    // Forzar mostrar todos los elementos necesarios
    if (elementos.section) {
        if (elementos.section.style.display === 'none') {
            elementos.section.style.display = 'block';
            console.log('[DEBUG] ✅ Section forzada a mostrarse');
        } else {
            console.log('[DEBUG] ℹ️ Section ya está visible');
        }
    }
    
    if (elementos.container) {
        if (elementos.container.style.display === 'none') {
            elementos.container.style.display = 'block';
            console.log('[DEBUG] ✅ Container forzado a mostrarse');
        } else {
            console.log('[DEBUG] ℹ️ Container ya está visible');
        }
    }
    
    // Forzar ocultar loading  
    if (elementos.loading) {
        if (elementos.loading.style.display !== 'none') {
            elementos.loading.style.display = 'none';
            console.log('[DEBUG] ✅ Loading forzado a ocultarse');
        } else {
            console.log('[DEBUG] ℹ️ Loading ya está oculto');
        }
    }
    
    return elementos;
};

/**
 * Calcula el Índice de Estrés por Calor para cultivos
 * Basado en temperatura máxima promedio del período
 */
function calculateHeatStressIndex(data) {
    if (!data || data.length === 0) {
        return { value: 0, risk: 'Sin datos' };
    }
    
    // Promediar las temperaturas máximas
    const tempMaxValues = data
        .map(d => d.temperature_max || d.temperature || 0)
        .filter(temp => temp > 0);
    
    if (tempMaxValues.length === 0) {
        return { value: 0, risk: 'Sin datos' };
    }
    
    const avgTempMax = tempMaxValues.reduce((sum, temp) => sum + temp, 0) / tempMaxValues.length;
    
    // Clasificación de riesgo según estándares agrícolas
    let risk = 'Bajo';
    if (avgTempMax > 35) {
        risk = 'Alto';
    } else if (avgTempMax > 30) {
        risk = 'Medio';
    }
    
    return { value: avgTempMax, risk };
}

/**
 * Calcula el Déficit de Presión de Vapor (VPD)
 * Métrica clave para estrés hídrico en plantas
 */
function calculateVaporPressureDeficit(data) {
    if (!data || data.length === 0) {
        return { value: 0, risk: 'Sin datos' };
    }
    
    const vpdValues = [];
    
    data.forEach(d => {
        const temp = d.temperature || 0;
        const humidity = d.humidity || 0;
        
        if (temp > 0 && humidity > 0) {
            // Calcular presión de vapor de saturación (es)
            const es = 0.6108 * Math.exp((17.27 * temp) / (temp + 237.3));
            
            // Calcular presión de vapor actual (ea)
            const ea = es * (humidity / 100);
            
            // VPD = es - ea (en kPa)
            const vpd = es - ea;
            vpdValues.push(vpd);
        }
    });
    
    if (vpdValues.length === 0) {
        return { value: 0, risk: 'Sin datos' };
    }
    
    const avgVPD = vpdValues.reduce((sum, vpd) => sum + vpd, 0) / vpdValues.length;
    
    // Clasificación según estándares de estrés hídrico
    let risk = 'Bajo';
    if (avgVPD > 2.0) {
        risk = 'Alto';
    } else if (avgVPD > 1.2) {
        risk = 'Medio';
    }
    
    return { value: avgVPD, risk };
}

/**
 * Calcula el riesgo de estrés por calor basado en temperatura máxima promedio
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
 * Calcula el índice de precipitación para determinar disponibilidad hídrica
 */
function calculatePrecipitationIndex(totalPrecip, daysWithRain) {
    let risk = 'Medio';
    
    if (totalPrecip < 200) {
        risk = 'Bajo'; // Muy poca lluvia
    } else if (totalPrecip > 800) {
        risk = 'Alto'; // Abundante lluvia
    }
    
    return { value: totalPrecip, risk };
}

// Inicializar módulo cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    initMeteorologicalAnalysis();
});

console.log('[METEOROLOGICAL] Módulo de análisis meteorológico profesional cargado correctamente');
console.log('[METEOROLOGICAL] 🔧 Para debug ejecuta: window.debugMeteorologicalAnalysis()');
