// Obtener dinámicamente el dominio base del tenant actual
console.log("fetchhelper.js loaded");
const API_BASE_URL = `${window.location.protocol}//${window.location.host}`;

// Función para obtener el token almacenado
function getToken() {
    return localStorage.getItem("token");
}

// Función para manejar solicitudes autenticadas
async function fetchWithAuth(endpoint, options = {}) {
    const token = getToken();
    if (!token) {
        console.error("No se encontró el token. Redirigiendo al login...");
        window.location.href = "/authentication/login/";
        return Promise.reject("No token found");
    }

    const headers = options.headers || {};
    headers["Authorization"] = `Token ${token}`;
    headers["Content-Type"] = "application/json";

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers,
        });
        if (!response.ok) {
            if (response.status === 401) {
                console.error("Token inválido o expirado. Redirigiendo al login...");
                localStorage.removeItem("token");
                window.location.href = "/authentication/login/";
            }
            throw new Error(`Error en la solicitud: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Error al realizar la solicitud:", error);
        throw error;
    }
}
