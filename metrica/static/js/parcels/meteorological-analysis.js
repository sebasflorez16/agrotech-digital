/**
 * Análisis Meteorológico - NDVI + Meteorología
 * Módulo para el análisis comparativo entre índices NDVI y datos meteorológicos reales
 * Incluye análisis histórico y pronósticos meteorológicos
 */

let meteorologicalChartInstance = null;
let currentParcelId = null;
let meteorologicalData = [];

/**
 * Inicializa el módulo de análisis meteorológico
 */
function initMeteorologicalAnalysis() {
    console.log('[METEOROLOGICAL] Iniciando módulo de análisis meteorológico');
    setupMeteorologicalControls();
}

/**
 * Configura los eventos de los controles del análisis meteorológico
 */
function setupMeteorologicalControls() {
    const weatherVariableSelect = document.getElementById('weatherVariable');
    if (weatherVariableSelect) {
        weatherVariableSelect.addEventListener('change', function() {
            const selectedVariable = this.value;
            console.log('[METEOROLOGICAL] Variable seleccionada:', selectedVariable);
            
            if (meteorologicalData.length > 0) {
                updateMeteorologicalChart(selectedVariable);
            }
        });
    }
    
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
            loadMeteorologicalAnalysis(currentParcelId);
        }
    };
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
    
    // Construir URL del backend usando utilitarios
    const endpoint = window.ApiUrls ? window.ApiUrls.weatherAnalysis(parcelId) : 
                    `${window.location.protocol}//${window.location.hostname}:8000/api/parcels/parcel/${parcelId}/ndvi-weather-comparison/`;
    
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
        console.log('[METEOROLOGICAL] Datos recibidos:', data);
        
        meteorologicalData = data.synchronized_data || [];
        
        const selectedVariable = document.getElementById('weatherVariable')?.value || 'precipitation_accumulated';
        renderMeteorologicalChart(meteorologicalData, selectedVariable);
        
        updateCorrelations(data.correlations || {});
        updateInsights(data.insights || []);
        showMeteorologicalLoading(false);
        
    })
    .catch(error => {
        console.error('[METEOROLOGICAL] Error cargando análisis:', error);
        showErrorMessage('Error cargando datos meteorológicos. Por favor, intente nuevamente.');
        showMeteorologicalLoading(false);
    });
}

/**
 * Muestra/oculta el loading del análisis meteorológico
 */
function showMeteorologicalLoading(show) {
    const loading = document.getElementById('meteorologicalAnalysisLoading');
    const container = document.getElementById('meteorologicalAnalysisContainer');
    
    if (loading && container) {
        loading.style.display = show ? 'flex' : 'none';
        container.style.display = show ? 'none' : 'block';
    }
}

/**
 * Renderiza el gráfico meteorológico con todas las variables disponibles
 */
