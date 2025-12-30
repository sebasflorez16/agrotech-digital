/**
 * AGROTECH DIGITAL - Sistema de Utilidades JavaScript
 * Funciones globales para notificaciones, errores y animaciones
 */

// Configuración Global AgroTech
window.AgroTech = window.AgroTech || {
    colors: {
        verde: '#2E8B57',
        verdeClaro: '#4a7c59',
        naranja: '#FF7A00',
        gris: '#2c3e50',
        blanco: '#FFFFFF'
    },
    mapConfig: {
        defaultCenter: [4.570868, -74.297333], // Bogotá, Colombia
        defaultZoom: 10,
        maxZoom: 18,
        minZoom: 3
    }
};

/**
 * Sistema de Notificaciones Neumórficas
 * @param {string} mensaje - Mensaje a mostrar
 * @param {string} tipo - Tipo de alerta: 'success', 'error', 'warning', 'info'
 * @param {number} duracion - Duración en milisegundos (default: 5000)
 * @returns {HTMLElement} - Elemento de alerta creado
 */
window.mostrarNotificacion = function(mensaje, tipo = 'info', duracion = 5000) {
    const iconMap = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-triangle',
        danger: 'fa-exclamation-triangle',
        warning: 'fa-exclamation-circle',
        info: 'fa-info-circle'
    };
    
    const colorMap = {
        success: 'success',
        error: 'danger',
        danger: 'danger',
        warning: 'warning',
        info: 'info'
    };
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${colorMap[tipo] || 'info'} alert-dismissible fade show neomorphic-alert position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px; animation: fadeInUp 0.5s ease-out;';
    alertDiv.innerHTML = `
        <i class="fas ${iconMap[tipo] || 'fa-info-circle'} me-2"></i>
        ${mensaje}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.style.animation = 'fadeOut 0.5s ease-out';
            setTimeout(() => alertDiv.remove(), 500);
        }
    }, duracion);
    
    return alertDiv;
};

/**
 * Sistema de Errores Críticos con Modal
 * @param {string} titulo - Título del error
 * @param {string} mensaje - Mensaje descriptivo
 * @param {string} detalles - Detalles técnicos opcionales
 */
window.mostrarErrorCritico = function(titulo, mensaje, detalles = '') {
    const modalId = 'errorModal' + Date.now();
    const modalHtml = `
        <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content neomorphic-card">
                    <div class="modal-header bg-danger text-white" style="border-radius: 28px 28px 0 0;">
                        <h5 class="modal-title" id="${modalId}Label">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            ${titulo}
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-danger neomorphic-alert">
                            <strong>Error:</strong> ${mensaje}
                        </div>
                        ${detalles ? `
                            <details class="mt-3">
                                <summary class="mb-2 fw-bold text-muted" style="cursor: pointer;">
                                    <i class="fas fa-code me-2"></i>Detalles técnicos
                                </summary>
                                <pre class="bg-light p-3 rounded" style="max-height: 300px; overflow-y: auto;"><code>${escapeHtml(detalles)}</code></pre>
                            </details>
                        ` : ''}
                        <div class="mt-3">
                            <h6 class="text-gradient-primary">
                                <i class="fas fa-lightbulb me-2"></i>Posibles soluciones:
                            </h6>
                            <ul class="mb-0">
                                <li>Verifique su conexión a internet</li>
                                <li>Revise la configuración del servidor</li>
                                <li>Intente recargar la página</li>
                                <li>Contacte al administrador del sistema si el problema persiste</li>
                            </ul>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn neomorphic btn-secondary" data-bs-dismiss="modal">
                            <i class="fas fa-times me-2"></i>Cerrar
                        </button>
                        <button type="button" class="btn neomorphic btn-primary" onclick="location.reload()">
                            <i class="fas fa-redo me-2"></i>Recargar Página
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modalElement = document.getElementById(modalId);
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
    
    modalElement.addEventListener('hidden.bs.modal', function() {
        this.remove();
    });
};

/**
 * Escape HTML para prevenir XSS
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Aplicar animaciones de entrada a las tarjetas
 */
window.aplicarAnimacionesTarjetas = function() {
    const cards = document.querySelectorAll('.card, .neomorphic-card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('fade-in-up');
        }, index * 100);
    });
};

/**
 * Agregar clase neumórfica a elementos automáticamente
 */
