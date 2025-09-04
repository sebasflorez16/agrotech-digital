// dashboard-inventario.js - Dashboard principal de inventario
// Carga los totales y el resumen de stock por almacén

const API_BASE = `http://${window.location.hostname}:8000/api/inventario/`;

async function fetchDashboardCounts() {
    const token = localStorage.getItem("accessToken");
    const endpoints = [
        { url: `${API_BASE}warehouses/`, el: 'dashboardWarehouseCount' },
        { url: `${API_BASE}supplies/`, el: 'dashboardSupplyCount' },
        { url: `${API_BASE}inventorymovements/`, el: 'dashboardMovementCount' },
        { url: `${API_BASE}machinery/`, el: 'dashboardMachineryCount' },
    ];
    for (const ep of endpoints) {
        try {
            const resp = await fetch(ep.url, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            if (!resp.ok) throw new Error();
            const data = await resp.json();
            document.getElementById(ep.el).textContent = data.length;
        } catch {
            document.getElementById(ep.el).textContent = 'Error';
        }
    }
}

async function fetchStockSummary() {
    const token = localStorage.getItem("accessToken");
    const url = `${API_BASE}supplies/`;
    try {
        const resp = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        if (!resp.ok) throw new Error();
        const supplies = await resp.json();
        const tbody = document.querySelector('#dashboardStockTable tbody');
        tbody.innerHTML = '';
        supplies.forEach(s => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${s.warehouse ? s.warehouse.name : '-'}</td>
                <td>${s.name}</td>
                <td>${s.quantity}</td>
                <td>${s.measure_unit ? s.measure_unit.name : '-'}</td>
            `;
            tbody.appendChild(row);
        });
    } catch {
        const tbody = document.querySelector('#dashboardStockTable tbody');
        tbody.innerHTML = '<tr><td colspan="4" class="text-danger">Error al cargar el stock</td></tr>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchDashboardCounts();
    fetchStockSummary();
});
