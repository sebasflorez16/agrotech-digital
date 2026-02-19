/**
 * analysis.js
 * Utilidad para análisis de imágenes satelitales (NDVI, NDMI, EVI, etc.) por color y porcentaje.
 * Agrotech - EOSDA
 *
 * Uso: import { analyzeImageByColor } from './analysis.js';
 *
 * Función principal: analyzeImageByColor(imageSrc, colorRanges)
 * - imageSrc: string (URL, base64, etc.)
 * - colorRanges: array de objetos { name, rgb, tolerance }
 *
 * Retorna: { totalPixels, results: [{ name, count, percent }] }
 */

/**
 * analysis.js
 * Utilidad para análisis de imágenes satelitales (NDVI, NDMI, EVI, etc.) por color y porcentaje.
 * Agrotech - EOSDA
 *
 * Uso: import { analyzeImageByColor, NDVI_COLOR_DEFINITIONS, NDMI_COLOR_DEFINITIONS } from './analysis.js';
 *
 * Función principal: analyzeImageByColor(imageSrc, colorRanges)
 * - imageSrc: string (URL, base64, etc.)
 * - colorRanges: array de objetos { name, rgb, tolerance }
 *
 * Retorna: { totalPixels, results: [{ name, count, percent }] }
 */

/**
 * Definiciones de colores predefinidas para NDVI (optimizadas para EOSDA)
 */
export const NDVI_COLOR_DEFINITIONS = [
    { name: 'Vegetación densa', rgb: [46, 125, 50], tolerance: 60 }, // Verde oscuro con mayor tolerancia
    { name: 'Vegetación moderada', rgb: [139, 195, 74], tolerance: 60 }, // Verde medio
    { name: 'Vegetación escasa', rgb: [255, 193, 7], tolerance: 60 }, // Amarillo
    { name: 'Suelo/Nubes', rgb: [158, 158, 158], tolerance: 60 } // Gris
];

/**
 * Definiciones de colores predefinidas para NDMI (optimizadas para EOSDA)
 */
export const NDMI_COLOR_DEFINITIONS = [
    { name: 'Muy húmedo', rgb: [13, 71, 161], tolerance: 60 }, // Azul oscuro
    { name: 'Húmedo', rgb: [30, 136, 229], tolerance: 60 }, // Azul medio
    { name: 'Normal', rgb: [100, 181, 246], tolerance: 60 }, // Azul claro
    { name: 'Seco', rgb: [255, 152, 0], tolerance: 60 }, // Naranja
    { name: 'Muy seco', rgb: [244, 67, 54], tolerance: 60 } // Rojo
];

/**
 * Definiciones de colores predefinidas para SAVI (Soil Adjusted Vegetation Index)
 * SAVI = ((NIR - Red) / (NIR + Red + L)) * (1 + L), donde L = 0.5 (factor de ajuste del suelo)
 * 
 * El SAVI es ideal para:
 * - Suelos con poca cobertura vegetal (20-50%)
 * - Cultivos jóvenes o recién sembrados
 * - Zonas áridas o semiáridas
 * - Detección temprana de estrés vegetal en suelos expuestos
 * 
 * Rangos interpretativos:
 * - SAVI > 0.5: Vegetación densa y saludable
 * - SAVI 0.3-0.5: Vegetación moderada
 * - SAVI 0.1-0.3: Vegetación escasa o cultivos jóvenes
 * - SAVI < 0.1: Suelo desnudo o muy poca vegetación
 */
export const SAVI_COLOR_DEFINITIONS = [
    { name: 'Vegetación densa (SAVI > 0.5)', rgb: [27, 94, 32], tolerance: 50 }, // Verde muy oscuro
    { name: 'Vegetación saludable (0.4-0.5)', rgb: [56, 142, 60], tolerance: 50 }, // Verde oscuro
    { name: 'Vegetación moderada (0.3-0.4)', rgb: [102, 187, 106], tolerance: 50 }, // Verde medio
    { name: 'Cultivo joven/Vegetación escasa (0.1-0.3)', rgb: [165, 214, 167], tolerance: 50 }, // Verde claro
    { name: 'Suelo con poca vegetación (0.05-0.1)', rgb: [210, 180, 140], tolerance: 50 }, // Marrón claro/Tan
    { name: 'Suelo desnudo (< 0.05)', rgb: [139, 90, 43], tolerance: 50 } // Marrón/Sienna
];

/**
 * Interpretaciones agronómicas por índice para mostrar al usuario
 */
