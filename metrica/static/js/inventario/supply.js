// supply.js - Gestión avanzada de insumos (CRUD, multi-tenant, modular)
// API de proveedores
const SUPPLIER_API = `http://${window.location.hostname}:8000/api/inventario/suppliers/`;

// Cargar proveedores en el select múltiple
async function loadSuppliersSelect(selectId) {
    try {
        const token = localStorage.getItem("accessToken");
        const resp = await fetch(SUPPLIER_API, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        const select = document.getElementById(selectId);
        select.innerHTML = '';
        const suppliers = await resp.json();
        suppliers.forEach(s => {
            const option = document.createElement('option');
            option.value = s.id;
            option.textContent = s.name;
            select.appendChild(option);
        });
        if (!resp.ok) throw new Error('Error cargando proveedores');
    } catch (error) {
        alert('Error cargando proveedores: ' + error);
    }
}

const API_URL = `http://${window.location.hostname}:8000/api/inventario/supplies/`;
const WAREHOUSE_API = `http://${window.location.hostname}:8000/api/inventario/warehouses/`;
const CATEGORY_API = `http://${window.location.hostname}:8000/api/inventario/categories/`;
const SUBCATEGORY_API = `http://${window.location.hostname}:8000/api/inventario/subcategories/`;
// Cargar categorías en el select
async function loadCategoriesSelect(selectId) {
    try {
        const token = localStorage.getItem("accessToken");
        const resp = await fetch(CATEGORY_API, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        const select = document.getElementById(selectId);
        select.innerHTML = '<option value="">Seleccione...</option>';
        const categories = await resp.json();
        console.log('Categorías recibidas:', categories, 'Status:', resp.status); // LOG
        categories.forEach(c => {
            const option = document.createElement('option');
            option.value = c.id;
            option.textContent = c.name;
            select.appendChild(option);
        });
        if (!resp.ok) throw new Error('Error cargando categorías');
    } catch (error) {
        alert('Error cargando categorías: ' + error);
    }
}

// Cargar subcategorías filtradas por categoría
async function loadSubcategoriesSelect(selectId, categoryId) {
    try {
        const token = localStorage.getItem("accessToken");
        let url = SUBCATEGORY_API;
        if (categoryId) url += `?category=${categoryId}`;
        const resp = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        const select = document.getElementById(selectId);
        select.innerHTML = '<option value="">Seleccione...</option>';
        const subcategories = await resp.json();
        console.log('Subcategorías recibidas:', subcategories, 'Status:', resp.status, 'Para categoría:', categoryId); // LOG
        // Si no hay categoría seleccionada, no mostrar nada
        if (!categoryId) return;
        // Si hay subcategorías, agregarlas
        if (Array.isArray(subcategories) && subcategories.length > 0) {
            subcategories.forEach(sc => {
                const option = document.createElement('option');
                option.value = sc.id;
                option.textContent = sc.name;
                select.appendChild(option);
            });
        }
        if (!resp.ok) throw new Error('Error cargando subcategorías');
    } catch (error) {
        alert('Error cargando subcategorías: ' + error);
    }
}

// Cargar insumos y renderizar tabla
async function loadSupplies() {
    try {
        const token = localStorage.getItem("accessToken");
        const resp = await fetch(API_URL, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        if (!resp.ok) throw new Error('Error cargando insumos');
        const supplies = await resp.json();
        const tbody = document.getElementById('tablaSupplies').querySelector('tbody');
        tbody.innerHTML = '';
        supplies.forEach(s => {
            const row = document.createElement('tr');
            let unidad = s.unit === 'otros' ? (s.unit_custom || 'Otros') : (s.unit || '');
            // Visualización profesional de categoría y subcategoría
            let categoria = '';
            if (s.category) {
                if (typeof s.category === 'object' && s.category.name) categoria = s.category.name;
                else if (typeof s.category === 'string') categoria = s.category;
            } else if (s.category_name) {
                categoria = s.category_name;
            }
            categoria = categoria && categoria.trim() ? categoria : '<span class="text-muted">Sin categoría</span>';
            let subcategoria = '';
            if (s.subcategory) {
                if (typeof s.subcategory === 'object' && s.subcategory.name) subcategoria = s.subcategory.name;
                else if (typeof s.subcategory === 'string') subcategoria = s.subcategory;
            } else if (s.subcategory_name) {
                subcategoria = s.subcategory_name;
            }
            subcategoria = subcategoria && subcategoria.trim() ? subcategoria : '<span class="text-muted">Sin subcategoría</span>';
            row.innerHTML = `
                <td>${s.name}</td>
                <td>${categoria}</td>
                <td>${subcategoria}</td>
                <td>${s.warehouse && s.warehouse.name ? s.warehouse.name : (typeof s.warehouse === 'string' ? s.warehouse : '')}</td>
                <td>${s.quantity}</td>
                <td>${s.unit_value} <span class="text-muted small">${unidad}</span></td>
                <td>${s.description || ''}</td>
                <td class="text-center">
                    <button class="btn btn-sm btn-outline-primary me-1" data-action="edit" data-id="${s.id}" title="Editar"><i class="fa fa-edit"></i></button>
                    <button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="${s.id}" title="Eliminar"><i class="fa fa-trash"></i></button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        alert('Error cargando insumos');
    }
}

// Cargar almacenes para el select
async function loadWarehousesSelect(selectId) {
    try {
        const token = localStorage.getItem("accessToken");
        const resp = await fetch(WAREHOUSE_API, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        if (!resp.ok) throw new Error('Error cargando almacenes');
        const select = document.getElementById(selectId);
        select.innerHTML = '<option value="">Seleccione...</option>';
        const warehouses = await resp.json();
        warehouses.forEach(w => {
            const option = document.createElement('option');
            option.value = w.id;
            option.textContent = w.name;
            select.appendChild(option);
        });
    } catch (error) {
        alert('Error cargando almacenes');
    }
}


// Crear o editar insumo (con categoría y subcategoría)
async function saveSupply(data, id=null) {
    try {
        const token = localStorage.getItem("accessToken");
        const url = id ? `${API_URL}${id}/` : API_URL;
        const method = id ? 'PUT' : 'POST';
        // Construir payload según lo que espera el serializer
        const payload = {
            name: document.getElementById('nombreSupply').value,
            unit_value: document.getElementById('valorSupply').value,
            unit: document.getElementById('unitSupply').value,
            unit_custom: document.getElementById('unitSupply').value === 'otros' ? document.getElementById('unitOtherSupply').value : '',
            unit_amount: document.getElementById('unitAmountSupply').value,
            quantity: document.getElementById('cantidadSupply').value,
            warehouse_id: document.getElementById('almacenSupply').value || null,
            description: document.getElementById('descripcionSupply').value,
            category: document.getElementById('categoriaSupply').value || null,
            subcategory: document.getElementById('subcategoriaSupply').value || null
        };
        const resp = await fetch(url, {
            method,
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        if (!resp.ok) {
            const errorData = await resp.json().catch(() => ({}));
            let msg = 'Error guardando insumo';
            if (errorData && typeof errorData === 'object') {
                msg += ': ' + JSON.stringify(errorData);
            }
            throw new Error(msg);
        }
        await loadSupplies();
    } catch (error) {
        alert(error);
    }
}

// Eliminar insumo
async function deleteSupply(id) {
    if (!confirm('¿Seguro que deseas eliminar este insumo?')) return;
    try {
        const token = localStorage.getItem("accessToken");
        const resp = await fetch(`${API_URL}${id}/`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        if (!resp.ok) throw new Error('Error eliminando insumo');
        await loadSupplies();
    } catch (error) {
        alert('Error eliminando insumo');
    }
}


// Inicialización automática y manejo de formulario
if (document.getElementById('tablaSupplies')) {
    loadSupplies();
    loadWarehousesSelect('almacenSupply');
    loadCategoriesSelect('categoriaSupply').then(() => {
        // Cargar subcategorías si hay una categoría seleccionada
        const categoriaSelect = document.getElementById('categoriaSupply');
        const categoriaId = categoriaSelect.value;
        loadSubcategoriesSelect('subcategoriaSupply', categoriaId);
    });
    loadSuppliersSelect('proveedoresSupply');
    // Cargar subcategorías dependientes
    document.getElementById('categoriaSupply').addEventListener('change', function() {
        loadSubcategoriesSelect('subcategoriaSupply', this.value);
    });
    // Botón elegante para crear nueva categoría
    if (!document.getElementById('btnNuevaCategoria')) {
        const btnCat = document.createElement('button');
        btnCat.type = 'button';
        btnCat.id = 'btnNuevaCategoria';
        btnCat.className = 'btn btn-light btn-sm ms-2 d-inline-flex align-items-center gap-1 border shadow-sm';
        btnCat.innerHTML = '<span style="font-size:1.1em; color:#28a745;"><i class="fa fa-plus-circle"></i></span> <span style="color:#222;font-weight:500;">Nueva categoría</span>';
        btnCat.style.background = '#f8f9fa';
        btnCat.style.borderRadius = '6px';
        btnCat.style.boxShadow = '0 1px 2px rgba(0,0,0,0.04)';
        document.getElementById('categoriaSupply').parentNode.appendChild(btnCat);
        btnCat.addEventListener('click', showCategoryModal);
    }
    // Botón elegante para crear nueva subcategoría
    if (!document.getElementById('btnNuevaSubcategoria')) {
        const btnSubcat = document.createElement('button');
        btnSubcat.type = 'button';
        btnSubcat.id = 'btnNuevaSubcategoria';
        btnSubcat.className = 'btn btn-light btn-sm ms-2 d-inline-flex align-items-center gap-1 border shadow-sm';
        btnSubcat.innerHTML = '<span style="font-size:1.1em; color:#28a745;"><i class="fa fa-plus-circle"></i></span> <span style="color:#222;font-weight:500;">Nueva subcategoría</span>';
        btnSubcat.style.background = '#f8f9fa';
        btnSubcat.style.borderRadius = '6px';
        btnSubcat.style.boxShadow = '0 1px 2px rgba(0,0,0,0.04)';
        document.getElementById('subcategoriaSupply').parentNode.appendChild(btnSubcat);
        btnSubcat.addEventListener('click', showSubcategoryModal);
    }
    // Botón elegante para crear nuevo almacén
    if (!document.getElementById('btnNuevoAlmacen')) {
        const btnAlm = document.createElement('button');
        btnAlm.type = 'button';
        btnAlm.id = 'btnNuevoAlmacen';
        btnAlm.className = 'btn btn-light btn-sm ms-2 d-inline-flex align-items-center gap-1 border shadow-sm';
        btnAlm.innerHTML = '<span style="font-size:1.1em; color:#28a745;"><i class="fa fa-plus-circle"></i></span> <span style="color:#222;font-weight:500;">Nuevo almacén</span>';
        btnAlm.style.background = '#f8f9fa';
        btnAlm.style.borderRadius = '6px';
        btnAlm.style.boxShadow = '0 1px 2px rgba(0,0,0,0.04)';
        document.getElementById('almacenSupply').parentNode.appendChild(btnAlm);
        btnAlm.addEventListener('click', showWarehouseModal);
    }
// Modal para crear nueva categoría
function showCategoryModal() {
    let modal = document.getElementById('modalNuevaCategoria');
    if (!modal) {
        modal = document.createElement('div');
        modal.innerHTML = `
        <div class="modal fade" id="modalNuevaCategoria" tabindex="-1" aria-labelledby="modalNuevaCategoriaLabel" aria-hidden="true">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="modalNuevaCategoriaLabel">Crear nueva categoría</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
              </div>
              <div class="modal-body">
                <form id="formNuevaCategoria">
                  <div class="mb-3">
                    <label for="nombreNuevaCategoria" class="form-label">Nombre</label>
                    <input type="text" class="form-control" id="nombreNuevaCategoria" required>
                  </div>
                  <div class="mb-3">
                    <label for="descNuevaCategoria" class="form-label">Descripción</label>
                    <textarea class="form-control" id="descNuevaCategoria"></textarea>
                  </div>
                  <button type="submit" class="btn btn-success">Crear</button>
                </form>
              </div>
            </div>
          </div>
        </div>`;
        document.body.appendChild(modal);
    }
    const modalInstance = new bootstrap.Modal(document.getElementById('modalNuevaCategoria'));
    modalInstance.show();
    document.getElementById('formNuevaCategoria').onsubmit = async function(e) {
        e.preventDefault();
        const nombre = document.getElementById('nombreNuevaCategoria').value;
        const desc = document.getElementById('descNuevaCategoria').value;
        try {
            const token = localStorage.getItem("accessToken");
            const resp = await fetch(CATEGORY_API, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name: nombre, description: desc })
            });
            if (!resp.ok) throw new Error('Error creando categoría');
            modalInstance.hide();
            await loadCategoriesSelect('categoriaSupply');
            // Selecciona la nueva categoría automáticamente
            const nueva = await resp.json();
            document.getElementById('categoriaSupply').value = nueva.id;
            loadSubcategoriesSelect('subcategoriaSupply', nueva.id);
        } catch (error) {
            alert('Error creando categoría: ' + error);
        }
    };
}

// Modal para crear nueva subcategoría
// Modal para crear nuevo almacén
function showWarehouseModal() {
    let modal = document.getElementById('modalNuevoAlmacen');
    if (!modal) {
        modal = document.createElement('div');
        modal.innerHTML = `
        <div class="modal fade" id="modalNuevoAlmacen" tabindex="-1" aria-labelledby="modalNuevoAlmacenLabel" aria-hidden="true">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="modalNuevoAlmacenLabel">Crear nuevo almacén</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
              </div>
              <div class="modal-body">
                <form id="formNuevoAlmacen">
                  <div class="mb-3">
                    <label for="nombreNuevoAlmacen" class="form-label">Nombre</label>
                    <input type="text" class="form-control" id="nombreNuevoAlmacen" required>
                  </div>
                  <div class="mb-3">
                    <label for="descNuevoAlmacen" class="form-label">Descripción</label>
                    <textarea class="form-control" id="descNuevoAlmacen"></textarea>
                  </div>
                  <button type="submit" class="btn btn-success">Crear</button>
                </form>
              </div>
            </div>
          </div>
        </div>`;
        document.body.appendChild(modal);
    }
    const modalInstance = new bootstrap.Modal(document.getElementById('modalNuevoAlmacen'));
    modalInstance.show();
    document.getElementById('formNuevoAlmacen').onsubmit = async function(e) {
        e.preventDefault();
        const nombre = document.getElementById('nombreNuevoAlmacen').value;
        const desc = document.getElementById('descNuevoAlmacen').value;
        try {
            const token = localStorage.getItem("accessToken");
            const resp = await fetch(WAREHOUSE_API, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name: nombre, description: desc })
            });
            if (!resp.ok) throw new Error('Error creando almacén');
            modalInstance.hide();
            await loadWarehousesSelect('almacenSupply');
            // Selecciona el nuevo almacén automáticamente
            const nuevo = await resp.json();
            document.getElementById('almacenSupply').value = nuevo.id;
        } catch (error) {
            alert('Error creando almacén: ' + error);
        }
    };
}
function showSubcategoryModal() {
    let modal = document.getElementById('modalNuevaSubcategoria');
    if (!modal) {
        modal = document.createElement('div');
        // Select de categoría padre
        let categoriasHtml = '<select class="form-select" id="categoriaPadreSubcat" required style="margin-bottom:10px;"><option value="">Seleccione categoría...</option>';
        const categoriaSelect = document.getElementById('categoriaSupply');
        Array.from(categoriaSelect.options).forEach(opt => {
            // Solo agrega opciones con valor numérico (ID de categoría)
            if (opt.value && !isNaN(opt.value)) {
                categoriasHtml += `<option value="${opt.value}"${opt.selected ? ' selected' : ''}>${opt.textContent}</option>`;
            }
        });
        categoriasHtml += '</select>';
        modal.innerHTML = `
        <div class="modal fade" id="modalNuevaSubcategoria" tabindex="-1" aria-labelledby="modalNuevaSubcategoriaLabel" aria-hidden="true">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="modalNuevaSubcategoriaLabel">Crear nueva subcategoría</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
              </div>
              <div class="modal-body">
                <form id="formNuevaSubcategoria">
                  <div class="mb-3">
                    <label for="nombreNuevaSubcategoria" class="form-label">Nombre</label>
                    <input type="text" class="form-control" id="nombreNuevaSubcategoria" required>
                  </div>
                  <div class="mb-3">
                    <label for="descNuevaSubcategoria" class="form-label">Descripción</label>
                    <textarea class="form-control" id="descNuevaSubcategoria"></textarea>
                  </div>
                  <div class="mb-3">
                    <label for="categoriaPadreSubcat" class="form-label">Categoría padre</label>
                    ${categoriasHtml}
                  </div>
                  <button type="submit" class="btn btn-success">Crear</button>
                </form>
              </div>
            </div>
          </div>
        </div>`;
        document.body.appendChild(modal);
    }
    const modalInstance = new bootstrap.Modal(document.getElementById('modalNuevaSubcategoria'));
    modalInstance.show();
    document.getElementById('formNuevaSubcategoria').onsubmit = async function(e) {
        e.preventDefault();
        const nombre = document.getElementById('nombreNuevaSubcategoria').value;
        const desc = document.getElementById('descNuevaSubcategoria').value;
        const categoriaId = document.getElementById('categoriaPadreSubcat').value;
        // Validar que el ID sea numérico y exista
        if (!categoriaId || isNaN(categoriaId)) {
            alert('Primero selecciona una categoría válida');
            return;
        }
        try {
            const token = localStorage.getItem("accessToken");
            const resp = await fetch(SUBCATEGORY_API, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name: nombre, description: desc, category_id: parseInt(categoriaId) })
            });
            if (!resp.ok) {
                let msg = 'Error creando subcategoría';
                try {
                    const errorData = await resp.json();
                    msg += ': ' + JSON.stringify(errorData);
                } catch {}
                alert(msg);
                return;
            }
            modalInstance.hide();
            await loadSubcategoriesSelect('subcategoriaSupply', categoriaId);
            // Selecciona la nueva subcategoría automáticamente
            const nueva = await resp.json();
            document.getElementById('subcategoriaSupply').value = nueva.id;
            // Actualiza el select de categoría en el modal principal si se creó una nueva categoría
            document.getElementById('categoriaSupply').value = categoriaId;
        } catch (error) {
            alert('Error creando subcategoría: ' + error);
        }
    };
}
    // Botón elegante para crear insumo nuevo (compacto y moderno, sin azul)
    const btnNuevoSupply = document.getElementById('btnNuevoSupply');
    if (btnNuevoSupply) {
        btnNuevoSupply.className = 'btn btn-success btn-sm d-inline-flex align-items-center gap-1 shadow-sm';
        btnNuevoSupply.innerHTML = '<span style="font-size:1.1em;"><i class="fa fa-plus-circle"></i></span> <span style="font-weight:500;">Nuevo insumo</span>';
        btnNuevoSupply.title = 'Crear nuevo insumo';
        btnNuevoSupply.style.minWidth = 'auto';
        btnNuevoSupply.style.padding = '0.375rem 0.75rem';
        btnNuevoSupply.style.background = '#28a745';
        btnNuevoSupply.style.border = 'none';
        btnNuevoSupply.style.color = '#fff';
        btnNuevoSupply.style.borderRadius = '6px';
        btnNuevoSupply.addEventListener('click', function() {
            document.getElementById('supplyForm').reset();
            document.getElementById('supplyId').value = '';
            document.getElementById('modalTitleText').textContent = 'Nuevo Insumo';
            // Recargar almacenes y categorías cada vez que se abre el modal
            loadWarehousesSelect('almacenSupply');
            loadCategoriesSelect('categoriaSupply');
            document.getElementById('subcategoriaSupply').innerHTML = '<option value="">Seleccione...</option>';
        });
    }

    // Guardar insumo (crear o editar)
    document.getElementById('supplyForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const token = localStorage.getItem("accessToken");
        const id = document.getElementById('supplyId').value || null;
        const url = id ? `${API_URL}${id}/` : API_URL;
        const method = id ? 'PUT' : 'POST';
        const formData = new FormData();
        formData.append('name', document.getElementById('nombreSupply').value);
        formData.append('unit_value', document.getElementById('valorSupply').value);
        formData.append('unit', document.getElementById('unitSupply').value);
        formData.append('unit_custom', document.getElementById('unitSupply').value === 'otros' ? document.getElementById('unitOtherSupply').value : '');
        formData.append('unit_amount', document.getElementById('unitAmountSupply').value);
        formData.append('quantity', document.getElementById('cantidadSupply').value);
        formData.append('warehouse_id', document.getElementById('almacenSupply').value || '');
        formData.append('description', document.getElementById('descripcionSupply').value);
        formData.append('notes', document.getElementById('notasSupply').value);
        formData.append('category', document.getElementById('categoriaSupply').value || '');
        formData.append('subcategory', document.getElementById('subcategoriaSupply').value || '');
        // Proveedores (múltiple)
        const proveedoresSelect = document.getElementById('proveedoresSupply');
        const selectedProveedores = Array.from(proveedoresSelect.selectedOptions).map(opt => opt.value);
        selectedProveedores.forEach(id => formData.append('suppliers', id));
        // Imagen y adjunto
        const imagen = document.getElementById('imagenSupply').files[0];
        if (imagen) formData.append('image', imagen);
        const adjunto = document.getElementById('adjuntoSupply').files[0];
        if (adjunto) formData.append('attachments', adjunto);
        try {
            const resp = await fetch(url, {
                method,
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });
            if (!resp.ok) {
                const errorData = await resp.json().catch(() => ({}));
                let msg = 'Error guardando insumo';
                if (errorData && typeof errorData === 'object') {
                    msg += ': ' + JSON.stringify(errorData);
                }
                throw new Error(msg);
            }
            await loadSupplies();
            const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('supplyModal'));
            modal.hide();
            this.reset();
            document.getElementById('supplyId').value = '';
            document.getElementById('modalTitleText').textContent = 'Nuevo Insumo';
        } catch (error) {
            alert(error);
        }
    });

    // Delegación de eventos para editar/eliminar con verificación
    document.getElementById('tablaSupplies').addEventListener('click', async function(e) {
        const btn = e.target.closest('button[data-action]');
        if (!btn) return;
        const action = btn.getAttribute('data-action');
        const id = btn.getAttribute('data-id');
        if (action === 'edit') {
            showVerifyModal(async () => {
                await editSupply(id);
            });
        } else if (action === 'delete') {
            showVerifyModal(async () => {
                await deleteSupply(id);
            });
        }
    });
}

// Mostrar modal de verificación y ejecutar callback si es correcto
function showVerifyModal(onVerified) {
    const verifyModal = new bootstrap.Modal(document.getElementById('verifyUserModal'));
    const verifyForm = document.getElementById('verifyUserForm');
    verifyForm.reset();
    verifyModal.show();
    const submitHandler = async function(e) {
        e.preventDefault();
        const password = document.getElementById('verifyPassword').value;
        // Aquí deberías hacer una petición a tu backend para verificar la contraseña
        // Por ahora, simula éxito si la contraseña no está vacía
        if (password.length > 0) {
            verifyModal.hide();
            verifyForm.removeEventListener('submit', submitHandler);
            await onVerified();
        } else {
            alert('Contraseña incorrecta');
        }
    };
    verifyForm.addEventListener('submit', submitHandler);
}

// Editar insumo: cargar datos en el modal
async function editSupply(id) {
    try {
        const token = localStorage.getItem("accessToken");
        const resp = await fetch(`${API_URL}${id}/`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        if (!resp.ok) throw new Error('No se pudo cargar el insumo');
        const s = await resp.json();
        document.getElementById('supplyId').value = s.id;
        document.getElementById('nombreSupply').value = s.name;
        document.getElementById('valorSupply').value = s.unit_value;
        document.getElementById('cantidadSupply').value = s.quantity;
        document.getElementById('almacenSupply').value = s.warehouse || '';
        document.getElementById('descripcionSupply').value = s.description || '';
        // Unidad y unidad personalizada
        document.getElementById('unitSupply').value = s.unit;
        if (s.unit === 'otros') {
            document.getElementById('unitOtherSupply').style.display = 'block';
            document.getElementById('unitOtherSupply').value = s.unit_custom || '';
        } else {
            document.getElementById('unitOtherSupply').style.display = 'none';
            document.getElementById('unitOtherSupply').value = '';
        }
        document.getElementById('unitAmountSupply').value = s.unit_amount;
        // Cargar categorías y subcategorías y seleccionar
        await loadCategoriesSelect('categoriaSupply');
        document.getElementById('categoriaSupply').value = s.category || '';
        await loadSubcategoriesSelect('subcategoriaSupply', s.category);
        document.getElementById('subcategoriaSupply').value = s.subcategory || '';
        document.getElementById('modalTitleText').textContent = 'Editar Insumo';
        const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('supplyModal'));
        modal.show();
    } catch (error) {
        alert('No se pudo cargar el insumo');
    }
}

