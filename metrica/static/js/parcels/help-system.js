/**
 * help-system.js
 * Sistema de ayuda contextual para usuarios no expertos
 * Proporciona explicaciones claras sobre NDVI, NDMI y análisis de imágenes satelitales
 */

/**
 * Definiciones de índices agrícolas para usuarios no expertos
 */
export const INDICES_EXPLANATIONS = {
    NDVI: {
        name: 'Índice de Vegetación (NDVI)',
        description: 'Mide la densidad y salud de la vegetación en sus cultivos',
        ranges: {
            'Alta (0.6-1.0)': {
                color: '#2E7D32',
                meaning: 'Vegetación muy densa y saludable',
                recommendation: 'Excelente estado del cultivo. Mantenga las prácticas actuales.',
                icon: '🌱'
            },
            'Moderada (0.3-0.6)': {
                color: '#8BC34A', 
                meaning: 'Vegetación moderada en desarrollo',
                recommendation: 'Buen crecimiento. Considere fertilización si es necesario.',
                icon: '🌿'
            },
            'Baja (0.1-0.3)': {
                color: '#FFC107',
                meaning: 'Vegetación escasa o estresada',
                recommendation: 'Revise riego, nutrientes o posibles plagas.',
                icon: '⚠️'
            },
            'Muy Baja (0.0-0.1)': {
                color: '#9E9E9E',
                meaning: 'Suelo desnudo o vegetación muy débil',
                recommendation: 'Área requiere atención inmediata o está en preparación.',
                icon: '🚨'
            }
        },
        tips: [
            'Valores más altos = mejor salud del cultivo',
            'Compare diferentes fechas para ver evolución',
            'Identifique áreas que necesitan atención especial'
        ]
    },
    NDMI: {
        name: 'Índice de Humedad (NDMI)', 
        description: 'Evalúa el contenido de agua en la vegetación y suelo',
        ranges: {
            'Muy Húmedo (0.4-1.0)': {
                color: '#0D47A1',
                meaning: 'Excelente contenido de humedad',
                recommendation: 'Condiciones óptimas de agua. Monitoree para evitar encharcamiento.',
                icon: '💧'
            },
            'Húmedo (0.2-0.4)': {
                color: '#1E88E5',
                meaning: 'Buen nivel de humedad',
                recommendation: 'Condiciones adecuadas para el crecimiento.',
                icon: '🌊'
            },
            'Normal (0.0-0.2)': {
                color: '#64B5F6',
                meaning: 'Humedad moderada',
                recommendation: 'Nivel normal. Mantenga el riego regular.',
                icon: '☁️'
            },
            'Seco (-0.2-0.0)': {
                color: '#FF9800',
                meaning: 'Bajo contenido de humedad',
                recommendation: 'Considere aumentar la frecuencia de riego.',
                icon: '🏜️'
            },
            'Muy Seco (-1.0 a -0.2)': {
                color: '#F44336',
                meaning: 'Déficit severo de humedad',
                recommendation: 'Riego urgente necesario para evitar pérdidas.',
                icon: '🔥'
            }
        },
        tips: [
            'Monitoree antes de épocas secas',
            'Combine con datos de precipitación local',
            'Identifique patrones de drenaje del campo'
        ]
    }
};

/**
 * Genera modal de ayuda contextual
 */
