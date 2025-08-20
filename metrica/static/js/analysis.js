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

export function analyzeImageByColor(imageSrc, colorRanges) {
    return new Promise((resolve, reject) => {
        const img = new window.Image();
        img.crossOrigin = "Anonymous";
        img.onload = function () {
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
            const imageData = ctx.getImageData(0, 0, img.width, img.height);
            const data = imageData.data;
            const totalPixels = img.width * img.height;
            const results = colorRanges.map(r => ({ name: r.name, count: 0, percent: 0 }));

            // Función para comparar colores con tolerancia
            function colorMatch(r1, g1, b1, r2, g2, b2, tolerance) {
                return Math.abs(r1 - r2) <= tolerance &&
                       Math.abs(g1 - g2) <= tolerance &&
                       Math.abs(b1 - b2) <= tolerance;
            }

            for (let i = 0; i < data.length; i += 4) {
                const r = data[i], g = data[i + 1], b = data[i + 2];
                for (let j = 0; j < colorRanges.length; j++) {
                    const { rgb, tolerance } = colorRanges[j];
                    if (colorMatch(r, g, b, rgb[0], rgb[1], rgb[2], tolerance)) {
                        results[j].count++;
                        break;
                    }
                }
            }
            results.forEach(r => {
                r.percent = ((r.count / totalPixels) * 100).toFixed(2);
            });
            resolve({ totalPixels, results });
        };
        img.onerror = function () {
            reject(new Error('No se pudo cargar la imagen para análisis.'));
        };
        img.src = imageSrc;
    });
}

/**
 * Ejemplo de uso para NDVI:
 *
 * import { analyzeImageByColor } from './analysis.js';
 *
 * const ndviColors = [
 *   { name: 'Vegetación densa', rgb: [46, 204, 64], tolerance: 20 }, // #2ecc40
 *   { name: 'Vegetación moderada', rgb: [255, 206, 52], tolerance: 20 }, // #ffce34
 *   { name: 'Vegetación escasa', rgb: [255, 127, 14], tolerance: 20 }, // #ff7f0e
 *   { name: 'Suelo/Nubes', rgb: [189, 189, 189], tolerance: 20 } // #bdbdbd
 * ];
 *
 * analyzeImageByColor(imageSrc, ndviColors).then(res => {
 *   // res.results: [{ name, count, percent }]
 * });
 */
