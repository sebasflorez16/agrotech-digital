// Botón independiente para solicitar analítica de la escena
window.solicitarAnaliticaEscenaEOSDA = async function(viewId) {
    const fieldId = window.EOSDA_STATE.selectedEosdaId;
    const parcelId = window.EOSDA_STATE.selectedParcelId;
    const token = localStorage.getItem("accessToken");
    if (!fieldId || !viewId) {
        showErrorToast("No se encontró el field_id o view_id para la escena seleccionada.");
        return;
    }
    // Buscar el request_id cacheado para la imagen NDVI
    const cacheKey = `${viewId}_ndvi`;
    const requestId = window.EOSDA_STATE.requestIds[cacheKey];
    if (!requestId) {
        showErrorToast("Primero debes solicitar la imagen NDVI para obtener el request_id.");
        return;
    }
    // Mostrar spinner y solicitar analítica NDVI
    showSpinner("Solicitando analítica NDVI...");
    try {
        const resp = await fetch(`${BASE_URL}/eosda-analytics/?field_id=${fieldId}&view_id=${viewId}&request_id=${requestId}&type=ndvi`, {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });
        const data = await resp.json();
        hideSpinner();
        if (data && data.analytics) {
            // Renderizar la analítica en la tabla NDVI
            const legendTable = document.getElementById('ndvi-legend-table');
            if (legendTable) {
                renderNDVIAnalyticsTable(data.analytics, legendTable);
                showInfoToast("Analítica NDVI cargada correctamente.");
            }
        } else {
            showErrorToast("No se encontraron datos analíticos NDVI.");
        }
    } catch (err) {
        hideSpinner();
        showErrorToast("Error al solicitar la analítica NDVI: " + (err.message || err));
    }
};
