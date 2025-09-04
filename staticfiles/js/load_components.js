// static/js/load-components.js

export async function loadLayoutComponents(components) {
    const loadComponent = async ([id, path]) => {
        try {
            const response = await fetch(path);
            if (!response.ok) throw new Error(`Error al cargar ${path}`);
            const html = await response.text();
            const container = document.getElementById(id);

            if (container) {
                container.innerHTML = html;

                // Ejecutar scripts en vendorjs
                if (id === "vendorjs") {
                    container.querySelectorAll("script").forEach(script => {
                        const s = document.createElement("script");
                        if (script.src) {
                            s.src = script.src;
                            s.async = false;
                        } else {
                            s.textContent = script.textContent;
                        }
                        document.body.appendChild(s);
                    });
                }
            } else {
                console.warn(`Elemento con ID '${id}' no encontrado en el DOM.`);
            }
        } catch (err) {
            console.error(`Error al cargar componente '${id}' desde ${path}:`, err);
        }
    };

    await Promise.all(Object.entries(components).map(loadComponent));
}
