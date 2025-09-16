const BASE_URL = window.ApiUrls ? window.ApiUrls.auth() : `${window.location.origin}/api/authentication`;

console.log("BASE_URL:", BASE_URL);
console.log("axios:", typeof axios !== "undefined" ? "disponible" : "no disponible");

// 🔹 Función de Login (Exportada)
export async function login(username, password) {
    console.log("login() llamado con:", username, password);

    if (!username || !password) {
        alert("⚠️ Por favor ingrese usuario y contraseña.");
        return;
    }

    try {
        const response = await axios.post(`${BASE_URL}/login/`, { username, password });

        console.log("Respuesta del servidor:", response.data);

        const { access, refresh } = response.data;

        // Guardar tokens en localStorage
        localStorage.setItem("accessToken", access);
        localStorage.setItem("refreshToken", refresh);

        // Redirigir al dashboard
        window.location.href = "/templates/vertical_base.html";

    } catch (error) {
        console.error("Error en el login:", error);

        if (error.response) {
            alert(`Error: ${error.response.data.detail || "Credenciales incorrectas"}`);
        } else {
            alert("Error de conexión con el servidor.");
        }
    }
}

// 🔹 Función de Logout (Exportada)
export function logout() {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    window.location.href = "/templates/authentication/login.html";
}
