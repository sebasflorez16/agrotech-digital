document.addEventListener("DOMContentLoaded", function () {
    const token = localStorage.getItem("accessToken"); // Obtener el token almacenado

    if (!token) {
        console.warn("⚠️ No hay token, redirigiendo al login...");
        window.location.href = "/static/templates/authentication/login.html";
        return;
    }

    // Llamada a la API para obtener los datos del usuario autenticado
    fetch(`${window.location.origin}/api/authentication/user/`, {
        method: "GET",
        headers: { "Authorization": `Bearer ${token}` }
    })
    .then(response => response.json())
    .then(data => {
        console.log("👤 Usuario autenticado:", data);

        // Mostrar el nombre del usuario
        document.getElementById("userName").textContent = `${data.first_name} ${data.last_name}`;

        // Mostrar la imagen del usuario si tiene una
        if (data.profile_picture) {
            document.getElementById("userAvatar").src = data.profile_picture;
        }
    })
    .catch(error => console.error("❌ Error al obtener los datos del usuario:", error));
});
