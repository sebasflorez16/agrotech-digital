// directory.js - CRUD visual para Empresas, Proveedores y Personas

// Endpoints API
const API_COMPANY = `http://${window.location.hostname}:8000/api/inventario/companies/`;
const API_SUPPLIER = `http://${window.location.hostname}:8000/api/inventario/suppliers/`;
const API_PERSON = `http://${window.location.hostname}:8000/api/inventario/persons/`;
const API_MACHINERY = `http://${window.location.hostname}:8000/api/inventario/machinery/`;
const token = localStorage.getItem("accessToken");

// --- CARGA DE TABLAS ---
document.addEventListener('DOMContentLoaded', function() {
    loadCompanyTable();
    loadSupplierTable();
    loadPersonTable();
    loadMachineryTable();
    // Listeners para botones de nuevo
    document.getElementById('btnNewCompany').addEventListener('click', showCompanyModal);
    document.getElementById('btnNewSupplier').addEventListener('click', showSupplierModal);
    document.getElementById('btnNewPerson').addEventListener('click', showPersonModal);
});

// --- FUNCIONES DE CARGA DE TABLAS ---
async function loadCompanyTable() {
    const tbody = document.querySelector('#companyTable tbody');
    tbody.innerHTML = '';
    try {
        const resp = await fetch(API_COMPANY, { headers: { 'Authorization': `Bearer ${token}` } });
        const data = await resp.json();
        data.forEach(c => {
            tbody.innerHTML += `<tr>
                <td>${c.name}</td>
                <td>${c.rut || ''}</td>
                <td>${c.address || ''}</td>
                <td>${c.phone || ''}</td>
                <td>${c.email || ''}</td>
                <td>
                    <button class='btn btn-sm btn-info' onclick='viewCompany(${c.id})'><i class='fa fa-eye'></i></button>
                    <button class='btn btn-sm btn-warning' onclick='editCompany(${c.id})'><i class='fa fa-edit'></i></button>
                    <button class='btn btn-sm btn-danger' onclick='deleteCompany(${c.id})'><i class='fa fa-trash'></i></button>
                </td>
            </tr>`;
        });
    } catch (e) { tbody.innerHTML = '<tr><td colspan="6">Error cargando empresas</td></tr>'; }
}

async function loadSupplierTable() {
    const tbody = document.querySelector('#supplierTable tbody');
    tbody.innerHTML = '';
    try {
        const resp = await fetch(API_SUPPLIER, { headers: { 'Authorization': `Bearer ${token}` } });
        const data = await resp.json();
        data.forEach(s => {
            tbody.innerHTML += `<tr>
                <td>${s.name}</td>
                <td>${s.contact || ''}</td>
                <td>${s.phone || ''}</td>
                <td>${s.email || ''}</td>
                <td>${s.company_name || ''}</td>
                <td>
                    <button class='btn btn-sm btn-info' onclick='viewSupplier(${s.id})'><i class='fa fa-eye'></i></button>
                    <button class='btn btn-sm btn-warning' onclick='editSupplier(${s.id})'><i class='fa fa-edit'></i></button>
                    <button class='btn btn-sm btn-danger' onclick='deleteSupplier(${s.id})'><i class='fa fa-trash'></i></button>
                </td>
            </tr>`;
        });
    } catch (e) { tbody.innerHTML = '<tr><td colspan="6">Error cargando proveedores</td></tr>'; }
}

async function loadPersonTable() {
    const tbody = document.querySelector('#personTable tbody');
    tbody.innerHTML = '';
    try {
        const resp = await fetch(API_PERSON, { headers: { 'Authorization': `Bearer ${token}` } });
        const data = await resp.json();
        data.forEach(p => {
            tbody.innerHTML += `<tr>
                <td>${p.name}</td>
                <td>${p.phone || ''}</td>
                <td>${p.email || ''}</td>
                <td>${p.notes || ''}</td>
                <td>
                    <button class='btn btn-sm btn-info' onclick='viewPerson(${p.id})'><i class='fa fa-eye'></i></button>
                    <button class='btn btn-sm btn-warning' onclick='editPerson(${p.id})'><i class='fa fa-edit'></i></button>
                    <button class='btn btn-sm btn-danger' onclick='deletePerson(${p.id})'><i class='fa fa-trash'></i></button>
                </td>
            </tr>`;
        });
    } catch (e) { tbody.innerHTML = '<tr><td colspan="5">Error cargando personas</td></tr>'; }
}

