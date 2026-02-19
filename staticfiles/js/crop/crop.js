/**
 * crop.js — Módulo de gestión de Cultivos
 * Fixes:
 *  - API_BASE sin puerto hardcoded
 *  - Funciones showCropDetail/deleteCrop/editCrop fuera del scope de loadCropTable
 *  - Endpoint variedades → /api/crop/varieties/
 *  - Encadenamiento tipo → variedad
 *  - Mini-modales inline (tipo, variedad, empleado, proveedor)
 *  - Banner cuando no hay parcelas
 *  - Empty-state en tabla
 */

const _hostname = window.location.hostname;
const _isLocal  = _hostname === 'localhost' || _hostname === '127.0.0.1';
const BACKEND   = _isLocal ? `http://${_hostname}:8000` : '';
const API_BASE  = `${BACKEND}/api/crop/`;
const API_VARIETY   = `${BACKEND}/api/crop/varieties/`;
const API_PARCELS   = `${BACKEND}/api/parcels/parcel/`;
const API_EMPLOYEES = `${BACKEND}/api/RRHH/empleados/`;
const API_SUPPLIERS = `${BACKEND}/api/inventario/suppliers/`;

function authHeaders() {
    const token = localStorage.getItem('accessToken');
    return { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
}

async function apiFetch(url, options = {}) {
    const defaults = { headers: authHeaders() };
    const config   = { ...defaults, ...options, headers: { ...defaults.headers, ...(options.headers || {}) } };
    let res = await fetch(url, config);
    if (res.status === 401) {
        const refresh = localStorage.getItem('refreshToken');
        if (refresh) {
            const rr = await fetch(`${BACKEND}/api/token/refresh/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh })
            });
            if (rr.ok) {
                const data = await rr.json();
                localStorage.setItem('accessToken', data.access);
                config.headers['Authorization'] = `Bearer ${data.access}`;
                res = await fetch(url, config);
            } else { handleAuthFailure(); throw new Error('session_expired'); }
        } else { handleAuthFailure(); throw new Error('session_expired'); }
    }
    return res;
}

function handleAuthFailure() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    window.location.href = '/templates/authentication/login.html';
}

let _cropModal, _cropDetailModal, _addTypeModal, _addVarietyModal, _addEmployeeModal, _addSupplierModal;
function getCropModal()        { return _cropModal        = _cropModal        || new bootstrap.Modal(document.getElementById('cropModal')); }
function getDetailModal()      { return _cropDetailModal  = _cropDetailModal  || new bootstrap.Modal(document.getElementById('cropDetailModal')); }
function getAddTypeModal()     { return _addTypeModal     = _addTypeModal     || new bootstrap.Modal(document.getElementById('modalAddType')); }
function getAddVarietyModal()  { return _addVarietyModal  = _addVarietyModal  || new bootstrap.Modal(document.getElementById('modalAddVariety')); }
function getAddEmployeeModal() { return _addEmployeeModal = _addEmployeeModal || new bootstrap.Modal(document.getElementById('modalAddEmployee')); }
function getAddSupplierModal() { return _addSupplierModal = _addSupplierModal || new bootstrap.Modal(document.getElementById('modalAddSupplier')); }

let editingCropId = null;

async function loadCropTable() {
    try {
        const res   = await apiFetch(`${API_BASE}crops/`);
        const data  = await res.json();
        const crops = Array.isArray(data) ? data : (data.results || []);
        const tbody = document.querySelector('#crop-summary-table tbody');
        tbody.innerHTML = '';
        if (!crops.length) {
            document.getElementById('crop-empty-state').style.display = 'block';
            document.getElementById('crop-table-card').style.display  = 'none';
            return;
        }
        document.getElementById('crop-empty-state').style.display = 'none';
        document.getElementById('crop-table-card').style.display   = '';
        crops.forEach(c => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${c.name||'—'}</td><td>${c.crop_type_name||c.crop_type||'—'}</td><td>${c.variety_name||'—'}</td><td>${c.parcel_name||'—'}</td><td>${c.area||'—'}</td><td>${c.sowing_date||'—'}</td><td>${c.harvest_date||'—'}</td><td>${c.manager_name||'—'}</td><td><button class="btn btn-sm btn-info me-1" onclick="showCropDetail(${c.id})"><i class="bi bi-eye"></i></button><button class="btn btn-sm btn-warning me-1" onclick="editCrop(${c.id})"><i class="bi bi-pencil"></i></button><button class="btn btn-sm btn-danger" onclick="deleteCrop(${c.id})"><i class="bi bi-trash"></i></button></td>`;
            tbody.appendChild(tr);
        });
    } catch (e) { if (e.message !== 'session_expired') console.error('Error al cargar cultivos:', e); }
}

async function showCropDetail(id) {
    try {
        const res  = await apiFetch(`${API_BASE}crops/${id}/`);
        const c    = await res.json();
        document.getElementById('crop-detail-body').innerHTML = `<div class="row g-3"><div class="col-6"><strong>Nombre:</strong> ${c.name||'—'}</div><div class="col-6"><strong>Tipo:</strong> ${c.crop_type_name||c.crop_type||'—'}</div><div class="col-6"><strong>Variedad:</strong> ${c.variety_name||'—'}</div><div class="col-6"><strong>Parcela:</strong> ${c.parcel_name||'—'}</div><div class="col-6"><strong>Área:</strong> ${c.area||'—'} ha</div><div class="col-6"><strong>Siembra:</strong> ${c.sowing_date||'—'}</div><div class="col-6"><strong>Cosecha:</strong> ${c.harvest_date||'—'}</div><div class="col-6"><strong>R.esperado:</strong> ${c.expected_yield||'—'} t/ha</div><div class="col-6"><strong>R.real:</strong> ${c.actual_yield||'—'} t/ha</div><div class="col-6"><strong>Riego:</strong> ${c.irrigation_type||'—'}</div><div class="col-6"><strong>Responsable:</strong> ${c.manager_name||'—'}</div><div class="col-6"><strong>Proveedor:</strong> ${c.seed_supplier_name||'—'}</div><div class="col-12"><strong>Notas:</strong> ${c.notes||'—'}</div>${c.image?`<div class="col-12"><img src="${c.image}" class="img-fluid rounded" style="max-height:200px;"></div>`:''}</div>`;
        getDetailModal().show();
    } catch (e) { if (e.message !== 'session_expired') console.error('Error detalle:', e); }
}

async function editCrop(id) {
    editingCropId = id;
    await showCropModal();
    try {
        const res = await apiFetch(`${API_BASE}crops/${id}/`);
        const c   = await res.json();
        document.getElementById('cropModalLabel').textContent     = 'Editar Cultivo';
        document.getElementById('crop-name').value                = c.name || '';
        document.getElementById('crop-area').value                = c.area || '';
        document.getElementById('crop-sowing-date').value         = c.sowing_date || '';
        document.getElementById('crop-harvest-date').value        = c.harvest_date || '';
        document.getElementById('crop-expected-yield').value      = c.expected_yield || '';
        document.getElementById('crop-actual-yield').value        = c.actual_yield || '';
        document.getElementById('crop-irrigation-type').value     = c.irrigation_type || '';
        document.getElementById('crop-notes').value               = c.notes || '';
        setSelectValue('crop-type',          c.crop_type);
        setSelectValue('crop-parcel',        c.parcel);
        setSelectValue('crop-manager',       c.manager);
        setSelectValue('crop-seed-supplier', c.seed_supplier);
        if (c.crop_type) { await loadVarieties(c.crop_type); setSelectValue('crop-variety', c.variety); }
        getCropModal().show();
    } catch (e) { if (e.message !== 'session_expired') console.error('Error editar:', e); }
}

function setSelectValue(selectId, value) {
    const sel = document.getElementById(selectId);
    if (!sel || value == null) return;
    for (const opt of sel.options) { if (String(opt.value) === String(value)) { opt.selected = true; break; } }
}

async function deleteCrop(id) {
    if (!confirm('¿Eliminar este cultivo?')) return;
    try {
        await apiFetch(`${API_BASE}crops/${id}/`, { method: 'DELETE' });
        loadCropTable();
    } catch (e) { if (e.message !== 'session_expired') alert('Error al eliminar.'); }
}

async function showCropModal() {
    document.getElementById('crop-form').reset();
    document.getElementById('cropModalLabel').textContent = 'Nuevo Cultivo';
    document.getElementById('crop-no-parcel-banner').classList.add('d-none');
    document.getElementById('crop-variety-hint').classList.add('d-none');
    try {
        const [typesRes, parcelsRes, employeesRes, suppliersRes] = await Promise.all([
            apiFetch(`${API_BASE}types/`),
            apiFetch(API_PARCELS),
            apiFetch(API_EMPLOYEES).catch(() => null),
            apiFetch(API_SUPPLIERS).catch(() => null),
        ]);
        const [types, parcels, employees, suppliers] = await Promise.all([
            typesRes.json(),
            parcelsRes.json(),
            employeesRes  ? employeesRes.json().catch(() => []) : Promise.resolve([]),
            suppliersRes  ? suppliersRes.json().catch(() => []) : Promise.resolve([]),
        ]);
        populateSelect('crop-type',         extractList(types),     'id', 'name',      'crop-type-hint',     '⚠ Sin tipos. Usa + para agregar.');
        populateSelect('crop-variety',       [],                     'id', 'name',      'crop-variety-hint',  'Selecciona primero el tipo para ver variedades.', null, false);
        populateSelect('crop-parcel',        extractList(parcels),   'id', 'name',      'crop-parcel-hint',   '⚠ Sin parcelas.', '/templates/parcels/parcels-dashboard.html');
        populateSelect('crop-manager',       extractList(employees), 'id', 'full_name', 'crop-manager-hint',  '⚠ Sin empleados. Usa + para agregar.');
        populateSelect('crop-seed-supplier', extractList(suppliers), 'id', 'name',      'crop-supplier-hint', '⚠ Sin proveedores. Usa + para agregar.');
        if (!extractList(parcels).length) {
            document.getElementById('crop-no-parcel-banner').classList.remove('d-none');
        }
        document.getElementById('crop-variety-hint').classList.remove('d-none');
    } catch (e) { if (e.message !== 'session_expired') console.error('Error opciones modal:', e); }
    if (!editingCropId) getCropModal().show();
}

function extractList(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.results)) return data.results;
    return [];
}

