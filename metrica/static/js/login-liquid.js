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
        // Hacer login
        const response = await fetch(`${API_BASE_URL}/api/authentication/login/`, {
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
        
        if (!response.ok) {
            // Error en la autenticación
            if (response.status === 401) {
                showError('Usuario o contraseña incorrectos');
            } else if (response.status === 400) {
                showError(data.detail || data.error || 'Datos inválidos');
            } else {
                showError('Error al iniciar sesión. Intenta nuevamente');
            }
            setLoading(false);
            return;
        }
        
        // Login exitoso
        if (data.access || data.token) {
            const token = data.access || data.token;
            
            // Guardar token
            localStorage.setItem('accessToken', token);
            if (data.refresh) {
                localStorage.setItem('refreshToken', data.refresh);
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