export const INTERPRETACIONES_INDICES = {
    ndvi: {
        nombre: 'NDVI - Índice de Vegetación Normalizado',
        descripcion: 'Mide la salud y densidad de la vegetación. Ideal para monitorear el vigor del cultivo.',
        rangos: [
            { rango: '> 0.6', interpretacion: 'Vegetación muy densa y saludable', color: '#1B5E20' },
            { rango: '0.4 - 0.6', interpretacion: 'Vegetación moderadamente sana', color: '#388E3C' },
            { rango: '0.2 - 0.4', interpretacion: 'Vegetación escasa o estresada', color: '#FFC107' },
            { rango: '< 0.2', interpretacion: 'Suelo desnudo, agua o nubes', color: '#9E9E9E' }
        ],
        recomendaciones: [
            'NDVI bajo en áreas esperadas verdes puede indicar estrés hídrico o nutricional',
            'Compare imágenes de diferentes fechas para detectar tendencias',
            'Combine con NDMI para confirmar si el estrés es por falta de agua'
        ]
    },
    ndmi: {
        nombre: 'NDMI - Índice de Humedad Normalizado',
        descripcion: 'Detecta el contenido de humedad en la vegetación y el suelo.',
        rangos: [
            { rango: '> 0.2', interpretacion: 'Alta humedad/Riego reciente', color: '#0D47A1' },
            { rango: '0 - 0.2', interpretacion: 'Humedad adecuada', color: '#1E88E5' },
            { rango: '-0.2 - 0', interpretacion: 'Humedad baja', color: '#FF9800' },
            { rango: '< -0.2', interpretacion: 'Estrés hídrico severo', color: '#F44336' }
        ],
        recomendaciones: [
            'NDMI negativo indica necesidad urgente de riego',
            'Monitoree zonas con NDMI decreciente para programar riego',
            'Valores muy altos pueden indicar encharcamiento'
        ]
    },
    savi: {
        nombre: 'SAVI - Índice de Vegetación Ajustado al Suelo',
        descripcion: 'Similar al NDVI pero corrige el brillo del suelo. Ideal para cultivos jóvenes o zonas con baja cobertura vegetal.',
        rangos: [
            { rango: '> 0.5', interpretacion: 'Vegetación densa y saludable', color: '#1B5E20' },
            { rango: '0.3 - 0.5', interpretacion: 'Vegetación moderada/Cultivo en desarrollo', color: '#66BB6A' },
            { rango: '0.1 - 0.3', interpretacion: 'Vegetación escasa/Cultivo joven', color: '#A5D6A7' },
            { rango: '< 0.1', interpretacion: 'Suelo desnudo o preparación de terreno', color: '#8B5A2B' }
        ],
        recomendaciones: [
            'Use SAVI en lugar de NDVI cuando el suelo sea visible (cobertura < 50%)',
            'Ideal para monitorear germinación y etapas tempranas del cultivo',
            'Compare con NDVI: si SAVI > NDVI, hay influencia significativa del suelo',
            'Útil para detectar problemas de germinación uniforme'
        ],
        usosPrincipales: [
            '🌱 Monitoreo de germinación',
            '🌾 Cultivos en etapa temprana',
            '🏜️ Zonas áridas o semiáridas',
            '📊 Comparación pre/post siembra'
        ]
    }
};

export function analyzeImageByColor(imageSrc, colorRanges) {
    return new Promise((resolve, reject) => {
        // Validación de parámetros
        if (!imageSrc) {
            return reject(new Error('imageSrc es requerido'));
        }
        if (!colorRanges || !Array.isArray(colorRanges) || colorRanges.length === 0) {
            console.warn('[ANALYSIS] colorRanges no válido, usando NDVI por defecto');
            colorRanges = NDVI_COLOR_DEFINITIONS;
        }
        
        console.log('[ANALYSIS] Iniciando análisis de imagen:', {
            imageSrcLength: imageSrc?.length || 0,
            colorRangesCount: colorRanges?.length || 0,
            isBase64: imageSrc?.startsWith('data:') || false
        });
        
        const img = new window.Image();
        img.crossOrigin = "Anonymous";
        
        img.onload = function () {
            console.log('[ANALYSIS] Imagen cargada exitosamente:', {
                width: img.width,
                height: img.height,
                naturalWidth: img.naturalWidth,
                naturalHeight: img.naturalHeight
            });
            
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');
            
            try {
                ctx.drawImage(img, 0, 0);
                console.log('[ANALYSIS] Imagen dibujada en canvas');
                
                const imageData = ctx.getImageData(0, 0, img.width, img.height);
                const data = imageData.data;
                const totalPixels = img.width * img.height;
                
                console.log('[ANALYSIS] ImageData obtenida:', {
                    dataLength: data.length,
                    totalPixels: totalPixels,
                    expectedDataLength: totalPixels * 4
                });
                
                const results = colorRanges.map(r => ({ name: r.name, count: 0, percent: 0 }));

                // Función para comparar colores con tolerancia
                function colorMatch(r1, g1, b1, r2, g2, b2, tolerance) {
                    return Math.abs(r1 - r2) <= tolerance &&
                           Math.abs(g1 - g2) <= tolerance &&
                           Math.abs(b1 - b2) <= tolerance;
                }
                
                console.log('[ANALYSIS] Iniciando análisis de pixels...');
                let analyzedPixels = 0;
                
                for (let i = 0; i < data.length; i += 4) {
                    const r = data[i], g = data[i + 1], b = data[i + 2], a = data[i + 3];
                    
                    // Ignorar pixels transparentes
                    if (a < 128) continue;
                    
                    analyzedPixels++;
                    let matched = false;
                    
                    for (let j = 0; j < colorRanges.length; j++) {
                        const { rgb, tolerance } = colorRanges[j];
                        if (colorMatch(r, g, b, rgb[0], rgb[1], rgb[2], tolerance)) {
                            results[j].count++;
                            matched = true;
                            break;
                        }
                    }
                    
                    // Log de muestra para debugging (solo los primeros 10 pixels)
                    if (analyzedPixels <= 10) {
                        console.log(`[ANALYSIS] Pixel ${analyzedPixels}: rgba(${r},${g},${b},${a}) - Matched: ${matched}`);
                    }
                }
                
                console.log('[ANALYSIS] Análisis de pixels completado:', {
                    totalPixels: totalPixels,
                    analyzedPixels: analyzedPixels,
                    transparentPixels: totalPixels - analyzedPixels
                });
                
                // Calcular porcentajes basados en pixels no transparentes
                const basePixels = analyzedPixels > 0 ? analyzedPixels : totalPixels;
                results.forEach(r => {
                    r.percent = ((r.count / basePixels) * 100).toFixed(1);
                });
                
                console.log('[ANALYSIS] Resultados finales:', results);
                
                resolve({ 
                    success: true,
                    totalPixels: analyzedPixels, 
                    results,
                    metadata: {
                        imageWidth: img.width,
                        imageHeight: img.height,
                        analyzedPixels: analyzedPixels,
                        analysisDate: new Date().toISOString()
                    }
                });
            } catch (error) {
                console.error('[ANALYSIS] Error al procesar imagen:', error);
                reject({
                    success: false,
                    error: 'Error al procesar la imagen: ' + error.message
                });
            }
        };
        
        img.onerror = function (e) {
            console.error('[ANALYSIS] Error al cargar imagen:', e);
            reject({
                success: false,
                error: 'No se pudo cargar la imagen para análisis. Verifique que sea una imagen válida.'
            });
        };
        
        console.log('[ANALYSIS] Asignando src a imagen...');
        img.src = imageSrc;
    });
}

