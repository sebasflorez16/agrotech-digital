/**
 * Script temporal para configurar el token de autenticación para pruebas
 * Este script debe ejecutarse desde la consola del navegador en cualquier tenant
 * 
 * USO: Primero obtén un token via login, luego pásalo como argumento:
 *   setupAuthToken('tu_token_aqui')
 */

// NO hardcodear tokens - se pasan como argumento
const ACCESS_TOKEN = null;

/**
 * Configura el token de autenticación en localStorage
 */
function setupAuthToken() {
    try {
        // Guardar el token en localStorage
        localStorage.setItem('accessToken', ACCESS_TOKEN);
        localStorage.setItem('authToken', ACCESS_TOKEN); // Fallback
        
        console.log('✅ Token de autenticación configurado correctamente');
        console.log('🔑 Token:', ACCESS_TOKEN.substring(0, 50) + '...');
        
        // Verificar que el token se guardó correctamente
        const storedToken = localStorage.getItem('accessToken');
        if (storedToken === ACCESS_TOKEN) {
            console.log('✅ Verificación exitosa: Token almacenado correctamente');
            
            // Mostrar información del token (decodificar payload sin verificar)
            try {
                const payload = JSON.parse(atob(ACCESS_TOKEN.split('.')[1]));
                console.log('📋 Información del token:');
                console.log('   - Usuario ID:', payload.user_id);
                console.log('   - Expira:', new Date(payload.exp * 1000).toLocaleString());
                console.log('   - Emitido:', new Date(payload.iat * 1000).toLocaleString());
            } catch (e) {
                console.warn('⚠️ No se pudo decodificar el payload del token');
            }
            
            return true;
        } else {
            console.error('❌ Error: El token no se almacenó correctamente');
            return false;
        }
    } catch (error) {
        console.error('❌ Error configurando el token:', error);
        return false;
    }
}

/**
 * Verifica que el dominio actual termine en localhost (para desarrollo)
 */
function verifyDomain() {
    const currentDomain = window.location.hostname;
    
    if (currentDomain.endsWith('.localhost') || currentDomain === 'localhost') {
        console.log(`✅ Dominio de desarrollo detectado: ${currentDomain}`);
        return true;
    } else {
        console.log(`ℹ️ Dominio actual: ${currentDomain} (puede ser producción)`);
        console.log('   Este script está diseñado principalmente para desarrollo local');
        return true; // Permitir que funcione en cualquier dominio
    }
}

/**
 * Limpia tokens existentes
 */
function clearAuthTokens() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('authToken');
    sessionStorage.removeItem('accessToken');
    sessionStorage.removeItem('authToken');
    console.log('🧹 Tokens de autenticación limpiados');
}

/**
 * Muestra el estado actual de los tokens
 */
function showTokenStatus() {
    console.log('📊 Estado actual de tokens:');
    console.log('   localStorage.accessToken:', localStorage.getItem('accessToken') ? '✅ Presente' : '❌ Ausente');
    console.log('   localStorage.authToken:', localStorage.getItem('authToken') ? '✅ Presente' : '❌ Ausente');
    console.log('   sessionStorage.accessToken:', sessionStorage.getItem('accessToken') ? '✅ Presente' : '❌ Ausente');
    console.log('   sessionStorage.authToken:', sessionStorage.getItem('authToken') ? '✅ Presente' : '❌ Ausente');
}

// Función principal
function initTestTokenSetup() {
    console.log('🔧 Configuración de token de prueba para análisis meteorológico');
    console.log('='.repeat(60));
    
    verifyDomain();
    showTokenStatus();
    
    if (setupAuthToken()) {
        console.log('✅ ¡Configuración completa! Ya puedes usar el análisis meteorológico');
        console.log('💡 Para probar, navega a una parcela y verifica la sección de análisis meteorológico');
    } else {
        console.error('❌ Error en la configuración. Revisa los mensajes anteriores.');
    }
    
    console.log('='.repeat(60));
}

// Exportar funciones para uso desde la consola
window.setupAuthToken = setupAuthToken;
window.clearAuthTokens = clearAuthTokens;
window.showTokenStatus = showTokenStatus;
window.initTestTokenSetup = initTestTokenSetup;

// Ejecutar automáticamente si se carga el script
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTestTokenSetup);
} else {
    initTestTokenSetup();
}
