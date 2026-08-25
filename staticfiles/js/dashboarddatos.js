// En este archivo traeremos datos del backend para mostrarlos en el dashboard
// Aca nos aseguramos que la funcion fetchUserCount() solo se ejecute apenas de carge el DOMContentLoaded
//para que los datos se mantengan actualizados y constantes.
document.addEventListener("DOMContentLoaded", () => {
    console.log("Dashboard cargado correctamente");
    // dashboarddatos.js: obsoleto - dashboard-liquid.js maneja la carga de stats
    // fetchUserCount() llamaba a endpoint inexistente /api/authentication/dashboard/
});
