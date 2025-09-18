const BASE_URL = window.ApiUrls ? window.ApiUrls.auth() : `${window.location.origin}/api/authentication`;

console.log("BASE_URL:", BASE_URL);
console.log("axios:", typeof axios !== "undefined" ? "disponible" : "no disponible");

// 🔹 Función de Login (Exportada)
export function login() {
    // Redirige directamente al formulario de login del backend
    window.location.href = "/authentication/login/";
}

// 🔹 Función de Logout (Exportada)
export function logout() {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    window.location.href = "/authentication/login/";
}
