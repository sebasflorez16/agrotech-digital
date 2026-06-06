/**
 * Utilidades para generar URLs de API de forma consistente en todos los tenants
 * Agrotech - Sistema Multi-tenant
 */

/**
 * Genera la URL base del backend
 * @param {string} apiPath - Ruta de la API (ej: '/api/parcels', '/api/authentication')
 * @param {number} port - Puerto del backend (no usado en producción)
 * @returns {string} URL completa del backend
 */
function getBackendUrl(apiPath = '', port = 8000) {
    // Usar config.js centralizado
    const cfg = window.AGROTECH_CONFIG;
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const baseUrl = cfg ? cfg.API_BASE : (isLocalhost ? `http://localhost:${port}` : 'https://agrotech-digital-production.up.railway.app');
    
    // Agregar path si se proporciona
    if (apiPath) {
        // Asegurar que el path comience con /
        const cleanPath = apiPath.startsWith('/') ? apiPath : `/${apiPath}`;
        return baseUrl + cleanPath;
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
    // Si ya se disparó un auth failure, no hacer más peticiones
    if (_authFailureTriggered) {
        throw new Error('session_expired');
    }

    const headers = getAuthHeaders(options.headers);
    
    let response = await fetch(url, {
        ...options,
        headers
    });
    
    // Si recibimos 401, intentar refrescar el token
    if (response.status === 401) {
        console.log('[API-UTILS] Token expirado, intentando refresh...');
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            // Reintentar la petición con el nuevo token
            const newHeaders = getAuthHeaders(options.headers);
            response = await fetch(url, {
                ...options,
                headers: newHeaders
            });
        } else {
            // Redirigir al login inmediatamente
            handleAuthFailure();
            throw new Error('session_expired');
        }
    }
    
    return response;
}

/**
 * Control de concurrencia para el refresh de tokens.
 * Evita que múltiples peticiones 401 simultáneas disparen múltiples refreshes.
 */
let _isRefreshing = false;
let _refreshPromise = null;
let _authFailureTriggered = false;

/**
 * Intenta refrescar el token de acceso usando el refresh token.
 * Si ya hay un refresh en curso, reutiliza la misma promesa.
 * @returns {Promise<boolean>} true si se refrescó exitosamente
 */
async function refreshAccessToken() {
    // Si ya se disparó el logout, no intentar más
    if (_authFailureTriggered) return false;

    // Si ya hay un refresh en curso, esperar al resultado existente
    if (_isRefreshing && _refreshPromise) {
        return _refreshPromise;
    }

    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) {
        console.warn('[API-UTILS] No hay refresh token disponible');
        return false;
    }

    _isRefreshing = true;
    _refreshPromise = (async () => {
        try {
            const refreshUrl = getBackendUrl('/api/token/refresh/');
            const response = await fetch(refreshUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: refreshToken })
            });

            if (response.ok) {
                const data = await response.json();
                const newAccessToken = data.access || data.accessToken || data.token;
                if (newAccessToken) {
                    localStorage.setItem('accessToken', newAccessToken);
                    console.log('[API-UTILS] Token refrescado exitosamente');
                    return true;
                }
            }

            console.warn('[API-UTILS] Fallo al refrescar token:', response.status);
            return false;
        } catch (error) {
            console.error('[API-UTILS] Error al refrescar token:', error);
            return false;
        } finally {
            _isRefreshing = false;
            _refreshPromise = null;
        }
    })();

    return _refreshPromise;
}

/**
 * Maneja la falla de autenticación redirigiendo al login INMEDIATAMENTE.
 * Protegido contra múltiples invocaciones simultáneas.
 */
function handleAuthFailure() {
    // Evitar múltiples redirects simultáneos
    if (_authFailureTriggered) return;
    _authFailureTriggered = true;

    console.warn('[API-UTILS] Sesión expirada. Redirigiendo a login...');

    // Limpiar tokens inmediatamente
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');

    // Determinar URL de login correcta
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const isNetlify = window.location.hostname.includes('netlify.app');
    let loginUrl;

    if (isLocalhost) {
        loginUrl = '/templates/authentication/login.html';
    } else if (isNetlify) {
        loginUrl = '/templates/authentication/login.html';
    } else {
        // Django backend (Railway u otro)
        loginUrl = '/login/';
    }

    // Redirigir INMEDIATAMENTE sin delay
    window.location.href = loginUrl;
}

// Exportar para uso global (siempre funciona)
window.getBackendUrl = getBackendUrl;
window.ApiUrls = ApiUrls;
window.getAuthToken = getAuthToken;
window.getAuthHeaders = getAuthHeaders;
window.authenticatedFetch = authenticatedFetch;
window.refreshAccessToken = refreshAccessToken;
window.handleAuthFailure = handleAuthFailure;

// Exportar para módulos ES6 (solo si se carga como módulo)
// Nota: Este export condicional evita errores cuando se carga como script regular
if (typeof exports !== 'undefined') {
    exports.getBackendUrl = getBackendUrl;
    exports.ApiUrls = ApiUrls;
    exports.getAuthToken = getAuthToken;
    exports.getAuthHeaders = getAuthHeaders;
    exports.authenticatedFetch = authenticatedFetch;
    exports.refreshAccessToken = refreshAccessToken;
    exports.handleAuthFailure = handleAuthFailure;
}

console.log('[API-UTILS] Utilidades de API cargadas para tenant:', window.location.hostname);
