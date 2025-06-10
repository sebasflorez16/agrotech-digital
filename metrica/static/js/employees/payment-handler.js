// Definir la URL base de la API
const PAYMENT_HANDLER_BASE_URL = `http://${window.location.hostname}:8000/api/RRHH`;

// Función para cargar los métodos de pago
async function cargarMetodosPago() {
    const token = localStorage.getItem("accessToken");

    if (!token) {
        console.warn("⚠️ No hay token, redirigiendo al login...");
        window.location.href = "/templates/authentication/login.html";
        return;
    }

    try {
        const response = await axios.get(`${PAYMENT_HANDLER_BASE_URL}/metodos-pago/`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        const tablaBody = document.getElementById("tabla-metodos-pago-body");

        if (!tablaBody) {
            console.error("Elemento tabla-metodos-pago-body no encontrado en el DOM.");
            return;
        }

        // Limpiar la tabla antes de agregar nuevos datos
        tablaBody.innerHTML = "";

        // Verificar si hay datos en la respuesta
        if (!response.data || response.data.length === 0) {
            tablaBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">No hay métodos de pago disponibles.</td>
                </tr>`;
            return;
        }

        // Insertar los datos en la tabla
        response.data.forEach(metodo => {
            tablaBody.innerHTML += `
                <tr>
                    <td>${metodo.id}</td>
                    <td>${metodo.name}</td>
                    <td>${metodo.amount}</td>
                    <td>${metodo.description || "No disponible"}</td>
                    <td>${metodo.created_date}</td>
                    <td>
                        <button class="btn btn-warning btn-sm" onclick="mostrarModalEditarMetodoPago(${metodo.id})">
                            Editar
                        </button>
                        <button class="btn btn-danger btn-sm" onclick="eliminarMetodoPago(${metodo.id})">
                            Eliminar
                        </button>
                    </td>
                </tr>`;
        });
    } catch (error) {
        console.error("Error al cargar los métodos de pago:", error);
        alert("Ocurrió un error al cargar los métodos de pago. Intenta nuevamente.");
    }
}

function mostrarModalCrearMetodoPago() {
    // Limpiar los campos del formulario
    document.getElementById("crear-nombre-metodo").value = "";
    document.getElementById("crear-monto-metodo").value = "";
    document.getElementById("crear-descripcion-metodo").value = "";

    // Mostrar el modal
    const modal = new bootstrap.Modal(document.getElementById("modalCrearMetodoPago"));
    modal.show();
}

function guardarNuevoMetodoPago() {
    const token = localStorage.getItem("accessToken");

    // Obtener los datos del formulario
    const name = document.getElementById("crear-nombre-metodo").value.trim();
    const amount = document.getElementById("crear-monto-metodo").value.trim();
    const description = document.getElementById("crear-descripcion-metodo").value.trim();

    if (!name || !amount) {
        alert("El nombre y el monto son obligatorios.");
        return;
    }

    // Enviar los datos al backend
    axios.post(`${PAYMENT_HANDLER_BASE_URL}/metodos-pago/`, {
        name: name,
        amount: amount,
        description: description
    }, {
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(() => {
        alert("Método de pago creado con éxito.");
        const modal = bootstrap.Modal.getInstance(document.getElementById("modalCrearMetodoPago"));
        modal.hide(); // Cerrar el modal
        cargarMetodosPago(); // Recargar la tabla
    })
    .catch(error => {
        console.error("Error al crear el método de pago:", error);
        alert("No se pudo crear el método de pago. Intenta nuevamente.");
    });
}

function mostrarModalEditarMetodoPago(id) {
    const token = localStorage.getItem("accessToken");
    const url = `${PAYMENT_HANDLER_BASE_URL}/metodos-pago/${id}/`;

    axios.get(url, {
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(response => {
        const metodo = response.data;

        // Cargar los datos en los campos del modal
        document.getElementById("editar-id-metodo").value = metodo.id;
        document.getElementById("editar-nombre-metodo").value = metodo.name;
        document.getElementById("editar-monto-metodo").value = metodo.amount;
        document.getElementById("editar-descripcion-metodo").value = metodo.description || "";

        // Mostrar el modal
        const modal = new bootstrap.Modal(document.getElementById("modalEditarMetodoPago"));
        modal.show();
    })
    .catch(error => {
        console.error("Error al obtener los datos del método de pago:", error);
        alert("No se pudo cargar la información del método de pago. Intenta nuevamente.");
    });
}

function guardarCambiosMetodoPago() {
    const token = localStorage.getItem("accessToken");

    // Obtener los datos del formulario
    const id = document.getElementById("editar-id-metodo").value;
    const name = document.getElementById("editar-nombre-metodo").value.trim();
    const amount = document.getElementById("editar-monto-metodo").value.trim();
    const description = document.getElementById("editar-descripcion-metodo").value.trim();

    if (!id) {
        console.error("El ID del método de pago no está definido.");
        alert("No se puede actualizar el método de pago porque falta el ID.");
        return;
    }

    if (!name || !amount) {
        alert("El nombre y el monto son obligatorios.");
        return;
    }

    // Enviar los datos al backend
    axios.patch(`${PAYMENT_HANDLER_BASE_URL}/metodos-pago/${id}/`, {
        name: name,
        amount: amount,
        description: description
    }, {
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(() => {
        alert("Método de pago actualizado con éxito.");
        const modal = bootstrap.Modal.getInstance(document.getElementById("modalEditarMetodoPago"));
        modal.hide(); // Cerrar el modal
        cargarMetodosPago(); // Recargar la tabla
    })
    .catch(error => {
        console.error("Error al actualizar el método de pago:", error);
        alert("No se pudo actualizar el método de pago. Intenta nuevamente.");
    });
}

function eliminarMetodoPago(id) {
    if (!confirm("¿Estás seguro de eliminar este método de pago?")) return;

    const token = localStorage.getItem("accessToken");

    axios.delete(`${PAYMENT_HANDLER_BASE_URL}/metodos-pago/${id}/`, {
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(() => {
        alert("Método de pago eliminado con éxito.");
        cargarMetodosPago(); // Recargar la tabla
    })
    .catch(error => {
        console.error("Error al eliminar el método de pago:", error);
        alert("No se pudo eliminar el método de pago. Intenta nuevamente.");
    });
}