async function loadMachineryTable() {
    const tbody = document.querySelector('#machineryTable tbody');
    tbody.innerHTML = '';
    try {
        const resp = await fetch(API_MACHINERY, { headers: { 'Authorization': `Bearer ${token}` } });
        const data = await resp.json();
        data.forEach(m => {
            tbody.innerHTML += `<tr>
                <td>${m.name}</td>
                <td>${m.brand || ''}</td>
                <td>${m.model || ''}</td>
                <td>${m.status || ''}</td>
                <td>${m.location || ''}</td>
                <td>
                    <button class='btn btn-sm btn-info' onclick='viewMachinery(${m.id})'><i class='fa fa-eye'></i></button>
                    <button class='btn btn-sm btn-warning' onclick='editMachinery(${m.id})'><i class='fa fa-edit'></i></button>
                    <button class='btn btn-sm btn-danger' onclick='deleteMachinery(${m.id})'><i class='fa fa-trash'></i></button>
                </td>
            </tr>`;
        });
    } catch (e) { tbody.innerHTML = '<tr><td colspan="6">Error cargando maquinaria</td></tr>'; }
}

// --- FUNCIONES PARA MODALES (placeholder, se implementan en el siguiente paso) ---
// --- MODALES PROFESIONALES ---
function showCompanyModal() {
    const modal = document.getElementById('companyModal');
    if (!modal) return;
    document.getElementById('companyForm').reset();
    document.getElementById('companyImagePreview').src = '';
    document.getElementById('companyImagePreview').style.display = 'none';
    document.getElementById('companyId').value = '';
    modal.querySelector('.modal-title').innerHTML = `<i class='fa fa-building me-2'></i> Nueva Empresa`;
    bootstrap.Modal.getOrCreateInstance(modal).show();
}

function showSupplierModal() {
    const modal = document.getElementById('supplierModal');
    if (!modal) return;
    document.getElementById('supplierForm').reset();
    document.getElementById('supplierImagePreview').src = '';
    document.getElementById('supplierImagePreview').style.display = 'none';
    document.getElementById('supplierId').value = '';
    modal.querySelector('.modal-title').innerHTML = `<i class='fa fa-truck me-2'></i> Nuevo Proveedor`;
    loadCompanyOptions();
    bootstrap.Modal.getOrCreateInstance(modal).show();
}

function showPersonModal() {
    const modal = document.getElementById('personModal');
    if (!modal) return;
    document.getElementById('personForm').reset();
    document.getElementById('personImagePreview').src = '';
    document.getElementById('personImagePreview').style.display = 'none';
    document.getElementById('personId').value = '';
    modal.querySelector('.modal-title').innerHTML = `<i class='fa fa-user me-2'></i> Nueva Persona`;
    bootstrap.Modal.getOrCreateInstance(modal).show();
}

// --- FICHAS DE DETALLE/CONTACTO ---
// --- FICHAS DE DETALLE/CONTACTO PROFESIONAL UX ---
async function viewCompany(id) {
    try {
        const resp = await fetch(API_COMPANY + id + '/', { headers: { 'Authorization': `Bearer ${token}` } });
        const c = await resp.json();
        let html = `<div class='row'>
            <div class='col-md-4 text-center'>
                <img src='${c.image || "https://via.placeholder.com/160x160?text=Sin+Imagen"}' alt='Imagen empresa' class='rounded shadow mb-2' style='max-width:160px;max-height:160px;'>
                <h5 class='mt-2 mb-0'>${c.name}</h5>
                <span class='badge bg-primary mb-2'>Empresa</span>
            </div>
            <div class='col-md-8'>
                <table class='table table-sm table-borderless mb-0'>
                    <tbody>
                        <tr><th>RUT</th><td>${c.rut || '-'}</td></tr>
                        <tr><th>Dirección</th><td>${c.address || '-'}</td></tr>
                        <tr><th>Teléfono</th><td>${c.phone || '-'}</td></tr>
                        <tr><th>Email</th><td>${c.email || '-'}</td></tr>
                        <tr><th>Sitio web</th><td>${c.website || '-'}</td></tr>
                        <tr><th>Contacto</th><td>${c.contact_person || '-'}<br><small>${c.contact_phone || ''} ${c.contact_email || ''}</small></td></tr>
                        <tr><th>Notas</th><td>${c.notes || '-'}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>`;
        showDetailModal('Ficha Empresa', html);
    } catch (e) { showDetailModal('Error', 'No se pudo cargar la empresa.'); }
}