export function showIndexHelp(indexType = 'NDVI') {
    const info = INDICES_EXPLANATIONS[indexType];
    if (!info) return;

    const modalHtml = `
        <div class="modal fade" id="helpModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">
                            📚 Guía: ${info.name}
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-info">
                            <strong>¿Qué es?</strong> ${info.description}
                        </div>
                        
                        <h6 class="mt-4 mb-3">🎯 Interpretación de Valores:</h6>
                        <div class="row">
                            ${Object.entries(info.ranges).map(([range, data]) => `
                                <div class="col-md-6 mb-3">
                                    <div class="card border-0" style="background: ${data.color}15; border-left: 4px solid ${data.color} !important;">
                                        <div class="card-body p-3">
                                            <h6 class="card-title mb-2" style="color: ${data.color};">
                                                ${data.icon} ${range}
                                            </h6>
                                            <p class="card-text mb-2"><strong>${data.meaning}</strong></p>
                                            <small class="text-muted">${data.recommendation}</small>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                        
                        <h6 class="mt-4 mb-3">💡 Consejos Prácticos:</h6>
                        <ul class="list-group list-group-flush">
                            ${info.tips.map(tip => `
                                <li class="list-group-item border-0 bg-light">
                                    <i class="fas fa-lightbulb text-warning me-2"></i>
                                    ${tip}
                                </li>
                            `).join('')}
                        </ul>
                        
                        <div class="alert alert-success mt-4">
                            <strong>💪 Recuerde:</strong> 
                            Los índices satelitales son herramientas de apoyo. 
                            Combine siempre con observación de campo y conocimiento local.
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                        <button type="button" class="btn btn-primary" onclick="downloadUserGuide('${indexType}')">
                            📄 Descargar Guía PDF
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remover modal anterior si existe
    const existingModal = document.getElementById('helpModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Agregar nuevo modal
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Mostrar modal
    const modal = new bootstrap.Modal(document.getElementById('helpModal'));
    modal.show();
}

/**
 * Agregar tooltips interactivos a elementos
 */
export function addInteractiveTooltips() {
    // Tooltip para botones NDVI/NDMI
    const ndviButton = document.querySelector('[onclick*="ndvi"]');
    if (ndviButton && !ndviButton.hasAttribute('data-bs-toggle')) {
        ndviButton.setAttribute('data-bs-toggle', 'tooltip');
        ndviButton.setAttribute('data-bs-placement', 'top');
        ndviButton.setAttribute('title', 'Haga clic para ver la salud de la vegetación');
    }

    const ndmiButton = document.querySelector('[onclick*="ndmi"]');
    if (ndmiButton && !ndmiButton.hasAttribute('data-bs-toggle')) {
        ndmiButton.setAttribute('data-bs-toggle', 'tooltip');
        ndmiButton.setAttribute('data-bs-placement', 'top');
        ndmiButton.setAttribute('title', 'Haga clic para ver el contenido de humedad');
    }

    // Inicializar tooltips de Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Genera indicadores de estado en tiempo real
 */
export function generateStatusIndicators(analysisResults, indexType = 'NDVI') {
    if (!analysisResults || !analysisResults.results) return '';

    const info = INDICES_EXPLANATIONS[indexType];
    const results = analysisResults.results;
    
    // Calcular estado general del campo
    let fieldStatus = 'normal';
    let statusColor = '#FFC107';
    let statusIcon = '⚠️';
    let statusMessage = 'Estado del campo: Normal';
    
    if (indexType === 'NDVI') {
        const vegetationDense = results.find(r => r.name.includes('Densa'))?.percent || 0;
        const vegetationSparse = results.find(r => r.name.includes('Escas'))?.percent || 0;
        
        if (parseFloat(vegetationDense) > 60) {
            fieldStatus = 'excellent';
            statusColor = '#4CAF50';
            statusIcon = '🌱';
            statusMessage = 'Estado del campo: Excelente';
        } else if (parseFloat(vegetationSparse) > 40) {
            fieldStatus = 'warning';
            statusColor = '#FF9800';
            statusIcon = '⚠️';
            statusMessage = 'Estado del campo: Requiere atención';
        }
    } else if (indexType === 'NDMI') {
        const dryAreas = results.find(r => r.name.includes('Seco'))?.percent || 0;
        const moistAreas = results.find(r => r.name.includes('Húmedo'))?.percent || 0;
        
        if (parseFloat(moistAreas) > 50) {
            fieldStatus = 'good';
            statusColor = '#2196F3';
            statusIcon = '💧';
            statusMessage = 'Humedad: Buena';
        } else if (parseFloat(dryAreas) > 50) {
            fieldStatus = 'dry';
            statusColor = '#F44336';
            statusIcon = '🔥';
            statusMessage = 'Humedad: Déficit';
        }
    }

    return `
        <div class="alert alert-dismissible fade show" style="background: ${statusColor}15; border-left: 4px solid ${statusColor};">
            <h6 class="alert-heading">
                ${statusIcon} ${statusMessage}
            </h6>
            <p class="mb-2">
                Análisis basado en ${analysisResults.totalPixels?.toLocaleString() || 'N/A'} píxeles de imagen satelital
            </p>
            <hr>
            <small class="text-muted">
                📅 Última actualización: ${new Date().toLocaleDateString('es-ES')} • 
                📊 Resolución: ${analysisResults.metadata?.imageWidth || 'N/A'}x${analysisResults.metadata?.imageHeight || 'N/A'}px
            </small>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
}

/**
 * Función para descargar guía en PDF (placeholder)
 */
window.downloadUserGuide = function(indexType) {
    // Aquí se implementaría la generación/descarga de PDF
    alert(`Funcionalidad en desarrollo: Descarga de guía ${indexType}`);
    console.log(`Generar PDF para ${indexType}`);
};

/**
 * Inicializar sistema de ayuda
 */
export function initializeHelpSystem() {
    // Agregar botones de ayuda si no existen
    addInteractiveTooltips();
    
    // Agregar enlaces de ayuda contextual
    const helpButtonHtml = `
        <div class="help-system-controls" style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;">
            <div class="btn-group-vertical">
                <button class="btn btn-primary btn-sm" onclick="window.showIndexHelp('NDVI')" title="Ayuda NDVI">
                    ❓ NDVI
                </button>
                <button class="btn btn-info btn-sm mt-1" onclick="window.showIndexHelp('NDMI')" title="Ayuda NDMI">
                    ❓ NDMI
                </button>
            </div>
        </div>
    `;
    
    // Solo agregar si no existe
    if (!document.querySelector('.help-system-controls')) {
        document.body.insertAdjacentHTML('beforeend', helpButtonHtml);
    }
    
    // Hacer funciones globales
    window.showIndexHelp = showIndexHelp;
}

// Auto-inicializar cuando se carga el módulo
document.addEventListener('DOMContentLoaded', initializeHelpSystem);