window.aplicarEstilosNeomorficos = function() {
    // Aplicar a cards existentes
    document.querySelectorAll('.card:not(.neomorphic)').forEach(card => {
        card.classList.add('neomorphic');
    });
    
    // Aplicar a botones
    document.querySelectorAll('.btn:not(.neomorphic):not(.btn-close)').forEach(btn => {
        btn.classList.add('neomorphic');
    });
    
    // Aplicar a formularios
    document.querySelectorAll('.form-control:not(.neomorphic), .form-select:not(.neomorphic)').forEach(input => {
        input.classList.add('neomorphic');
    });
    
    // Aplicar a tablas
    document.querySelectorAll('.table:not(.neomorphic)').forEach(table => {
        table.classList.add('neomorphic');
    });
    
    // Aplicar a alerts
    document.querySelectorAll('.alert:not(.neomorphic)').forEach(alert => {
        alert.classList.add('neomorphic');
    });
};

/**
 * Inicializar tema neumórfico en el body
 */
window.inicializarTemaNeumorfico = function() {
    document.body.classList.add('neomorphic-theme');
    
    // Aplicar estilos a elementos existentes
    aplicarEstilosNeomorficos();
    
    // Aplicar animaciones
    setTimeout(() => {
        aplicarAnimacionesTarjetas();
    }, 100);
};

/**
 * Loading overlay neumórfico
 */
window.mostrarLoading = function(mensaje = 'Cargando...') {
    const loadingId = 'agrotechLoading';
    
    // Remover loading anterior si existe
    const existingLoading = document.getElementById(loadingId);
    if (existingLoading) {
        existingLoading.remove();
    }
    
    const loadingHtml = `
        <div id="${loadingId}" class="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center" 
             style="background: rgba(232, 240, 248, 0.9); z-index: 10000; backdrop-filter: blur(10px);">
            <div class="text-center neomorphic-card p-5">
                <div class="spinner-border text-success mb-3" role="status" style="width: 4rem; height: 4rem;">
                    <span class="visually-hidden">Cargando...</span>
                </div>
                <h5 class="text-gradient-primary mb-0">${mensaje}</h5>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', loadingHtml);
    return document.getElementById(loadingId);
};

window.ocultarLoading = function() {
    const loading = document.getElementById('agrotechLoading');
    if (loading) {
        loading.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => loading.remove(), 300);
    }
};

/**
 * Confirmación neumórfica
 */
window.confirmarAccion = function(titulo, mensaje, onConfirm, onCancel) {
    const modalId = 'confirmModal' + Date.now();
    const modalHtml = `
        <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content neomorphic-card">
                    <div class="modal-header border-0">
                        <h5 class="modal-title text-gradient-primary">
                            <i class="fas fa-question-circle me-2"></i>${titulo}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p class="mb-0">${mensaje}</p>
                    </div>
                    <div class="modal-footer border-0">
                        <button type="button" class="btn neomorphic btn-secondary" data-bs-dismiss="modal">
                            <i class="fas fa-times me-2"></i>Cancelar
                        </button>
                        <button type="button" class="btn neomorphic btn-primary" id="${modalId}Confirm">
                            <i class="fas fa-check me-2"></i>Confirmar
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modalElement = document.getElementById(modalId);
    const modal = new bootstrap.Modal(modalElement);
    
    document.getElementById(modalId + 'Confirm').addEventListener('click', () => {
        modal.hide();
        if (onConfirm) onConfirm();
    });
    
    modalElement.addEventListener('hidden.bs.modal', function() {
        if (onCancel) onCancel();
        this.remove();
    });
    
    modal.show();
};

/**
 * Añadir animación fadeOut para notificaciones
 */
const fadeOutKeyframes = `
@keyframes fadeOut {
    from {
        opacity: 1;
        transform: translateY(0);
    }
    to {
        opacity: 0;
        transform: translateY(-20px);
    }
}
`;

if (!document.getElementById('agrotechAnimations')) {
    const style = document.createElement('style');
    style.id = 'agrotechAnimations';
    style.innerHTML = fadeOutKeyframes;
    document.head.appendChild(style);
}

/**
 * Inicialización automática cuando el DOM esté listo
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('🌾 AgroTech Neomorphic System v1.0 - Inicializando...');
    
    // Esperar un tick para que otros scripts se carguen
    setTimeout(() => {
        inicializarTemaNeumorfico();
        console.log('✅ Sistema neumórfico aplicado correctamente');
    }, 50);
});

// Exportar funciones globalmente
window.AgroTech.UI = {
    mostrarNotificacion,
    mostrarErrorCritico,
    mostrarLoading,
    ocultarLoading,
    confirmarAccion,
    aplicarEstilosNeomorficos,
    aplicarAnimacionesTarjetas,
    inicializarTemaNeumorfico
};

console.log('🚀 AgroTech Neomorphic JavaScript cargado');
