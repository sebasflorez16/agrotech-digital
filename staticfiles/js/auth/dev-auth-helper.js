/**
 * Sistema de Desarrollo Seguro - Sin Tokens Hardcodeados
 * Agrotech - Sistema Multi-tenant
 */

/**
 * Verifica si el usuario tiene una sesión activa válida
 * @returns {boolean} true si hay sesión activa
 */
function checkAuthenticationStatus() {
    console.log('🔐 Verificando estado de autenticación...');
    
    const accessToken = localStorage.getItem('accessToken');
    const refreshToken = localStorage.getItem('refreshToken');
    
    if (!accessToken) {
        console.warn('⚠️ No hay token de acceso almacenado');
        return false;
    }
    
    // Verificar si el token está expirado (sin revelar el contenido)
    try {
        const payload = JSON.parse(atob(accessToken.split('.')[1]));
        const isExpired = payload.exp * 1000 < Date.now();
        
        if (isExpired) {
            console.warn('⏰ Token de acceso expirado');
            if (refreshToken) {
                console.log('🔄 Token de refresh disponible - se puede renovar');
            } else {
                console.log('❌ No hay token de refresh - requiere nuevo login');
            }
            return false;
        }
        
        console.log('✅ Token de acceso válido');
        console.log(`👤 Usuario ID: ${payload.user_id}`);
        console.log(`⏰ Expira: ${new Date(payload.exp * 1000).toLocaleString()}`);
        return true;
        
    } catch (error) {
        console.error('❌ Error verificando token:', error.message);
        return false;
    }
}

/**
 * Redirige al usuario al login si no está autenticado
 */
function redirectToLoginIfNeeded() {
    if (!checkAuthenticationStatus()) {
        console.log('🔀 Redirigiendo al login...');
        const loginUrl = '/templates/authentication/login.html';
        
        // Guardar la URL actual para redirección post-login
        sessionStorage.setItem('postLoginRedirect', window.location.href);
        
        window.location.href = loginUrl;
        return true;
    }
    return false;
}

/**
 * Muestra información del tenant actual (sin exponer datos sensibles)
 */
function showTenantInfo() {
    console.log('🏢 Información del Tenant:');
    console.log(`- Hostname: ${window.location.hostname}`);
    console.log(`- Protocolo: ${window.location.protocol}`);
    console.log(`- Puerto Frontend: ${window.location.port || 'default'}`);
    console.log(`- Backend URL: ${window.getBackendUrl ? window.getBackendUrl() : 'API utils no cargadas'}`);
}

/**
 * Realiza una prueba de conectividad con el backend
 */
async function testBackendConnectivity() {
    if (!checkAuthenticationStatus()) {
        console.log('❌ No se puede probar conectividad sin autenticación');
        return false;
    }
    
    try {
        const healthUrl = window.getBackendUrl ? 
            window.getBackendUrl('/api/authentication/dashboard/') :
            `${window.location.protocol}//${window.location.hostname}:8000/api/authentication/dashboard/`;
        
        console.log('🔗 Probando conectividad con backend...');
        
        const response = await fetch(healthUrl, {
            method: 'GET',
            headers: window.getAuthHeaders ? window.getAuthHeaders() : {
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            console.log('✅ Conectividad con backend exitosa');
            const data = await response.json();
            console.log('📊 Datos del dashboard recibidos correctamente');
            return true;
        } else {
            console.error(`❌ Error de conectividad: ${response.status} ${response.statusText}`);
            return false;
        }
        
    } catch (error) {
        console.error('❌ Error de red:', error.message);
        return false;
    }
}

/**
 * Comando de desarrollo seguro para hacer logout
 */
function devLogout() {
    console.log('🚪 Realizando logout...');
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    sessionStorage.clear();
    console.log('✅ Sesión limpia - redirigiendo al login');
    window.location.href = '/templates/authentication/login.html';
}

/**
 * Comando de desarrollo para mostrar información del sistema
 */
function devSystemInfo() {
    console.log('=== INFORMACIÓN DEL SISTEMA DE DESARROLLO ===');
    showTenantInfo();
    checkAuthenticationStatus();
    
    if (window.getBackendUrl) {
        console.log('✅ Utilidades de API cargadas correctamente');
    } else {
        console.log('⚠️ Utilidades de API no encontradas');
    }
    
    console.log('=== COMANDOS DISPONIBLES ===');
    console.log('- devSystemInfo(): Mostrar información del sistema');
    console.log('- devLogout(): Hacer logout seguro');
    console.log('- testBackendConnectivity(): Probar conectividad con backend');
    console.log('- redirectToLoginIfNeeded(): Verificar autenticación y redirigir si es necesario');
    console.log('=======================================');
}

// Exportar funciones para uso en desarrollo
window.devSystemInfo = devSystemInfo;
window.devLogout = devLogout;
window.testBackendConnectivity = testBackendConnectivity;
window.redirectToLoginIfNeeded = redirectToLoginIfNeeded;
window.checkAuthenticationStatus = checkAuthenticationStatus;

// Mensaje inicial
console.log('🛡️ Sistema de desarrollo seguro cargado');
console.log('💡 Ejecuta devSystemInfo() para ver comandos disponibles');

export { 
    checkAuthenticationStatus, 
    redirectToLoginIfNeeded, 
    testBackendConnectivity, 
    devLogout, 
    devSystemInfo 
};
