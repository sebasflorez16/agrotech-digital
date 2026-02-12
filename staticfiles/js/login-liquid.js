/**
 * 🍎 Login Liquid Glass - AgroTech Digital
 * Autenticación con diseño Apple-inspired
 */

// Configuración API (usa config.js si está disponible)
const API_BASE_URL = window.AGROTECH_CONFIG ? window.AGROTECH_CONFIG.API_BASE : 
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://agrotechcolombia.com');

// Elementos del DOM
const loginForm = document.getElementById('loginForm');
const btnLogin = document.getElementById('btnLogin');
const btnText = document.getElementById('btnText');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');

// Verificar si ya está autenticado
function checkExistingAuth() {
    const token = localStorage.getItem('accessToken');
    if (token && token !== 'null' && token !== 'undefined') {
        console.log('Usuario ya autenticado, redirigiendo...');
        window.location.href = '../dashboard.html';
    }
}

// Mostrar error
function showError(message) {
    errorText.textContent = message;
    errorMessage.classList.add('show');
    
    // Ocultar después de 5 segundos
    setTimeout(() => {
        errorMessage.classList.remove('show');
    }, 5000);
}

// Ocultar error
function hideError() {
    errorMessage.classList.remove('show');
}

// Cambiar estado de loading
function setLoading(loading) {
    btnLogin.disabled = loading;
    if (loading) {
        btnLogin.classList.add('loading');
        btnText.textContent = 'Iniciando sesión...';
    } else {
        btnLogin.classList.remove('loading');
        btnText.textContent = 'Iniciar Sesión';
    }
}

// Manejar submit del form
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideError();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    
    // Validación básica
    if (!username || !password) {
        showError('Por favor completa todos los campos');
        return;
    }
    
    setLoading(true);
    
    try {
        // Hacer login - Usar endpoint correcto
        const loginUrl = window.AGROTECH_CONFIG?.ENDPOINTS?.LOGIN || '/api/auth/login/';
        const response = await fetch(`${API_BASE_URL}${loginUrl}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });
        
        const data = await response.json();
        
        if (!response.ok || data.success === false) {
            // Error en la autenticación
            const errorMsg = data.error || data.detail || data.message || 'Credenciales inválidas';
            showError(errorMsg);
            setLoading(false);
            return;
        }
        
        // Login exitoso - Backend devuelve { success: true, tokens: {...}, user: {...} }
        // o también puede ser { success: true, data: { tokens: {...}, user: {...} } }
        const tokens = data.tokens || data.data?.tokens || data;
        const accessToken = tokens.access || data.access || data.token;
        
        if (accessToken) {
            // Guardar token
            localStorage.setItem('accessToken', accessToken);
            const refreshToken = tokens.refresh || data.refresh;
            if (refreshToken) {
                localStorage.setItem('refreshToken', refreshToken);
            }
            
            // Guardar info del usuario si existe
            const userData = data.user || data.data?.user;
            if (userData) {
                localStorage.setItem('user', JSON.stringify(userData));
            }
            const tenantData = data.tenant || data.data?.tenant;
            if (tenantData) {
                localStorage.setItem('tenant', JSON.stringify(tenantData));
            }
            
            console.log('✅ Login exitoso');
            
            // Redirigir al dashboard
            setTimeout(() => {
                window.location.href = '../dashboard.html';
            }, 500);
            
        } else {
            showError('Respuesta inválida del servidor');
            setLoading(false);
        }
        
    } catch (error) {
        console.error('Error en login:', error);
        showError('No se pudo conectar con el servidor. Verifica tu conexión');
        setLoading(false);
    }
});

// Enter en los campos
document.getElementById('username').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('password').focus();
    }
});

// Verificar autenticación al cargar
document.addEventListener('DOMContentLoaded', () => {
    console.log('🍎 Login Liquid Glass - Iniciando...');
    checkExistingAuth();
});