async function viewSupplier(id) {
    try {
        const resp = await fetch(API_SUPPLIER + id + '/', { headers: { 'Authorization': `Bearer ${token}` } });
        const s = await resp.json();
        let html = `<div class='row'>
            <div class='col-md-4 text-center'>
                <img src='${s.image || "https://via.placeholder.com/160x160?text=Sin+Imagen"}' alt='Imagen proveedor' class='rounded shadow mb-2' style='max-width:160px;max-height:160px;'>
                <h5 class='mt-2 mb-0'>${s.name}</h5>
                <span class='badge bg-success mb-2'>Proveedor</span>
            </div>
            <div class='col-md-8'>
                <table class='table table-sm table-borderless mb-0'>
                    <tbody>
                        <tr><th>Contacto</th><td>${s.contact || '-'}</td></tr>
                        <tr><th>Teléfono</th><td>${s.phone || '-'}</td></tr>
                        <tr><th>Email</th><td>${s.email || '-'}</td></tr>
                        <tr><th>Empresa</th><td>${s.company_name || '-'}</td></tr>
                        <tr><th>Dirección</th><td>${s.address || '-'}</td></tr>
                        <tr><th>Sitio web</th><td>${s.website || '-'}</td></tr>
                        <tr><th>NIT/RUT</th><td>${s.tax_id || '-'}</td></tr>
                        <tr><th>Activo</th><td>${s.is_active ? 'Sí' : 'No'}</td></tr>
                        <tr><th>Notas</th><td>${s.notes || '-'}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>`;
        showDetailModal('Ficha Proveedor', html);
    } catch (e) { showDetailModal('Error', 'No se pudo cargar el proveedor.'); }
}

async function viewPerson(id) {
    try {
        const resp = await fetch(API_PERSON + id + '/', { headers: { 'Authorization': `Bearer ${token}` } });
        const p = await resp.json();
        let html = `<div class='row'>
            <div class='col-md-4 text-center'>
                <img src='${p.image || "https://via.placeholder.com/160x160?text=Sin+Imagen"}' alt='Imagen persona' class='rounded shadow mb-2' style='max-width:160px;max-height:160px;'>
                <h5 class='mt-2 mb-0'>${p.name}</h5>
                <span class='badge bg-info mb-2'>Persona</span>
            </div>
            <div class='col-md-8'>
                <table class='table table-sm table-borderless mb-0'>
                    <tbody>
                        <tr><th>Teléfono</th><td>${p.phone || '-'}</td></tr>
                        <tr><th>Email</th><td>${p.email || '-'}</td></tr>
                        <tr><th>Notas</th><td>${p.notes || '-'}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>`;
        showDetailModal('Ficha Persona', html);
    } catch (e) { showDetailModal('Error', 'No se pudo cargar la persona.'); }
}

async function viewMachinery(id) {
    try {
        const resp = await fetch(API_MACHINERY + id + '/', { headers: { 'Authorization': `Bearer ${token}` } });
        const m = await resp.json();
        let html = `<div class='row'>
            <div class='col-md-4 text-center'>
                <img src='${m.image || "https://via.placeholder.com/180x180?text=Sin+Imagen"}' alt='Imagen maquinaria' class='rounded shadow mb-2' style='max-width:180px;max-height:180px;'>
                <h5 class='mt-2'>${m.name}</h5>
                <span class='badge bg-primary mb-2'>${m.type || "Tipo no definido"}</span>
            </div>
            <div class='col-md-8'>
                <table class='table table-sm table-borderless mb-0'>
                    <tbody>
                        <tr><th>Marca</th><td>${m.brand || '-'}</td></tr>
                        <tr><th>Modelo</th><td>${m.model || '-'}</td></tr>
                        <tr><th>Serie</th><td>${m.serial || '-'}</td></tr>
                        <tr><th>Estado</th><td><span class='badge ${m.status === "Operativa" ? "bg-success" : "bg-warning"}'>${m.status || '-'}</span></td></tr>
                        <tr><th>Ubicación</th><td>${m.location || '-'}</td></tr>
                        <tr><th>Fecha de adquisición</th><td>${m.purchase_date || '-'}</td></tr>
                        <tr><th>Valor</th><td>${m.value ? `$${m.value}` : '-'}</td></tr>
                        <tr><th>Notas técnicas</th><td>${m.notes || '-'}</td></tr>
                        <tr><th>Responsable</th><td>${m.responsible || '-'}</td></tr>
                        <tr><th>Mantenimiento</th><td>${m.maintenance || '-'}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>`;
        showDetailModal('Ficha Técnica Maquinaria/Herramienta', html);
    } catch (e) {
        showDetailModal('Error', 'No se pudo cargar la ficha técnica.');
    }
}

