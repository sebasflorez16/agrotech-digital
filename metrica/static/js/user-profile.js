// Detaes del usuario

document.addEventListener('DOMContentLoaded', fetchAndRenderUserProfile);

function fetchAndRenderUserProfile() {
    const token = localStorage.getItem("accessToken");
    if (!token) {
        console.error("No se encontró el token de acceso.");
        return;
    }

    const baseUrl = window.location.origin;
    const endpoint = `${window.location.origin}/users/api/profile-utils/`;

    fetch(endpoint, { 
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
        .then(response => response.json())
        .then(data => {
            console.log(data);
            renderUserProfile(data);
        })
        .catch(error => {
            console.error(error);
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