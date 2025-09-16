// En este archivo traeremos datos del backend para mostrarlos en el dashboard
// Aca nos aseguramos que la funcion fetchUserCount() solo se ejecute apenas de carge el DOMContentLoaded
//para que los datos se mantengan actualizados y constantes.
document.addEventListener("DOMContentLoaded", () => {
    console.log("Dashboard cargado correctamente");
    fetchUserCount(); 
});

function fetchUserCount() {
    let token = localStorage.getItem("accessToken");

    fetch(`${window.location.origin}/api/authentication/dashboard/`, {  //Ruta correcta
        method: "GET",
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(response => response.json())
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
