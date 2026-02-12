/**
 * 🍎 Billing Liquid Glass - AgroTech Digital
 * Gestión de facturación y uso con diseño Apple-inspired
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

// Cargar métricas de uso
async function loadUsageMetrics() {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/billing/api/usage/dashboard/`);
        if (!response || !response.ok) {
            console.error('Error cargando métricas');
            return;
        }
        
        const data = await response.json();
        displayMetrics(data);
        
    } catch (error) {
        console.error('Error:', error);
    }
}

// Mostrar métricas en cards
function displayMetrics(data) {
    const container = document.getElementById('metricsGrid');
    if (!container) return;
    
    const usage = data.current_usage || {};
    const resources = ['eosda_requests', 'parcels', 'hectares', 'users'];
    
    const labels = {
        eosda_requests: 'Análisis EOSDA',
        parcels: 'Parcelas',
        hectares: 'Hectáreas',
        users: 'Usuarios'
    };
    
    const icons = {
        eosda_requests: 'satellite',
        parcels: 'map',
        hectares: 'ruler',
        users: 'users'
    };
    
    container.innerHTML = resources.map(resource => {
        const metric = usage[resource] || {};
        const used = metric.used || 0;
        const limit = metric.limit || 0;
        const percentage = metric.percentage || 0;
        const status = metric.status || 'ok';
        
        let statusClass = 'success';
        let statusIcon = '✅';
        
        if (status === 'warning') {
            statusClass = 'warning';
            statusIcon = '⚠️';
        } else if (status === 'exceeded') {
            statusClass = 'danger';
            statusIcon = '🚫';
        }
        
        return `
            <div class="metric-card">
                <div class="metric-header">
                    <div class="metric-title">
                        <i class="ti ti-${icons[resource]}"></i>
                        ${labels[resource]}
                    </div>
                    <div class="alert-badge ${statusClass}" style="font-size: 1rem;">
                        ${statusIcon}
                    </div>
                </div>
                <div class="metric-value">${used}</div>
                <div class="metric-limit">de ${limit} disponibles</div>
                <div style="margin-top: var(--space-md);">
                    <div class="progress-glass">
                        <div class="progress-glass-bar ${statusClass}" style="width: ${Math.min(percentage, 100)}%"></div>
                    </div>
                    <div style="text-align: right; margin-top: var(--space-xs); font-size: 0.875rem; color: var(--text-secondary);">
                        ${percentage.toFixed(1)}%
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Cargar historial de uso
let usageChart = null;

async function loadUsageHistory(months = 6) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/billing/api/usage/history/?months=${months}`);
        if (!response || !response.ok) {
            console.error('Error cargando historial');
            return;
        }
        
        const data = await response.json();
        displayUsageChart(data);
        
    } catch (error) {
        console.error('Error:', error);
    }
}

// Mostrar gráfico de uso
function displayUsageChart(data) {
    const ctx = document.getElementById('usageChart');
    if (!ctx) return;
    
    // Ordenar por fecha (más antiguo primero)
    const sortedData = Object.entries(data).sort((a, b) => a[0].localeCompare(b[0]));
    
    const labels = sortedData.map(([month, _]) => {
        const [year, monthNum] = month.split('-');
        const monthNames = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
        return `${monthNames[parseInt(monthNum) - 1]} ${year}`;
    });
    
    const eosdaData = sortedData.map(([_, metrics]) => metrics.eosda_requests || 0);
    
    // Destruir chart anterior si existe
    if (usageChart) {
        usageChart.destroy();
    }
    
    usageChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Análisis EOSDA',
                data: eosdaData,
                borderColor: '#2FB344',
                backgroundColor: 'rgba(47, 179, 68, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#2FB344',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    titleColor: '#1D1D1F',
                    bodyColor: '#1D1D1F',
                    borderColor: 'rgba(0, 0, 0, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#86868B',
                        font: {
                            family: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", sans-serif'
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)',
                        borderDash: [5, 5]
                    }
                },
                x: {
                    ticks: {
                        color: '#86868B',
                        font: {
                            family: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", sans-serif'
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Cargar factura actual
async function loadCurrentInvoice() {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/billing/api/invoice/current/`);
        if (!response || !response.ok) {
            console.error('Error cargando factura');
            return;
        }
        
        const invoice = await response.json();
        displayInvoice(invoice);
        
    } catch (error) {
        console.error('Error:', error);
    }
}

// Mostrar factura
function displayInvoice(invoice) {
    // Actualizar período
    const periodElement = document.getElementById('invoicePeriod');
    if (periodElement) {
        const startDate = new Date(invoice.period_start).toLocaleDateString('es-CO', { day: 'numeric', month: 'long', year: 'numeric' });
        const endDate = new Date(invoice.period_end).toLocaleDateString('es-CO', { day: 'numeric', month: 'long', year: 'numeric' });
        periodElement.textContent = `Período: ${startDate} - ${endDate} (${invoice.days_remaining} días restantes)`;
    }
    
    // Actualizar líneas de factura
    const linesContainer = document.getElementById('invoiceLines');
    if (linesContainer) {
        linesContainer.innerHTML = invoice.line_items.map(item => `
            <div class="invoice-line">
                <div>
                    <div style="font-weight: var(--font-weight-medium); margin-bottom: var(--space-xs);">${item.description}</div>
                    ${item.quantity > 1 ? `<div style="font-size: 0.875rem; color: var(--text-secondary);">${item.quantity} × $${Number(item.unit_price).toLocaleString('es-CO')} COP</div>` : ''}
                </div>
                <div style="font-weight: var(--font-weight-semibold); font-size: 1.125rem;">
                    $${Number(item.amount).toLocaleString('es-CO')} COP
                </div>
            </div>
        `).join('') + `
            <div class="invoice-line" style="opacity: 0.6;">
                <div>Subtotal</div>
                <div style="font-weight: var(--font-weight-medium);">$${Number(invoice.subtotal).toLocaleString('es-CO')} COP</div>
            </div>
            <div class="invoice-line" style="opacity: 0.6;">
                <div>IVA (19%)</div>
                <div style="font-weight: var(--font-weight-medium);">$${Number(invoice.tax_amount).toLocaleString('es-CO')} COP</div>
            </div>
        `;
    }
    
    // Actualizar total
    const totalElement = document.getElementById('invoiceTotal');
    if (totalElement) {
        totalElement.textContent = `$${Number(invoice.total).toLocaleString('es-CO')} COP`;
    }
}

// Procesar pago
function processPayment() {
    alert('🚧 Integración de pago en desarrollo\n\nPróximamente: MercadoPago');
}

// Logout
function logout() {
    if (confirm('¿Estás seguro que deseas cerrar sesión?')) {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '../authentication/login.html';
    }
}

// Cambio de período en el select
document.addEventListener('DOMContentLoaded', () => {
    const monthsSelect = document.getElementById('monthsSelect');
    if (monthsSelect) {
        monthsSelect.addEventListener('change', (e) => {
            loadUsageHistory(parseInt(e.target.value));
        });
    }
});

// Inicialización
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🍎 Billing Liquid Glass - Iniciando...');
    
    // Verificar autenticación
    if (!getAuthToken()) {
        return;
    }
    
    // Cargar datos
    await loadUsageMetrics();
    await loadUsageHistory(6);
    await loadCurrentInvoice();
    
    console.log('✅ Billing cargado correctamente');
});