// Modal genérico profesional para mostrar detalles
function showDetailModal(title, html) {
    let modal = document.getElementById('detailModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'detailModal';
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

// --- FUNCIONES CRUD ---
async function editCompany(id) {
    try {
        const resp = await fetch(`${API_COMPANY}${id}/`, { headers: { 'Authorization': `Bearer ${token}` } });
        const c = await resp.json();
        document.getElementById('companyId').value = c.id;
        document.getElementById('companyName').value = c.name || '';
        document.getElementById('companyRut').value = c.rut || '';
        document.getElementById('companyAddress').value = c.address || '';
        document.getElementById('companyPhone').value = c.phone || '';
        document.getElementById('companyEmail').value = c.email || '';
        document.getElementById('companyWebsite').value = c.website || '';
        document.getElementById('companyContactPerson').value = c.contact_person || '';
        document.getElementById('companyContactPhone').value = c.contact_phone || '';
        document.getElementById('companyContactEmail').value = c.contact_email || '';
        document.getElementById('companyNotes').value = c.notes || '';
        if (c.image) {
            document.getElementById('companyImagePreview').src = c.image;
            document.getElementById('companyImagePreview').style.display = 'block';
        } else {
            document.getElementById('companyImagePreview').style.display = 'none';
        }
        bootstrap.Modal.getOrCreateInstance(document.getElementById('companyModal')).show();
    } catch (e) { alert('Error cargando empresa'); }
}

async function deleteCompany(id) {
    if (!confirm('¿Seguro que deseas eliminar esta empresa?')) return;
    try {
        const resp = await fetch(`${API_COMPANY}${id}/`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (resp.ok) loadCompanyTable();
        else alert('Error eliminando empresa');
    } catch (e) { alert('Error de red al eliminar empresa'); }
}

async function editSupplier(id) {
    try {
        const resp = await fetch(`${API_SUPPLIER}${id}/`, { headers: { 'Authorization': `Bearer ${token}` } });
        const s = await resp.json();
        document.getElementById('supplierId').value = s.id;
        document.getElementById('supplierName').value = s.name || '';
        document.getElementById('supplierContact').value = s.contact || '';
        document.getElementById('supplierPhone').value = s.phone || '';
        document.getElementById('supplierEmail').value = s.email || '';
        await loadCompanyOptions();
        document.getElementById('supplierCompany').value = s.company || '';
        document.getElementById('supplierAddress').value = s.address || '';
        document.getElementById('supplierWebsite').value = s.website || '';
        document.getElementById('supplierTaxId').value = s.tax_id || '';
        document.getElementById('supplierIsActive').value = s.is_active ? 'true' : 'false';
        document.getElementById('supplierNotes').value = s.notes || '';
        if (s.image) {
            document.getElementById('supplierImagePreview').src = s.image;
            document.getElementById('supplierImagePreview').style.display = 'block';
        } else {
            document.getElementById('supplierImagePreview').style.display = 'none';
        }
        bootstrap.Modal.getOrCreateInstance(document.getElementById('supplierModal')).show();
    } catch (e) { alert('Error cargando proveedor'); }
}

async function deleteSupplier(id) {
    if (!confirm('¿Seguro que deseas eliminar este proveedor?')) return;
    try {
        const resp = await fetch(`${API_SUPPLIER}${id}/`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (resp.ok) loadSupplierTable();
        else alert('Error eliminando proveedor');
    } catch (e) { alert('Error de red al eliminar proveedor'); }
}

async function editPerson(id) {
    try {
        const resp = await fetch(`${API_PERSON}${id}/`, { headers: { 'Authorization': `Bearer ${token}` } });
        const p = await resp.json();
        document.getElementById('personId').value = p.id;
        document.getElementById('personName').value = p.name || '';
        document.getElementById('personPhone').value = p.phone || '';
        document.getElementById('personEmail').value = p.email || '';
        document.getElementById('personNotes').value = p.notes || '';
        if (p.image) {
            document.getElementById('personImagePreview').src = p.image;
            document.getElementById('personImagePreview').style.display = 'block';
        } else {
            document.getElementById('personImagePreview').style.display = 'none';
        }
        bootstrap.Modal.getOrCreateInstance(document.getElementById('personModal')).show();
    } catch (e) { alert('Error cargando persona'); }
}

async function deletePerson(id) {
    if (!confirm('¿Seguro que deseas eliminar esta persona?')) return;
    try {
        const resp = await fetch(`${API_PERSON}${id}/`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (resp.ok) loadPersonTable();
        else alert('Error eliminando persona');
    } catch (e) { alert('Error de red al eliminar persona'); }
}

// --- PREVISUALIZACIÓN DE IMÁGENES EN MODALES ---
function setupImagePreview(inputId, previewId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    if (!input || !preview) return;
    input.addEventListener('change', function() {
        if (input.files && input.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                preview.src = e.target.result;
                preview.style.display = 'block';
            };
            reader.readAsDataURL(input.files[0]);
        } else {
            preview.src = '#';
            preview.style.display = 'none';
        }
    });
}

// --- INICIALIZACIÓN DE MODALES Y PREVIEWS ---
document.addEventListener('DOMContentLoaded', function() {
    // Previews de imagen
    setupImagePreview('companyImage', 'companyImagePreview');
    setupImagePreview('supplierImage', 'supplierImagePreview');
    setupImagePreview('personImage', 'personImagePreview');

    // Listeners para abrir modales
    document.getElementById('btnNewCompany').addEventListener('click', function() {
        document.getElementById('companyForm').reset();
        document.getElementById('companyImagePreview').style.display = 'none';
        document.getElementById('companyId').value = '';
        bootstrap.Modal.getOrCreateInstance(document.getElementById('companyModal')).show();
    });
    document.getElementById('btnNewSupplier').addEventListener('click', async function() {
        document.getElementById('supplierForm').reset();
        document.getElementById('supplierImagePreview').style.display = 'none';
        document.getElementById('supplierId').value = '';
        await loadCompanyOptions();
        bootstrap.Modal.getOrCreateInstance(document.getElementById('supplierModal')).show();
    });
    document.getElementById('btnNewPerson').addEventListener('click', function() {
        document.getElementById('personForm').reset();
        document.getElementById('personImagePreview').style.display = 'none';
        document.getElementById('personId').value = '';
        bootstrap.Modal.getOrCreateInstance(document.getElementById('personModal')).show();
    });

    // Listeners para submit de formularios (asegurado que el DOM ya tiene los formularios)
    document.getElementById('companyForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const id = document.getElementById('companyId').value || null;
        const formData = new FormData(this);
        const ok = await saveCompany(formData, id);
        if (ok) {
            bootstrap.Modal.getOrCreateInstance(document.getElementById('companyModal')).hide();
            this.reset();
            document.getElementById('companyImagePreview').style.display = 'none';
            document.getElementById('companyId').value = '';
        }
    });
    document.getElementById('supplierForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const id = document.getElementById('supplierId').value || null;
        const formData = new FormData(this);
        const ok = await saveSupplier(formData, id);
        if (ok) {
            bootstrap.Modal.getOrCreateInstance(document.getElementById('supplierModal')).hide();
            this.reset();
            document.getElementById('supplierImagePreview').style.display = 'none';
            document.getElementById('supplierId').value = '';
        }
    });
    document.getElementById('personForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const id = document.getElementById('personId').value || null;
        const formData = new FormData(this);
        const ok = await savePerson(formData, id);
        if (ok) {
            bootstrap.Modal.getOrCreateInstance(document.getElementById('personModal')).hide();
            this.reset();
            document.getElementById('personImagePreview').style.display = 'none';
            document.getElementById('personId').value = '';
        }
    });
});

// --- CARGA DINÁMICA DE EMPRESAS EN SELECT DE PROVEEDOR ---
async function loadCompanyOptions() {
    const select = document.getElementById('supplierCompany');
    if (!select) return;
    select.innerHTML = '<option value="">Seleccione empresa...</option>';
    try {
        const resp = await fetch(API_COMPANY, { headers: { 'Authorization': `Bearer ${token}` } });
        const data = await resp.json();
        data.forEach(c => {
            select.innerHTML += `<option value="${c.id}">${c.name}</option>`;
        });
    } catch (e) {
        select.innerHTML = '<option value="">Error cargando empresas</option>';
    }
}

// --- CRUD Y FICHAS DE DETALLE ---

async function saveCompany(formData, id = null) {
    const url = id ? `${API_COMPANY}${id}/` : API_COMPANY;
    const method = id ? 'PUT' : 'POST';
    try {
        const resp = await fetch(url, {
            method,
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        if (!resp.ok) {
            let errorText = '';
            try {
                const error = await resp.json();
                if (error.detail) errorText = error.detail;
                else if (typeof error === 'object') {
                    for (const k in error) {
                        errorText += `\n${k}: ${error[k]}`;
                    }
                } else errorText = JSON.stringify(error);
            } catch (e) {
                errorText = 'Error desconocido';
            }
            alert('Error guardando empresa:' + errorText);
            return false;
        }
        loadCompanyTable();
        return true;
    } catch (e) {
        alert('Error de red al guardar empresa');
        return false;
    }
}

async function saveSupplier(formData, id = null) {
    const url = id ? `${API_SUPPLIER}${id}/` : API_SUPPLIER;
    const method = id ? 'PUT' : 'POST';
    try {
        const resp = await fetch(url, {
            method,
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        if (!resp.ok) {
            let errorText = '';
            try {
                const error = await resp.json();
                if (error.detail) errorText = error.detail;
                else if (typeof error === 'object') {
                    for (const k in error) {
                        errorText += `\n${k}: ${error[k]}`;
                    }
                } else errorText = JSON.stringify(error);
            } catch (e) {
                errorText = 'Error desconocido';
            }
            alert('Error guardando proveedor:' + errorText);
            return false;
        }
        loadSupplierTable();
        return true;
    } catch (e) {
        alert('Error de red al guardar proveedor');
        return false;
    }
}

async function savePerson(formData, id = null) {
    const url = id ? `${API_PERSON}${id}/` : API_PERSON;
    const method = id ? 'PUT' : 'POST';
    try {
        const resp = await fetch(url, {
            method,
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        if (!resp.ok) {
            let errorText = '';
            try {
                const error = await resp.json();
                if (error.detail) errorText = error.detail;
                else if (typeof error === 'object') {
                    for (const k in error) {
                        errorText += `\n${k}: ${error[k]}`;
                    }
                } else errorText = JSON.stringify(error);
            } catch (e) {
                errorText = 'Error desconocido';
            }
            alert('Error guardando persona:' + errorText);
            return false;
        }
        loadPersonTable();
        return true;
    } catch (e) {
        alert('Error de red al guardar persona');
        return false;
    }
}

// Guardar desde los formularios
if (document.getElementById('companyForm')) {
    document.getElementById('companyForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const id = document.getElementById('companyId').value || null;
        const formData = new FormData(this);
        const ok = await saveCompany(formData, id);
        if (ok) {
            bootstrap.Modal.getOrCreateInstance(document.getElementById('companyModal')).hide();
            this.reset();
            document.getElementById('companyImagePreview').style.display = 'none';
            document.getElementById('companyId').value = '';
        }
    });
}
if (document.getElementById('supplierForm')) {
    document.getElementById('supplierForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const id = document.getElementById('supplierId').value || null;
        const formData = new FormData(this);
        const ok = await saveSupplier(formData, id);
        if (ok) {
            bootstrap.Modal.getOrCreateInstance(document.getElementById('supplierModal')).hide();
            this.reset();
            document.getElementById('supplierImagePreview').style.display = 'none';
            document.getElementById('supplierId').value = '';
        }
    });
}
if (document.getElementById('personForm')) {
    document.getElementById('personForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const id = document.getElementById('personId').value || null;
        const formData = new FormData(this);
        const ok = await savePerson(formData, id);
        if (ok) {
            bootstrap.Modal.getOrCreateInstance(document.getElementById('personModal')).hide();
            this.reset();
            document.getElementById('personImagePreview').style.display = 'none';
            document.getElementById('personId').value = '';
        }
    });
}

// --- VER DETALLE/FICHA ---
window.viewCompany = async function(id) {
    const resp = await fetch(`${API_COMPANY}${id}/`, { headers: { 'Authorization': `Bearer ${token}` } });
    const c = await resp.json();
    let html = `<h5>${c.name}</h5><p><b>RUT:</b> ${c.rut || ''}<br><b>Dirección:</b> ${c.address || ''}<br><b>Teléfono:</b> ${c.phone || ''}<br><b>Email:</b> ${c.email || ''}<br><b>Sitio web:</b> ${c.website || ''}<br><b>Contacto:</b> ${c.contact_person || ''} (${c.contact_phone || ''}, ${c.contact_email || ''})<br><b>Notas:</b> ${c.notes || ''}</p>`;
    if (c.image) html += `<img src="${c.image}" style="max-width:120px;">`;
    showDetailModal('Empresa', html);
}
window.viewSupplier = async function(id) {
    const resp = await fetch(`${API_SUPPLIER}${id}/`, { headers: { 'Authorization': `Bearer ${token}` } });
    const s = await resp.json();
    let html = `<h5>${s.name}</h5><p><b>Contacto:</b> ${s.contact || ''}<br><b>Teléfono:</b> ${s.phone || ''}<br><b>Email:</b> ${s.email || ''}<br><b>Empresa:</b> ${s.company || ''}<br><b>Dirección:</b> ${s.address || ''}<br><b>Sitio web:</b> ${s.website || ''}<br><b>NIT/RUT:</b> ${s.tax_id || ''}<br><b>Activo:</b> ${s.is_active ? 'Sí' : 'No'}<br><b>Notas:</b> ${s.notes || ''}</p>`;
    if (s.image) html += `<img src="${s.image}" style="max-width:120px;">`;
    showDetailModal('Proveedor', html);
}
window.viewPerson = async function(id) {
    const resp = await fetch(`${API_PERSON}${id}/`, { headers: { 'Authorization': `Bearer ${token}` } });
    const p = await resp.json();
    let html = `<h5>${p.name}</h5><p><b>Teléfono:</b> ${p.phone || ''}<br><b>Email:</b> ${p.email || ''}<br><b>Notas:</b> ${p.notes || ''}</p>`;
    if (p.image) html += `<img src="${p.image}" style="max-width:120px;">`;
    showDetailModal('Persona', html);
}
window.viewMachinery = async function(id) {
    const resp = await fetch(`${API_MACHINERY}${id}/`, { headers: { 'Authorization': `Bearer ${token}` } });
    const m = await resp.json();
    let html = `<h5>${m.name}</h5><p><b>Marca:</b> ${m.brand || ''}<br><b>Modelo:</b> ${m.model || ''}<br><b>Serie:</b> ${m.serial || ''}<br><b>Estado:</b> ${m.status || ''}<br><b>Ubicación:</b> ${m.location || ''}<br><b>Fecha de adquisición:</b> ${m.purchase_date || ''}<br><b>Valor:</b> ${m.value ? `$${m.value}` : ''}<br><b>Notas técnicas:</b> ${m.notes || ''}<br><b>Responsable:</b> ${m.responsible || ''}<br><b>Mantenimiento:</b> ${m.maintenance || ''}</p>`;
    if (m.image) html += `<img src="${m.image}" style="max-width:120px;">`;
    showDetailModal('Ficha Técnica Maquinaria/Herramienta', html);
}
function showDetailModal(title, html) {
    let modal = document.getElementById('detailModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'detailModal';
        modal.tabIndex = -1;
        modal.innerHTML = `<div class='modal-dialog'><div class='modal-content'><div class='modal-header'><h5 class='modal-title'></h5><button type='button' class='btn-close' data-bs-dismiss='modal'></button></div><div class='modal-body'></div></div></div>`;
        document.body.appendChild(modal);
    }
    modal.querySelector('.modal-title').innerText = title;
    modal.querySelector('.modal-body').innerHTML = html;
    bootstrap.Modal.getOrCreateInstance(modal).show();
}

// --- FUNCIONES CRUD MAQUINARIA (placeholder, puedes implementar igual que las demás) ---
async function editMachinery(id) {
    // Implementar lógica de edición similar a editCompany
}
async function deleteMachinery(id) {
    // Implementar lógica de eliminación similar a deleteCompany
}
