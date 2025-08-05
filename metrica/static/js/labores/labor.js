// labor.js - Gestión profesional de labores agrícolas (Ruta Firme)
const API_LABOR = `/api/labores/labores/`;
const API_LABOR_TYPE = `/api/labores/labortype/`;
const API_EMPLOYEE = `/api/RRHH/empleados/`;
const API_PARCEL = `/api/parcels/parcel/`;
const API_LABOR_INPUT = `/api/labores/labor-insumos/`;
const API_LABOR_PHOTO = `/api/labores/labor-fotos/`;
const token = localStorage.getItem("accessToken");

// --- CARGA DE TABLA DE LABORES ---
document.addEventListener('DOMContentLoaded', function() {
    loadLaborTable();
    document.getElementById('btn-new-labor').addEventListener('click', showLaborModal);
    document.getElementById('labor-form').addEventListener('submit', submitLaborForm);
});

async function loadLaborTable() {
    const tbody = document.querySelector('#labor-summary-table tbody');
    tbody.innerHTML = '';
    try {
        const cropId = getCropIdFromContext();
        const resp = await fetch(`${API_LABOR}?cultivo=${cropId}`, { headers: { 'Authorization': `Bearer ${token}` } });
        const data = await resp.json();
        data.forEach(labor => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${labor.tipo ? labor.tipo : '-'}</td>
                <td>${labor.nombre}</td>
                <td>${labor.fecha_programada || ''}</td>
                <td>${labor.estado || ''}</td>
                <td>${(labor.responsables_nombres || []).join(', ')}</td>
                <td>${(labor.parcelas_nombres || []).join(', ')}</td>
                <td>${labor.insumos.length}</td>
                <td>${labor.costo_total != null ? labor.costo_total.toLocaleString('es-CO', { style: 'currency', currency: 'COP' }) : '-'}</td>
                <td>${labor.fotos && labor.fotos.length > 0 ? labor.fotos.map(f => `<img src="${f.image}" alt="foto" class="rounded" style="width:40px;height:40px;object-fit:cover;">`).join('') : '-'}</td>
                <td class="text-center">
                  <button class="btn btn-sm btn-outline-info me-1" title="Ver" onclick="showLaborDetail('${labor.id}')"><i class="fa fa-eye"></i></button>
                  <button class="btn btn-sm btn-outline-warning me-1" title="Editar" onclick="editLabor('${labor.id}')"><i class="fa fa-edit"></i></button>
                  <button class="btn btn-sm btn-outline-danger" title="Eliminar" onclick="deleteLabor('${labor.id}')"><i class="fa fa-trash"></i></button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="10">Error cargando labores</td></tr>';
    }
}

// --- MODAL DE CREACIÓN/EDICIÓN DE LABOR ---
async function showLaborModal() {
    document.getElementById('labor-form').reset();
    clearLaborFormFeedback();
    await Promise.all([
        loadSelectOptions(API_LABOR_TYPE, 'labor-type'),
        loadSelectOptions(API_EMPLOYEE, 'labor-responsables', 'id', 'full_name', true),
        loadSelectOptions(API_PARCEL, 'labor-parcelas', 'id', 'name', true)
    ]);
    bootstrap.Modal.getOrCreateInstance(document.getElementById('laborModal')).show();
}

function clearLaborFormFeedback() {
    const form = document.getElementById('labor-form');
    form.querySelectorAll('.is-invalid, .is-valid').forEach(el => {
        el.classList.remove('is-invalid', 'is-valid');
    });
    const alert = document.getElementById('labor-form-alert');
    if (alert) alert.innerHTML = '';
}

function showLaborFormFeedback(success, message, fieldErrors = {}) {
    const form = document.getElementById('labor-form');
    let alert = document.getElementById('labor-form-alert');
    if (!alert) {
        alert = document.createElement('div');
        alert.id = 'labor-form-alert';
        form.prepend(alert);
    }
    alert.className = `alert ${success ? 'alert-success' : 'alert-danger'} mt-2`;
    alert.innerText = message;
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

async function submitLaborForm(event) {
    event.preventDefault();
    clearLaborFormFeedback();
    const form = event.target;
    const formData = new FormData(form);
    let body = {};
    formData.forEach((v, k) => { body[k] = v; });
    // Manejo de relaciones ManyToMany
    body['responsables'] = Array.from(form['responsables'].selectedOptions).map(opt => opt.value);
    body['parcelas'] = Array.from(form['parcelas'].selectedOptions).map(opt => opt.value);
    // Relacionar con el cultivo actual
    body['cultivos'] = [getCropIdFromContext()];
    try {
        let url = API_LABOR;
        let method = 'POST';
        const editId = form.getAttribute('data-edit-id');
        if (editId) {
            url = `${API_LABOR}${editId}/`;
            method = 'PUT';
        }
        const resp = await fetch(url, {
            method,
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await resp.json();
        if (resp.ok) {
            showLaborFormFeedback(true, editId ? '¡Labor actualizada!' : '¡Labor guardada exitosamente!');
            setTimeout(() => {
                bootstrap.Modal.getOrCreateInstance(document.getElementById('laborModal')).hide();
                loadLaborTable();
            }, 1200);
        } else {
            showLaborFormFeedback(false, 'Error al guardar la labor', data);
        }
        form.removeAttribute('data-edit-id');
        document.getElementById('laborModalLabel').textContent = 'Nueva labor';
    } catch (e) {
        showLaborFormFeedback(false, 'Error de conexión');
    }
}

function getCropIdFromContext() {
    // Implementa según cómo pases el contexto del cultivo (puede ser un hidden input, variable global, etc.)
    return window.currentCropId || document.getElementById('labor-crop-name').getAttribute('data-crop-id');
}

async function loadSelectOptions(url, selectId, valueField = 'id', textField = 'name', multiple = false) {
    const select = document.getElementById(selectId);
    select.innerHTML = multiple ? '' : '<option value="">Selecciona...</option>';
    try {
        const resp = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
        if (!resp.ok) {
            select.innerHTML = '<option value="">Error de conexión o tenant</option>';
            return;
        }
        let data = await resp.json();
        if (data && data.results && Array.isArray(data.results)) {
            data = data.results;
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


// --- DETALLE DE LABOR ---
window.showLaborDetail = async function showLaborDetail(id) {
    try {
        const resp = await fetch(`${API_LABOR}${id}/`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (!resp.ok) throw new Error('No se pudo cargar el detalle');
        const labor = await resp.json();
        const body = document.getElementById('labor-detail-body');
        body.innerHTML = `
        <div class="card border-0 shadow-sm mb-0">
          <div class="row g-0">
            <div class="col-md-4 text-center p-4">
              <div class="fw-bold fs-5 mb-1">${labor.nombre}</div>
              <div class="text-muted mb-1">${labor.tipo || ''}</div>
              <div class="small text-secondary mb-2">${labor.fecha_programada || ''}</div>
              <span class="badge bg-primary">${labor.estado || '-'}</span>
              <div class="mt-3">
                ${(labor.fotos || []).map(f => `<img src="${f.image}" alt="foto" class="img-fluid rounded shadow mb-2" style="max-height:100px;">`).join('') || '<div class="bg-light border rounded p-2 mb-2">Sin fotos</div>'}
              </div>
            </div>
            <div class="col-md-8 p-4">
              <div class="row mb-2">
                <div class="col-6 mb-2"><strong>Responsables:</strong> ${(labor.responsables_nombres || []).join(', ')}</div>
                <div class="col-6 mb-2"><strong>Parcelas:</strong> ${(labor.parcelas_nombres || []).join(', ')}</div>
                <div class="col-6 mb-2"><strong>Insumos:</strong> ${labor.insumos.length}</div>
                <div class="col-6 mb-2"><strong>Costo total:</strong> ${labor.costo_total != null ? labor.costo_total.toLocaleString('es-CO', { style: 'currency', currency: 'COP' }) : '-'}</div>
              </div>
              <div class="mb-2"><strong>Descripción:</strong><br><span class="text-secondary">${labor.descripcion || '-'}</span></div>
              <div class="mb-2"><strong>Observaciones:</strong><br><span class="text-secondary">${labor.observaciones || '-'}</span></div>
            </div>
          </div>
        </div>
        <div class="mt-3">
          <h6>Insumos aplicados</h6>
          <ul class="list-group">
            ${(labor.insumos || []).map(i => `<li class="list-group-item d-flex justify-content-between align-items-center">
              ${i.supply || '-'} <span class="badge bg-secondary">${i.quantity} ${i.unit}</span>
            </li>`).join('') || '<li class="list-group-item">Sin insumos</li>'}
          </ul>
        </div>
        `;
        bootstrap.Modal.getOrCreateInstance(document.getElementById('laborDetailModal')).show();
    } catch (e) {
        alert('No se pudo cargar el detalle de la labor');
    }
}

// --- ELIMINAR LABOR ---
window.deleteLabor = async function deleteLabor(id) {
    if (!confirm('¿Seguro que deseas eliminar esta labor?')) return;
    try {
        const resp = await fetch(`${API_LABOR}${id}/`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) throw new Error('No se pudo eliminar');
        loadLaborTable();
        showToast('Labor eliminada', 'success');
    } catch (e) {
        showToast('Error al eliminar la labor', 'danger');
    }
}

// --- EDITAR LABOR (precarga en modal) ---
window.editLabor = async function editLabor(id) {
    try {
        const resp = await fetch(`${API_LABOR}${id}/`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (!resp.ok) throw new Error('No se pudo cargar la labor');
        const labor = await resp.json();
        await showLaborModal();
        // Precargar datos en el formulario
        const form = document.getElementById('labor-form');
        form['nombre'].value = labor.nombre || '';
        form['tipo'].value = labor.tipo || '';
        form['fecha_programada'].value = labor.fecha_programada || '';
        form['estado'].value = labor.estado || '';
        form['descripcion'].value = labor.descripcion || '';
        form['observaciones'].value = labor.observaciones || '';
        // Precargar responsables y parcelas
        Array.from(form['responsables'].options).forEach(opt => { opt.selected = (labor.responsables || []).includes(parseInt(opt.value)); });
        Array.from(form['parcelas'].options).forEach(opt => { opt.selected = (labor.parcelas || []).includes(parseInt(opt.value)); });
        form.setAttribute('data-edit-id', labor.id);
        document.getElementById('laborModalLabel').textContent = 'Editar Labor';
    } catch (e) {
        showToast('No se pudo cargar la labor para editar', 'danger');
    }
}

// --- TOAST VISUAL ---
function showToast(msg, type = 'info') {
    const toast = document.getElementById('main-toast');
    if (!toast) return;
    toast.textContent = msg;
    toast.className = `toast align-items-center text-bg-${type} show`;
    setTimeout(() => toast.classList.remove('show'), 3000);
}
