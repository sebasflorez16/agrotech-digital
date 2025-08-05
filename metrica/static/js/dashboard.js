document.addEventListener("DOMContentLoaded", () => {
    console.log("🚀 Dashboard cargado correctamente");
    checkAuth(); // Verificar autenticación antes de cargar el contenido
});



// ✅ Función para cargar información del dashboard
function loadDashboardData() {
    console.log("📡 Cargando datos del dashboard...");

    // Aquí puedes agregar futuras funciones para obtener estadísticas, métricas, etc.
}


// Funcion para ver los productos


function checkAuth() {
    let token = localStorage.getItem("accessToken");

    console.log("Verificando autenticación...");
    console.log("Token encontrado:", token ? token : "No hay token almacenado");

    if (!token) {
        console.warn("⚠️ No hay token, redirigiendo al login...");
        window.location.href = "/templates/authentication/login.html";
        return;
    }

    //Validar si el token es realmente válido llamando a una API protegida
    fetch(`http://${window.location.hostname}:8000/api/authentication/dashboard/`, {
        method: "GET",
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(response => {
        console.log("Respuesta del servidor:", response.status);
        
        if (!response.ok) {
            console.error("Token inválido o expirado, redirigiendo al login...");
            localStorage.removeItem("accessToken");
            localStorage.removeItem("refreshToken");
            window.location.href = "/templates/authentication/login.html";
        } else {
            console.log("Token válido, cargando dashboard...");
            loadDashboardData();
        }
    })
    .catch(error => {
        console.error("Error al verificar autenticación:", error);
        window.location.href = "/templates/authentication/login.html";
    });
}





// función para cerrar sesión

function logout() {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    window.location.href = "/authentication/login.html";
}

// Botón para ir a la gestión de labores
const btnLabores = document.createElement("button");
btnLabores.className = "btn btn-success mb-3";
btnLabores.innerHTML = '<i class="fa fa-tasks"></i> Gestionar Labores';
btnLabores.onclick = function() {
    window.location.href = "/templates/labores.html";
};
// Insertar el botón en el dashboard (por ejemplo, arriba del resumen de parcelas)
window.addEventListener("DOMContentLoaded", () => {
    const resumen = document.querySelector("#resumen-parcelas, .resumen-parcelas");
    if (resumen) {
        resumen.parentNode.insertBefore(btnLabores, resumen);
    } else {
        document.body.prepend(btnLabores);
    }
});