function populateSelect(selectId, items, valueKey, labelKey, hintId, emptyHint, linkHref, showHintOnEmpty = true) {
    const sel  = document.getElementById(selectId);
    const hint = hintId ? document.getElementById(hintId) : null;
    if (!sel) return;
    sel.innerHTML = '';
    if (!items.length) {
        const opt = document.createElement('option');
        opt.value = ''; opt.textContent = '— Sin opciones —'; sel.appendChild(opt);
        if (hint && emptyHint && showHintOnEmpty) {
            hint.innerHTML = linkHref ? `${emptyHint} <a href="${linkHref}">Ir →</a>` : emptyHint;
            hint.classList.remove('d-none');
        }
        return;
    }
    if (hint) hint.classList.add('d-none');
    const blankOpt = document.createElement('option');
    blankOpt.value = ''; blankOpt.textContent = '— Seleccionar —'; sel.appendChild(blankOpt);
    items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item[valueKey];
        opt.textContent = item[labelKey] || `${item.first_name||''} ${item.last_name||''}`.trim() || String(item.id);
        sel.appendChild(opt);
    });
}

async function loadVarieties(cropTypeId) {
    const sel  = document.getElementById('crop-variety');
    const hint = document.getElementById('crop-variety-hint');
    if (!sel) return;
    sel.innerHTML = '<option value="">Cargando...</option>';
    try {
        const res      = await apiFetch(`${API_VARIETY}?crop_type=${cropTypeId}`);
        const data     = await res.json();
        const varieties = extractList(data);
        populateSelect('crop-variety', varieties, 'id', 'name', 'crop-variety-hint', '⚠ Sin variedades. Usa + para agregar.');
        if (hint) hint.classList.toggle('d-none', varieties.length > 0);
    } catch (e) {
        if (e.message !== 'session_expired') { if (sel) sel.innerHTML = '<option value="">Error al cargar</option>'; }
    }
}

