// labores.js
// Script para gestionar el CRUD de labores agrícolas en el frontend Agrotech
// Usa axios para las peticiones y sigue el estilo visual del dashboard

// Asegúrate de tener axios incluido en tu proyecto (CDN o npm)
// <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>

document.addEventListener("DOMContentLoaded", () => {
    cargarLabores();
});

function cargarLabores() {
    const token = localStorage.getItem("accessToken");
    if (!token) {
        window.location.href = "/templates/authentication/login.html";
        return;
    }
    axios.get(`http://${window.location.hostname}:8000/api/labores/labores/`, {
        headers: { "Authorization": `Bearer ${token}`, }
    })
    .then(response => {
        renderTablaLabores(response.data);
    })
    .catch(error => {
        if (error.response && error.response.status === 401) {
            localStorage.removeItem("accessToken");
            localStorage.removeItem("refreshToken");
            window.location.href = "/templates/authentication/login.html";
        } else {
            alert("Error al cargar labores: " + error);
        }
    });
}

function renderTablaLabores(labores) {
    const tbody = document.getElementById("labores-tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    labores.forEach(labor => {
        const tr = document.createElement("tr");
        const parcelas = labor.parcelas_nombres ? labor.parcelas_nombres.join(", ") : (labor.parcelas?.length || 0);
        const responsables = labor.responsables_nombres ? labor.responsables_nombres.join(", ") : (labor.responsables?.length || 0);
        tr.innerHTML = `
            <td>${labor.nombre}</td>
            <td>${labor.tipo}</td>
            <td><span class="badge badge-${getEstadoColor(labor.estado)}">${labor.estado}</span></td>
            <td>${labor.fecha_programada}</td>
            <td>${labor.fecha_realizada || '-'}</td>
            <td>${parcelas}</td>
            <td>${responsables}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="verLabor(${labor.id})">Ver</button>
                <button class="btn btn-sm btn-warning" onclick="editarLabor(${labor.id})">Editar</button>
                <button class="btn btn-sm btn-danger" onclick="eliminarLabor(${labor.id})">Eliminar</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function getEstadoColor(estado) {
    switch (estado) {
        case "pendiente": return "secondary";
        case "en_progreso": return "info";
        case "completada": return "success";
        case "cancelada": return "danger";
        default: return "light";
    }
}

// Funciones stub para ver, editar, eliminar (puedes expandirlas luego)
function verLabor(id) {
    // (Opcional) Mostrar detalles en un modal de solo lectura
}

function editarLabor(id) {
    const token = localStorage.getItem("accessToken");
    axios.get(`http://${window.location.hostname}:8000/api/labores/labores/${id}/`, {
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(res => {
        const labor = res.data;
        document.getElementById("laborId").value = labor.id;
        document.getElementById("nombreLabor").value = labor.nombre;
        document.getElementById("tipoLabor").value = labor.tipo;
        document.getElementById("estadoLabor").value = labor.estado;
        document.getElementById("fechaProgramada").value = labor.fecha_programada;
        document.getElementById("fechaRealizada").value = labor.fecha_realizada || "";
        // Seleccionar parcelas y responsables
        setTimeout(() => {
            const parcelasSelect = document.getElementById("parcelasLabor");
            const responsablesSelect = document.getElementById("responsablesLabor");
            Array.from(parcelasSelect.options).forEach(opt => {
                opt.selected = labor.parcelas.includes(parseInt(opt.value));
            });
            Array.from(responsablesSelect.options).forEach(opt => {
                opt.selected = labor.responsables.includes(parseInt(opt.value));
            });
        }, 200);
        document.getElementById("laborModalLabel").textContent = "Editar Labor";
        const modal = new bootstrap.Modal(document.getElementById('laborModal'));
        modal.show();
    });
}

function eliminarLabor(id) {
    if (!confirm("¿Seguro que deseas eliminar esta labor?")) return;
    const token = localStorage.getItem("accessToken");
    axios.delete(`http://${window.location.hostname}:8000/api/labores/labores/${id}/`, {
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(() => {
        cargarLabores();
    })
    .catch(err => {
        alert("Error al eliminar labor: " + (err.response?.data?.detail || err));
    });
}
