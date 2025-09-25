// 🔹 Archivo único para lógica de autenticación del formulario

// 🔹 Lógica del formulario de login
document.addEventListener("DOMContentLoaded", function () {
    const loginForm = document.getElementById("login-form");

    if (!loginForm) {
        console.log("No se encontró formulario de login - probablemente en index.html");
        return;
    }

    loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value.trim();

        // Validación básica
        if (!username || !password) {
            alert("Por favor completa todos los campos");
            return;
        }

        try {
            // POST al backend para autenticación
            const response = await fetch('https://agrotechcolombia.com/api/authentication/login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    username: username, 
                    password: password 
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.access) {
                // ✅ Autenticación exitosa
                localStorage.setItem("accessToken", data.access);
                localStorage.setItem("refreshToken", data.refresh);
                
                // Redirigir al dashboard principal
                window.location.href = "https://site-production-208b.up.railway.app/templates/vertical_base.html";
                
            } else {
                // ❌ Error de autenticación
                alert("Error: " + (data.error || 'Credenciales incorrectas'));
            }
        } catch (error) {
            console.error('Error de red:', error);
            alert("Error de conexión. Intenta de nuevo.");
        }
    });
});