async function saveCrop(e) {
    e.preventDefault();
    const formData = new FormData(document.getElementById('crop-form'));
    const body = {};
    for (const [key, val] of formData.entries()) { if (key !== 'image' && val !== '') body[key] = val; }
    const url    = editingCropId ? `${API_BASE}crops/${editingCropId}/` : `${API_BASE}crops/`;
    const method = editingCropId ? 'PUT' : 'POST';
    try {
        const res = await apiFetch(url, { method, body: JSON.stringify(body) });
        if (res.ok) { getCropModal().hide(); editingCropId = null; loadCropTable(); }
        else { const err = await res.json().catch(() => ({})); alert('Error al guardar: ' + JSON.stringify(err)); }
    } catch (e) { if (e.message !== 'session_expired') alert('Error de red al guardar.'); }
}

// ─── Mini-modal: Tipo ────────────────────────────────────────────────────────
function openAddTypeModal() {
    document.getElementById('new-type-name').value = '';
    document.getElementById('new-type-desc').value  = '';
    getAddTypeModal().show();
}
async function saveNewType() {
    const name = document.getElementById('new-type-name').value.trim();
    if (!name) { alert('Nombre obligatorio.'); return; }
    try {
        const res = await apiFetch(`${API_BASE}types/`, {
            method: 'POST',
            body: JSON.stringify({ name, description: document.getElementById('new-type-desc').value.trim() })
        });
        if (res.ok) {
            const tipo = await res.json();
            getAddTypeModal().hide();
            const sel = document.getElementById('crop-type');
            const opt = document.createElement('option'); opt.value = tipo.id; opt.textContent = tipo.name;
            sel.appendChild(opt); sel.value = tipo.id;
            sel.dispatchEvent(new Event('change'));
        } else { const err = await res.json().catch(() => ({})); alert('Error: ' + JSON.stringify(err)); }
    } catch (e) { if (e.message !== 'session_expired') alert('Error de red.'); }
}

