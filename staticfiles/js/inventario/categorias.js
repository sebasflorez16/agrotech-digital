// categorias.js - CRUD visual para categorías y subcategorías de inventario
const API_BASE = `http://${window.location.hostname}:8000/api/inventario/`;
const token = localStorage.getItem("accessToken");

// Utilidades
function showModal(id) { new bootstrap.Modal(document.getElementById(id)).show(); }
function hideModal(id) {
    const modal = document.getElementById(id);
    // Quitar el atributo inert antes de mostrar
    modal.removeAttribute('inert');
    bootstrap.Modal.getInstance(modal).hide();
    // Al cerrar, poner el foco en el botón de abrir
    if(id === 'modalCategoria') {
        setTimeout(() => {
            document.getElementById('btnNuevaCategoria').focus();
        }, 300);
    }
}
// Al mostrar el modal, quitar el atributo inert
document.addEventListener('shown.bs.modal', function(e) {
    if(e.target && e.target.id === 'modalCategoria') {
        e.target.removeAttribute('inert');
    }
});
// Al ocultar el modal, poner el atributo inert
document.addEventListener('hidden.bs.modal', function(e) {
    if(e.target && e.target.id === 'modalCategoria') {
        e.target.setAttribute('inert', '');
    }
});

// CATEGORÍAS
async function cargarCategorias() {
    const resp = await fetch(`${API_BASE}categories/`, { headers: { 'Authorization': `Bearer ${token}` } });
    const data = await resp.json();
    const tbody = document.querySelector('#tablaCategorias tbody');
    tbody.innerHTML = '';
    data.forEach(cat => {
        const tr = document.createElement('tr');
        // Escapar comillas y caracteres especiales para evitar errores de sintaxis
        const safeName = String(cat.name).replace(/'/g, "&#39;").replace(/"/g, '&quot;');
        const safeDesc = String(cat.description || '').replace(/'/g, "&#39;").replace(/"/g, '&quot;');
        tr.innerHTML = `
            <td>${cat.name}</td>
            <td>${cat.description || ''}</td>
            <td class="action-btns">
                <button class="btn btn-sm btn-outline-primary" onclick="editarCategoria(${cat.id}, '${safeName}', '${safeDesc}')"><i class="fa fa-edit"></i></button>
                <button class="btn btn-sm btn-outline-danger" onclick="eliminarCategoria(${cat.id})"><i class="fa fa-trash"></i></button>
            </td>`;
        tbody.appendChild(tr);
    });
    cargarCategoriasEnSelect();
}

async function crearCategoria(e) {
    e.preventDefault();
    const id = document.getElementById('categoriaId').value;
    const nombre = document.getElementById('categoriaNombre').value;
    const descripcion = document.getElementById('categoriaDescripcion').value;
    const method = id ? 'PUT' : 'POST';
    const url = id ? `${API_BASE}categories/${id}/` : `${API_BASE}categories/`;
    await fetch(url, {
        method,
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: nombre, description: descripcion })
    });
    hideModal('modalCategoria');
    document.getElementById('formCategoria').reset();
    document.getElementById('categoriaId').value = '';
    cargarCategorias();
}

function editarCategoria(id, nombre, descripcion) {
    document.getElementById('categoriaId').value = id;
    document.getElementById('categoriaNombre').value = nombre;
    document.getElementById('categoriaDescripcion').value = descripcion;
    showModal('modalCategoria');
}

