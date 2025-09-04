// JS profesional para gestión de movimientos de inventario
// CRUD, carga dinámica de activos, validaciones y feedback visual

// Ruta DRF real para movimientos
const API_BASE = '/api/inventario/inventory-movements/';
const ASSET_TYPES = [
    { name: 'Insumo', api: '/api/supplies/', contentTypeId: null },
    { name: 'Maquinaria', api: '/api/machinery/', contentTypeId: null },
    // Puedes agregar más tipos si tienes herramientas, etc.
];

// Cargar ContentType IDs dinámicamente
async function loadContentTypeIds() {
    // Requiere endpoint /api/contenttypes/ o similar
    // Aquí se simula con valores fijos, deberías ajustarlo según tu backend
    ASSET_TYPES[0].contentTypeId = 7; // Ejemplo: Supply
    ASSET_TYPES[1].contentTypeId = 8; // Ejemplo: Machinery
}

// Cargar tipos de activo en el modal
function renderAssetTypeOptions() {
    const select = document.getElementById('movementAssetType');
    select.innerHTML = '';
    ASSET_TYPES.forEach(type => {
        const opt = document.createElement('option');
        opt.value = type.contentTypeId;
        opt.textContent = type.name;
        select.appendChild(opt);
    });
}

// Cargar activos según tipo seleccionado
async function loadAssetsForType(contentTypeId) {
    const type = ASSET_TYPES.find(t => t.contentTypeId == contentTypeId);
    if (!type) return;
    const res = await fetch(type.api);
    const data = await res.json();
    const select = document.getElementById('movementAsset');
    select.innerHTML = '';
    data.forEach(asset => {
        const opt = document.createElement('option');
        opt.value = asset.id;
        opt.textContent = asset.name || asset.model || asset.serial_number || `ID ${asset.id}`;
        select.appendChild(opt);
    });
}