// ─── Mini-modal: Variedad ────────────────────────────────────────────────────
function openAddVarietyModal() {
    const typeId = document.getElementById('crop-type').value;
    if (!typeId) { alert('Selecciona primero el tipo de cultivo.'); return; }
    document.getElementById('add-variety-type-label').textContent = 'Para: ' + (document.getElementById('crop-type').selectedOptions[0]?.text || '');
    document.getElementById('new-variety-name').value = '';
    document.getElementById('new-variety-days').value  = '';
    getAddVarietyModal().show();
}
async function saveNewVariety() {
    const typeId = document.getElementById('crop-type').value;
    const name   = document.getElementById('new-variety-name').value.trim();
    const days   = document.getElementById('new-variety-days').value;
    if (!name) { alert('Nombre obligatorio.'); return; }
    try {
        const res = await apiFetch(API_VARIETY, {
            method: 'POST',
            body: JSON.stringify({ name, crop_type: parseInt(typeId), cycle_days: days || null })
        });
        if (res.ok) {
            const v = await res.json();
            getAddVarietyModal().hide();
            const sel = document.getElementById('crop-variety');
            const opt = document.createElement('option'); opt.value = v.id; opt.textContent = v.name;
            sel.appendChild(opt); sel.value = v.id;
        } else { const err = await res.json().catch(() => ({})); alert('Error: ' + JSON.stringify(err)); }
    } catch (e) { if (e.message !== 'session_expired') alert('Error de red.'); }
}

