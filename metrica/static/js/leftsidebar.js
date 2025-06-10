
// Para menejar el sidebar resondo al click del botón responsive

document.addEventListener("DOMContentLoaded", function () {
    const toggleSidebarButton = document.getElementById("toggleSidebar");
    const sidebar = document.getElementById("sidebar");

    toggleSidebarButton.addEventListener("click", function () {
        sidebar.classList.toggle("show");
        document.body.classList.toggle("sidebar-open");
    });
});
