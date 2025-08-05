// supplier_company.js - Gestión de empresas y proveedores (CRUD, selects dinámicos)
// --- LISTENERS PARA BOTONES DE MODALES ---
document.addEventListener('DOMContentLoaded', function() {
    // Botón Nueva Empresa
    const btnNewCompany = document.getElementById('btnNewCompany');
    if (btnNewCompany) {
        btnNewCompany.addEventListener('click', function() {
            // Limpiar formulario
            if (document.getElementById('companyForm')) {
                document.getElementById('companyForm').reset();
                document.getElementById('companyId').value = '';
            }
            // Mostrar modal solo si existe
            const modalEl = document.getElementById('companyModal');
            if (modalEl) {
                const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
                modal.show();
            } else {
                alert('No se encontró el modal de empresa (companyModal) en el DOM.');
            }
        });
    }
    // Botón Nuevo Proveedor
    const btnNewSupplier = document.getElementById('btnNewSupplier');
    if (btnNewSupplier) {
        btnNewSupplier.addEventListener('click', function() {
            // Limpiar formulario
            if (document.getElementById('supplierForm')) {
                document.getElementById('supplierForm').reset();
                document.getElementById('supplierId').value = '';
            }
            // Mostrar modal solo si existe
            const modalEl = document.getElementById('supplierModal');
            if (modalEl) {
                const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
                modal.show();
                // Recargar select de empresa en modal proveedor
                loadCompanySelect('supplierCompany');
            } else {
                alert('No se encontró el modal de proveedor (supplierModal) en el DOM.');
            }
        });
    }
});

const API_COMPANY = `http://${window.location.hostname}:8000/api/inventario/companies/`;
const API_SUPPLIER = `http://${window.location.hostname}:8000/api/inventario/suppliers/`;
const token = localStorage.getItem("accessToken");

// --- EMPRESA ---
async function loadCompanySelect(selectId, selectedId = '') {
    const select = document.getElementById(selectId);
    select.innerHTML = '<option value="">Selecciona empresa</option>';
    try {
        const resp = await fetch(API_COMPANY, { headers: { 'Authorization': `Bearer ${token}` } });
        const data = await resp.json();
        data.forEach(c => {
            select.innerHTML += `<option value="${c.id}"${selectedId == c.id ? ' selected' : ''}>${c.name}</option>`;
        });
    } catch (e) { select.innerHTML += '<option value="">Error cargando</option>'; }
}

// Guardar empresa
if (document.getElementById('companyForm')) {
    document.getElementById('companyForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const id = document.getElementById('companyId').value || null;
        const formData = new FormData();
        formData.append('name', document.getElementById('companyName').value);
        formData.append('rut', document.getElementById('companyRut').value);
        formData.append('address', document.getElementById('companyAddress').value);
        formData.append('phone', document.getElementById('companyPhone').value);
        formData.append('email', document.getElementById('companyEmail').value);
        formData.append('website', document.getElementById('companyWebsite').value);
        formData.append('contact_person', document.getElementById('companyContactPerson').value);
        formData.append('contact_phone', document.getElementById('companyContactPhone').value);
        formData.append('contact_email', document.getElementById('companyContactEmail').value);
        formData.append('notes', document.getElementById('companyNotes').value);
        await saveCompany(formData, id);
        const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('companyModal'));
        modal.hide();
        this.reset();
        document.getElementById('companyId').value = '';
        // Recargar selects de empresa en toda la app
        if (document.getElementById('supplierCompany')) loadCompanySelect('supplierCompany');
        if (document.getElementById('companySelect')) loadCompanySelect('companySelect');
    });
}

async function saveCompany(formData, id=null) {
    try {
        const url = id ? `${API_COMPANY}${id}/` : API_COMPANY;
        const method = id ? 'PUT' : 'POST';
        const resp = await fetch(url, {
            method,
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        if (!resp.ok) throw new Error('Error guardando empresa');
        // Recargar selects de empresa en proveedores
        loadCompanySelect('supplierCompany');
    } catch (error) {
        alert('Error guardando empresa');
    }
}

// --- PROVEEDOR ---
if (document.getElementById('supplierForm')) {
    document.getElementById('supplierForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const id = document.getElementById('supplierId').value || null;
        const formData = new FormData();
        formData.append('name', document.getElementById('supplierName').value);
        formData.append('contact', document.getElementById('supplierContact').value);
        formData.append('phone', document.getElementById('supplierPhone').value);
        formData.append('email', document.getElementById('supplierEmail').value);
        formData.append('company', document.getElementById('supplierCompany').value);
        formData.append('address', document.getElementById('supplierAddress').value);
        formData.append('website', document.getElementById('supplierWebsite').value);
        formData.append('tax_id', document.getElementById('supplierTaxId').value);
        formData.append('is_active', document.getElementById('supplierIsActive').value);
        formData.append('notes', document.getElementById('supplierNotes').value);
        await saveSupplier(formData, id);
        const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('supplierModal'));
        modal.hide();
        this.reset();
        document.getElementById('supplierId').value = '';
        // Recargar selects de proveedor en toda la app
        if (document.getElementById('machinerySupplier')) loadSupplierSelect('machinerySupplier');
        if (document.getElementById('supplySupplier')) loadSupplierSelect('supplySupplier');
    });
}

async function saveSupplier(formData, id=null) {
    try {
        const url = id ? `${API_SUPPLIER}${id}/` : API_SUPPLIER;
        const method = id ? 'PUT' : 'POST';
        const resp = await fetch(url, {
            method,
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        if (!resp.ok) throw new Error('Error guardando proveedor');
        // Recargar selects de proveedor en insumos/maquinaria si aplica
    } catch (error) {
        alert('Error guardando proveedor');
    }
}

// Inicialización de selects de empresa en el modal de proveedor
if (document.getElementById('supplierModal')) {
    document.getElementById('supplierModal').addEventListener('show.bs.modal', function() {
        loadCompanySelect('supplierCompany');
    });
}

// --- FUNCION PARA RECARGAR SELECT DE PROVEEDOR ---
async function loadSupplierSelect(selectId, selectedId = '') {
    const select = document.getElementById(selectId);
    if (!select) return;
    select.innerHTML = '<option value="">Selecciona proveedor</option>';
    try {
        const resp = await fetch(API_SUPPLIER, { headers: { 'Authorization': `Bearer ${token}` } });
        const data = await resp.json();
        data.forEach(s => {
            select.innerHTML += `<option value="${s.id}"${selectedId == s.id ? ' selected' : ''}>${s.name}</option>`;
        });
    } catch (e) { select.innerHTML += '<option value="">Error cargando</option>'; }
}