// Cargar movimientos en la tabla
async function loadMovements() {
    const res = await fetch(API_BASE);
    const data = await res.json();
    const tbody = document.querySelector('#movementTable tbody');
    tbody.innerHTML = '';
    data.forEach(mov => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${new Date(mov.date).toLocaleString()}</td>
            <td>${mov.movement_type}</td>
            <td>${mov.asset_id}</td>
            <td>${mov.quantity}</td>
            <td>${mov.origin_location || ''}</td>
            <td>${mov.destination_location || ''}</td>
            <td>${mov.user || ''}</td>
            <td>${mov.reason || ''}</td>
            <td>
                <button class="btn btn-info btn-sm" onclick="viewMovement(${mov.id})"><i class="fa fa-eye"></i></button>
                <button class="btn btn-warning btn-sm" onclick="editMovement(${mov.id})"><i class="fa fa-edit"></i></button>
                <button class="btn btn-danger btn-sm" onclick="deleteMovement(${mov.id})"><i class="fa fa-trash"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Abrir modal para nuevo movimiento
function openNewMovementModal() {
    document.getElementById('movementForm').reset();
    document.getElementById('movementId').value = '';
    document.getElementById('movementModalLabel').textContent = 'Registrar Movimiento';
    document.getElementById('movementModal').classList.add('show');
    document.getElementById('movementModal').style.display = 'block';
}

// Cerrar modal
function closeMovementModal() {
    document.getElementById('movementModal').classList.remove('show');
    document.getElementById('movementModal').style.display = 'none';
}

// Guardar movimiento (crear/editar)
document.getElementById('movementForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const id = document.getElementById('movementId').value;
    const formData = new FormData(this);
    // content_type y asset_id deben ir en el payload
    formData.set('content_type', document.getElementById('movementAssetType').value);
    formData.set('asset_id', document.getElementById('movementAsset').value);
    const method = id ? 'PUT' : 'POST';
    const url = id ? `${API_BASE}${id}/` : API_BASE;
    const res = await fetch(url, {
        method,
        body: formData
    });
    if (res.ok) {
        closeMovementModal();
        loadMovements();
    } else {
        let msg = 'Error al guardar el movimiento';
        try {
            const err = await res.json();
            if (err.detail) msg += ': ' + err.detail;
        } catch {}
        alert(msg);
    }
});

// Editar movimiento
async function editMovement(id) {
    const res = await fetch(`${API_BASE}${id}/`);
    const mov = await res.json();
    document.getElementById('movementId').value = mov.id;
    document.getElementById('movementType').value = mov.movement_type;
    document.getElementById('movementAssetType').value = mov.content_type;
    await loadAssetsForType(mov.content_type);
    document.getElementById('movementAsset').value = mov.asset_id;
    document.getElementById('movementQuantity').value = mov.quantity;
    document.getElementById('movementUnitValue').value = mov.unit_value || '';
    document.getElementById('movementOrigin').value = mov.origin_location || '';
    document.getElementById('movementDestination').value = mov.destination_location || '';
    document.getElementById('movementUser').value = mov.user || '';
    document.getElementById('movementReason').value = mov.reason || '';
    document.getElementById('movementNotes').value = mov.notes || '';
    document.getElementById('movementModalLabel').textContent = 'Editar Movimiento';
    document.getElementById('movementModal').classList.add('show');
    document.getElementById('movementModal').style.display = 'block';
}

// Eliminar movimiento
async function deleteMovement(id) {
    if (!confirm('¿Seguro que deseas eliminar este movimiento?')) return;
    const res = await fetch(`${API_BASE}${id}/`, { method: 'DELETE' });
    if (res.ok) loadMovements();
    else alert('Error al eliminar');
}

// Ver detalle (puedes mejorar esto con un modal profesional)
// Modal profesional para ver detalle de movimiento
async function viewMovement(id) {
    const res = await fetch(`${API_BASE}${id}/`);
    if (!res.ok) {
        alert('No se pudo cargar el detalle');
        return;
    }
    const mov = await res.json();
    // Renderiza el detalle en el modal
    let html = `<div class="mb-2"><strong>Tipo:</strong> ${mov.movement_type}</div>`;
    html += `<div class="mb-2"><strong>Activo:</strong> ${mov.asset_id}</div>`;
    html += `<div class="mb-2"><strong>Cantidad:</strong> ${mov.quantity}</div>`;
    html += `<div class="mb-2"><strong>Valor unitario:</strong> ${mov.unit_value || ''}</div>`;
    html += `<div class="mb-2"><strong>Origen:</strong> ${mov.origin_location || ''}</div>`;
    html += `<div class="mb-2"><strong>Destino:</strong> ${mov.destination_location || ''}</div>`;
    html += `<div class="mb-2"><strong>Usuario:</strong> ${mov.user || ''}</div>`;
    html += `<div class="mb-2"><strong>Motivo:</strong> ${mov.reason || ''}</div>`;
    html += `<div class="mb-2"><strong>Notas:</strong> ${mov.notes || ''}</div>`;
    html += `<div class="mb-2"><strong>Fecha:</strong> ${new Date(mov.date).toLocaleString()}</div>`;
    if (mov.document) {
        html += `<div class="mb-2"><strong>Documento:</strong> <a href="${mov.document}" target="_blank">Ver documento</a></div>`;
    }
    document.getElementById('movementDetailBody').innerHTML = html;
    document.getElementById('movementDetailModal').classList.add('show');
    document.getElementById('movementDetailModal').style.display = 'block';
}

function closeMovementDetailModal() {
    document.getElementById('movementDetailModal').classList.remove('show');
    document.getElementById('movementDetailModal').style.display = 'none';
}

// Inicialización
window.addEventListener('DOMContentLoaded', async () => {
    await loadContentTypeIds();
    renderAssetTypeOptions();
    loadMovements();
    document.getElementById('btnNewMovement').addEventListener('click', openNewMovementModal);
    document.getElementById('movementAssetType').addEventListener('change', function() {
        loadAssetsForType(this.value);
    });
});

// Exponer funciones globales
window.closeMovementModal = closeMovementModal;
window.closeMovementDetailModal = closeMovementDetailModal;
window.editMovement = editMovement;
window.deleteMovement = deleteMovement;
window.viewMovement = viewMovement;
