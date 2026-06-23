/**
 * 🍎 Dashboard Liquid Glass - AgroTech Digital
 * Maneja la lógica del dashboard principal con diseño Apple-inspired
 */

// Configuración API
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : window.location.origin;

// Obtener token de autenticación
function getAuthToken() {
    const token = localStorage.getItem('accessToken');
    if (!token || token === 'null' || token === 'undefined') {
        return null;
    }
    return token;
}

// Headers para requests
function getHeaders() {
    const token = getAuthToken();
    if (!token) return null;
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
            if (typeof window.refreshAccessToken === 'function') {
                const refreshed = await window.refreshAccessToken();
                if (refreshed) {
                    const newHeaders = getHeaders();
                    return await fetch(url, {
                        ...options,
                        headers: { ...newHeaders, ...options.headers }
                    });
                }
            }
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            window.location.href = '/auth-login.html';
            return null;
        }
        
        return response;
    } catch (error) {
        console.warn('Error de conexión:', error.message);
        return null;
    }
}

// Cargar información del usuario
async function loadUserInfo() {
    try {
        const token = getAuthToken();
        if (token) {
            const payload = JSON.parse(atob(token.split('.')[1]));
            
            const userName = document.getElementById('userName');
            if (userName && payload.username) {
                userName.textContent = payload.username;
            }
            
            const userAvatar = document.querySelector('.user-avatar');
            if (userAvatar && payload.username) {
                userAvatar.textContent = payload.username.charAt(0).toUpperCase();
            }
            
            const headerTitle = document.querySelector('.header-title h1');
            if (headerTitle && payload.username) {
                headerTitle.textContent = `Bienvenido de nuevo, ${payload.username} 👋`;
            }
        }
    } catch (error) {
        console.warn('Error cargando usuario:', error.message);
    }
}

// Cargar estadísticas del dashboard
async function loadDashboardStats() {
    // Cargar parcelas
    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/api/parcels/parcel/`);
        if (res && res.ok) {
            const data = await res.json();
            const list = Array.isArray(data) ? data : (data.results || []);
            updateStat('parcelCount', list.length);
        }
    } catch (e) {
        console.warn('No se pudieron cargar las parcelas');
        updateStat('parcelCount', 0);
    }
    
    // Cargar cultivos
    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/api/crop/`);
        if (res && res.ok) {
            const data = await res.json();
            const list = Array.isArray(data) ? data : (data.results || []);
            updateStat('cropCount', list.length);
        }
    } catch (e) {
        console.warn('No se pudieron cargar los cultivos');
        updateStat('cropCount', 0);
    }
    
    // Cargar empleados
    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/api/RRHH/empleados/`);
        if (res && res.ok) {
            const data = await res.json();
            const list = Array.isArray(data) ? data : (data.results || []);
            updateStat('employeeCount', list.length);
        }
    } catch (e) {
        console.warn('No se pudieron cargar los empleados');
        updateStat('employeeCount', 0);
    }
    
    // Cargar suscripción
    await loadSubscriptionInfo();
    
    // Cargar actividad reciente
    await loadRecentActivity();
}

// Actualizar un contador de estadística
function updateStat(elementId, value) {
    const el = document.getElementById(elementId);
    if (!el) return;
    animateNumber(el, value || 0);
}

// Cargar información de suscripción
async function loadSubscriptionInfo() {
    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/billing/api/my-subscription/`);
        if (res && res.ok) {
            const sub = await res.json();
            
            const planName = document.getElementById('subPlanName');
            const subStatus = document.getElementById('subStatus');
            
            if (planName && sub.plan_name) {
                planName.textContent = sub.plan_name;
            }
            if (subStatus) {
                const statusMap = {
                    'active': 'Activo ✅',
                    'paused': 'Pausado ⏸️',
                    'cancelled': 'Cancelado ❌',
                    'pending': 'Pendiente ⏳'
                };
                subStatus.textContent = statusMap[sub.status] || sub.status || 'Sin suscripción';
                subStatus.style.color = sub.status === 'active' ? 'var(--agrotech-primary-dark)' : 'var(--text-secondary)';
            }
        }
        
        // Intentar también cargar uso
        try {
            const usageRes = await fetchWithAuth(`${API_BASE_URL}/billing/api/usage/dashboard/`);
            if (usageRes && usageRes.ok) {
                const usageData = await usageRes.json();
                const satData = usageData.current_usage?.eosda_requests;
                const satUsage = document.getElementById('eosdaUsage');
                if (satUsage && satData) {
                    const used = satData.used || 0;
                    const limit = satData.limit || 100;
                    eosdaUsage.textContent = `${used}/${limit}`;
                }
            }
        } catch (e) {
            // Uso no disponible, mantener valor por defecto
        }
        
    } catch (e) {
        console.warn('Información de suscripción no disponible');
    }
}

// Cargar actividad reciente desde parcelas y cultivos
async function loadRecentActivity() {
    const activities = [];
    
    // Intentar cargar últimas parcelas
    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/api/parcels/parcel/`);
        if (res && res.ok) {
            const data = await res.json();
            const list = Array.isArray(data) ? data : (data.results || []);
            if (list.length > 0) {
                const last = list[list.length - 1];
                activities.push({
                    icon: '🌾',
                    text: `Parcela "${last.name || 'Sin nombre'}" registrada`,
                    date: last.created_at ? new Date(last.created_at).toLocaleDateString('es-ES') : 'Reciente'
                });
            }
        }
    } catch (e) {}
    
    // Intentar cargar últimos cultivos
    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/api/crop/`);
        if (res && res.ok) {
            const data = await res.json();
            const list = Array.isArray(data) ? data : (data.results || []);
            if (list.length > 0) {
                const last = list[list.length - 1];
                const name = last.crop_name || last.name || 'Sin nombre';
                activities.push({
                    icon: '📋',
                    text: `Cultivo "${name}" registrado`,
                    date: last.created_at ? new Date(last.created_at).toLocaleDateString('es-ES') : 'Reciente'
                });
            }
        }
    } catch (e) {}
    
    // Actualizar UI
    if (activities.length >= 1) {
        updateActivityItem('activityText1', 'activityDate1', activities[0]);
    }
    if (activities.length >= 2) {
        updateActivityItem('activityText2', 'activityDate2', activities[1]);
    }
}

