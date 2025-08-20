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

export function analyzeImageByColor(imageSrc, colorRanges) {
    return new Promise((resolve, reject) => {
        console.log('[ANALYSIS] Iniciando análisis de imagen:', {
            imageSrcLength: imageSrc.length,
            colorRangesCount: colorRanges.length,
            isBase64: imageSrc.startsWith('data:')
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
    
    const legendItems = results.map(result => {
        // Buscar el color correspondiente en las definiciones
        const color = result.color || [128, 128, 128]; // Color por defecto
        const colorStyle = `background-color: rgb(${color.join(',')})`;
        return `
            <div class="d-flex align-items-center mb-2">
                <div class="legend-color-box" style="${colorStyle}; width: 20px; height: 20px; margin-right: 8px; border: 1px solid #ccc; border-radius: 3px;"></div>
                <span class="legend-label">${result.name}: <strong>${result.percent}%</strong></span>
            </div>
        `;
    }).join('');
    
    return `
        <div class="color-analysis-legend">
            <h6 class="mb-3">${title}</h6>
            ${legendItems}
            <small class="text-muted">Total pixels analizados: ${results.reduce((sum, r) => sum + parseInt(r.count || 0), 0).toLocaleString()}</small>
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
 * @returns {Array} Array de colores predominantes con porcentajes
 */
function dynamicColorAnalysis(imageData, clusters = 5) {
    const data = imageData.data;
    const colorMap = new Map();
    
    // Agrupar colores similares
    for (let i = 0; i < data.length; i += 4) {
        const r = data[i], g = data[i + 1], b = data[i + 2], a = data[i + 3];
        
        // Ignorar pixels transparentes
        if (a < 128) continue;
        
        // Reducir resolución de color para agrupar similares
        const reducedR = Math.floor(r / 20) * 20;
        const reducedG = Math.floor(g / 20) * 20;
        const reducedB = Math.floor(b / 20) * 20;
        
        const colorKey = `${reducedR},${reducedG},${reducedB}`;
        colorMap.set(colorKey, (colorMap.get(colorKey) || 0) + 1);
    }
    
    // Ordenar colores por frecuencia
    const sortedColors = Array.from(colorMap.entries())
        .sort((a, b) => b[1] - a[1])
        .slice(0, clusters);
    
    const totalPixels = Array.from(colorMap.values()).reduce((sum, count) => sum + count, 0);
    
    return sortedColors.map(([colorKey, count], index) => {
        const [r, g, b] = colorKey.split(',').map(Number);
        const percent = ((count / totalPixels) * 100).toFixed(1);
        
        // Asignar nombres basados en tonalidad
        let name = `Color ${index + 1}`;
        if (r > g && r > b) name = r > 200 ? 'Rojizo' : 'Marrón/Seco';
        else if (g > r && g > b) name = g > 150 ? 'Verde/Vegetación' : 'Verde oscuro';
        else if (b > r && b > g) name = 'Azul/Agua';
        else if (r + g + b < 300) name = 'Oscuro/Sombra';
        else name = 'Claro/Suelo';
        
        return {
            name: `${name}`,
            rgb: [r, g, b],
            count: count,
            percent: percent
        };
    });
}

/**
 * Función mejorada que combina análisis predefinido con análisis dinámico
 */
export function analyzeImageByColorAdvanced(imageSrc, colorRanges) {
    return new Promise((resolve, reject) => {
        console.log('[ANALYSIS] Iniciando análisis avanzado de imagen:', {
            imageSrcLength: imageSrc.length,
            colorRangesCount: colorRanges.length,
            isBase64: imageSrc.startsWith('data:')
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
                
                // Si menos del 20% de pixels coinciden, usar análisis dinámico
                const matchPercentage = (matchedPixels / analyzedPixels) * 100;
                console.log('[ANALYSIS] Porcentaje de coincidencia con colores predefinidos:', matchPercentage.toFixed(1) + '%');
                
                if (matchPercentage < 20) {
                    console.log('[ANALYSIS] Bajo porcentaje de coincidencia, activando análisis dinámico...');
                    const dynamicResults = dynamicColorAnalysis(imageData);
                    
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
