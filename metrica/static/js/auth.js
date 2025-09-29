// 🔹 Función para verificar si el usuario está autenticado
export function isAuthenticated() {
    const token = localStorage.getItem("accessToken");
    return token && token !== "null" && token !== "undefined" && token.trim() !== "";
}

// 🔹 Función para redirigir al login
export function redirectToLogin() {
    window.location.href = "https://agrotechcolombia.netlify.app/templates/authentication/login.html";
}

// 🔹 Función para redirigir al dashboard después del login
export function redirectToDashboard() {
    window.location.href = "https://agrotechcolombia.netlify.app/templates/vertical_base.html";
}

// 🔹 Función de Logout
export function logout() {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    redirectToLogin();
}

// 🔹 Función para proteger páginas (usar en vertical_base.html)
export function requireAuth() {
    if (!isAuthenticated()) {
        redirectToLogin();
    }
}