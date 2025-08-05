// almacenes.js - CRUD simple de almacenes con modales
const API_URL = `http://${window.location.hostname}:8000/api/inventario/warehouses/`;
const token = localStorage.getItem("accessToken");

// Cargar almacenes y renderizar tabla
async function loadWarehouses() {
    try {
        const resp = await fetch(API_URL, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        if (!resp.ok) throw new Error('Error cargando almacenes');
        const almacenes = await resp.json();
const tbody = document.getElementById('tablaAlmacenes').querySelector('tbody');
        tbody.innerHTML = '';
        almacenes.forEach(a => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${a.name}</td>
                <td>${a.address || ''}</td>
                <td>${a.location || ''}</td>
                <td>${a.description || ''}</td>
                <td>${a.is_active ? 'Sí' : 'No'}</td>
                <td class="text-center">
                    <button class="btn btn-sm btn-outline-primary me-1" data-action="edit" data-id="${a.id}" title="Editar"><i class="fa fa-edit"></i></button>
                    <button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="${a.id}" title="Eliminar"><i class="fa fa-trash"></i></button>
                    <button class="btn btn-sm btn-outline-info ms-1" data-action="detail" data-id="${a.id}" title="Detalle"><i class="fa fa-eye"></i> Detalle</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        alert('Error cargando almacenes');
    }
}

// Guardar almacén (crear o editar)
document.getElementById('almacenForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const id = document.getElementById('almacenId').value || null;
    const data = {
        name: document.getElementById('nombreAlmacen').value,
        address: document.getElementById('direccionAlmacen').value,
        location: document.getElementById('ubicacionAlmacen').value,
        description: document.getElementById('descripcionAlmacen').value,
        is_active: document.getElementById('activoAlmacen').value === 'true'
    };
    await saveWarehouse(data, id);
    // Cerrar modal
    const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('almacenModal'));
    modal.hide();
    this.reset();
    document.getElementById('almacenId').value = '';
    document.getElementById('modalTitleAlmacen').textContent = 'Nuevo Almacén';
});

