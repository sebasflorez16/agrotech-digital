// warehouse_report.js
// Lógica para descargar PDF y mejorar experiencia visual

// warehouse_report.js
// Lógica para mostrar el reporte en modal y descargar PDF sin abrir nueva pestaña

// Función para descargar el PDF usando fetch y JWT
async function descargarPDF(warehouseId) {
    const token = localStorage.getItem("accessToken");
    try {
        const resp = await fetch(`/inventario/warehouse-report/${warehouseId}/pdf/`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!resp.ok) throw new Error('No se pudo descargar el PDF');
        const blob = await resp.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `inventario_almacen_${warehouseId}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (err) {
        alert('Error al descargar PDF');
    }
}

// Escucha el click en el botón de descarga dentro del modal
document.addEventListener('click', function(e) {
    if (e.target && e.target.id === 'btnDescargarPDFModal') {
        const warehouseId = e.target.getAttribute('data-warehouse-id');
        if (warehouseId) {
            descargarPDF(warehouseId);
        }
    }
});
