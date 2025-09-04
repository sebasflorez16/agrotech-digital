// Definir la URL base para la API
const BASE_URL = window.ApiUrls ? window.ApiUrls.rrhh() : `${window.location.protocol}//${window.location.hostname}:8000/api/RRHH`;

// Ejecutar el código cuando el DOM esté completamente cargado
document.addEventListener("DOMContentLoaded", function () {
    console.log("Página de empleados cargada. Obteniendo datos...");
    cargarEmpleados(); // Llamar a la función automáticamente para cargar los empleados

    // Agregar evento al botón para crear empleados
    const btnCrearEmpleados = document.getElementById("btnCrearEmpleados");
    if (btnCrearEmpleados) {
        btnCrearEmpleados.addEventListener("click", function () {
            window.location.href = "/templates/forms/employee-create-form.html";
        });
    }

    // Agregar evento al formulario para crear un nuevo empleado
    const employeeForm = document.getElementById("employeeForm");
    if (employeeForm) {
        employeeForm.addEventListener("submit", function (event) {
            event.preventDefault();
            crearEmpleado();
        });
    }
});

// Función para cargar los empleados desde la API
function cargarEmpleados() {
    // Obtener el token de autenticación del almacenamiento local
    const token = localStorage.getItem("accessToken");

    // Si no hay token, redirigir al usuario a la página de login
    if (!token) {
        console.warn("⚠️ No hay token, redirigiendo al login...");
        window.location.href = "/templates/authentication/login.html";
        return;
    }

    console.log("🔍 Token encontrado:", token);

    // Hacer una solicitud GET a la API para obtener los empleados
    axios.get(`${BASE_URL}/employees/`, {
        headers: { "Authorization": `Bearer ${token}` } // Incluir el token en los encabezados de la solicitud
    })
    .then(response => {
        console.log("✅ Respuesta de la API:", response.data);
        mostrarEmpleados(response.data); // Llamar a la función para mostrar los empleados en la tabla
    })
    .catch(error => {
        console.error("❌ Error al obtener empleados:", error);
    });
}

// Función para mostrar los empleados en la tabla
function mostrarEmpleados(empleados) {
    // Obtener el cuerpo de la tabla donde se mostrarán los empleados
    const tableBody = document.getElementById("employee-table-body");
    if (!tableBody) {
        console.error("❌ Error: No se encontró la tabla en el DOM.");
        return;
    }

    // Limpiar la tabla antes de agregar nuevos datos
    tableBody.innerHTML = "";

    // Si no hay empleados, mostrar un mensaje en la tabla
    if (empleados.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="7" class="text-center">No hay empleados registrados.</td></tr>`;
        return;
    }

    // Iterar sobre los empleados y crear filas en la tabla para cada uno
    empleados.forEach((employee, index) => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <th scope="row">${index + 1}</th>
            <td>${employee.first_name}</td>
            <td>${employee.last_name}</td>
            <td>${employee.email || "No registrado"}</td>
            <td>${employee.phone || "No registrado"}</td>
            <td>${employee.department_name || "No asignado"}</td>
            <td>${employee.position_name || "No asignado"}</td>
            <td>
                <button class="btn btn-sm btn-primary me-2" title="Editar" onclick="editEmployee(${employee.id})">
                    <i class="mdi mdi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-danger" title="Eliminar" onclick="deleteEmployee(${employee.id})">
                    <i class="mdi mdi-delete"></i>
                </button>
            </td>
        `;
        tableBody.appendChild(row); // Agregar la fila a la tabla
    });
}