/**
 * Genera una leyenda HTML para mostrar los resultados del análisis
 * @param {Array} results - Resultados del análisis
 * @param {string} title - Título de la leyenda
 * @returns {string} HTML de la leyenda
 */
export function generateColorLegendHTML(results, title = 'Análisis de Colores') {
    if (!results || !results.length) {
        return '<div class="alert alert-warning">No hay resultados de análisis disponibles</div>';
    }
    
    // Ordenar resultados por porcentaje (mayor a menor)
    const sortedResults = [...results].sort((a, b) => parseFloat(b.percent) - parseFloat(a.percent));
    
    const legendItems = sortedResults.map(result => {
        // Buscar el color correspondiente en las definiciones
        const color = result.color || result.rgb || [128, 128, 128]; // Color por defecto
        const colorStyle = `background-color: rgb(${color.join(',')})`;
        const percentage = parseFloat(result.percent || 0);
        
        // Agregar barra de progreso visual
        const progressBar = `
            <div style="width: 100%; background: #f0f0f0; border-radius: 10px; height: 4px; margin-top: 4px;">
                <div style="width: ${Math.min(percentage, 100)}%; background: rgb(${color.join(',')}); height: 100%; border-radius: 10px;"></div>
            </div>
        `;
        
        return `
            <div class="d-flex align-items-start mb-3" style="padding: 8px; border: 1px solid #e9ecef; border-radius: 6px; background: #fafafa;">
                <div class="legend-color-box" style="${colorStyle}; width: 24px; height: 24px; margin-right: 12px; border: 2px solid #fff; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);"></div>
                <div style="flex: 1;">
                    <div class="legend-label" style="font-weight: 600; font-size: 0.9rem; color: #333;">
                        ${result.name}: <span style="color: #2c5aa0;">${result.percent}%</span>
                    </div>
                    <small style="color: #666; font-size: 0.8rem;">${parseInt(result.count || 0).toLocaleString()} píxeles</small>
                    ${progressBar}
                </div>
            </div>
        `;
    }).join('');
    
    const totalPixels = results.reduce((sum, r) => sum + parseInt(r.count || 0), 0);
    const analysisType = results.length > 5 ? 'automático' : 'predefinido';
    
    return `
        <div class="color-analysis-legend" style="background: white; border: 1px solid #dee2e6; border-radius: 8px; padding: 16px;">
            <h6 class="mb-3" style="color: #2c5aa0; border-bottom: 2px solid #e9ecef; padding-bottom: 8px;">
                📊 ${title}
            </h6>
            ${legendItems}
            <div style="margin-top: 16px; padding: 8px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #2c5aa0;">
                <small class="text-muted" style="display: block; margin-bottom: 4px;">
                    <strong>Total píxeles analizados:</strong> ${totalPixels.toLocaleString()}
                </small>
                <small class="text-muted">
                    <strong>Tipo de análisis:</strong> ${analysisType} • <strong>Precisión:</strong> ${results.length > 5 ? 'Adaptativa' : 'Estándar'}
                </small>
            </div>
        </div>
    `;
}

/**
 * Actualiza la leyenda de colores en el DOM
 * @param {string} containerId - ID del contenedor donde mostrar la leyenda
 * @param {Array} results - Resultados del análisis
 * @param {string} title - Título de la leyenda
 */
export function updateColorLegendInDOM(containerId, results, title) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.warn(`Contenedor ${containerId} no encontrado para actualizar leyenda`);
        return;
    }
    
    container.innerHTML = generateColorLegendHTML(results, title);
}

/**
 * Análisis dinámico de colores - detecta automáticamente los colores predominantes
 * @param {ImageData} imageData - Datos de la imagen
 * @param {number} clusters - Número de clusters de color a detectar
 * @param {string} indexType - Tipo de índice: 'ndvi', 'ndmi', 'savi' (opcional)
 * @returns {Array} Array de colores predominantes con porcentajes
 */
