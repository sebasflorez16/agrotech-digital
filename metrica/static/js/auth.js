const BASE_URL = window.ApiUrls ? window.ApiUrls.auth() : `${window.location.origin}/api/authentication`;

console.log("BASE_URL:", BASE_URL);
console.log("axios:", typeof axios !== "undefined" ? "disponible" : "no disponible");

// 🔹 Función de Login (Exportada)
export function login() {
    // Redirige al formulario de login del backend con next al dashboard del frontend
    window.location.href = "https://agrotechcolombia.com/authentication/login/?next=https://site-production-208b.up.railway.app/vertical_base.html";
}

// 🔹 Función de Logout (Exportada)
export function logout() {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    window.location.href = "https://agrotechcolombia.com/authentication/login/?next=https://site-production-208b.up.railway.app/vertical_base.html";
}
