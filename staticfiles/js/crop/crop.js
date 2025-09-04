// crop.js - Gestión profesional de cultivos
const API_BASE = `http://${window.location.hostname}:8000/api/crop/`;
const API_TYPE = `${API_BASE}types/`;
const API_CROP = `${API_BASE}crops/`;
const API_PARCEL = `http://${window.location.hostname}:8000/api/parcels/parcel/`;
const API_EMPLOYEE = `http://${window.location.hostname}:8000/api/RRHH/empleados/`;
const API_VARIETY = `http://${window.location.hostname}:8000/api/inventario/supplies/`;
const API_SUPPLIER = `http://${window.location.hostname}:8000/api/inventario/suppliers/`;
const token = localStorage.getItem("accessToken");

// --- CARGA DE TABLA DE CULTIVOS ---
document.addEventListener('DOMContentLoaded', function() {
    loadCropTable();
    document.getElementById('btn-new-crop').addEventListener('click', showCropModal);
    document.getElementById('crop-form').addEventListener('submit', submitCropForm);
});

async function loadCropTable() {
    const tbody = document.querySelector('#crop-summary-table tbody');
    tbody.innerHTML = '';
    try {
        const resp = await fetch(API_CROP, { headers: { 'Authorization': `Bearer ${token}` } });
        const data = await resp.json();
        data.forEach(crop => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${crop.name}</td>
                <td>${crop.crop_type_name || ''}</td>
                <td>${crop.variety_name || ''}</td>
                <td>${crop.parcel_name || ''}</td>
                <td>${crop.area || ''}</td>
                <td>${crop.sowing_date || ''}</td>
                <td>${crop.harvest_date || ''}</td>
                <td>${crop.manager_name || ''}</td>
                <td class="text-center">
                  <button class="btn btn-sm btn-outline-info me-1" title="Ver" onclick="showCropDetail('${crop.id}')"><i class="fa fa-eye"></i></button>
                  <button class="btn btn-sm btn-outline-warning me-1" title="Editar" onclick="editCrop('${crop.id}')"><i class="fa fa-edit"></i></button>
                  <button class="btn btn-sm btn-outline-danger" title="Eliminar" onclick="deleteCrop('${crop.id}')"><i class="fa fa-trash"></i></button>
                </td>
            `;
            tbody.appendChild(row);
        });
// --- DETALLE DE CULTIVO ---
window.showCropDetail = async function showCropDetail(id) {
    try {
        const resp = await fetch(`${API_CROP}${id}/`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (!resp.ok) throw new Error('No se pudo cargar el detalle');
        const crop = await resp.json();
        const body = document.getElementById('crop-detail-body');
        body.innerHTML = `
        <div class="card border-0 shadow-sm mb-0">
          <div class="row g-0">
            <div class="col-md-4 text-center p-4">
              ${crop.image ? `<img src="${crop.image}" alt="Imagen cultivo" class="img-fluid rounded shadow mb-3" style="max-height:180px;">` : '<div class="bg-light border rounded p-4 mb-3">Sin imagen</div>'}
              <div class="fw-bold fs-5 mb-1">${crop.name}</div>
              <div class="text-muted mb-1">${crop.crop_type_name || ''}</div>
              <div class="small text-secondary mb-2">${crop.variety_name || ''}</div>
              <span class="badge bg-primary">${crop.parcel_name || '-'}</span>
            </div>
            <div class="col-md-8 p-4">
              <div class="row mb-2">
                <div class="col-6 mb-2"><strong>Área (ha):</strong> ${crop.area || '-'}</div>
                <div class="col-6 mb-2"><strong>Responsable:</strong> ${crop.manager_name || '-'}</div>
                <div class="col-6 mb-2"><strong>Proveedor semilla:</strong> ${crop.seed_supplier_name || '-'}</div>
                <div class="col-6 mb-2"><strong>Tipo de riego:</strong> ${crop.irrigation_type || '-'}</div>
                <div class="col-6 mb-2"><strong>Siembra:</strong> ${crop.sowing_date || '-'}</div>
                <div class="col-6 mb-2"><strong>Cosecha:</strong> ${crop.harvest_date || '-'}</div>
                <div class="col-6 mb-2"><strong>Rend. esperado:</strong> ${crop.expected_yield || '-'}</div>
                <div class="col-6 mb-2"><strong>Rend. real:</strong> ${crop.actual_yield || '-'}</div>
              </div>
              <div class="mb-2"><strong>Notas:</strong><br><span class="text-secondary">${crop.notes || '-'}</span></div>
            </div>
          </div>
        </div>
        `;
        bootstrap.Modal.getOrCreateInstance(document.getElementById('cropDetailModal')).show();
    } catch (e) {
        alert('No se pudo cargar el detalle del cultivo');
    }
}

// --- ELIMINAR CULTIVO ---
window.deleteCrop = async function deleteCrop(id) {
    if (!confirm('¿Seguro que deseas eliminar este cultivo?')) return;
    try {
        const resp = await fetch(`${API_CROP}${id}/`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) throw new Error('No se pudo eliminar');
        loadCropTable();
        showToast('Cultivo eliminado', 'success');
    } catch (e) {
        showToast('Error al eliminar el cultivo', 'danger');
    }
}

// --- EDITAR CULTIVO (precarga en modal) ---
window.editCrop = async function editCrop(id) {
    try {
        const resp = await fetch(`${API_CROP}${id}/`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (!resp.ok) throw new Error('No se pudo cargar el cultivo');
        const crop = await resp.json();
        await showCropModal();
        // Precargar datos en el formulario
        const form = document.getElementById('crop-form');
        form['name'].value = crop.name || '';
        form['crop_type'].value = crop.crop_type || '';
        form['variety'].value = crop.variety || '';
        form['parcel'].value = crop.parcel || '';
        form['area'].value = crop.area || '';
        form['sowing_date'].value = crop.sowing_date || '';
        form['harvest_date'].value = crop.harvest_date || '';
        form['expected_yield'].value = crop.expected_yield || '';
        form['actual_yield'].value = crop.actual_yield || '';
        form['irrigation_type'].value = crop.irrigation_type || '';
        form['seed_supplier'].value = crop.seed_supplier || '';
        form['notes'].value = crop.notes || '';
        // Imagen: no se precarga por seguridad
        form.setAttribute('data-edit-id', crop.id);
        document.getElementById('cropModalLabel').textContent = 'Editar Cultivo';
    } catch (e) {
        showToast('No se pudo cargar el cultivo para editar', 'danger');
    }
}
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="8">Error cargando cultivos</td></tr>';
    }
}

// --- CARGA DE SELECTS EN MODAL ---
async function showCropModal() {
    document.getElementById('crop-form').reset();
    clearCropFormFeedback();
    await Promise.all([
        loadSelectOptions(API_TYPE, 'crop-type'),
        loadSelectOptions(API_VARIETY, 'crop-variety'),
        loadSelectOptions(API_PARCEL, 'crop-parcel'),
        loadSelectOptions(API_EMPLOYEE, 'crop-manager', 'id', 'full_name'),
        loadSelectOptions(API_SUPPLIER, 'crop-seed-supplier', 'id', 'name')
    ]);
    bootstrap.Modal.getOrCreateInstance(document.getElementById('cropModal')).show();
}

// Limpia feedback visual de errores/éxito en el formulario
function clearCropFormFeedback() {
    const form = document.getElementById('crop-form');
    form.querySelectorAll('.is-invalid, .is-valid').forEach(el => {
        el.classList.remove('is-invalid', 'is-valid');
    });
    const alert = document.getElementById('crop-form-alert');
    if (alert) alert.remove();
}

// Muestra feedback visual en el formulario
function showCropFormFeedback(success, message, fieldErrors = {}) {
    const form = document.getElementById('crop-form');
    // Mensaje general
    let alert = document.getElementById('crop-form-alert');
    if (!alert) {
        alert = document.createElement('div');
        alert.id = 'crop-form-alert';
        form.prepend(alert);
    }
    alert.className = `alert ${success ? 'alert-success' : 'alert-danger'} mt-2`;
    alert.innerText = message;
    // Campos con error
    form.querySelectorAll('.is-invalid, .is-valid').forEach(el => {
        el.classList.remove('is-invalid', 'is-valid');
    });
    Object.entries(fieldErrors).forEach(([field, msg]) => {
        const input = form.querySelector(`[name="${field}"]`);
        if (input) {
            input.classList.add('is-invalid');
            let feedback = input.nextElementSibling;
            if (!feedback || !feedback.classList.contains('invalid-feedback')) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                input.parentNode.insertBefore(feedback, input.nextSibling);
            }
            feedback.innerText = Array.isArray(msg) ? msg.join(', ') : msg;
        }
    });
}
// --- ENVÍO DEL FORMULARIO DE CULTIVO POR POST ---
async function submitCropForm(event) {
    event.preventDefault();
    clearCropFormFeedback();
    const form = event.target;
    const formData = new FormData(form);
    // Si hay campo de imagen, incluirlo
    let body;
    let headers = { 'Authorization': `Bearer ${token}` };
    if (form.querySelector('input[type="file"]')) {
        body = formData;
    } else {
        // Convierte a JSON
        body = {};
        formData.forEach((v, k) => { body[k] = v; });
        headers['Content-Type'] = 'application/json';
        body = JSON.stringify(body);
    }
    try {
        let url = API_CROP;
        let method = 'POST';
        const editId = form.getAttribute('data-edit-id');
        if (editId) {
            url = `${API_CROP}${editId}/`;
            method = 'PUT';
        }
        const resp = await fetch(url, {
            method,
            headers,
            body
        });
        const data = await resp.json();
        if (resp.ok) {
            showCropFormFeedback(true, editId ? '¡Cultivo actualizado!' : '¡Cultivo guardado exitosamente!');
            setTimeout(() => {
                bootstrap.Modal.getOrCreateInstance(document.getElementById('cropModal')).hide();
                loadCropTable();
            }, 1200);
        } else {
            // Errores de validación
            showCropFormFeedback(false, 'Error al guardar el cultivo', data);
        }
        form.removeAttribute('data-edit-id');
        document.getElementById('cropModalLabel').textContent = 'Nuevo Cultivo';
    } catch (e) {
        showCropFormFeedback(false, 'Error de conexión');
    }
}

// --- TOAST VISUAL ---
function showToast(msg, type = 'info') {
    // Requiere un div con id="main-toast" en el template
    const toast = document.getElementById('main-toast');
    if (!toast) return;
    toast.textContent = msg;
    toast.className = `toast align-items-center text-bg-${type} show`;
    setTimeout(() => toast.classList.remove('show'), 3000);
}

async function loadSelectOptions(url, selectId, valueField = 'id', textField = 'name') {
    const select = document.getElementById(selectId);
    select.innerHTML = '<option value="">Selecciona...</option>';
    try {
        const resp = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
        if (!resp.ok) {
            select.innerHTML = '<option value="">Error de conexión o tenant</option>';
            return;
        }
        let data = await resp.json();
        console.log('Cargando select:', selectId, 'URL:', url, 'Respuesta:', data);
        // Soporta respuesta paginada (DRF), array directo o respuesta con clave 'parcels'
        if (data && data.results && Array.isArray(data.results)) {
            data = data.results;
        } else if (data && data.parcels && Array.isArray(data.parcels)) {
            data = data.parcels;
        }
        if (!Array.isArray(data) || data.length === 0) {
            select.innerHTML = '<option value="">No hay datos disponibles</option>';
            return;
        }
        data.forEach(item => {
            select.innerHTML += `<option value="${item[valueField]}">${item[textField]}</option>`;
        });
    } catch (e) {
        select.innerHTML = '<option value="">Error</option>';
    }
}
