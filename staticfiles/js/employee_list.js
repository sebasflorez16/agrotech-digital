document.addEventListener("DOMContentLoaded", async () => {
    console.log("Intentando cargar la lista de empleados...");

    let token = localStorage.getItem("token");
    console.log("Token from localStorage:", token);

    if (!token) {
        console.error("Token no encontrado. Redirigiendo al login...");
        window.location.href = "/authentication/login/";
        return;
    }

    try {
        console.log("Enviando solicitud al backend...");
        const response = await axios.get("/RRHH/employee/list/", {
            headers: {
                "Authorization": `Token ${token}`,
                "Content-Type": "application/json"
            }
        });

        if (response.status === 200) {
            console.log("Datos de los empleados:", response.data);
            const employeeList = response.data.results;  // DRF paginación por defecto
            const employeeTable = document.getElementById("employeeTable");

            employeeList.forEach(employee => {
                const employeeRow = document.createElement("tr");

                employeeRow.innerHTML = `
                    <td>
                        <img src="${employee.identification_image ? employee.identification_image.url : '/static/images/users/user-4.jpg'}" alt="" class="thumb-lg rounded me-2">
                    </td>
                    <td>
                        <a href="/RRHH/employee/${employee.id}/detail/">${employee.full_name}</a>
                    </td>
                    <td>${employee.identification_number}</td>
                    <td>${employee.phone}</td>
                    <td>${employee.state ? 'Activo' : 'Inactivo'}</td>
                    <td>${employee.join_date}</td>
                    <td>${employee.position}</td>
                    <td class="text-right">
                        <a href="#"><i class="las la-pen text-secondary font-18"></i></a>
                        <a href="#"><i class="las la-trash-alt text-secondary font-18"></i></a>
                    </td>
                `;

                employeeTable.appendChild(employeeRow);
            });
        }
    } catch (error) {
        console.error("Error al cargar la lista de empleados:", error.response || error);

        if (error.response && error.response.status === 401) {
            console.error("Token inválido o expirado. Redirigiendo al login...");
            localStorage.removeItem("token");
            window.location.href = "/authentication/login/";
        }
    }
});