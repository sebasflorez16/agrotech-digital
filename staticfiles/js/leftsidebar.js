// Para menejar el sidebar resondo al click del botón responsive

// Sidebar offcanvas global para todo el proyecto
function setupSidebarOffcanvas() {
    // Buscar el sidebar en cualquier parte del DOM
    const sidebar = document.getElementById("sidebar");
    if (!sidebar) return;

    // Buscar el botón hamburguesa globalmente (puede estar en cualquier partial)
    function waitForToggle() {
        const mobileToggle = document.getElementById("mobileToggle");
        if (!mobileToggle) {
            setTimeout(waitForToggle, 100);
            return;
        }
        // Evitar múltiples listeners
        if (!mobileToggle.classList.contains("sidebar-listener")) {
            mobileToggle.classList.add("sidebar-listener");
            mobileToggle.addEventListener("click", function (e) {
                e.preventDefault();
                sidebar.classList.toggle("show");
                document.body.classList.toggle("sidebar-open");
            });
        }
    }
    waitForToggle();

    // Cerrar sidebar al hacer click fuera en móvil
    document.addEventListener("click", function (e) {
        if (window.innerWidth <= 991 && sidebar.classList.contains("show")) {
            if (!sidebar.contains(e.target) && !e.target.closest("#mobileToggle")) {
                sidebar.classList.remove("show");
                document.body.classList.remove("sidebar-open");
            }
        }
    });
}

// Dropdown funcional para el menú lateral
// Elimina el JS personalizado de dropdown, Bootstrap gestiona el menú nativamente

// Ejecutar siempre que se cargue el archivo (incluso si se recarga el sidebar por AJAX)
document.addEventListener("DOMContentLoaded", function () {
    setupSidebarOffcanvas();
});