function renderMeteorologicalChart(data, weatherVariable = 'precipitation_7d') {
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
    const ndviData = data.map(d => d.ndvi?.mean || 0);
    
    // Configuración de variables meteorológicas
    const weatherConfig = getWeatherVariableConfig(weatherVariable, data);
    
    // Separar datos históricos de pronósticos
    const historicalIndices = [];
    const forecastIndices = [];
    
    data.forEach((point, index) => {
        if (point.weather?.data_type === 'forecast') {
            forecastIndices.push(index);
        } else {
            historicalIndices.push(index);
        }
    });
    
    // Configurar datasets
    const datasets = [
        {
            label: 'NDVI Histórico',
            data: historicalIndices.map(i => ({ x: dates[i], y: ndviData[i] })),
            borderColor: '#2E7D32',
            backgroundColor: 'rgba(46, 125, 50, 0.1)',
            yAxisID: 'y',
            tension: 0.4,
            type: 'line',
            borderWidth: 3,
            pointRadius: 4,
            pointHoverRadius: 6,
            fill: false
        }
    ];
    
    // Agregar línea de pronóstico NDVI si hay datos futuros
    if (forecastIndices.length > 0) {
        datasets.push({
            label: 'NDVI Proyectado',
            data: forecastIndices.map(i => ({ x: dates[i], y: ndviData[i] })),
            borderColor: '#2E7D32',
            backgroundColor: 'rgba(46, 125, 50, 0.1)',
            yAxisID: 'y',
            tension: 0.4,
            type: 'line',
            borderWidth: 2,
            borderDash: [10, 5],
            pointRadius: 3,
            pointHoverRadius: 5,
            fill: false
        });
    }
    
    // Agregar variable meteorológica
    if (weatherVariable.includes('precipitation')) {
        // Barras para precipitación con colores más intensos
        datasets.push({
            label: weatherConfig.label,
            data: weatherConfig.data,
            borderColor: weatherConfig.color,
            backgroundColor: weatherConfig.backgroundColorIntense,
            yAxisID: 'y1',
            type: 'bar',
            borderWidth: 1,
            borderRadius: 3,
            borderSkipped: false
        });
    } else {
        // Líneas para otras variables
        datasets.push({
            label: weatherConfig.label,
            data: weatherConfig.data,
            borderColor: weatherConfig.color,
            backgroundColor: weatherConfig.backgroundColor,
            yAxisID: 'y1',
            tension: 0.4,
            type: 'line',
            borderDash: [8, 4],
            borderWidth: 3,
            pointRadius: 3,
            pointHoverRadius: 5,
            fill: false
        });
    }
    
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
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'month',
                        displayFormats: {
                            month: 'MMM yyyy'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Período de Análisis',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.3)'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Índice NDVI',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    min: 0,
                    max: 1,
                    grid: {
                        color: 'rgba(46, 125, 50, 0.15)'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: weatherConfig.label,
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    max: weatherConfig.axisMax,
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        font: {
                            size: 11,
                            weight: 'bold'
                        },
                        usePointStyle: true,
                        padding: 15
                    }
                },
                title: {
                    display: true,
                    text: `Análisis Comparativo NDVI vs ${weatherConfig.label}`,
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
                            
                            if (context.dataset.label.includes('NDVI')) {
                                label += context.parsed.y.toFixed(3);
                            } else {
                                label += context.parsed.y.toFixed(1);
                                
                                // Agregar unidad
                                if (weatherVariable.includes('temperature')) {
                                    label += ' °C';
                                } else if (weatherVariable.includes('precipitation')) {
                                    label += ' mm';
                                } else if (weatherVariable === 'humidity') {
                                    label += ' %';
                                } else if (weatherVariable === 'wind_speed') {
                                    label += ' km/h';
                                } else if (weatherVariable === 'solar_radiation') {
                                    label += ' MJ/m²';
                                }
                            }
                            
                            // Indicar tipo de dato
                            const dataIndex = context.dataIndex;
                            if (data[dataIndex]?.weather?.data_type === 'forecast') {
                                label += ' (Pronóstico)';
                            }
                            
                            return label;
                        }
                    }
                }
            }
        }
    });
    
    console.log(`[METEOROLOGICAL] Gráfico renderizado: ${data.length} puntos, variable: ${weatherVariable}`);
}

/**
 * Obtiene la configuración para una variable meteorológica específica
 */
function getWeatherVariableConfig(weatherVariable, data) {
    const configs = {
        'precipitation_daily': {
            label: 'Precipitación Diaria (mm)',
            color: '#1565C0',
            backgroundColorIntense: 'rgba(21, 101, 192, 0.85)',
            backgroundColor: 'rgba(21, 101, 192, 0.2)'
        },
        'precipitation_7d': {
            label: 'Precipitación Acumulada 7d (mm)',
            color: '#0D47A1',
            backgroundColorIntense: 'rgba(13, 71, 161, 0.9)',
            backgroundColor: 'rgba(13, 71, 161, 0.2)'
        },
        'precipitation_15d': {
            label: 'Precipitación Acumulada 15d (mm)',
            color: '#01579B',
            backgroundColorIntense: 'rgba(1, 87, 155, 0.9)',
            backgroundColor: 'rgba(1, 87, 155, 0.2)'
        },
        'precipitation_30d': {
            label: 'Precipitación Acumulada 30d (mm)',
            color: '#003C75',
            backgroundColorIntense: 'rgba(0, 60, 117, 0.9)',
            backgroundColor: 'rgba(0, 60, 117, 0.2)'
        },
        'temperature': {
            label: 'Temperatura Media (°C)',
            color: '#E65100',
            backgroundColor: 'rgba(230, 81, 0, 0.2)'
        },
        'temperature_max': {
            label: 'Temperatura Máxima (°C)',
            color: '#D84315',
            backgroundColor: 'rgba(216, 67, 21, 0.2)'
        },
        'temperature_min': {
            label: 'Temperatura Mínima (°C)',
            color: '#FF6F00',
            backgroundColor: 'rgba(255, 111, 0, 0.2)'
        },
        'humidity': {
            label: 'Humedad Relativa (%)',
            color: '#00ACC1',
            backgroundColor: 'rgba(0, 172, 193, 0.2)'
        },
        'wind_speed': {
            label: 'Velocidad del Viento (km/h)',
            color: '#5E35B1',
            backgroundColor: 'rgba(94, 53, 177, 0.2)'
        },
        'solar_radiation': {
            label: 'Radiación Solar (MJ/m²)',
            color: '#FF8F00',
            backgroundColor: 'rgba(255, 143, 0, 0.2)'
        }
    };
    
    const config = configs[weatherVariable] || configs['precipitation_7d'];
    
    // Extraer datos según la variable
    let weatherData = [];
    switch (weatherVariable) {
        case 'precipitation_daily':
            weatherData = data.map(d => d.weather?.precipitation_daily || 0);
            break;
        case 'precipitation_7d':
            weatherData = data.map(d => d.weather?.precipitation_accumulated_7d || 0);
            break;
        case 'precipitation_15d':
            weatherData = data.map(d => d.weather?.precipitation_accumulated_15d || 0);
            break;
        case 'precipitation_30d':
            weatherData = data.map(d => d.weather?.precipitation_accumulated_30d || 0);
            break;
        case 'temperature':
            weatherData = data.map(d => d.weather?.temperature || 0);
            break;
        case 'temperature_max':
            weatherData = data.map(d => d.weather?.temperature_max || 0);
            break;
        case 'temperature_min':
            weatherData = data.map(d => d.weather?.temperature_min || 0);
            break;
        case 'humidity':
            weatherData = data.map(d => d.weather?.humidity || 0);
            break;
        case 'wind_speed':
            weatherData = data.map(d => d.weather?.wind_speed || 0);
            break;
        case 'solar_radiation':
            weatherData = data.map(d => d.weather?.solar_radiation || 0);
            break;
        default:
            weatherData = data.map(d => d.weather?.precipitation_accumulated_7d || 0);
    }
    
    // Calcular máximo del eje
    let axisMax;
    if (weatherVariable === 'humidity') {
        axisMax = 100;
    } else if (weatherVariable.includes('temperature')) {
        axisMax = Math.max(...weatherData) + 5;
    } else {
        axisMax = Math.max(...weatherData) * 1.2 || 10;
    }
    
    return {
        ...config,
        data: weatherData,
        axisMax: axisMax
    };
}

