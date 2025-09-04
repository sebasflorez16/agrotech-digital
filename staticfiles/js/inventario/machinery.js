// machinery.js - CRUD para maquinaria
const API_URL = `http://${window.location.hostname}:8000/api/inventario/machinery/`;
const token = localStorage.getItem("accessToken");

// Cargar maquinaria y renderizar tabla
async function loadMachinery() {
    try {
        const resp = await fetch(API_URL, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        if (!resp.ok) throw new Error('Error loading machinery');
        const machinery = await resp.json();
        const tbody = document.getElementById('machineryTable').querySelector('tbody');
        tbody.innerHTML = '';
        machinery.forEach(m => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${m.name}</td>
                <td>${m.brand || ''}</td>
                <td>${m.model || ''}</td>
                <td>${m.serial_number || ''}</td>
                <td>${m.year || ''}</td>
                <td>${m.warehouse && m.warehouse.name ? m.warehouse.name : '-'}</td>
                <td>${m.category_name || '-'}</td>
                <td>${m.subcategory_name || '-'}</td>
                <td>${m.description || '-'}</td>
                <td>${m.image_url ? `<img src='${m.image_url}' alt='Image' style='max-width:60px;max-height:40px;border-radius:6px;'>` : ''}</td>
                <td class="text-center">
                    <button class="btn btn-sm btn-outline-info me-1" data-action="view" data-id="${m.id}" title="Ver ficha"><i class="fa fa-eye"></i></button>
                    <button class="btn btn-sm btn-outline-primary me-1" data-action="edit" data-id="${m.id}" title="Edit"><i class="fa fa-edit"></i></button>
                    <button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="${m.id}" title="Delete"><i class="fa fa-trash"></i></button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        alert('Error loading machinery');
    }
}

// Guardar maquinaria (crear o editar)
document.getElementById('machineryForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const id = document.getElementById('machineryId').value || null;
    const formData = new FormData();
    formData.append('name', document.getElementById('machineryName').value);
    formData.append('brand', document.getElementById('machineryBrand').value);
    formData.append('model', document.getElementById('machineryModel').value);
    formData.append('serial_number', document.getElementById('machinerySerial').value);
    formData.append('year', document.getElementById('machineryYear').value);
    formData.append('warehouse_id', document.getElementById('machineryWarehouse').value);
    formData.append('category', document.getElementById('machineryCategory').value);
    formData.append('subcategory', document.getElementById('machinerySubcategory').value);
    formData.append('status', document.getElementById('machineryStatus').value);
    formData.append('acquisition_date', document.getElementById('machineryAcquisitionDate').value);
    formData.append('purchase_value', document.getElementById('machineryPurchaseValue').value);
    formData.append('current_value', document.getElementById('machineryCurrentValue').value);
    formData.append('supplier', document.getElementById('machinerySupplier').value);
    formData.append('location', document.getElementById('machineryLocation').value);
    formData.append('usage_hours', document.getElementById('machineryUsageHours').value);
    formData.append('last_maintenance', document.getElementById('machineryLastMaintenance').value);
    formData.append('next_maintenance', document.getElementById('machineryNextMaintenance').value);
    formData.append('responsible', document.getElementById('machineryResponsible').value);
    formData.append('description', document.getElementById('machineryDescription').value);
    formData.append('notes', document.getElementById('machineryNotes').value);
    const imageInput = document.getElementById('machineryImage');
    if (imageInput.files[0]) {
        formData.append('image', imageInput.files[0]);
    }
    await saveMachinery(formData, id);
    // Cerrar modal
    const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('machineryModal'));
    modal.hide();
    this.reset();
    document.getElementById('machineryId').value = '';
    document.getElementById('modalTitleMachinery').textContent = 'New Machinery';
});

async function saveMachinery(data, id=null) {
    try {
        const url = id ? `${API_URL}${id}/` : API_URL;
        const method = id ? 'PUT' : 'POST';
        const resp = await fetch(url, {
            method,
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: data
        });
        if (!resp.ok) throw new Error('Error saving machinery');
        await loadMachinery();
    } catch (error) {
        alert('Error saving machinery');
    }
}