async function eliminarCategoria(id) {
    if (!confirm('¿Eliminar esta categoría?')) return;
    await fetch(`${API_BASE}categories/${id}/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    cargarCategorias();
}

// SUBCATEGORÍAS
async function cargarSubcategorias() {
    const resp = await fetch(`${API_BASE}subcategories/`, { headers: { 'Authorization': `Bearer ${token}` } });
    const data = await resp.json();
    const tbody = document.querySelector('#tablaSubcategorias tbody');
    tbody.innerHTML = '';
    data.forEach(sub => {
        const tr = document.createElement('tr');
        // Mostrar correctamente la relación de categoría
        let catName = '-';
        let catId = '';
        if (sub.category && (typeof sub.category === 'object')) {
            catName = sub.category.name || '-';
            catId = sub.category.id || '';
        } else if (sub.category && typeof sub.category === 'string') {
            catName = sub.category;
            catId = sub.category;
        }
        // Escapar comillas y caracteres especiales
        const safeName = String(sub.name).replace(/'/g, "&#39;").replace(/"/g, '&quot;');
        const safeDesc = String(sub.description || '').replace(/'/g, "&#39;").replace(/"/g, '&quot;');
        tr.innerHTML = `
            <td>${sub.name}</td>
            <td>${catName}</td>
            <td class="action-btns">
                <button class="btn btn-sm btn-outline-primary" onclick="editarSubcategoria(${sub.id}, '${safeName}', '${safeDesc}', '${catId}')"><i class="fa fa-edit"></i></button>
                <button class="btn btn-sm btn-outline-danger" onclick="eliminarSubcategoria(${sub.id})"><i class="fa fa-trash"></i></button>
            </td>`;
        tbody.appendChild(tr);
    });
}

async function crearSubcategoria(e) {
    e.preventDefault();
    const id = document.getElementById('subcategoriaId').value;
    const nombre = document.getElementById('subcategoriaNombre').value;
    const descripcion = document.getElementById('subcategoriaDescripcion').value;
    const categoria = document.getElementById('subcategoriaCategoria').value;
    if (!categoria) {
        alert('Selecciona una categoría válida');
        return;
    }
    const method = id ? 'PUT' : 'POST';
    const url = id ? `${API_BASE}subcategories/${id}/` : `${API_BASE}subcategories/`;
    await fetch(url, {
        method,
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: nombre, description: descripcion, category_id: parseInt(categoria) })
    });
    hideModal('modalSubcategoria');
    document.getElementById('formSubcategoria').reset();
    document.getElementById('subcategoriaId').value = '';
    cargarSubcategorias();
}

function editarSubcategoria(id, nombre, descripcion, categoriaId) {
    document.getElementById('subcategoriaId').value = id;
    document.getElementById('subcategoriaNombre').value = nombre;
    document.getElementById('subcategoriaDescripcion').value = descripcion;
    document.getElementById('subcategoriaCategoria').value = categoriaId;
    showModal('modalSubcategoria');
}

async function eliminarSubcategoria(id) {
    if (!confirm('¿Eliminar esta subcategoría?')) return;
    await fetch(`${API_BASE}subcategories/${id}/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    cargarSubcategorias();
}

// Utilidad para cargar categorías en el select de subcategoría
async function cargarCategoriasEnSelect() {
    const resp = await fetch(`${API_BASE}categories/`, { headers: { 'Authorization': `Bearer ${token}` } });
    const data = await resp.json();
    const select = document.getElementById('subcategoriaCategoria');
    select.innerHTML = '';
    data.forEach(cat => {
        const opt = document.createElement('option');
        opt.value = cat.id;
        opt.textContent = cat.name;
        select.appendChild(opt);
    });
}

// Eventos
window.editarCategoria = editarCategoria;
window.eliminarCategoria = eliminarCategoria;
window.editarSubcategoria = editarSubcategoria;
window.eliminarSubcategoria = eliminarSubcategoria;

document.getElementById('btnNuevaCategoria').addEventListener('click', () => {
    document.getElementById('formCategoria').reset();
    document.getElementById('categoriaId').value = '';
    showModal('modalCategoria');
});
document.getElementById('btnNuevaSubcategoria').addEventListener('click', () => {
    document.getElementById('formSubcategoria').reset();
    document.getElementById('subcategoriaId').value = '';
    cargarCategoriasEnSelect();
    showModal('modalSubcategoria');
});
document.getElementById('formCategoria').addEventListener('submit', crearCategoria);
document.getElementById('formSubcategoria').addEventListener('submit', crearSubcategoria);

document.addEventListener('DOMContentLoaded', () => {
    cargarCategorias();
    cargarSubcategorias();
});