function dynamicColorAnalysis(imageData, clusters = 8, indexType = 'ndvi') {
    const data = imageData.data;
    const colorMap = new Map();
    
    // Agrupar colores similares
    for (let i = 0; i < data.length; i += 4) {
        const r = data[i], g = data[i + 1], b = data[i + 2], a = data[i + 3];
        
        // Ignorar pixels transparentes
        if (a < 128) continue;
        
        // Reducir resolución de color para agrupar similares (más granular)
        const reducedR = Math.floor(r / 15) * 15;
        const reducedG = Math.floor(g / 15) * 15;
        const reducedB = Math.floor(b / 15) * 15;
        
        const colorKey = `${reducedR},${reducedG},${reducedB}`;
        colorMap.set(colorKey, (colorMap.get(colorKey) || 0) + 1);
    }
    
    // Ordenar colores por frecuencia y filtrar los muy pequeños
    const sortedColors = Array.from(colorMap.entries())
        .sort((a, b) => b[1] - a[1])
        .filter(([colorKey, count]) => {
            const totalPixels = Array.from(colorMap.values()).reduce((sum, c) => sum + c, 0);
            return (count / totalPixels) >= 0.01; // Al menos 1% para aparecer
        })
        .slice(0, clusters);
    
    const totalPixels = sortedColors.reduce((sum, [, count]) => sum + count, 0);
    const usedNames = [];
    
    return sortedColors.map(([colorKey, count], index) => {
        const [r, g, b] = colorKey.split(',').map(Number);
        const percent = ((count / totalPixels) * 100).toFixed(1);
        
        // Obtener nombre único según el tipo de índice
        const name = getIndexSpecificColorName(r, g, b, index, usedNames, indexType);
        
        return {
            name: name,
            rgb: [r, g, b],
            color: [r, g, b], // Compatibilidad con leyenda
            count: count,
            percent: percent
        };
    });
}

/**
 * Obtiene nombres descriptivos específicos según el tipo de índice
 * @param {number} r - Componente rojo
 * @param {number} g - Componente verde  
 * @param {number} b - Componente azul
 * @param {number} index - Índice del color en la lista
 * @param {Array} usedNames - Nombres ya utilizados
 * @param {string} indexType - Tipo de índice: 'ndvi', 'ndmi', 'savi'
 * @returns {string} Nombre descriptivo único
 */
