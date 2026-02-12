/**
 * 🍎 Dashboard Liquid Glass - AgroTech Digital
 * Maneja la lógica del dashboard principal con diseño Apple-inspired
 */

// Configuración API
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://agrotechcolombia.com';

// Obtener token de autenticación
function getAuthToken() {
    const token = localStorage.getItem('accessToken');
    if (!token || token === 'null' || token === 'undefined') {
        window.location.href = '../authentication/login.html';
        return null;
    }
    return token;
}

// Headers para requests
function getHeaders() {
    const token = getAuthToken();
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

// Función para hacer fetch con autenticación
async function fetchWithAuth(url, options = {}) {
    const headers = getHeaders();
    if (!headers) return null;
    
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                ...headers,
                ...options.headers
            }
        });
        
        if (response.status === 401) {
            localStorage.removeItem('accessToken');
            window.location.href = '../authentication/login.html';
            return null;
        }
        
        return response;
    } catch (error) {
        console.error('Error en fetch:', error);
        return null;
    }
}

// Cargar información del usuario
async function loadUserInfo() {
    try {
        const token = getAuthToken();
        if (token) {
            // Decodificar payload del JWT
            const payload = JSON.parse(atob(token.split('.')[1]));
            
            // Actualizar nombre de usuario
            const userName = document.getElementById('userName');
            if (userName && payload.username) {
                userName.textContent = payload.username;
            }
            
            // Actualizar avatar con inicial
            const userAvatar = document.querySelector('.user-avatar');
            if (userAvatar && payload.username) {
                userAvatar.textContent = payload.username.charAt(0).toUpperCase();
            }
            
            // Actualizar saludo personalizado
            const headerTitle = document.querySelector('.header-title h1');
            if (headerTitle && payload.username) {
                headerTitle.textContent = `Bienvenido de nuevo, ${payload.username} 👋`;
            }
        }
    } catch (error) {
        console.error('Error cargando usuario:', error);
    }
}

// Cargar estadísticas del dashboard
async function loadDashboardStats() {
    try {
        // Cargar parcelas
        const parcelsResponse = await fetchWithAuth(`${API_BASE_URL}/api/parcels/`);
        if (parcelsResponse && parcelsResponse.ok) {
            const parcels = await parcelsResponse.json();
            const parcelCount = document.getElementById('parcelCount');
            if (parcelCount) {
                parcelCount.textContent = parcels.length || 0;
                animateNumber(parcelCount, parcels.length || 0);
            }
        }
        
        // Cargar cultivos
        const cropsResponse = await fetchWithAuth(`${API_BASE_URL}/api/crop/crops/`);
        if (cropsResponse && cropsResponse.ok) {
            const crops = await cropsResponse.json();
            const cropCount = document.getElementById('cropCount');
            if (cropCount) {
                animateNumber(cropCount, crops.length || 0);
            }
        }
        
        // Cargar empleados
        const employeesResponse = await fetchWithAuth(`${API_BASE_URL}/api/RRHH/empleados/`);
        if (employeesResponse && employeesResponse.ok) {
            const employees = await employeesResponse.json();
            const employeeCount = document.getElementById('employeeCount');
            if (employeeCount) {
                animateNumber(employeeCount, employees.length || 0);
            }
        }
        
        // Cargar uso de EOSDA
        await loadEOSDAUsage();
        
    } catch (error) {
        console.error('Error cargando estadísticas:', error);
    }
}

// Cargar uso de EOSDA desde billing
async function loadEOSDAUsage() {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/billing/api/usage/dashboard/`);
        if (response && response.ok) {
            const data = await response.json();
            const eosdaUsage = document.getElementById('eosdaUsage');
            
            if (eosdaUsage && data.current_usage && data.current_usage.eosda_requests) {
                const used = data.current_usage.eosda_requests.used || 0;
                const limit = data.current_usage.eosda_requests.limit || 100;
                eosdaUsage.textContent = `${used}/${limit}`;
                animateNumber(eosdaUsage, used);
            }
            
            // Actualizar información de suscripción
            displaySubscriptionInfo(data);
        }
    } catch (error) {
        console.error('Error cargando uso EOSDA:', error);
        const eosdaUsage = document.getElementById('eosdaUsage');
        if (eosdaUsage) {
            eosdaUsage.textContent = '--';
        }
    }
}

// Mostrar información de suscripción
function displaySubscriptionInfo(data) {
    const container = document.getElementById('subscriptionInfo');
    if (!container) return;
    
    const subscription = data.subscription || {};
    const eosdaUsage = data.current_usage?.eosda_requests || {};
    const alerts = data.alerts || [];
    
    const percentage = eosdaUsage.percentage || 0;
    const status = eosdaUsage.status || 'ok';
    
    let statusClass = 'success';
    let statusText = 'Todo bien';
    let statusIcon = '✅';
    
    if (status === 'warning') {
        statusClass = 'warning';
        statusText = 'Acercándose al límite';
        statusIcon = '⚠️';
    } else if (status === 'exceeded') {
        statusClass = 'danger';
        statusText = 'Límite excedido';
        statusIcon = '🚫';
    }
    
    container.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-lg);">
            <div>
                <h3 style="font-size: 1.125rem; margin-bottom: var(--space-xs);">${subscription.name || 'Plan Básico'}</h3>
                <p style="color: var(--text-secondary); font-size: 0.875rem;">
                    $${Number(subscription.monthly_price || 0).toLocaleString('es-CO')} COP/mes
                </p>
            </div>
            <div class="alert-badge ${statusClass}">
                ${statusIcon} ${statusText}
            </div>
        </div>
        
        <div style="margin-bottom: var(--space-sm);">
            <div style="display: flex; justify-content: space-between; margin-bottom: var(--space-xs);">
                <span style="font-size: 0.875rem; color: var(--text-secondary);">Análisis EOSDA</span>
                <span style="font-weight: var(--font-weight-semibold);">${eosdaUsage.used || 0} / ${eosdaUsage.limit || 100}</span>
            </div>
            <div class="progress-glass">
                <div class="progress-glass-bar ${statusClass}" style="width: ${Math.min(percentage, 100)}%"></div>
            </div>
        </div>
        
        ${alerts.length > 0 ? `
            <div style="margin-top: var(--space-lg); padding: var(--space-md); background: rgba(255, 159, 10, 0.1); border-radius: var(--radius-md); border: 1px solid rgba(255, 159, 10, 0.2);">
                <p style="font-size: 0.875rem; color: #D97706; margin: 0;">
                    <i class="ti ti-alert-circle"></i> ${alerts[0].message}
                </p>
            </div>
        ` : ''}
        
        <div style="margin-top: var(--space-lg);">
            <a href="billing.html" class="btn-glass-primary" style="width: 100%; text-align: center; display: block; text-decoration: none;">
                Ver Detalles de Facturación
            </a>
        </div>
    `;
}

// Animar números (contador)
function animateNumber(element, target) {
    if (!element) return;
    
    const duration = 1000;
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = target;
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current);
        }
    }, 16);
}

// Logout
function logout() {
    if (confirm('¿Estás seguro que deseas cerrar sesión?')) {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '../authentication/login.html';
    }
}

// Inicialización
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🍎 Dashboard Liquid Glass - Iniciando...');
    
    // Verificar autenticación
    if (!getAuthToken()) {
        return;
    }
    
    // Cargar datos
    await loadUserInfo();
    await loadDashboardStats();
    
    console.log('✅ Dashboard cargado correctamente');
});