/**
 * Actualiza las correlaciones mostradas
 */
function updateCorrelations(correlations) {
    // Correlación con precipitación (usar la mejor)
    const bestPrecipPeriod = correlations.best_precipitation_period || '7d';
    const bestPrecipCorr = correlations.best_precipitation_correlation || correlations.ndvi_vs_precipitation_7d || 0;
    
    const precipElem = document.getElementById('correlationPrecipitation');
    const precipStrengthElem = document.getElementById('correlationStrengthPrecip');
    
    if (precipElem && precipStrengthElem) {
        precipElem.textContent = bestPrecipCorr.toFixed(2);
        precipStrengthElem.textContent = getCorrelationStrength(bestPrecipCorr);
        precipStrengthElem.className = `badge ${getCorrelationBadgeClass(bestPrecipCorr)}`;
    }
    
    // Correlación con temperatura
    const tempCorr = correlations.ndvi_vs_temperature || 0;
    const tempElem = document.getElementById('correlationTemperature');
    const tempStrengthElem = document.getElementById('correlationStrengthTemp');
    
    if (tempElem && tempStrengthElem) {
        tempElem.textContent = tempCorr.toFixed(2);
        tempStrengthElem.textContent = getCorrelationStrength(tempCorr);
        tempStrengthElem.className = `badge ${getCorrelationBadgeClass(tempCorr)}`;
    }
}

/**
 * Obtiene la descripción de la fuerza de correlación
 */
function getCorrelationStrength(correlation) {
    const abs = Math.abs(correlation);
    if (abs >= 0.7) return 'Fuerte';
    if (abs >= 0.5) return 'Moderada';
    if (abs >= 0.3) return 'Débil';
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
 * Actualiza la lista de insights profesionales
 */
function updateInsights(insights) {
    const insightsList = document.getElementById('insightsList');
    if (!insightsList) return;
    
    insightsList.innerHTML = '';
    
    if (!insights || insights.length === 0) {
        const li = document.createElement('li');
        li.textContent = 'No hay análisis disponibles para este período.';
        li.className = 'text-muted small';
        insightsList.appendChild(li);
        return;
    }
    
    insights.forEach((insight, index) => {
        const li = document.createElement('li');
        li.className = 'mb-2 small';
        li.innerHTML = `<span class="text-primary fw-bold">${index + 1}.</span> ${insight}`;
        insightsList.appendChild(li);
    });
}

/**
 * Actualiza el gráfico cuando cambia la variable meteorológica
 */
function updateMeteorologicalChart(weatherVariable) {
    if (meteorologicalData.length > 0) {
        renderMeteorologicalChart(meteorologicalData, weatherVariable);
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

// Exportar funciones globales
window.initMeteorologicalAnalysis = initMeteorologicalAnalysis;
window.loadMeteorologicalAnalysis = loadMeteorologicalAnalysis;
window.exportMeteorologicalData = exportMeteorologicalData;
window.refreshMeteorologicalAnalysis = refreshMeteorologicalAnalysis;

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    initMeteorologicalAnalysis();
});

console.log('[METEOROLOGICAL] Módulo de análisis meteorológico profesional cargado correctamente');
