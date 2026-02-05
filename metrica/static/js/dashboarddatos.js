// En este archivo traeremos datos del backend para mostrarlos en el dashboard
// Aca nos aseguramos que la funcion fetchUserCount() solo se ejecute apenas de carge el DOMContentLoaded
//para que los datos se mantengan actualizados y constantes.
document.addEventListener("DOMContentLoaded", () => {
    console.log("Dashboard cargado correctamente");
    fetchUserCount(); 
});

function fetchUserCount() {
    let token = localStorage.getItem("accessToken");

    const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://localhost:8000' : 'https://agrotechcolombia.com';
    fetch(`${API_BASE}/api/authentication/dashboard/`, {
        method: "GET",
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(response => {
        if (response.status === 401) {
            // Token inválido o expirado: redirige al login y limpia tokens
            localStorage.removeItem("accessToken");
            localStorage.removeItem("refreshToken");
            window.location.href = "https://agrotechcolombia.netlify.app/templates/authentication/login.html";
            throw new Error("No autorizado, redirigiendo al login.");
        }
        return response.json();
    })
    .then(data => {
        console.log("Número de usuarios registrados:", data.user_count);
        const userCountElement = document.getElementById("userCount");
        if (userCountElement) {
            userCountElement.textContent = `Usuarios registrados: ${data.user_count}`;
        } else {
            console.error("Elemento con ID 'userCount' no encontrado en el DOM.");
        }
    })
    .catch(error => {
        console.error("Error al obtener el número de usuarios:", error);
    });
}
