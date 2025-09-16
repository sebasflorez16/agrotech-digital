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

        // NOTA: Usamos window.location.origin para que la URL sea dinámica y soporte multi-tenant.
        // Así, cada tenant accede a su propio subdominio/API sin hardcodear el host.
        const url = `${window.location.origin}/api/parcels/parcel/summary/`;
        const resp = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        console.log("Respuesta del servidor:", resp);

        if (resp.status === 401) {
            console.error("Token inválido o expirado. Redirigiendo al login.");
            window.location.href = "/templates/authentication/login.html";
            return;
        }

        if (!resp.ok) {
            throw new Error(`Error en la solicitud: ${resp.statusText}`);
        }

        const data = await resp.json();

        // Verificar si los elementos del DOM están presentes
        const ids = [
            'parcelCount', 'parcelTotalArea', 'parcelRemaining', 'parcelActive', 'parcelInactive',
            'parcelAvgArea', 'parcelTopTypes', 'parcelLastName', 'parcelLastDate'
        ];
        ids.forEach(id => {
            const element = document.getElementById(id);
            if (!element) {
                console.warn(`Elemento con ID '${id}' no encontrado en el DOM.`);
            }
        });

        // Actualizar los elementos del DOM con los datos obtenidos
        document.getElementById('parcelCount').textContent = data.total || 0;
        document.getElementById('parcelTotalArea').textContent = (data.total_area || 0).toLocaleString(undefined, {maximumFractionDigits:2}) + ' ha';
        document.getElementById('parcelRemaining').textContent = Math.max(PARCEL_LIMIT - (data.total || 0), 0);
        document.getElementById('parcelActive').textContent = data.activas || 0;
        document.getElementById('parcelInactive').textContent = data.inactivas || 0;
        document.getElementById('parcelAvgArea').textContent = (data.area_promedio || 0).toLocaleString(undefined, {maximumFractionDigits:2}) + ' ha';
        document.getElementById('parcelTopTypes').textContent = data.top_tipos && data.top_tipos.length > 0 ? data.top_tipos.map(t => `${t[0]} (${t[1]})`).join(', ') : '-';
        document.getElementById('parcelLastName').textContent = data.last_parcel || '-';
        document.getElementById('parcelLastDate').textContent = data.last_parcel_date ? `(${data.last_parcel_date})` : '';

        const ndviData = Object.values(data.ndvi_data || {});
        const ndviMonths = Object.keys(data.ndvi_data || {});

        // Actualizar el gráfico Tickets_Status
        const chartElement = document.querySelector("#Tickets_Status");
        if (chartElement) {
            const optionsTickets = {
                chart: {
                    type: "area",
                    height: 350,
                    toolbar: { show: false }
                },
                colors: ["#39b54a"],
                series: [
                    {
                        name: "NDVI Promedio",
                        data: ndviData
                    }
                ],
                xaxis: {
                    categories: ndviMonths
                },
                stroke: {
                    curve: "smooth",
                    width: 2
                },
                fill: {
                    type: "gradient",
                    gradient: { shadeIntensity: 1, opacityFrom: 0.5, opacityTo: 0 }
                }
            };

            new ApexCharts(chartElement, optionsTickets).render();
        }
    } catch (e) {
        console.error("Error al obtener el resumen de parcelas:", e);
        document.getElementById('parcelCount').textContent = 'Error';
        document.getElementById('parcelTotalArea').textContent = 'Error';
        document.getElementById('parcelRemaining').textContent = 'Error';
        document.getElementById('parcelActive').textContent = 'Error';
        document.getElementById('parcelInactive').textContent = 'Error';
        document.getElementById('parcelAvgArea').textContent = 'Error';
        document.getElementById('parcelTopTypes').textContent = 'Error';
        document.getElementById('parcelLastName').textContent = 'Error';
        document.getElementById('parcelLastDate').textContent = '';
    }
}

async function fetchParcels() {
    try {
        const token = localStorage.getItem("accessToken");
        if (!token) {
            console.error("Token no encontrado. Redirigiendo al login.");
            window.location.href = "/login/";
            return;
        }

        const url = `${window.location.origin}/api/parcels/parcel/list-parcels/`;
        const resp = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!resp.ok) {
            throw new Error(`Error en la solicitud: ${resp.statusText}`);
        }

        const parcels = await resp.json();

        const parcelSelect = document.getElementById("parcelSelect");
        if (parcelSelect) {
            parcels.forEach(parcel => {
                const option = document.createElement("option");
                option.value = parcel.id;
                option.textContent = parcel.name;
                parcelSelect.appendChild(option);
            });

            parcelSelect.addEventListener("change", async function () {
                const selectedParcelId = this.value;
                const selectedParcel = parcels.find(p => p.id == selectedParcelId);
                if (selectedParcel) {
                    await updateNDVIChart(selectedParcel.polygon);
                    await updateWaterStressChart(selectedParcel.polygon); // Actualizar gráfico de estrés hídrico
                }
            });
        }
    } catch (error) {
        console.error("Error al obtener las parcelas:", error);
    }
}