function getIndexSpecificColorName(r, g, b, index, usedNames = [], indexType = 'ndvi') {
    const brightness = (r + g + b) / 3;
    const total = r + g + b;
    const redRatio = total > 0 ? r / total : 0;
    const greenRatio = total > 0 ? g / total : 0;
    const blueRatio = total > 0 ? b / total : 0;
    
    let candidateNames = [];
    
    // Nombres específicos según el tipo de índice
    switch (indexType.toLowerCase()) {
        case 'ndmi':
            // NDMI: Índice de humedad - azul = húmedo, verde-azul = normal, amarillo-rojo = seco
            // El NDMI usa una paleta específica donde:
            // - Azules intensos = muy húmedo
            // - Azules claros/cyan = húmedo
            // - Verdes = humedad normal
            // - Amarillos = humedad baja
            // - Naranjas/Rojos = muy seco
            
            if (b > 180 && b > r && b > g) {
                candidateNames.push('Muy Húmedo', 'Alta Saturación de Agua', 'Riego Reciente');
            } else if (b > 140 && blueRatio > 0.35) {
                candidateNames.push('Húmedo', 'Humedad Alta', 'Buena Disponibilidad Hídrica');
            } else if (b > 100 && g > 100 && r < 120) {
                candidateNames.push('Humedad Moderada', 'Contenido Hídrico Medio', 'Humedad Aceptable');
            } else if (g > 150 && greenRatio > 0.36) {
                candidateNames.push('Humedad Normal', 'Equilibrio Hídrico', 'Condiciones Normales');
            } else if (g > 120 && r > 120 && b < 100) {
                candidateNames.push('Humedad Baja', 'Inicio de Estrés Hídrico', 'Requiere Monitoreo');
            } else if (r > 180 && g > 120 && b < 100) {
                candidateNames.push('Seco', 'Estrés Hídrico', 'Necesita Riego');
            } else if (r > 200 && redRatio > 0.45) {
                candidateNames.push('Muy Seco', 'Estrés Hídrico Severo', 'Requiere Riego Urgente');
            } else if (brightness > 220) {
                candidateNames.push('Sin Datos/Nubes', 'Cobertura Nubosa', 'Área Enmascarada');
            } else if (brightness < 50) {
                candidateNames.push('Sombra', 'Área Sombreada', 'Zona Oscura');
            } else if (brightness > 180 && Math.abs(r - g) < 30 && Math.abs(g - b) < 30) {
                candidateNames.push('Suelo Seco', 'Superficie Seca', 'Área Sin Vegetación');
            } else {
                candidateNames.push('Transición', 'Zona Intermedia', 'Humedad Variable');
            }
            break;
            
        case 'savi':
            // SAVI: Similar a NDVI pero ajustado para suelos expuestos
            // Mejor para detectar vegetación en áreas con mucho suelo visible
            if (g > 180 && greenRatio > 0.42) {
                candidateNames.push('Vegetación Muy Densa', 'Cobertura Vegetal Completa', 'Dosel Cerrado');
            } else if (g > 150 && greenRatio > 0.38) {
                candidateNames.push('Vegetación Densa', 'Alta Cobertura Vegetal', 'Cultivo Desarrollado');
            } else if (g > 120 && greenRatio > 0.35) {
                candidateNames.push('Vegetación Moderada', 'Cobertura Media', 'Cultivo en Crecimiento');
            } else if (g > 100 && greenRatio > 0.32) {
                candidateNames.push('Vegetación Escasa', 'Baja Cobertura', 'Cultivo Joven');
            } else if (r > 150 && g > 100 && b < 100) {
                candidateNames.push('Suelo con Vegetación Incipiente', 'Germinación', 'Emergencia de Cultivo');
            } else if (r > 140 && brightness > 120) {
                candidateNames.push('Suelo Expuesto', 'Suelo Desnudo', 'Sin Cobertura Vegetal');
            } else if (brightness > 200) {
                candidateNames.push('Sin Datos/Nubes', 'Cobertura Nubosa', 'Área Enmascarada');
            } else if (brightness < 60) {
                candidateNames.push('Sombra', 'Área Sombreada', 'Baja Iluminación');
            } else {
                candidateNames.push('Área Mixta', 'Suelo y Vegetación', 'Transición');
            }
            break;
            
        case 'ndvi':
        default:
            // NDVI: verde = vegetación sana, amarillo = estrés leve, rojo = estrés severo
            if (g > 180 && greenRatio > 0.42) {
                candidateNames.push('Vegetación Muy Densa', 'Vigor Óptimo', 'Máxima Actividad Fotosintética');
            } else if (g > 150 && greenRatio > 0.38) {
                candidateNames.push('Vegetación Densa', 'Vigor Alto', 'Buena Salud Vegetal');
            } else if (g > 120 && greenRatio > 0.35) {
                candidateNames.push('Vegetación Moderada', 'Vigor Medio', 'Desarrollo Normal');
            } else if (g > 100 && greenRatio > 0.32) {
                candidateNames.push('Vegetación Escasa', 'Vigor Bajo', 'Cobertura Limitada');
            } else if (r > 180 && g > 150) {
                candidateNames.push('Estrés Leve', 'Alerta de Estrés', 'Requiere Atención');
            } else if (r > 200 && g < 150) {
                candidateNames.push('Estrés Moderado', 'Estrés Visible', 'Acción Requerida');
            } else if (r > 200 && redRatio > 0.45) {
                candidateNames.push('Estrés Severo', 'Estrés Crítico', 'Intervención Urgente');
            } else if (brightness > 200) {
                candidateNames.push('Nubes/Sin Datos', 'Cobertura Nubosa', 'Área Enmascarada');
            } else if (brightness < 60) {
                candidateNames.push('Sombra/Agua', 'Área Oscura', 'Cuerpo de Agua');
            } else if (Math.abs(r - g) < 30 && Math.abs(g - b) < 30 && brightness > 100) {
                candidateNames.push('Suelo Desnudo', 'Sin Vegetación', 'Área Descubierta');
            } else {
                candidateNames.push('Zona de Transición', 'Área Mixta', 'Vegetación Variable');
            }
            break;
    }
    
    // Evitar duplicados - buscar nombre único de la lista de candidatos
    for (let name of candidateNames) {
        if (!usedNames.includes(name)) {
            usedNames.push(name);
            return name;
        }
    }
    
    // Si todos los candidatos están usados, generar nombre descriptivo basado en valores RGB
    // en lugar de agregar números genéricos
    let descriptiveName;
    if (indexType.toLowerCase() === 'ndmi') {
        // Nombres alternativos para NDMI basados en los valores de color
        if (brightness > 180) descriptiveName = `Zona Clara (${Math.round(brightness)})`;
        else if (brightness < 80) descriptiveName = `Zona Oscura (${Math.round(brightness)})`;
        else if (blueRatio > 0.35) descriptiveName = `Área Húmeda ${index + 1}`;
        else if (redRatio > 0.35) descriptiveName = `Área Seca ${index + 1}`;
        else descriptiveName = `Humedad Variable ${index + 1}`;
    } else if (indexType.toLowerCase() === 'savi') {
        if (greenRatio > 0.35) descriptiveName = `Vegetación ${index + 1}`;
        else if (brightness > 150) descriptiveName = `Suelo ${index + 1}`;
        else descriptiveName = `Área Mixta ${index + 1}`;
    } else {
        if (greenRatio > 0.35) descriptiveName = `Vegetación ${index + 1}`;
        else if (redRatio > 0.35) descriptiveName = `Estrés ${index + 1}`;
        else descriptiveName = `Área ${index + 1}`;
    }
    
    // Asegurar unicidad
    while (usedNames.includes(descriptiveName)) {
        descriptiveName = descriptiveName.replace(/\d+$/, '') + (index + Math.random().toString(36).substr(2, 2));
    }
    usedNames.push(descriptiveName);
    return descriptiveName;
}

/**
 * Obtiene nombres descriptivos agrícolas para colores evitando duplicados
 * @param {number} r - Componente rojo
 * @param {number} g - Componente verde  
 * @param {number} b - Componente azul
 * @param {number} index - Índice del color en la lista
 * @param {Array} usedNames - Nombres ya utilizados
 * @returns {string} Nombre descriptivo único
 */