// ─── Mini-modal: Empleado ────────────────────────────────────────────────────
function openAddEmployeeModal() {
    ['new-emp-id','new-emp-fname','new-emp-lname','new-emp-addr','new-emp-phone','new-emp-hire'].forEach(id => { document.getElementById(id).value = ''; });
    getAddEmployeeModal().show();
}
async function saveNewEmployee() {
    const body = {
        identification_number: document.getElementById('new-emp-id').value.trim(),
        first_name: document.getElementById('new-emp-fname').value.trim(),
        last_name: document.getElementById('new-emp-lname').value.trim(),
        address: document.getElementById('new-emp-addr').value.trim(),
        phone: document.getElementById('new-emp-phone').value.trim(),
        date_of_hire: document.getElementById('new-emp-hire').value,
    };
    if (!body.identification_number || !body.first_name || !body.last_name) { alert('Cédula, nombre y apellido obligatorios.'); return; }
    try {
        const res = await apiFetch(API_EMPLOYEES, { method: 'POST', body: JSON.stringify(body) });
        if (res.ok) {
            const emp = await res.json();
            getAddEmployeeModal().hide();
            const sel = document.getElementById('crop-manager');
            const opt = document.createElement('option'); opt.value = emp.id; opt.textContent = `${emp.first_name} ${emp.last_name}`;
            sel.appendChild(opt); sel.value = emp.id;
        } else { const err = await res.json().catch(() => ({})); alert('Error: ' + JSON.stringify(err)); }
    } catch (e) { if (e.message !== 'session_expired') alert('Error de red.'); }
}

// ─── Mini-modal: Proveedor ───────────────────────────────────────────────────
function openAddSupplierModal() {
    ['new-supplier-name','new-supplier-phone','new-supplier-email'].forEach(id => { document.getElementById(id).value = ''; });
    getAddSupplierModal().show();
}
async function saveNewSupplier() {
    const body = {
        name: document.getElementById('new-supplier-name').value.trim(),
        phone: document.getElementById('new-supplier-phone').value.trim(),
        email: document.getElementById('new-supplier-email').value.trim(),
    };
    if (!body.name) { alert('Nombre obligatorio.'); return; }
    try {
        const res = await apiFetch(API_SUPPLIERS, { method: 'POST', body: JSON.stringify(body) });
        if (res.ok) {
            const s = await res.json();
            getAddSupplierModal().hide();
            const sel = document.getElementById('crop-seed-supplier');
            const opt = document.createElement('option'); opt.value = s.id; opt.textContent = s.name;
            sel.appendChild(opt); sel.value = s.id;
        } else { const err = await res.json().catch(() => ({})); alert('Error: ' + JSON.stringify(err)); }
    } catch (e) { if (e.message !== 'session_expired') alert('Error de red.'); }
}

// ─── Init ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadCropTable();
    document.getElementById('btn-new-crop')?.addEventListener('click', () => { editingCropId = null; showCropModal(); });
    document.getElementById('btn-new-crop-empty')?.addEventListener('click', () => { editingCropId = null; showCropModal(); });
    document.getElementById('crop-form')?.addEventListener('submit', saveCrop);
    document.getElementById('crop-type')?.addEventListener('change', (e) => {
        if (e.target.value) loadVarieties(e.target.value);
        else {
            populateSelect('crop-variety', [], 'id', 'name', 'crop-variety-hint', 'Selecciona primero el tipo.', null, true);
            document.getElementById('crop-variety-hint').classList.remove('d-none');
        }
    });
    document.getElementById('btn-add-type')?    .addEventListener('click', openAddTypeModal);
    document.getElementById('btn-add-variety')?.addEventListener('click', openAddVarietyModal);
    document.getElementById('btn-add-employee')?.addEventListener('click', openAddEmployeeModal);
    document.getElementById('btn-add-supplier')?.addEventListener('click', openAddSupplierModal);
    document.getElementById('btn-save-type')?    .addEventListener('click', saveNewType);
    document.getElementById('btn-save-variety')?.addEventListener('click', saveNewVariety);
    document.getElementById('btn-save-employee')?.addEventListener('click', saveNewEmployee);
    document.getElementById('btn-save-supplier')?.addEventListener('click', saveNewSupplier);
});

window.showCropDetail = showCropDetail;
window.editCrop       = editCrop;
window.deleteCrop     = deleteCrop;
