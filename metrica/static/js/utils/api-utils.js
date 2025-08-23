/**
 * Utilidades para generar URLs de API de forma consistente en todos los tenants
 * Agrotech - Sistema Multi-tenant
 */

/**
 * Genera la URL base del backend para el tenant actual
 * @param {string} apiPath - Ruta de la API (ej: '/api/parcels', '/api/authentication')
 * @param {number} port - Puerto del backend (por defecto 8000)
 * @returns {string} URL completa del backend
 */
function getBackendUrl(apiPath = '', port = 8000) {
    const protocol = window.location.protocol; // http: o https:
    const hostname = window.location.hostname; // tenant dinámico
    
    // Construir URL base
    let baseUrl = `${protocol}//${hostname}:${port}`;
    
    // Agregar path si se proporciona
    if (apiPath) {
        // Asegurar que el path comience con /
        const cleanPath = apiPath.startsWith('/') ? apiPath : `/${apiPath}`;
        baseUrl += cleanPath;
    }
    
    return baseUrl;
}

/**
 * Genera URLs específicas para diferentes módulos de la API
 */
const ApiUrls = {
    // Parcelas
    parcels: () => getBackendUrl('/api/parcels'),
    
    // Autenticación
    auth: () => getBackendUrl('/api/authentication'),
    
    // Recursos Humanos
    rrhh: () => getBackendUrl('/api/RRHH'),
    
    // Inventario
    inventario: () => getBackendUrl('/api/inventario'),
    
    // Cultivos
    crop: () => getBackendUrl('/api/crop'),
    
    // Usuarios
    users: () => getBackendUrl('/users/api'),
    
    // EOSDA Proxy
    eosdaWmts: () => getBackendUrl('/api/parcels/eosda-wmts-tile'),
    
    // Análisis meteorológico
    weatherAnalysis: (parcelId) => getBackendUrl(`/api/parcels/parcel/${parcelId}/ndvi-weather-comparison`),
    
    // Sentinel WMTS
    sentinelWmts: () => getBackendUrl('/parcels/sentinel-wmts-urls'),
};

/**
 * Obtiene el token de autenticación actual
 * @returns {string} Token de acceso
 */
function getAuthToken() {
    return localStorage.getItem('accessToken') || 
           localStorage.getItem('authToken') || 
           sessionStorage.getItem('accessToken') ||
           sessionStorage.getItem('authToken') || 
           '';
}

/**
 * Crea headers estándar para peticiones autenticadas
 * @param {Object} additionalHeaders - Headers adicionales opcionales
 * @returns {Object} Headers para fetch/axios
 */
function getAuthHeaders(additionalHeaders = {}) {
    const token = getAuthToken();
    const headers = {
        'Content-Type': 'application/json',
        ...additionalHeaders
    };
    
    if (token) {
        // Usar Bearer para JWT tokens, Token para DRF tokens
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
}

/**
 * Wrapper para fetch con autenticación automática
 * @param {string} url - URL del endpoint
 * @param {Object} options - Opciones de fetch
 * @returns {Promise} Promesa de fetch
 */
async function authenticatedFetch(url, options = {}) {
    const headers = getAuthHeaders(options.headers);
    
    return fetch(url, {
        ...options,
        headers
    });
}

// Exportar para uso global
window.getBackendUrl = getBackendUrl;
window.ApiUrls = ApiUrls;
window.getAuthToken = getAuthToken;
window.getAuthHeaders = getAuthHeaders;
window.authenticatedFetch = authenticatedFetch;

// Exportar para módulos ES6
export { getBackendUrl, ApiUrls, getAuthToken, getAuthHeaders, authenticatedFetch };

console.log('[API-UTILS] Utilidades de API cargadas para tenant:', window.location.hostname);