// Actualizar un item de actividad
function updateActivityItem(textId, dateId, activity) {
    const textEl = document.getElementById(textId);
    const dateEl = document.getElementById(dateId);
    if (textEl) textEl.textContent = activity.text;
    if (dateEl) dateEl.textContent = activity.date;
}

// Animar números (contador)
function animateNumber(element, target) {
    if (!element) return;
    if (target === 0) {
        element.textContent = '0';
        return;
    }
    
    const duration = 800;
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
        localStorage.removeItem('devMode');
        localStorage.removeItem('devModeUser');
        window.location.href = '/auth-login.html';
    }
}

// ── 🔧 Developer Mode Toggle ──────────────────────────────────────
async function checkDevModeStatus() {
    const btn = document.getElementById('devModeToggle');
    if (!btn) return;

    const token = getAuthToken();
    if (!token) return;

    try {
        const res = await fetchWithAuth(`${API_BASE_URL}/api/auth/devmode/status/`);
        if (res && res.ok) {
            const data = await res.json();
            // Solo mostrar toggle si es superuser
            if (!data.is_superuser) return;
            btn.style.display = 'flex';
            updateDevModeUI(data.dev_mode === true);
        }
    } catch { /* silencioso */ }
}

function updateDevModeUI(active) {
    const btn = document.getElementById('devModeToggle');
    if (!btn) return;

    const label = btn.querySelector('.devmode-label');
    if (active) {
        btn.classList.add('devmode-on');
        btn.classList.remove('devmode-off');
        if (label) label.textContent = '🔧 DEV ON';
    } else {
        btn.classList.remove('devmode-on');
        btn.classList.add('devmode-off');
        if (label) label.textContent = 'DEV OFF';
    }
}

async function toggleDevMode() {
    const btn = document.getElementById('devModeToggle');
    const isActive = btn.classList.contains('devmode-on');

    if (isActive) {
        // Desactivar directamente
        const res = await fetchWithAuth(`${API_BASE_URL}/api/auth/devmode/deactivate/`, { method: 'POST' });
        if (res && res.ok) {
            updateDevModeUI(false);
        }
    } else {
        // Pedir PIN para activar
        showDevModePinModal(async (pin) => {
            const res = await fetchWithAuth(`${API_BASE_URL}/api/auth/devmode/activate/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pin })
            });
            if (res && res.ok) {
                const data = await res.json();
                if (data.success) {
                    updateDevModeUI(true);
                    return;
                }
            }
            alert('PIN incorrecto. Usa el PIN de desarrollador configurado en el servidor.');
        });
    }
}

function showDevModePinModal(onSubmit) {
    // Eliminar modal existente si hay
    const existing = document.querySelector('.devmode-modal-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.className = 'devmode-modal-overlay';
    overlay.innerHTML = `
        <div class="devmode-modal">
            <h3>🔐 Acceso Desarrollador</h3>
            <p style="font-size:0.85rem;color:#64748b;margin:0 0 16px;">Ingresa el PIN de desarrollador para activar el modo sin límites.</p>
            <input type="password" id="devmodePinInput" placeholder="PIN de desarrollador" autofocus />
            <div class="devmode-modal-actions">
                <button class="btn-cancel" id="devmodeCancel">Cancelar</button>
                <button class="btn-confirm" id="devmodeConfirm">Activar</button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    const input = overlay.querySelector('#devmodePinInput');
    const confirmBtn = overlay.querySelector('#devmodeConfirm');
    const cancelBtn = overlay.querySelector('#devmodeCancel');

    const cleanup = () => overlay.remove();

    confirmBtn.addEventListener('click', () => {
        const pin = input.value.trim();
        if (!pin) { alert('Ingresa el PIN'); return; }
        cleanup();
        onSubmit(pin);
    });

    cancelBtn.addEventListener('click', cleanup);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) cleanup();
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') confirmBtn.click();
        if (e.key === 'Escape') cleanup();
    });

    input.focus();
}

// ── Inicialización ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async function() {
    console.log('🍎 Dashboard Liquid Glass - Iniciando...');
    
    const token = getAuthToken();
    if (!token) {
        window.location.href = '/auth-login.html';
        return;
    }
    
    // Verificar expiración del token JWT
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp * 1000 < Date.now()) {
            console.warn('[AUTH] Token JWT expirado. Intentando refrescar...');
            const refreshed = typeof window.refreshAccessToken === 'function'
                ? await window.refreshAccessToken()
                : false;
            if (refreshed) {
                location.reload();
                return;
            }
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            window.location.href = '/auth-login.html';
            return;
        }
    } catch (e) {
        // Token no es JWT válido
    }
    
    // Cargar datos secuencialmente con manejo de errores
    await loadUserInfo();
    await loadDashboardStats();
    await checkDevModeStatus();

    // Vincular toggle de dev mode
    const devBtn = document.getElementById('devModeToggle');
    if (devBtn) {
        devBtn.addEventListener('click', toggleDevMode);
    }

    console.log('✅ Dashboard cargado');
});