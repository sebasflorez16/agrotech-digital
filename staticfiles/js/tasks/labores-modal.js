// labores-modal.js
// Lógica para el modal de alta/edición de labores

document.addEventListener("DOMContentLoaded", () => {
    cargarOpcionesResponsables();
    
    // Abrir modal para nueva labor
    document.getElementById("btnNuevaLabor").addEventListener("click", () => {
        limpiarFormularioLabor();
        document.getElementById("laborModalLabel").textContent = "Nueva Labor";
    });

    // Guardar labor (alta o edición)
    document.getElementById("laborForm").addEventListener("submit", function(e) {
        e.preventDefault();
        guardarLabor();
    });
});

function cargarOpcionesResponsables() {
    const token = localStorage.getItem("accessToken");
    // Usar el mismo hostname y puerto del frontend, pero forzar el puerto 8000 para el backend
    let backendHost = window.location.hostname;
    // Si el frontend corre en 3000, cambiar a 8000
    let backendPort = window.location.port === "3000" ? "8000" : window.location.port;
    const apiUrl = `${window.location.protocol}//${backendHost}:${backendPort}/api/RRHH/empleados/`;
    axios.get(apiUrl, {
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(res => {
        const select = document.getElementById("responsablesLabor");
        select.innerHTML = "";
        res.data.forEach(emp => {
            const opt = document.createElement("option");
            opt.value = emp.id;
            opt.textContent = emp.first_name + ' ' + emp.last_name;
            select.appendChild(opt);
        });
    })
    .catch(err => {
        const select = document.getElementById("responsablesLabor");
        select.innerHTML = "<option disabled>No se pudo cargar empleados</option>";
        console.error("Error cargando empleados:", err);
    });
}

function limpiarFormularioLabor() {
    document.getElementById("laborId").value = "";
    document.getElementById("nombreLabor").value = "";
    document.getElementById("tipoLabor").value = "";
    document.getElementById("estadoLabor").value = "pendiente";
    document.getElementById("fechaProgramada").value = "";
    document.getElementById("fechaRealizada").value = "";
    document.getElementById("responsablesLabor").selectedIndex = -1;
}

function guardarLabor() {
    const token = localStorage.getItem("accessToken");
    const id = document.getElementById("laborId").value;
    const data = {
        nombre: document.getElementById("nombreLabor").value,
        tipo: document.getElementById("tipoLabor").value,
        estado: document.getElementById("estadoLabor").value,
        fecha_programada: document.getElementById("fechaProgramada").value,
        fecha_realizada: document.getElementById("fechaRealizada").value || null,
        responsables: Array.from(document.getElementById("responsablesLabor").selectedOptions).map(o => o.value)
    };
    const url = `http://${window.location.hostname}:8000/api/labores/labores/` + (id ? id + '/' : '');
    const method = id ? 'put' : 'post';
    axios({
        method,
        url,
        data,
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(() => {
        cargarLabores();
        document.querySelector('#laborModal .btn-close').click();
    })
    .catch(err => {
        alert("Error al guardar labor: " + (err.response?.data?.detail || err));
    });
}
