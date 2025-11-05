/**
 * AGROTECH DIGITAL - Utilidades Futuristas para Móvil
 * Funciones JavaScript para mejorar la experiencia en dispositivos móviles
 * @version 1.0.0
 */

class AgrotechMobileFuturistic {
    constructor() {
        this.isMobile = window.innerWidth <= 767;
        this.init();
    }

    init() {
        if (this.isMobile) {
            console.log('🚀 Agrotech Mobile Futuristic Mode Activated');
            this.setupMobileOptimizations();
            this.setupGestureHandlers();
            this.setupScrollEffects();
            this.setupCardAnimations();
        }
    }

    /**
     * Configuración de optimizaciones móviles
     */
    setupMobileOptimizations() {
        // Prevenir zoom en inputs (iOS)
        const viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
            viewport.setAttribute('content', 
                'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'
            );
        }

        // Optimizar scroll performance
        document.body.style.webkitOverflowScrolling = 'touch';

        // Prevenir pull-to-refresh en Chrome móvil
        document.body.style.overscrollBehavior = 'none';
    }

    /**
     * Manejadores de gestos táctiles
     */
    setupGestureHandlers() {
        let touchStartX = 0;
        let touchEndX = 0;

        // Swipe para abrir/cerrar sidebar
        document.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            this.handleSwipeGesture(touchStartX, touchEndX);
        }, { passive: true });
    }

    handleSwipeGesture(startX, endX) {
        const swipeThreshold = 100;
        const diff = endX - startX;

        // Swipe desde la izquierda para abrir menú
        if (startX < 50 && diff > swipeThreshold) {
            this.openSidebar();
        }

        // Swipe hacia la izquierda para cerrar menú
        if (startX > window.innerWidth - 280 && diff < -swipeThreshold) {
            this.closeSidebar();
        }
    }

    openSidebar() {
        const sidebar = document.getElementById('mobile-sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        
        if (sidebar && overlay) {
            sidebar.classList.add('show');
            overlay.classList.add('show');
            this.triggerHapticFeedback('light');
        }
    }

    closeSidebar() {
        const sidebar = document.getElementById('mobile-sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        
        if (sidebar && overlay) {
            sidebar.classList.remove('show');
            overlay.classList.remove('show');
            this.triggerHapticFeedback('light');
        }
    }

    /**
     * Efectos de scroll parallax suaves
     */
    setupScrollEffects() {
        let ticking = false;

        window.addEventListener('scroll', () => {
            if (!ticking) {
                window.requestAnimationFrame(() => {
                    this.updateScrollEffects();
                    ticking = false;
                });
                ticking = true;
            }
        }, { passive: true });
    }

    updateScrollEffects() {
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('[data-parallax]');

        parallaxElements.forEach(element => {
            const speed = element.dataset.parallax || 0.5;
            const yPos = -(scrolled * speed);
            element.style.transform = `translateY(${yPos}px)`;
        });
    }

    /**
     * Animaciones de entrada para cards
     */
    setupCardAnimations() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        // Observar todas las cards
        document.querySelectorAll('.card').forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(30px)';
            card.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
            observer.observe(card);
        });
    }

    /**
     * Feedback háptico (Vibration API)
     */
    triggerHapticFeedback(type = 'medium') {
        if ('vibrate' in navigator) {
            const patterns = {
                light: 10,
                medium: 20,
                heavy: 30,
                success: [10, 50, 10],
                error: [20, 100, 20]
            };
            navigator.vibrate(patterns[type] || patterns.medium);
        }
    }

    /**
     * Mostrar toast notification
     */
    showToast(message, type = 'success', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast-notification ${type}`;
        
        const iconMap = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            info: 'fa-info-circle',
            warning: 'fa-exclamation-triangle'
        };

        toast.innerHTML = `
            <div class="toast-icon">
                <i class="fas ${iconMap[type] || iconMap.success}"></i>
            </div>
            <div class="toast-content">
                <div class="toast-title">${type.charAt(0).toUpperCase() + type.slice(1)}</div>
                <div class="toast-message">${message}</div>
            </div>
        `;

        document.body.appendChild(toast);
        
        this.triggerHapticFeedback(type === 'error' ? 'error' : 'success');

        setTimeout(() => {
            toast.style.animation = 'slideOutUp 0.4s ease-in forwards';
            setTimeout(() => toast.remove(), 400);
        }, duration);
    }

    /**
     * Crear skeleton loader
     */
    createSkeletonLoader(container, type = 'card') {
        const templates = {
            card: `
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-text"></div>
                <div class="skeleton skeleton-text" style="width: 80%"></div>
            `,
            list: `
                <div style="display: flex; gap: 12px; margin-bottom: 16px;">
                    <div class="skeleton skeleton-avatar"></div>
                    <div style="flex: 1;">
                        <div class="skeleton skeleton-text"></div>
                        <div class="skeleton skeleton-text" style="width: 60%"></div>
                    </div>
                </div>
            `
        };

        container.innerHTML = templates[type] || templates.card;
    }

    /**
     * Animar valor numérico (count up)
     */
    animateValue(element, start, end, duration = 1000) {
        const range = end - start;
        const increment = range / (duration / 16);
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
                current = end;
                clearInterval(timer);
            }
            element.textContent = Math.round(current);
        }, 16);
    }

    /**
     * Crear efecto ripple en botones
     */
    addRippleEffect(element) {
        element.classList.add('ripple-effect');
        
        element.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            ripple.style.cssText = `
                position: absolute;
                left: ${x}px;
                top: ${y}px;
                width: 0;
                height: 0;
                border-radius: 50%;
                background: rgba(53, 184, 53, 0.3);
                transform: translate(-50%, -50%);
                animation: ripple 0.6s ease-out;
                pointer-events: none;
            `;

            this.appendChild(ripple);

            setTimeout(() => ripple.remove(), 600);
        });
    }

    /**
     * Lazy loading de imágenes
     */
    setupLazyLoading() {
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.add('loaded');
                    imageObserver.unobserve(img);
                }
            });
        });

        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }

    /**
     * Pull to refresh
     */
    setupPullToRefresh(callback) {
        let startY = 0;
        let currentY = 0;
        let isPulling = false;

        document.addEventListener('touchstart', (e) => {
            if (window.scrollY === 0) {
                startY = e.touches[0].pageY;
                isPulling = true;
            }
        }, { passive: true });

        document.addEventListener('touchmove', (e) => {
            if (!isPulling) return;
            currentY = e.touches[0].pageY;
            const pullDistance = currentY - startY;

            if (pullDistance > 100) {
                // Mostrar indicador de refresh
                this.showRefreshIndicator();
            }
        }, { passive: true });

        document.addEventListener('touchend', () => {
            if (isPulling && currentY - startY > 100) {
                callback();
                this.triggerHapticFeedback('medium');
            }
            isPulling = false;
            this.hideRefreshIndicator();
        }, { passive: true });
    }

    showRefreshIndicator() {
        // Implementar indicador visual
        console.log('🔄 Pull to refresh triggered');
    }

    hideRefreshIndicator() {
        // Ocultar indicador
    }

    /**
     * Detectar modo oscuro del sistema
     */
    detectSystemDarkMode() {
        const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
        return darkModeQuery.matches;
    }

    /**
     * Performance monitoring
     */
    monitorPerformance() {
        if ('performance' in window) {
            window.addEventListener('load', () => {
                const perfData = performance.getEntriesByType('navigation')[0];
                console.log('📊 Performance Metrics:');
                console.log(`   DOM Content Loaded: ${perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart}ms`);
                console.log(`   Page Load: ${perfData.loadEventEnd - perfData.loadEventStart}ms`);
            });
        }
    }

    /**
     * Añadir efectos de brillo al hacer scroll
     */
    addScrollGlowEffects() {
        const cards = document.querySelectorAll('.card');
        
        window.addEventListener('scroll', () => {
            cards.forEach(card => {
                const rect = card.getBoundingClientRect();
                const isVisible = rect.top < window.innerHeight && rect.bottom > 0;
                
                if (isVisible) {
                    const scrollProgress = (window.innerHeight - rect.top) / window.innerHeight;
                    const glowIntensity = Math.min(scrollProgress, 0.3);
                    card.style.boxShadow = `
                        0 8px 32px rgba(0, 0, 0, 0.3),
                        0 0 0 1px rgba(53, 184, 53, 0.1) inset,
                        0 0 ${glowIntensity * 100}px rgba(53, 184, 53, ${glowIntensity})
                    `;
                }
            });
        }, { passive: true });
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.agrotechMobile = new AgrotechMobileFuturistic();
    
    // Ejemplos de uso:
    
    // Animar números en stats
    const statElements = document.querySelectorAll('.stat-value, h4.my-1, h3.mb-0');
    statElements.forEach(el => {
        const finalValue = parseInt(el.textContent) || 0;
        if (finalValue > 0 && window.agrotechMobile.isMobile) {
            window.agrotechMobile.animateValue(el, 0, finalValue, 1500);
        }
    });

    // Añadir ripple a botones
    const buttons = document.querySelectorAll('.btn, .fab-button');
    buttons.forEach(btn => {
        if (window.agrotechMobile.isMobile) {
            window.agrotechMobile.addRippleEffect(btn);
        }
    });

    // Setup lazy loading
    if (window.agrotechMobile.isMobile) {
        window.agrotechMobile.setupLazyLoading();
        window.agrotechMobile.addScrollGlowEffects();
        window.agrotechMobile.monitorPerformance();
    }
});

// Exportar para uso global
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AgrotechMobileFuturistic;
}
