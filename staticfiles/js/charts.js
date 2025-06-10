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
                colors: ["#39b54a", "#f15a23"],
                series: [
                    {
                        name: "Income",
                        data: [30, 40, 35, 50, 49, 60, 70, 91, 125, 130, 140, 150]
                    },
                    {
                        name: "Expenses",
                        data: [20, 30, 25, 40, 39, 50, 60, 81, 95, 100, 110, 120]
                    }
                ],
                xaxis: {
                    categories: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
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