function getAgriculturalColorName(r, g, b, index, usedNames = []) {
    // Calcular brillo general y relaciones
    const brightness = (r + g + b) / 3;
    const total = r + g + b;
    
    // Calcular ratios de color
    const redRatio = total > 0 ? r / total : 0;
    const greenRatio = total > 0 ? g / total : 0;
    const blueRatio = total > 0 ? b / total : 0;
    
    let candidateNames = [];
    
    // Nombres basados en características vegetativas y de humedad para NDVI/NDMI
    if (greenRatio > 0.4) {
        if (g > 180) candidateNames.push('Vegetación Muy Densa');
        else if (g > 140) candidateNames.push('Vegetación Densa');
        else if (g > 100) candidateNames.push('Vegetación Moderada');
        else candidateNames.push('Vegetación Escasa');
    } else if (redRatio > 0.4) {
        if (r > 200 && g < 100) candidateNames.push('Muy Seco');
        else if (r > 170 && g < 120) candidateNames.push('Seco');
        else if (r > 140) candidateNames.push('Suelo Seco');
        else candidateNames.push('Suelo Expuesto');
    } else if (blueRatio > 0.35) {
        if (b > 150) candidateNames.push('Agua/Muy Húmedo');
        else if (b > 120) candidateNames.push('Húmedo');
        else candidateNames.push('Sombra Húmeda');
    } else {
        // Colores neutros o mixtos
        if (brightness > 210) candidateNames.push('Suelo Claro');
        else if (brightness < 80) candidateNames.push('Sombra/Oscuro');
        else if (r > 120 && g > 80 && b < 100) candidateNames.push('Suelo Marrón');
        else if (Math.abs(r - g) < 30 && Math.abs(g - b) < 30) candidateNames.push('Gris/Neutro');
        else candidateNames.push('Mixto');
    }
    
    // Evitar duplicados
    for (let name of candidateNames) {
        if (!usedNames.includes(name)) {
            usedNames.push(name);
            return name;
        }
    }
    
    // Si todos los nombres están usados, agregar índice
    const baseName = candidateNames[0] || 'Área';
    let uniqueName = `${baseName} ${index + 1}`;
    let counter = 2;
    while (usedNames.includes(uniqueName)) {
        uniqueName = `${baseName} ${counter}`;
        counter++;
    }
    usedNames.push(uniqueName);
    return uniqueName;
}

/**
 * Función mejorada que combina análisis predefinido con análisis dinámico
 * @param {string} imageSrc - URL o base64 de la imagen
 * @param {Array} colorRanges - Rangos de colores predefinidos
 * @param {string} indexType - Tipo de índice: 'ndvi', 'ndmi', 'savi' (opcional)
 */
export function analyzeImageByColorAdvanced(imageSrc, colorRanges, indexType = 'ndvi') {
    return new Promise((resolve, reject) => {
        // Validación de parámetros
        if (!imageSrc) {
            return reject(new Error('imageSrc es requerido'));
        }
        if (!colorRanges || !Array.isArray(colorRanges) || colorRanges.length === 0) {
            console.warn('[ANALYSIS] colorRanges no válido en análisis avanzado, usando NDVI por defecto');
            colorRanges = NDVI_COLOR_DEFINITIONS;
        }
        
        console.log('[ANALYSIS] Iniciando análisis avanzado de imagen:', {
            imageSrcLength: imageSrc?.length || 0,
            colorRangesCount: colorRanges?.length || 0,
            isBase64: imageSrc?.startsWith('data:') || false,
            indexType: indexType
        });
        
        const img = new window.Image();
        img.crossOrigin = "Anonymous";
        
        img.onload = function () {
            console.log('[ANALYSIS] Imagen cargada exitosamente:', {
                width: img.width,
                height: img.height
            });
            
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');
            
            try {
                ctx.drawImage(img, 0, 0);
                const imageData = ctx.getImageData(0, 0, img.width, img.height);
                const data = imageData.data;
                const totalPixels = img.width * img.height;
                
                // Primero intentar análisis predefinido
                const results = colorRanges.map(r => ({ name: r.name, count: 0, percent: 0 }));
                let analyzedPixels = 0;
                let matchedPixels = 0;

                function colorMatch(r1, g1, b1, r2, g2, b2, tolerance) {
                    return Math.abs(r1 - r2) <= tolerance &&
                           Math.abs(g1 - g2) <= tolerance &&
                           Math.abs(b1 - b2) <= tolerance;
                }
                
                for (let i = 0; i < data.length; i += 4) {
                    const r = data[i], g = data[i + 1], b = data[i + 2], a = data[i + 3];
                    
                    if (a < 128) continue;
                    analyzedPixels++;
                    
                    let matched = false;
                    for (let j = 0; j < colorRanges.length; j++) {
                        const { rgb, tolerance } = colorRanges[j];
                        if (colorMatch(r, g, b, rgb[0], rgb[1], rgb[2], tolerance)) {
                            results[j].count++;
                            matched = true;
                            matchedPixels++;
                            break;
                        }
                    }
                }
                
                // Si menos del 30% de pixels coinciden, usar análisis dinámico
                const matchPercentage = (matchedPixels / analyzedPixels) * 100;
                console.log('[ANALYSIS] Porcentaje de coincidencia con colores predefinidos:', matchPercentage.toFixed(1) + '%');
                
                if (matchPercentage < 30) {
                    console.log('[ANALYSIS] Bajo porcentaje de coincidencia, activando análisis dinámico con indexType:', indexType);
                    const dynamicResults = dynamicColorAnalysis(imageData, 8, indexType);
                    
                    resolve({ 
                        success: true,
                        totalPixels: analyzedPixels,
                        results: dynamicResults,
                        analysisType: 'dynamic',
                        metadata: {
                            imageWidth: img.width,
                            imageHeight: img.height,
                            matchPercentage: matchPercentage,
                            analysisDate: new Date().toISOString()
                        }
                    });
                } else {
                    // Usar resultados predefinidos
                    const basePixels = analyzedPixels > 0 ? analyzedPixels : totalPixels;
                    results.forEach(r => {
                        r.percent = ((r.count / basePixels) * 100).toFixed(1);
                    });
                    
                    resolve({ 
                        success: true,
                        totalPixels: analyzedPixels,
                        results: results,
                        analysisType: 'predefined',
                        metadata: {
                            imageWidth: img.width,
                            imageHeight: img.height,
                            matchPercentage: matchPercentage,
                            analysisDate: new Date().toISOString()
                        }
                    });
                }
                
            } catch (error) {
                console.error('[ANALYSIS] Error al procesar imagen:', error);
                reject({
                    success: false,
                    error: 'Error al procesar la imagen: ' + error.message
                });
            }
        };
        
        img.onerror = function (e) {
            console.error('[ANALYSIS] Error al cargar imagen:', e);
            reject({
                success: false,
                error: 'No se pudo cargar la imagen para análisis.'
            });
        };
        
        img.src = imageSrc;
    });
}