async function saveWarehouse(data, id=null) {
    try {
        const url = id ? `${API_URL}${id}/` : API_URL;
        const method = id ? 'PUT' : 'POST';
        const resp = await fetch(url, {
            method,
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        if (!resp.ok) throw new Error('Error guardando almacén');
        await loadWarehouses();
    } catch (error) {
        alert('Error guardando almacén');
    }
}

// Eliminar almacén
async function deleteWarehouse(id) {
    if (!confirm('¿Seguro que deseas eliminar este almacén?')) return;
    try {
        const resp = await fetch(`${API_URL}${id}/`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        if (!resp.ok) throw new Error('Error eliminando almacén');
        await loadWarehouses();
    } catch (error) {
        alert('Error eliminando almacén');
    }
}

// Delegación de eventos para acciones en la tabla de almacenes
if (document.getElementById('tablaAlmacenes')) {
    document.getElementById('tablaAlmacenes').addEventListener('click', async function(e) {
        const btn = e.target.closest('button[data-action]');
        if (!btn) return;
        const action = btn.getAttribute('data-action');
        const id = btn.getAttribute('data-id');
        const row = btn.closest('tr');
        if (action === 'edit') {
            await editWarehouse(id);
        } else if (action === 'delete') {
            await deleteWarehouse(id);
        } else if (action === 'detail') {
            // Mostrar modal con datos del almacén, insumos y herramientas/maquinaria
            const nombre = row.children[0].textContent;
            const direccion = row.children[1].textContent;
            const ubicacion = row.children[2].textContent;
            const descripcion = row.children[3].textContent;
            const activo = row.children[4].textContent;
            const modalBody = document.getElementById('detalleAlmacenBody');
            modalBody.innerHTML = '';
            let html = `
                <div class='p-4'>
                    <h4 class='mb-3'><i class='fa fa-warehouse'></i> ${nombre}</h4>
                    <div class='mb-2'><strong>ID:</strong> ${id}</div>
                    <div class='mb-2'><strong>Dirección:</strong> ${direccion}</div>
                    <div class='mb-2'><strong>Ubicación:</strong> ${ubicacion}</div>
                    <div class='mb-2'><strong>Descripción:</strong> ${descripcion}</div>
                    <div class='mb-2'><strong>Activo:</strong> ${activo}</div>
                </div>
                <hr>
                <h5 class='mt-4 mb-3'><i class='fa fa-boxes'></i> Insumos en este almacén</h5>
                <div id='tablaInsumosWrap'><div class='text-center text-muted'>Cargando insumos...</div></div>
                <h5 class='mt-4 mb-3'><i class='fa fa-tools'></i> Herramientas y Maquinaria en este almacén</h5>
                <div id='tablaHerramientasWrap'><div class='text-center text-muted'>Cargando herramientas y maquinaria...</div></div>
            `;
            modalBody.innerHTML = html;
            // --- INSUMOS ---
            fetch(`http://${window.location.hostname}:8000/api/inventario/supplies/?warehouse=${id}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            })
            .then(function(resp) { return resp.json(); })
            .then(function(data) {
                let insumosHtml = '';
                if (Array.isArray(data) && data.length > 0) {
                    insumosHtml += `<div class='table-responsive'><table class='table table-bordered table-sm'><thead><tr><th>Nombre</th><th>Categoría</th><th>Subcategoría</th><th>Cantidad</th><th>Unidad</th><th>Valor unitario</th><th>Valor total</th><th>Descripción</th></tr></thead><tbody>`;
                    data.forEach(function(insumo) {
                        insumosHtml += `<tr>
                            <td>${insumo.name}</td>
                            <td>${insumo.category && insumo.category.name ? insumo.category.name : (insumo.category_name || insumo.category || '-')}</td>
                            <td>${insumo.subcategory && insumo.subcategory.name ? insumo.subcategory.name : (insumo.subcategory_name || insumo.subcategory || '-')}</td>
                            <td>${insumo.quantity}</td>
                            <td>${insumo.unit_display || insumo.unit || '-'}</td>
                            <td>${insumo.unit_value}</td>
                            <td>${(insumo.quantity * insumo.unit_value).toFixed(2)}</td>
                            <td>${insumo.description || '-'}</td>
                        </tr>`;
                    });
                    insumosHtml += `</tbody></table></div>`;
                } else {
                    insumosHtml = `<div class='alert alert-info mt-2'>No hay insumos registrados en este almacén.</div>`;
                }
                document.getElementById('tablaInsumosWrap').innerHTML = insumosHtml;
            })
            .catch(function() {
                document.getElementById('tablaInsumosWrap').innerHTML = `<div class='alert alert-warning mt-2'>No se pudieron cargar los insumos.</div>`;
            });
            // --- MAQUINARIA ---
            fetch(`http://${window.location.hostname}:8000/api/inventario/machinery/?warehouse=${id}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            })
            .then(function(resp) { return resp.json(); })
            .then(function(data) {
                let maquinariaHtml = '';
                if (Array.isArray(data) && data.length > 0) {
                    maquinariaHtml += `<div class='table-responsive'><table class='table table-bordered table-sm'><thead><tr><th>Nombre</th><th>Categoría</th><th>Subcategoría</th><th>Cantidad</th><th>Unidad</th><th>Valor unitario</th><th>Valor total</th><th>Descripción</th></tr></thead><tbody>`;
                    data.forEach(function(maquinaria) {
                        maquinariaHtml += `<tr>
                            <td>${maquinaria.name}</td>
                            <td>${maquinaria.category && maquinaria.category.name ? maquinaria.category.name : (maquinaria.category_name || maquinaria.category || '-')}</td>
                            <td>${maquinaria.subcategory && maquinaria.subcategory.name ? maquinaria.subcategory.name : (maquinaria.subcategory_name || maquinaria.subcategory || '-')}</td>
                            <td>${maquinaria.quantity || '-'}</td>
                            <td>${maquinaria.unit_display || maquinaria.unit || '-'}</td>
                            <td>${maquinaria.unit_value || '-'}</td>
                            <td>${maquinaria.quantity && maquinaria.unit_value ? (maquinaria.quantity * maquinaria.unit_value).toFixed(2) : '-'}</td>
                            <td>${maquinaria.description || '-'}</td>
                        </tr>`;
                    });
                    maquinariaHtml += `</tbody></table></div>`;
                } else {
                    maquinariaHtml = `<div class='alert alert-info mt-2'>No hay maquinaria registrada en este almacén.</div>`;
                }
                document.getElementById('tablaHerramientasWrap').innerHTML = maquinariaHtml;
            })
            .catch(function() {
                document.getElementById('tablaHerramientasWrap').innerHTML = `<div class='alert alert-warning mt-2'>No se pudo cargar la maquinaria.</div>`;
            });
            // Mostrar el modal
            const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('detalleAlmacenModal'));
            modal.show();
            // Limpiar backdrop y contenido al cerrar el modal
            document.getElementById('detalleAlmacenModal').addEventListener('hidden.bs.modal', function () {
                modalBody.innerHTML = '';
                // Eliminar manualmente el backdrop si queda
                const backdrops = document.querySelectorAll('.modal-backdrop');
                backdrops.forEach(function(b) { b.parentNode.removeChild(b); });
            }, { once: true });
        }
    });
}

// Editar almacén: cargar datos en el modal
async function editWarehouse(id) {
    try {
        const resp = await fetch(`${API_URL}${id}/`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        if (!resp.ok) throw new Error('No se pudo cargar el almacén');
        const a = await resp.json();
        document.getElementById('almacenId').value = a.id;
        document.getElementById('nombreAlmacen').value = a.name;
        document.getElementById('direccionAlmacen').value = a.address || '';
        document.getElementById('ubicacionAlmacen').value = a.location || '';
        document.getElementById('descripcionAlmacen').value = a.description || '';
        document.getElementById('activoAlmacen').value = a.is_active ? 'true' : 'false';
        document.getElementById('modalTitleAlmacen').textContent = 'Editar Almacén';
        const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('almacenModal'));
        modal.show();
    } catch (error) {
        alert('No se pudo cargar el almacén');
    }
}

// Inicialización automática
if (document.getElementById('tablaAlmacenes')) {
    loadWarehouses();
}

document.getElementById('btnNuevoAlmacen').addEventListener('click', function() {
    document.getElementById('almacenForm').reset();
    document.getElementById('almacenId').value = '';
    document.getElementById('modalTitleAlmacen').textContent = 'Nuevo Almacén';
});
