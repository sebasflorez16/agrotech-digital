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
 * @returns {Array} Array de colores predominantes con porcentajes
 */
function dynamicColorAnalysis(imageData, clusters = 8) {
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
        
        // Obtener nombre único
        const name = getAgriculturalColorName(r, g, b, index, usedNames);
        
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
                
                // Si menos del 30% de pixels coinciden, usar análisis dinámico
                const matchPercentage = (matchedPixels / analyzedPixels) * 100;
                console.log('[ANALYSIS] Porcentaje de coincidencia con colores predefinidos:', matchPercentage.toFixed(1) + '%');
                
                if (matchPercentage < 30) {
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
