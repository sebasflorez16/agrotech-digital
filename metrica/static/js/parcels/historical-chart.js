/**
 * Gráfico Histórico de Índices Satelitales - NDVI, NDMI, EVI
 * Implementación con Chart.js para visualización interactiva
 */

// Variables globales
let historicalChart = null;
let historicalData = null;
let selectedParcelId = null;

/**
 * Inicializar el gráfico histórico
 */
function initializeHistoricalChart() {
    const graficoBtn = document.getElementById('graficoHistoricoBtn');
    if (graficoBtn) {
        graficoBtn.addEventListener('click', mostrarGraficoHistorico);
    }
    
    // Event listeners para checkboxes de mostrar/ocultar líneas
    document.getElementById('showNDVI')?.addEventListener('change', toggleChartLine);
    document.getElementById('showNDMI')?.addEventListener('change', toggleChartLine);
    document.getElementById('showEVI')?.addEventListener('change', toggleChartLine);
}

/**
 * Función principal para mostrar el gráfico histórico
 */
async function mostrarGraficoHistorico() {
    // Verificar que haya una parcela seleccionada
    if (!selectedParcelId) {
        if (typeof showErrorToast === 'function') {
            showErrorToast('Selecciona una parcela primero');
        } else {
            alert('Selecciona una parcela primero');
        }
        return;
    }
    
    // Mostrar modal
    const modal = new bootstrap.Modal(document.getElementById('historicalChartModal'));
    modal.show();
    
    // Mostrar loading
    document.getElementById('historicalChartLoading').style.display = 'block';
    document.getElementById('historicalChartContainer').style.display = 'none';
    
    try {
        // Obtener datos históricos
        console.log('[GRAFICO_HISTORICO] Obteniendo datos para parcela:', selectedParcelId);
        
        const response = await window.axiosInstance.get(`/parcel/${selectedParcelId}/historical-indices/`);
        historicalData = response.data;
        
        console.log('[GRAFICO_HISTORICO] Datos obtenidos:', historicalData);
        
        // Actualizar nombre de la parcela en el modal
        document.getElementById('parcelNameChart').textContent = historicalData.parcel_info.name;
        
        // Crear el gráfico
        createHistoricalChart(historicalData);
        
        // Mostrar estadísticas
        updateStatistics(historicalData);
        
        // Ocultar loading y mostrar gráfico
        document.getElementById('historicalChartLoading').style.display = 'none';
        document.getElementById('historicalChartContainer').style.display = 'block';
        
        if (typeof showToast === 'function') {
            showToast('✅ Gráfico histórico generado exitosamente', 'success');
        }
        
    } catch (error) {
        console.error('[GRAFICO_HISTORICO] Error:', error);
        
        let errorMessage = 'Error desconocido';
        
        if (error.response) {
            // Error del servidor (4xx, 5xx)
            switch (error.response.status) {
                case 404:
                    errorMessage = 'Parcela no encontrada. Verifica que la parcela exista y tenga datos.';
                    break;
                case 400:
                    errorMessage = error.response.data?.error || 'Datos de parcela inválidos.';
                    break;
                case 500:
                    errorMessage = 'Error interno del servidor. Contacta al administrador.';
                    break;
                default:
                    errorMessage = `Error del servidor (${error.response.status}): ${error.response.data?.error || error.message}`;
            }
        } else if (error.request) {
            // Error de red
            errorMessage = 'Error de conexión. Verifica tu conexión a internet.';
        } else {
            // Error de configuración
            errorMessage = error.message;
        }
        
        // Mostrar error
        document.getElementById('historicalChartLoading').innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Error al cargar datos históricos:</strong><br>
                ${errorMessage}
                <br><br>
                <small class="text-muted">
                    Tip: Asegúrate de que la parcela tenga un eosda_id configurado y que existan datos históricos.
                </small>
            </div>
        `;
        
        if (typeof showErrorToast === 'function') {
            showErrorToast(`Error al cargar gráfico histórico: ${errorMessage}`);
        }
    }
}

/**
 * Crear el gráfico con Chart.js
 */
function createHistoricalChart(data) {
    const ctx = document.getElementById('historicalChart').getContext('2d');
    
    // Destruir gráfico anterior si existe
    if (historicalChart) {
        historicalChart.destroy();
    }
    
    // Preparar datasets
    const datasets = [];
    
    // NDVI - Verde
    if (data.historical_data.ndvi && data.historical_data.ndvi.length > 0) {
        datasets.push({
            label: 'NDVI',
            data: data.historical_data.ndvi.map(point => ({
                x: point.date,
                y: point.mean,
                min: point.min,
                max: point.max,
                median: point.median,
                std: point.std
            })),
            borderColor: '#2E7D32',
            backgroundColor: 'rgba(46, 125, 50, 0.1)',
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
            tension: 0.4,
            fill: false
        });
    }
    
    // NDMI - Azul
    if (data.historical_data.ndmi && data.historical_data.ndmi.length > 0) {
        datasets.push({
            label: 'NDMI',
            data: data.historical_data.ndmi.map(point => ({
                x: point.date,
                y: point.mean,
                min: point.min,
                max: point.max,
                median: point.median,
                std: point.std
            })),
            borderColor: '#1565C0',
            backgroundColor: 'rgba(21, 101, 192, 0.1)',
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
            tension: 0.4,
            fill: false
        });
    }
    
    // EVI - Naranja
    if (data.historical_data.evi && data.historical_data.evi.length > 0) {
        datasets.push({
            label: 'EVI',
            data: data.historical_data.evi.map(point => ({
                x: point.date,
                y: point.mean,
                min: point.min,
                max: point.max,
                median: point.median,
                std: point.std
            })),
            borderColor: '#E65100',
            backgroundColor: 'rgba(230, 81, 0, 0.1)',
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
            tension: 0.4,
            fill: false
        });
    }
    
    // Configuración del gráfico
    historicalChart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                title: {
                    display: true,
                    text: `Evolución Histórica de Índices - ${data.period.start_date} a ${data.period.end_date}`,
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: 'white',
                    borderWidth: 1,
                    callbacks: {
                        title: function(context) {
                            const date = new Date(context[0].parsed.x);
                            return `📅 ${date.toLocaleDateString('es-ES', { 
                                year: 'numeric', 
                                month: 'long', 
                                day: 'numeric' 
                            })}`;
                        },
                        label: function(context) {
                            const point = context.raw;
                            return [
                                `${context.dataset.label}: ${point.y.toFixed(3)}`,
                                `📊 Min: ${point.min?.toFixed(3) || 'N/A'} | Max: ${point.max?.toFixed(3) || 'N/A'}`,
                                `📐 Mediana: ${point.median?.toFixed(3) || 'N/A'} | Std: ${point.std?.toFixed(3) || 'N/A'}`
                            ];
                        }
                    }
                },
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true,
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'x',
                    },
                    pan: {
                        enabled: true,
                        mode: 'x',
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        parser: 'yyyy-MM-dd',
                        tooltipFormat: 'dd/MM/yyyy',
                        displayFormats: {
                            day: 'dd/MM',
                            week: 'dd/MM',
                            month: 'MMM yyyy'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Fecha'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Valor del Índice'
                    },
                    beginAtZero: false
                }
            }
        }
    });
}

/**
 * Toggle mostrar/ocultar líneas del gráfico
 */
function toggleChartLine(event) {
    if (!historicalChart) return;
    
    const checkboxId = event.target.id;
    const isChecked = event.target.checked;
    
    let datasetIndex = -1;
    if (checkboxId === 'showNDVI') datasetIndex = 0;
    else if (checkboxId === 'showNDMI') datasetIndex = 1;
    else if (checkboxId === 'showEVI') datasetIndex = 2;
    
    if (datasetIndex >= 0 && historicalChart.data.datasets[datasetIndex]) {
        historicalChart.data.datasets[datasetIndex].hidden = !isChecked;
        historicalChart.update();
    }
}

/**
 * Reset zoom del gráfico
 */
function resetChartZoom() {
    if (historicalChart && historicalChart.resetZoom) {
        historicalChart.resetZoom();
    }
}

/**
 * Actualizar estadísticas
 */
function updateStatistics(data) {
    // NDVI Stats
    if (data.historical_data.ndvi && data.historical_data.ndvi.length > 0) {
        const ndviValues = data.historical_data.ndvi.map(p => p.mean);
        const ndviStats = calculateStats(ndviValues);
        document.getElementById('ndviStats').innerHTML = `
            Promedio: ${ndviStats.avg.toFixed(3)}<br>
            Min: ${ndviStats.min.toFixed(3)} | Max: ${ndviStats.max.toFixed(3)}<br>
            Puntos: ${ndviValues.length}
        `;
    } else {
        document.getElementById('ndviStats').innerHTML = 'Sin datos';
    }
    
    // NDMI Stats
    if (data.historical_data.ndmi && data.historical_data.ndmi.length > 0) {
        const ndmiValues = data.historical_data.ndmi.map(p => p.mean);
        const ndmiStats = calculateStats(ndmiValues);
        document.getElementById('ndmiStats').innerHTML = `
            Promedio: ${ndmiStats.avg.toFixed(3)}<br>
            Min: ${ndmiStats.min.toFixed(3)} | Max: ${ndmiStats.max.toFixed(3)}<br>
            Puntos: ${ndmiValues.length}
        `;
    } else {
        document.getElementById('ndmiStats').innerHTML = 'Sin datos';
    }
    
    // EVI Stats
    if (data.historical_data.evi && data.historical_data.evi.length > 0) {
        const eviValues = data.historical_data.evi.map(p => p.mean);
        const eviStats = calculateStats(eviValues);
        document.getElementById('eviStats').innerHTML = `
            Promedio: ${eviStats.avg.toFixed(3)}<br>
            Min: ${eviStats.min.toFixed(3)} | Max: ${eviStats.max.toFixed(3)}<br>
            Puntos: ${eviValues.length}
        `;
    } else {
        document.getElementById('eviStats').innerHTML = 'Sin datos';
    }
}

/**
 * Calcular estadísticas básicas
 */
function calculateStats(values) {
    if (!values || values.length === 0) {
        return { avg: 0, min: 0, max: 0 };
    }
    
    const sum = values.reduce((a, b) => a + b, 0);
    const avg = sum / values.length;
    const min = Math.min(...values);
    const max = Math.max(...values);
    
    return { avg, min, max };
}

/**
 * Exportar datos del gráfico a CSV
 */
function exportChartData() {
    if (!historicalData) {
        alert('No hay datos para exportar');
        return;
    }
    
    // Preparar datos para CSV
    const csvData = [];
    csvData.push(['Fecha', 'NDVI', 'NDMI', 'EVI']);
    
    // Obtener todas las fechas únicas
    const allDates = new Set();
    Object.values(historicalData.historical_data).forEach(indexData => {
        indexData.forEach(point => allDates.add(point.date));
    });
    
    // Ordenar fechas
    const sortedDates = Array.from(allDates).sort();
    
    // Crear filas del CSV
    sortedDates.forEach(date => {
        const row = [date];
        
        // NDVI
        const ndviPoint = historicalData.historical_data.ndvi?.find(p => p.date === date);
        row.push(ndviPoint ? ndviPoint.mean.toFixed(3) : '');
        
        // NDMI
        const ndmiPoint = historicalData.historical_data.ndmi?.find(p => p.date === date);
        row.push(ndmiPoint ? ndmiPoint.mean.toFixed(3) : '');
        
        // EVI
        const eviPoint = historicalData.historical_data.evi?.find(p => p.date === date);
        row.push(eviPoint ? eviPoint.mean.toFixed(3) : '');
        
        csvData.push(row);
    });
    
    // Generar CSV
    const csvContent = csvData.map(row => row.join(',')).join('\n');
    
    // Descargar archivo
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `historico_indices_${historicalData.parcel_info.name}_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    if (typeof showToast === 'function') {
        showToast('📊 Datos históricos exportados a CSV', 'success');
    }
}

/**
 * Función para establecer la parcela seleccionada (llamada desde el dashboard principal)
 */
function setSelectedParcelForChart(parcelId) {
    selectedParcelId = parcelId;
    console.log('[GRAFICO_HISTORICO] Parcela seleccionada:', parcelId);
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', initializeHistoricalChart);

// Exportar funciones globales
window.mostrarGraficoHistorico = mostrarGraficoHistorico;
window.setSelectedParcelForChart = setSelectedParcelForChart;
window.resetChartZoom = resetChartZoom;
window.exportChartData = exportChartData;