// Eliminar maquinaria
async function deleteMachinery(id) {
    if (!confirm('Are you sure you want to delete this machinery?')) return;
    try {
        const resp = await fetch(`${API_URL}${id}/`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        if (!resp.ok) throw new Error('Error deleting machinery');
        await loadMachinery();
    } catch (error) {
        alert('Error deleting machinery');
    }
}

// Delegación de eventos para acciones en la tabla de maquinaria
if (document.getElementById('machineryTable')) {
    document.getElementById('machineryTable').addEventListener('click', async function(e) {
        const btn = e.target.closest('button[data-action]');
        if (!btn) return;
        const id = btn.getAttribute('data-id');
        const action = btn.getAttribute('data-action');
        if (action === 'edit') {
            await editMachinery(id);
        } else if (action === 'delete') {
            await deleteMachinery(id);
        } else if (action === 'view') {
            await viewMachineryDetail(id);
        }
    });
}

// Editar maquinaria: cargar datos en el modal
async function editMachinery(id) {
    try {
        const resp = await fetch(`${API_URL}${id}/`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        if (!resp.ok) throw new Error('Could not load machinery');
        const m = await resp.json();
        await loadMachineryFormSelects(m.warehouse ? m.warehouse.id : '', m.category || '', m.subcategory || '', m.supplier || '');
        document.getElementById('machineryId').value = m.id;
        document.getElementById('machineryName').value = m.name;
        document.getElementById('machineryBrand').value = m.brand || '';
        document.getElementById('machineryModel').value = m.model || '';
        document.getElementById('machinerySerial').value = m.serial_number || '';
        document.getElementById('machineryYear').value = m.year || '';
        document.getElementById('machineryWarehouse').value = m.warehouse ? m.warehouse.id : '';
        document.getElementById('machineryCategory').value = m.category || '';
        document.getElementById('machinerySubcategory').value = m.subcategory || '';
        document.getElementById('machineryStatus').value = m.status || 'nuevo';
        document.getElementById('machineryAcquisitionDate').value = m.acquisition_date || '';
        document.getElementById('machineryPurchaseValue').value = m.purchase_value || '';
        document.getElementById('machineryCurrentValue').value = m.current_value || '';
        document.getElementById('machinerySupplier').value = m.supplier || '';
        document.getElementById('machineryLocation').value = m.location || '';
        document.getElementById('machineryUsageHours').value = m.usage_hours || '';
        document.getElementById('machineryLastMaintenance').value = m.last_maintenance || '';
        document.getElementById('machineryNextMaintenance').value = m.next_maintenance || '';
        document.getElementById('machineryResponsible').value = m.responsible || '';
        document.getElementById('machineryDescription').value = m.description || '';
        document.getElementById('machineryNotes').value = m.notes || '';
        document.getElementById('machineryImagePreview').src = m.image_url || '';
        document.getElementById('modalTitleMachinery').textContent = 'Edit Machinery';
        const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('machineryModal'));
        modal.show();
    } catch (error) {
        alert('Could not load machinery');
    }
}

// --- CARGA DE SELECTS PARA FORMULARIO DE MAQUINARIA ---
async function loadMachineryFormSelects(selectedWarehouse = '', selectedCategory = '', selectedSubcategory = '') {
    // Warehouses
    const warehouseSelect = document.getElementById('machineryWarehouse');
    warehouseSelect.innerHTML = '<option value="">Selecciona almacén</option>';
    try {
        const resp = await fetch(`http://${window.location.hostname}:8000/api/inventario/warehouses/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await resp.json();
        data.forEach(w => {
            warehouseSelect.innerHTML += `<option value="${w.id}"${selectedWarehouse == w.id ? ' selected' : ''}>${w.name}</option>`;
        });
    } catch (e) { warehouseSelect.innerHTML += '<option value="">Error cargando</option>'; }
    // Categories
    const categorySelect = document.getElementById('machineryCategory');
    categorySelect.innerHTML = '<option value="">Selecciona categoría</option>';
    try {
        const resp = await fetch(`http://${window.location.hostname}:8000/api/inventario/categories/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await resp.json();
        data.forEach(c => {
            categorySelect.innerHTML += `<option value="${c.id}"${selectedCategory == c.id ? ' selected' : ''}>${c.name}</option>`;
        });
    } catch (e) { categorySelect.innerHTML += '<option value="">Error cargando</option>'; }
    // Subcategories
    const subcategorySelect = document.getElementById('machinerySubcategory');
    subcategorySelect.innerHTML = '<option value="">Selecciona subcategoría</option>';
    try {
        const resp = await fetch(`http://${window.location.hostname}:8000/api/inventario/subcategories/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await resp.json();
        data.forEach(s => {
            subcategorySelect.innerHTML += `<option value="${s.id}"${selectedSubcategory == s.id ? ' selected' : ''}>${s.name}</option>`;
        });
    } catch (e) { subcategorySelect.innerHTML += '<option value="">Error cargando</option>'; }
    // Suppliers
    const supplierSelect = document.getElementById('machinerySupplier');
    supplierSelect.innerHTML = '<option value="">Selecciona proveedor</option>';
    try {
        const resp = await fetch(`http://${window.location.hostname}:8000/api/inventario/suppliers/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await resp.json();
        data.forEach(sup => {
            supplierSelect.innerHTML += `<option value="${sup.id}"${arguments[3] == sup.id ? ' selected' : ''}>${sup.name}</option>`;
        });
    } catch (e) { supplierSelect.innerHTML += '<option value="">Error cargando</option>'; }
}

// Cargar selects al abrir modal de maquinaria
if (document.getElementById('btnNewMachinery')) {
    document.getElementById('btnNewMachinery').addEventListener('click', function() {
        loadMachineryFormSelects();
        document.getElementById('machineryForm').reset();
        document.getElementById('machineryId').value = '';
        document.getElementById('modalTitleMachinery').textContent = 'New Machinery';
        document.getElementById('machineryImagePreview').src = '';
    });
}

// Inicialización automática
if (document.getElementById('machineryTable')) {
    loadMachinery();
}

document.getElementById('btnNewMachinery').addEventListener('click', function() {
    document.getElementById('machineryForm').reset();
    document.getElementById('machineryId').value = '';
    document.getElementById('modalTitleMachinery').textContent = 'New Machinery';
});

document.getElementById('machineryImage').addEventListener('change', function(e) {
    const file = e.target.files[0];
    const preview = document.getElementById('machineryImagePreview');
    if (file) {
        const reader = new FileReader();
        reader.onload = function(ev) {
            preview.src = ev.target.result;
        };
        reader.readAsDataURL(file);
    } else {
        preview.src = '';
    }
});

// --- FICHA TÉCNICA PROFESIONAL DE MAQUINARIA ---
async function viewMachineryDetail(id) {
    try {
        const resp = await fetch(`${API_URL}${id}/`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (!resp.ok) throw new Error('No se pudo cargar la maquinaria');
        const m = await resp.json();
        let imageUrl = m.image_url && (m.image_url.startsWith('http') || m.image_url.startsWith('/'))
            ? m.image_url
            : (m.image_url ? `/media/${m.image_url}` : "https://placehold.co/240x180?text=Sin+Imagen");
        let html = `<div class='row'>
            <div class='col-md-5 text-center'>
                <img src='${imageUrl}' alt='Imagen maquinaria' class='rounded shadow mb-3 bg-light' style='width:220px;height:180px;object-fit:contain;border:4px solid #eee;background:#f8f9fa;display:block;margin:auto;'>
                <h4 class='mt-2 mb-1 fw-bold text-primary'>${m.name}</h4>
                <span class='badge bg-dark mb-2'>${m.category_name || "Sin categoría"}</span>
            </div>
            <div class='col-md-7'>
                <table class='table table-sm table-borderless mb-0'>
                    <tbody>
                        <tr><th>Marca</th><td>${m.brand || '-'}</td></tr>
                        <tr><th>Modelo</th><td>${m.model || '-'}</td></tr>
                        <tr><th>Serie</th><td>${m.serial_number || '-'}</td></tr>
                        <tr><th>Año</th><td>${m.year || '-'}</td></tr>
                        <tr><th>Estado</th><td><span class='badge ${m.status === "Operativa" ? "bg-success" : "bg-warning"}'>${m.status || '-'}</span></td></tr>
                        <tr><th>Almacén</th><td>${m.warehouse && m.warehouse.name ? m.warehouse.name : '-'}</td></tr>
                        <tr><th>Ubicación física</th><td>${m.location || '-'}</td></tr>
                        <tr><th>Proveedor</th><td>${m.supplier_name || '-'}</td></tr>
                        <tr><th>Valor compra</th><td>${m.purchase_value ? `$${m.purchase_value}` : '-'}</td></tr>
                        <tr><th>Valor actual</th><td>${m.current_value ? `$${m.current_value}` : '-'}</td></tr>
                        <tr><th>Horas de uso</th><td>${m.usage_hours || '-'}</td></tr>
                        <tr><th>Último mantenimiento</th><td>${m.last_maintenance || '-'}</td></tr>
                        <tr><th>Próximo mantenimiento</th><td>${m.next_maintenance || '-'}</td></tr>
                        <tr><th>Responsable</th><td>${m.responsible || '-'}</td></tr>
                        <tr><th>Descripción</th><td>${m.description || '-'}</td></tr>
                        <tr><th>Observaciones</th><td>${m.notes || '-'}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>`;
        showMachineryDetailModal('Ficha Técnica Maquinaria', html);
    } catch (e) {
        showMachineryDetailModal('Error', 'No se pudo cargar la ficha técnica.');
    }
}

function showMachineryDetailModal(title, html) {
    let modal = document.getElementById('machineryDetailModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'machineryDetailModal';
        modal.className = 'modal fade';
        modal.tabIndex = -1;
        modal.innerHTML = `
        <div class='modal-dialog modal-lg'>
            <div class='modal-content shadow-lg'>
                <div class='modal-header bg-light'>
                    <h5 class='modal-title fw-bold'></h5>
                    <button type='button' class='btn-close' data-bs-dismiss='modal'></button>
                </div>
                <div class='modal-body p-4'></div>
            </div>
        </div>`;
        document.body.appendChild(modal);
    }
    modal.querySelector('.modal-title').innerHTML = title;
    modal.querySelector('.modal-body').innerHTML = html;
    bootstrap.Modal.getOrCreateInstance(modal).show();
}