// Exportar la función original mejorada como la principal
// peurba del commit

/**
 * Genera una interpretación agronómica profesional basada en los resultados del análisis
 * @param {Array} results - Resultados del análisis de colores
 * @param {string} indexType - Tipo de índice: 'ndvi', 'ndmi', 'savi'
 * @param {Object} metadata - Metadatos del análisis
 * @returns {Object} Interpretación con diagnóstico, recomendaciones y alertas
 */
export function generarInterpretacionProfesional(results, indexType = 'ndvi', metadata = {}) {
    const interpretaciones = INTERPRETACIONES_INDICES[indexType.toLowerCase()];
    if (!interpretaciones) {
        return {
            diagnostico: 'Índice no reconocido',
            alertas: [],
            recomendaciones: [],
            resumenEjecutivo: ''
        };
    }
    
    // Calcular porcentajes por categoría
    let vegetacionDensa = 0;
    let vegetacionModerada = 0;
    let vegetacionEscasa = 0;
    let sueloDesnudo = 0;
    let estresHidrico = 0;
    
    results.forEach(r => {
        const percent = parseFloat(r.percent) || 0;
        const name = r.name.toLowerCase();
        
        if (name.includes('densa') || (name.includes('muy') && name.includes('húmedo'))) {
            vegetacionDensa += percent;
        } else if (name.includes('moderada') || name.includes('saludable') || name.includes('húmedo')) {
            vegetacionModerada += percent;
        } else if (name.includes('escasa') || name.includes('joven') || name.includes('normal')) {
            vegetacionEscasa += percent;
        } else if (name.includes('suelo') || name.includes('desnudo')) {
            sueloDesnudo += percent;
        } else if (name.includes('seco') || name.includes('estrés')) {
            estresHidrico += percent;
        }
    });
    
    // Generar diagnóstico basado en el índice
    let diagnostico = '';
    let nivelAlerta = 'normal'; // 'normal', 'warning', 'critical'
    let alertas = [];
    let recomendaciones = [];
    
    if (indexType === 'ndvi') {
        if (vegetacionDensa > 60) {
            diagnostico = '✅ Excelente estado del cultivo. La vegetación presenta un vigor óptimo con alta densidad de clorofila.';
            nivelAlerta = 'normal';
        } else if (vegetacionDensa + vegetacionModerada > 50) {
            diagnostico = '👍 Buen estado del cultivo. La mayoría del área presenta vegetación saludable.';
            nivelAlerta = 'normal';
        } else if (vegetacionEscasa > 30 || sueloDesnudo > 25) {
            diagnostico = '⚠️ Atención requerida. Se detectan zonas con vegetación escasa o suelo expuesto.';
            nivelAlerta = 'warning';
            alertas.push('Posible estrés nutricional o hídrico en algunas zonas');
            recomendaciones.push('Inspeccionar las áreas con menor NDVI en campo');
        } else if (sueloDesnudo > 40) {
            diagnostico = '🚨 Alerta crítica. Gran parte del área muestra poco vigor vegetal.';
            nivelAlerta = 'critical';
            alertas.push('Posible daño severo al cultivo o problema de germinación');
            recomendaciones.push('Evaluación urgente en campo recomendada');
        }
    } else if (indexType === 'ndmi') {
        if (estresHidrico > 40) {
            diagnostico = '🚨 Estrés hídrico detectado. Se recomienda riego inmediato en las zonas afectadas.';
            nivelAlerta = 'critical';
            alertas.push('Riesgo de pérdida de rendimiento por falta de agua');
            recomendaciones.push('Programar riego de emergencia');
            recomendaciones.push('Verificar sistema de riego en zonas secas');
        } else if (estresHidrico > 20) {
            diagnostico = '⚠️ Humedad baja en algunas zonas. Monitorear y considerar riego preventivo.';
            nivelAlerta = 'warning';
            recomendaciones.push('Aumentar frecuencia de monitoreo');
        } else {
            diagnostico = '✅ Niveles de humedad adecuados en el cultivo.';
            nivelAlerta = 'normal';
        }
    } else if (indexType === 'savi') {
        if (vegetacionDensa > 50) {
            diagnostico = '✅ Excelente desarrollo del cultivo considerando el factor suelo. La vegetación está bien establecida.';
            nivelAlerta = 'normal';
        } else if (vegetacionModerada > 40 || vegetacionEscasa > 30) {
            diagnostico = '📊 Cultivo en desarrollo. Típico de etapas tempranas o media temporada.';
            nivelAlerta = 'normal';
            recomendaciones.push('Comparar con imágenes anteriores para verificar progreso normal');
        } else if (sueloDesnudo > 50) {
            diagnostico = '⚠️ Alta exposición de suelo detectada. Puede indicar germinación desigual o pérdida de plantas.';
            nivelAlerta = 'warning';
            alertas.push('Verificar densidad de siembra y uniformidad de germinación');
            recomendaciones.push('Inspección de campo recomendada para identificar causa');
            recomendaciones.push('Si es post-siembra reciente, puede ser normal. Comparar en 2 semanas.');
        }
        
        // Recomendaciones específicas de SAVI
        recomendaciones.push(...(interpretaciones.recomendaciones || []));
    }
    
    // Generar resumen ejecutivo
    const resumenEjecutivo = `
        📊 **Resumen del Análisis ${indexType.toUpperCase()}**
        
        - Vegetación densa: ${vegetacionDensa.toFixed(1)}%
        - Vegetación moderada: ${vegetacionModerada.toFixed(1)}%
        - Zonas de atención: ${(vegetacionEscasa + sueloDesnudo + estresHidrico).toFixed(1)}%
        
        ${diagnostico}
    `.trim();
    
    return {
        diagnostico,
        nivelAlerta,
        alertas,
        recomendaciones: [...new Set(recomendaciones)], // Eliminar duplicados
        resumenEjecutivo,
        estadisticas: {
            vegetacionDensa,
            vegetacionModerada,
            vegetacionEscasa,
            sueloDesnudo,
            estresHidrico
        },
        indiceInfo: interpretaciones
    };
}

