// 🔹 Función para verificar si el usuario está autenticado
export function isAuthenticated() {
    const token = localStorage.getItem("accessToken");
    return token && token !== "null" && token !== "undefined" && token.trim() !== "";
}

// 🔹 Función para redirigir al login
export function redirectToLogin() {
    window.location.href = "../authentication/login.html";
}

// 🔹 Función para redirigir al dashboard después del login
export function redirectToDashboard() {
    window.location.href = "../dashboard.html";
}

// 🔹 Función de Logout
export function logout() {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    redirectToLogin();
}

