

// Definir la URL base de la API, utilizando la dirección del servidor dinámicamente
const LIST_HANDLER_BASE_UR = `http://${window.location.hostname}:8000/api/RRHH`;

// Función para actualizar los contadores
async function actualizarContadores(token) {
    try {
        // Realizar solicitudes para obtener los conteos
        const [empleadosResponse, departamentosResponse, posicionesResponse] = await Promise.all([
            axios.get(`${LIST_HANDLER_BASE_UR}/empleados/`, { headers: { "Authorization": `Bearer ${token}` } }),
            axios.get(`${LIST_HANDLER_BASE_UR}/departamentos/`, { headers: { "Authorization": `Bearer ${token}` } }),
            axios.get(`${LIST_HANDLER_BASE_UR}/posiciones/`, { headers: { "Authorization": `Bearer ${token}` } })
        ]);

        // Actualizar los contadores en el DOM
        document.getElementById("employeeCount").textContent = empleadosResponse.data.length;
        document.getElementById("departmentCount").textContent = departamentosResponse.data.length;
        document.getElementById("positionCount").textContent = posicionesResponse.data.length;
    } catch (error) {
        console.error("Error al actualizar los contadores:", error);
        alert("No se pudieron actualizar los contadores. Intenta nuevamente.");
    }
}


// Función para cargar datos en las tablas

async function cargarDatos(tipo) {
    const token = localStorage.getItem("accessToken");

    if (!token) {
        console.warn("⚠️ No hay token, redirigiendo al login...");
        window.location.href = "/templates/authentication/login.html";
        return;
    }

    try {
        const response = await axios.get(`${LIST_HANDLER_BASE_UR}/${tipo}/`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        const tablaBody = document.getElementById(`tabla-${tipo}-body`);
        const tablaHead = document.getElementById(`tabla-${tipo}-head`);

        if (!tablaBody || !tablaHead) {
            console.error(`Elemento tabla-${tipo}-body o tabla-${tipo}-head no encontrado en el DOM.`);
            return;
        }

        // Limpiar la tabla antes de agregar nuevos datos
        tablaBody.innerHTML = "";
        tablaHead.innerHTML = "";

        // Configurar las columnas según el tipo
        switch (tipo) {
            case "empleados":
                tablaHead.innerHTML = `
                    <tr>
                        <th>ID</th>
                        <th>Nombre</th>
                        <th>Email</th>
                        <th>Teléfono</th>
                        <th>Departamento</th>
                        <th>Posición</th>
                        <th>Acciones</th>
                    </tr>`;
                response.data.forEach(item => {
                    const nombre = `${item.first_name || "No disponible"} ${item.last_name || ""}`.trim();
                    tablaBody.innerHTML += `
                        <tr>
                            <td>${item.id}</td>
                            <td>${nombre}</td>
                            <td>${item.email || "No disponible"}</td>
                            <td>${item.phone || "No disponible"}</td>
                            <td>${item.department_name || "No disponible"}</td>
                            <td>${item.position_name || "No disponible"}</td>
                            <td>
                                <button class="btn btn-warning btn-sm" onclick="editarRegistro('${tipo}', ${item.id})">
                                    Editar
                                </button>
                                <button class="btn btn-danger btn-sm" onclick="eliminarRegistro('${tipo}', ${item.id})">
                                    Eliminar
                                </button>
                            </td>
                        </tr>`;
                });
                break;

            case "departamentos":
            case "posiciones":
                tablaHead.innerHTML = `
                    <tr>
                        <th>ID</th>
                        <th>Nombre</th>
                        <th>Descripción</th>
                        <th>Acciones</th>
                    </tr>`;
                response.data.forEach(item => {
                    tablaBody.innerHTML += `
                        <tr>
                            <td>${item.id}</td>
                            <td>${item.name || "No disponible"}</td>
                            <td>${item.description || "No disponible"}</td>
                            <td>
                                <button class="btn btn-warning btn-sm" onclick="editarRegistro('${tipo}', ${item.id})">
                                    Editar
                                </button>
                                <button class="btn btn-danger btn-sm" onclick="eliminarRegistro('${tipo}', ${item.id})">
                                    Eliminar
                                </button>
                            </td>
                        </tr>`;
                });
                break;

            default:
                console.warn(`Tipo desconocido: ${tipo}`);
        }
    } catch (error) {
        console.error(`Error cargando ${tipo}:`, error);
    }
}

// Función para crear un nuevo departamento o posición
function mostrarDescripcion(tipo) {
    const descripcionContainer = document.getElementById(`descripcion-${tipo}-container`);
    if (descripcionContainer) {
        descripcionContainer.classList.remove("d-none"); // Mostrar el campo de descripción
    }
}

function crearRegistro(tipo) {
    const nombreInput = document.getElementById(`nombre-${tipo}`);
    const descripcionInput = document.getElementById(`descripcion-${tipo}`);
    const token = localStorage.getItem("accessToken");

    if (!nombreInput) {
        console.error(`Elemento nombre-${tipo} no encontrado en el DOM.`);
        return;
    }

    const name = nombreInput.value.trim(); // Cambiar a "name"
    const description = descripcionInput ? descripcionInput.value.trim() : null; // Cambiar a "description"

    if (!name) {
        alert("El nombre es obligatorio");
        return;
    }

    // Datos a enviar al backend
    const data = { name }; // Usar "name" en lugar de "nombre"
    if (description) {
        data.description = description; // Usar "description" en lugar de "descripcion"
    }

    axios.post(`${LIST_HANDLER_BASE_UR}/${tipo}/`, data, {
        headers: { "Authorization": `Bearer ${token}` } // Incluir el token en la solicitud
    })
    .then(() => {
        alert(`${tipo} creado con éxito`);
        nombreInput.value = ""; // Limpiar el input de nombre
        if (descripcionInput) descripcionInput.value = ""; // Limpiar el input de descripción
        cargarDatos(tipo); // Recargar la lista
    })
    .catch(error => {
        console.error(`Error al crear ${tipo}:`, error);

        // Mostrar un mensaje de error más detallado
        if (error.response && error.response.data) {
            alert(`Error al crear ${tipo}: ${JSON.stringify(error.response.data)}`);
        } else {
            alert(`Ocurrió un error al crear ${tipo}. Verifica los datos e inténtalo de nuevo.`);
        }
    });
}

// Función para eliminar un departamento o posición
function eliminarRegistro(tipo, id) {
    if (!confirm(`¿Estás seguro de eliminar este ${tipo}?`)) return;

    const token = localStorage.getItem("accessToken");

    axios.delete(`${LIST_HANDLER_BASE_UR}/${tipo}/${id}/`, {
        headers: { "Authorization": `Bearer ${token}` } // Incluir el token en la solicitud
    })
    .then(() => {
        alert(`${tipo} eliminado con éxito`);
        cargarDatos(tipo);
    })
    .catch(error => {
        console.error(`Error al eliminar ${tipo}:`, error);
        alert(`No se pudo eliminar el ${tipo}. Verifica si tiene dependencias.`);
    });
}