// Refactorización para mejorar la legibilidad y organización

async function fetchChartData(url, polygon, token) {
    if (!polygon || polygon.length < 3) {
        console.error("El polígono proporcionado no es válido.");
        alert("No se puede obtener datos para un polígono inválido.");
        return null;
    }

    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ polygon })
        });

        if (!response.ok) {
            throw new Error(`Error en la solicitud: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data || Object.keys(data).length === 0) {
            console.error("No se recibieron datos válidos.");
            alert("No se encontraron datos para la parcela seleccionada.");
            return null;
        }

        return data;
    } catch (error) {
        console.error("Error al obtener datos:", error);
        alert("Hubo un error al obtener los datos. Por favor, intenta nuevamente.");
        return null;
    }
}

function renderChart(chartElementId, chartTitle, dataValues, dataLabels, color) {
    const chartElement = document.querySelector(`#${chartElementId}`);
    if (!chartElement) {
        console.warn(`Elemento de gráfico con ID '${chartElementId}' no encontrado.`);
        return;
    }

    const options = {
        chart: {
            type: "area",
            height: 350,
            toolbar: { show: false }
        },
        colors: [color],
        series: [{
            name: chartTitle,
            data: dataValues
        }],
        xaxis: {
            categories: dataLabels
        },
        stroke: {
            curve: "smooth",
            width: 2
        },
        fill: {
            type: "gradient",
            gradient: { shadeIntensity: 1, opacityFrom: 0.5, opacityTo: 0 }
        }
    };

    new ApexCharts(chartElement, options).render();
}

async function updateNDVIChart(polygon) {
    const token = localStorage.getItem("accessToken");
    const url = `${window.location.origin}/api/parcels/parcel/ndvi-historical/`;

    const ndviData = await fetchChartData(url, polygon, token);
    if (ndviData) {
        const ndviValues = Object.values(ndviData);
        const ndviMonths = Object.keys(ndviData);
        renderChart("Tickets_Status", "NDVI Promedio", ndviValues, ndviMonths, "#39b54a");
    }
}

async function updateWaterStressChart(polygon) {
    const token = localStorage.getItem("accessToken");
    const url = `${window.location.origin}/api/parcels/parcel/water-stress-historical/`;

    const waterStressData = await fetchChartData(url, polygon, token);
    if (waterStressData) {
        const waterStressValues = Object.values(waterStressData);
        const waterStressMonths = Object.keys(waterStressData);
        renderChart("Water_Stress_Status", "Estrés Hídrico Promedio", waterStressValues, waterStressMonths, "#ff5733");
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    await fetchParcelSummary();
    await fetchParcels();
});

document.addEventListener("DOMContentLoaded", async () => {
    const parcelSelect = document.getElementById("parcelSelect");
    const tableBody = document.getElementById("parcelTable").querySelector("tbody");

    // Función para actualizar la tabla con los datos de la parcela seleccionada
    async function updateTable(parcelId) {
        try {
            const token = localStorage.getItem("accessToken");
            const url = `${window.location.origin}/api/parcels/parcel/${parcelId}/`;
            const resp = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!resp.ok) {
                throw new Error(`Error en la solicitud: ${resp.statusText}`);
            }

            const parcel = await resp.json();

            // Limpiar la tabla
            tableBody.innerHTML = "";

            // Agregar datos de la parcela seleccionada
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${parcel.properties.name || "Sin nombre"}</td>
                <td>${parcel.properties.description || "Sin descripción"}</td>
                <td>${parcel.properties.field_type || "N/A"}</td>
                <td>${parcel.properties.soil_type || "N/A"}</td>
                <td>${parcel.properties.topography || "N/A"}</td>
            `;
            tableBody.appendChild(row);
        } catch (error) {
            console.error("Error al actualizar la tabla:", error);
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-danger">Error al cargar los datos de la parcela.</td>
                </tr>
            `;
        }
    }

    // Seleccionar la primera parcela por defecto al cargar la página
    if (parcelSelect && parcelSelect.options.length > 0) {
        const firstParcelId = parcelSelect.options[0].value;
        parcelSelect.value = firstParcelId;
        await updateTable(firstParcelId);
    }

    // Configurar evento para cambiar la tabla al seleccionar una parcela
    parcelSelect.addEventListener("change", async (event) => {
        const selectedParcelId = event.target.value;
        await updateTable(selectedParcelId);
    });
});
