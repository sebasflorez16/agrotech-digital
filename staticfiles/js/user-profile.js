// Detaes del usuario

document.addEventListener('DOMContentLoaded', fetchAndRenderUserProfile);

function fetchAndRenderUserProfile() {
    const token = localStorage.getItem("accessToken");
    if (!token) {
        console.error("No se encontró el token de acceso.");
        return;
    }

    // Apuntar al backend correcto, no al frontend
    const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://localhost:8000' : 'https://agrotechcolombia.com';
    const endpoint = `${API_BASE}/users/api/profile-utils/`;

    fetch(endpoint, { 
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log(data);
            renderUserProfile(data);
        })
        .catch(error => {
            console.error("Error cargando perfil de usuario:", error);
            // NO redirigir al login por errores de perfil
        });
}

function renderUserProfile(data) {
    if (!data || data.length === 0) return;
    const user = data[0]; // Asumimos que el primer elemento contiene los datos del usuario

    const nameElement = document.getElementById('userName');
    if (nameElement) nameElement.textContent = user.name;

    const emailElement = document.getElementById('userEmail');
    if (emailElement) emailElement.textContent = user.email;

    const phoneElement = document.getElementById('userPhone');
    if (phoneElement) phoneElement.textContent = user.phone;

    const imageElement = document.getElementById('userImage');
    if (imageElement) imageElement.src = user.image ? user.image : 'default-profile.png'; // Ruta por defecto si no hay imagen
}