// Funcion para cargar los o estender de otras plantillas los componentes en otras plantillas
function loadComponents(components) {
    for (const [id, file] of Object.entries(components)) {
        fetch(file)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error al cargar ${file}: ${response.status} ${response.statusText}`);
                }
                return response.text();
            })
            .then(html => {
                const element = document.getElementById(id);
                if (element) {
                    element.innerHTML = html;

                    // Si el archivo cargado es vendorjs.html, ejecuta los scripts
                    if (id === "vendorjs") {
                        element.querySelectorAll("script").forEach(oldScript => {
                            const newScript = document.createElement("script");
                            if (oldScript.src) {
                                newScript.src = oldScript.src; // Para scripts externos
                                newScript.async = false;
                            } else {
                                newScript.textContent = oldScript.textContent; // Para scripts inline
                            }
                            document.body.appendChild(newScript);
                        });
                    }
                } else {
                    console.warn(`Elemento con ID '${id}' no encontrado en el DOM.`);
                }
            })
            .catch(error => console.error(`Error al cargar componente '${id}' desde ${file}:`, error));
    }
}
const components = {
    "topbar-container": "/static/partials/horizontal-nav.html",
    "vendorjs": "/static/partials/vendorjs.html",
    "footer-container": "/static/partials/footer.html",
    "horizontal-nav": "/static/partials/horizontal-nav.html",
    "right-sidebar": "/static/partials/right-sidebar.html",
    "footer": "/static/partials/footer.html",
    "left-sidebar": "/static/partials/left-sidebar.html"
};
document.addEventListener("DOMContentLoaded", () => {
    loadComponents(components);
});