/**
 * Genera HTML para mostrar la interpretación profesional al usuario
 * @param {Object} interpretacion - Resultado de generarInterpretacionProfesional
 * @param {string} indexType - Tipo de índice
 * @returns {string} HTML formateado
 */
export function generarHTMLInterpretacion(interpretacion, indexType = 'ndvi') {
    const { diagnostico, nivelAlerta, alertas, recomendaciones, estadisticas, indiceInfo } = interpretacion;
    
    // Colores según nivel de alerta
    const alertColors = {
        normal: { bg: '#E8F5E9', border: '#4CAF50', icon: '✅' },
        warning: { bg: '#FFF3E0', border: '#FF9800', icon: '⚠️' },
        critical: { bg: '#FFEBEE', border: '#F44336', icon: '🚨' }
    };
    const colors = alertColors[nivelAlerta] || alertColors.normal;
    
    let html = `
        <div class="interpretacion-container" style="background: ${colors.bg}; border: 2px solid ${colors.border}; border-radius: 12px; padding: 16px; margin-top: 16px;">
            <h5 style="color: ${colors.border}; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
                ${colors.icon} ${indiceInfo?.nombre || indexType.toUpperCase()}
            </h5>
            
            <p style="font-size: 1rem; margin-bottom: 12px;">${diagnostico}</p>
            
            ${alertas.length > 0 ? `
                <div style="background: rgba(244, 67, 54, 0.1); padding: 10px; border-radius: 8px; margin-bottom: 12px;">
                    <strong>⚡ Alertas:</strong>
                    <ul style="margin: 8px 0 0 20px; padding: 0;">
                        ${alertas.map(a => `<li>${a}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${recomendaciones.length > 0 ? `
                <div style="background: rgba(33, 150, 243, 0.1); padding: 10px; border-radius: 8px; margin-bottom: 12px;">
                    <strong>💡 Recomendaciones:</strong>
                    <ul style="margin: 8px 0 0 20px; padding: 0;">
                        ${recomendaciones.slice(0, 4).map(r => `<li>${r}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px;">
                <span class="badge" style="background: #1B5E20; color: white; padding: 4px 8px; border-radius: 4px;">
                    🌿 Densa: ${estadisticas.vegetacionDensa.toFixed(1)}%
                </span>
                <span class="badge" style="background: #66BB6A; color: white; padding: 4px 8px; border-radius: 4px;">
                    🌱 Moderada: ${estadisticas.vegetacionModerada.toFixed(1)}%
                </span>
                ${estadisticas.estresHidrico > 5 ? `
                    <span class="badge" style="background: #F44336; color: white; padding: 4px 8px; border-radius: 4px;">
                        💧 Estrés: ${estadisticas.estresHidrico.toFixed(1)}%
                    </span>
                ` : ''}
            </div>
        </div>
    `;
    
    // Agregar información específica de SAVI
    if (indexType === 'savi' && indiceInfo?.usosPrincipales) {
        html += `
            <div style="background: linear-gradient(135deg, #FFF8E1, #FFECB3); border: 1px solid #FFB300; border-radius: 12px; padding: 16px; margin-top: 12px;">
                <h6 style="color: #F57C00; margin-bottom: 8px;">🌾 ¿Por qué usar SAVI?</h6>
                <p style="font-size: 0.9rem; color: #5D4037;">${indiceInfo.descripcion}</p>
                <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px;">
                    ${indiceInfo.usosPrincipales.map(uso => `
                        <span style="background: #FFF3E0; border: 1px solid #FFCC80; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem;">
                            ${uso}
                        </span>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    return html;
}
