// Script para actualizar el resumen de parcelas en el dashboard
// Suponiendo un límite de parcelas por plan (puedes cambiar este valor)
const PARCEL_LIMIT = 50;

async function fetchParcelSummary() {
    try {
        const token = localStorage.getItem("accessToken");
        if (!token) {
            console.error("Token no encontrado. Redirigiendo al login.");
            window.location.href = "/login/";
            return;
        }

        const url = `http://${window.location.hostname}:8000/api/parcels/parcel/summary/`;
        const resp = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (resp.status === 401) {
            console.error("Token inválido o expirado. Redirigiendo al login.");
            window.location.href = "/login/";
            return;
        }

        if (!resp.ok) {
            throw new Error(`Error en la solicitud: ${resp.statusText}`);
        }

        const data = await resp.json();
        document.getElementById('parcelCount').textContent = data.total;
        document.getElementById('parcelTotalArea').textContent = data.total_area.toLocaleString(undefined, {maximumFractionDigits:2}) + ' ha';
        document.getElementById('parcelRemaining').textContent = Math.max(PARCEL_LIMIT - data.total, 0);
        document.getElementById('parcelActive').textContent = data.activas;
        document.getElementById('parcelInactive').textContent = data.inactivas;
        document.getElementById('parcelAvgArea').textContent = data.area_promedio.toLocaleString(undefined, {maximumFractionDigits:2}) + ' ha';
        document.getElementById('parcelTopTypes').textContent = data.top_tipos && data.top_tipos.length > 0 ? data.top_tipos.map(t => `${t[0]} (${t[1]})`).join(', ') : '-';
        document.getElementById('parcelLastName').textContent = data.last_parcel || '-';
        document.getElementById('parcelLastDate').textContent = data.last_parcel_date ? `(${data.last_parcel_date})` : '';
        document.getElementById('parcelAreaRestante').textContent = data.area_restante.toLocaleString(undefined, {maximumFractionDigits:2}) + ' ha';
    } catch (e) {
        console.error("Error al obtener el resumen de parcelas:", e);
        document.getElementById('parcelCount').textContent = 'Error';
        document.getElementById('parcelTotalArea').textContent = 'Error';
        document.getElementById('parcelRemaining').textContent = 'Error';
    }
}
console.log("✅ dashboard-parcels-summary.js fue cargado correctamente");


document.addEventListener('DOMContentLoaded', fetchParcelSummary);
