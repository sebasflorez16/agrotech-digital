// maquinaria.js - Gestión avanzada de maquinaria agrícola (CRUD, multi-tenant, modular)

const API_URL = `http://${window.location.hostname}:8000/api/inventario/machinery/`;
const token = localStorage.getItem("accessToken");

// Cargar maquinaria y renderizar tabla
async function loadMaquinaria() {
    try {
        const resp = await fetch(API_URL, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        if (!resp.ok) throw new Error('Error cargando maquinaria');
        const maquinaria = await resp.json();
        const tbody = document.getElementById('tablaMaquinaria').querySelector('tbody');
        tbody.innerHTML = '';
        maquinaria.forEach(m => {
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
                    <button class="btn btn-sm btn-outline-primary me-1" data-action="edit" data-id="${m.id}" title="Editar"><i class="fa fa-edit"></i></button>
                    <button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="${m.id}" title="Eliminar"><i class="fa fa-trash"></i></button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        alert('Error cargando maquinaria');
    }
}

// Guardar maquinaria (crear o editar)
document.getElementById('maquinariaForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const id = document.getElementById('maquinariaId').value || null;
    const formData = new FormData();
    formData.append('name', document.getElementById('maquinariaNombre').value);
    formData.append('brand', document.getElementById('maquinariaMarca').value);
    formData.append('model', document.getElementById('maquinariaModelo').value);
    formData.append('serial_number', document.getElementById('maquinariaSerial').value);
    formData.append('year', document.getElementById('maquinariaAnio').value);
    formData.append('warehouse_id', document.getElementById('maquinariaAlmacen').value);
    formData.append('category', document.getElementById('maquinariaCategoria').value);
    formData.append('subcategory', document.getElementById('maquinariaSubcategoria').value);
    formData.append('description', document.getElementById('maquinariaDescripcion').value);
    const imageInput = document.getElementById('machineryImage');
    if (imageInput.files[0]) {
        formData.append('image', imageInput.files[0]);
    }
    await saveMaquinaria(formData, id);
    // Cerrar modal
    const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('maquinariaModal'));
    modal.hide();
    this.reset();
    document.getElementById('maquinariaId').value = '';
    document.getElementById('modalTitleMaquinaria').textContent = 'Nueva Maquinaria';
    document.getElementById('machineryImagePreview').src = '';
});

async function saveMaquinaria(formData, id=null) {
    try {
        const url = id ? `${API_URL}${id}/` : API_URL;
        const method = id ? 'PUT' : 'POST';
        const resp = await fetch(url, {
            method,
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        if (!resp.ok) throw new Error('Error guardando maquinaria');
        await loadMaquinaria();
    } catch (error) {
        alert('Error guardando maquinaria');
    }
}

// Eliminar maquinaria
async function deleteMaquinaria(id) {
    if (!confirm('¿Seguro que deseas eliminar esta maquinaria?')) return;
    try {
        const resp = await fetch(`${API_URL}${id}/`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!resp.ok) throw new Error('Error eliminando maquinaria');
        await loadMaquinaria();
    } catch (error) {
        alert('Error eliminando maquinaria');
    }
}

// Inicialización automática
if (document.getElementById('tablaMaquinaria')) {
    loadMaquinaria();
}
// Previsualización de imagen
if (document.getElementById('machineryImage')) {
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
}
