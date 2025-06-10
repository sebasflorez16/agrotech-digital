document.addEventListener("DOMContentLoaded", function () {
    // Esperar hasta que se cargue dinámicamente el dashboard
    let checkExist = setInterval(function () {
        let chartElement = document.querySelector("#Tickets_Status");
        
        if (chartElement) {
            clearInterval(checkExist); // Detiene la espera

            var optionsTickets = {
                chart: {
                    type: "area",
                    height: 350,
                    toolbar: { show: false }
                },
                colors: ["#39b54a"],
                series: [
                    {
                        name: "NDVI Promedio",
                        data: [0.45, 0.50, 0.60] // Datos simulados, reemplazar con datos reales del backend
                    }
                ],
                xaxis: {
                    categories: ["Enero", "Febrero", "Marzo"] // Meses correspondientes
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
    }, 500); // Revisa cada 500ms si el elemento ya existe
});
