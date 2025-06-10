const BASE_URL = `http://${window.location.hostname}:8000/api/RRHH`;

// Manejar el envío del formulario
async function handleEmployeeSubmit(event) {
    event.preventDefault(); // Evitar el comportamiento predeterminado del formulario

    const cedula = document.getElementById("cedula-input").value.trim();
    const nombres = document.getElementById("nombres-input").value.trim();
    const apellidos = document.getElementById("apellidos-input").value.trim();
    const direccion = document.getElementById("direccion-input").value.trim();
    const telefono = document.getElementById("telefono-input").value.trim();
    const email = document.getElementById("email-input").value.trim();
    const password = document.getElementById("password-input").value.trim();
    const departamento = document.getElementById("departamento-select").value;
    const posicion = document.getElementById("posicion-select").value;
    const isStaff = document.getElementById("is_staff").checked;

    const token = localStorage.getItem("accessToken");

    if (!token) {
        alert("No se encontró un token de autenticación. Por favor, inicia sesión.");
        return;
    }

    const data = {
        cedula,
        nombres,
        apellidos,
        direccion,
        telefono,
        email,
        password,
        departamento,
        posicion,
        is_staff: isStaff,
    };

    try {
        const response = await axios.post(`${BASE_URL}/empleados/`, data, {
            headers: { "Authorization": `Bearer ${token}` },
        });
        alert("Empleado creado con éxito");
        window.location.href = "/templates/employees/RRHH-dashboard.html"; // Redirigir al dashboard
    } catch (error) {
        console.error("Error al crear el empleado:", error);
        alert("Ocurrió un error al crear el empleado. Verifica los datos e inténtalo nuevamente.");
    }
}

// Cargar opciones dinámicas para departamentos y posiciones
async function cargarOpciones() {
    const token = localStorage.getItem("accessToken");

    if (!token) {
        alert("No se encontró un token de autenticación. Por favor, inicia sesión.");
        return;
    }

    try {
        const [departamentosResponse, posicionesResponse] = await Promise.all([
            axios.get(`${BASE_URL}/departamentos/`, { headers: { "Authorization": `Bearer ${token}` } }),
            axios.get(`${BASE_URL}/posiciones/`, { headers: { "Authorization": `Bearer ${token}` } }),
        ]);

        const departamentoSelect = document.getElementById("departamento-select");
        const posicionSelect = document.getElementById("posicion-select");

        // Llenar las opciones de departamentos
        departamentosResponse.data.forEach(departamento => {
            const option = document.createElement("option");
            option.value = departamento.id;
            option.textContent = departamento.name;
            departamentoSelect.appendChild(option);
        });

        // Llenar las opciones de posiciones
        posicionesResponse.data.forEach(posicion => {
            const option = document.createElement("option");
            option.value = posicion.id;
            option.textContent = posicion.name;
            posicionSelect.appendChild(option);
        });
    } catch (error) {
        console.error("Error al cargar las opciones:", error);
        alert("Ocurrió un error al cargar las opciones. Intenta nuevamente.");
    }
}

// Ejecutar la carga de opciones al cargar la página
document.addEventListener("DOMContentLoaded", cargarOpciones);