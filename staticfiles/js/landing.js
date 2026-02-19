/**
 * AGROTECH DIGITAL - Landing Page JavaScript
 * Main functionality and interactions
 * Version: 2.0.0
 */

// ============================================
// CONFIGURATION
// ============================================
const CONFIG = {
    BACKEND_URL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' ? 'http://localhost:8000' : 'https://agrotechcolombia.com',
    LOGIN_URL: 'https://agrotechcolombia.netlify.app/templates/authentication/login.html',
    DASHBOARD_URL: 'https://agrotechcolombia.netlify.app/templates/vertical_base.html',
    API_VERSION: 'v1',
    DEBUG: false
};

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Log to console only in debug mode
 */
function debugLog(...args) {
    if (CONFIG.DEBUG) {
        console.log('[Agrotech Debug]', ...args);
    }
}

/**
 * Show notification toast
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        background: ${type === 'error' ? '#F44336' : type === 'success' ? '#4CAF50' : '#2196F3'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        animation: slideInRight 0.3s ease-out;
        max-width: 400px;
    `;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ============================================
// NAVIGATION
// ============================================

/**
 * Redirect to login page
 */
function redirectToLogin() {
    debugLog('Redirecting to login...');
    window.location.href = CONFIG.LOGIN_URL;
}

/**
 * Redirect to dashboard
 */
function redirectToDashboard() {
    debugLog('Redirecting to dashboard...');
    window.location.href = CONFIG.DASHBOARD_URL;
}

/**
 * Initialize mobile menu
 */
function initMobileMenu() {
    const navBurger = document.getElementById('navBurger');
    const navLinks = document.getElementById('navLinks');

    if (!navBurger || !navLinks) return;

    navBurger.addEventListener('click', () => {
        navBurger.classList.toggle('active');
        navLinks.classList.toggle('active');
        document.body.style.overflow = navLinks.classList.contains('active') ? 'hidden' : '';
    });

    // Close menu when clicking a link
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', () => {
            navBurger.classList.remove('active');
            navLinks.classList.remove('active');
            document.body.style.overflow = '';
        });
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!navLinks.contains(e.target) && !navBurger.contains(e.target) && navLinks.classList.contains('active')) {
            navBurger.classList.remove('active');
            navLinks.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
}

// ============================================
// SCROLL EFFECTS
// ============================================

/**
 * Initialize header scroll effect
 */
function initHeaderScroll() {
    const header = document.getElementById('header');
    if (!header) return;

    let lastScroll = 0;
    
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
        
        // Hide header on scroll down, show on scroll up
        if (currentScroll > lastScroll && currentScroll > 100) {
            header.style.transform = 'translateY(-100%)';
        } else {
            header.style.transform = 'translateY(0)';
        }
        
        lastScroll = currentScroll;
    });
}

/**
 * Initialize scroll to top button
 */
function initScrollToTop() {
    const scrollToTopBtn = document.getElementById('scrollToTop');
    if (!scrollToTopBtn) return;

    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            scrollToTopBtn.classList.add('visible');
        } else {
            scrollToTopBtn.classList.remove('visible');
        }
    });
}

/**
 * Scroll to top function
 */
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

/**
 * Initialize smooth scrolling for anchor links
 */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#' || href === '#inicio') return;
            
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                const header = document.getElementById('header');
                const headerHeight = header ? header.offsetHeight : 80;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - headerHeight;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// ============================================
// REVEAL ANIMATIONS
// ============================================

/**
 * Initialize reveal animations on scroll
 */
function initRevealAnimations() {
    const revealElements = document.querySelectorAll('.reveal');
    
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                revealObserver.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    revealElements.forEach(element => {
        revealObserver.observe(element);
    });
}

// ============================================
// API TESTING
// ============================================

/**
 * Test API connection
 */
async function testAPI() {
    const btn = document.getElementById('testApiBtn');
    const resultDiv = document.getElementById('apiResult');
    
    if (!btn || !resultDiv) return;
    
    btn.disabled = true;
    btn.textContent = '⏳ Probando conexión...';
    
    try {
        debugLog('Testing API connection to:', CONFIG.BACKEND_URL);
        
        const response = await fetch(`${CONFIG.BACKEND_URL}/api/parcels/summary/`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            },
            mode: 'cors'
        });
        
        if (response.ok) {
            const data = await response.json();
            resultDiv.innerHTML = `
                <div style="background: rgba(76, 175, 80, 0.1); border: 1px solid rgba(76, 175, 80, 0.3); border-radius: var(--radius-md); padding: var(--spacing-md); color: var(--brand-green-light);">
                    <h4 style="margin-bottom: var(--spacing-sm);">✅ Conexión Exitosa</h4>
                    <pre style="background: var(--dark-bg); padding: var(--spacing-sm); border-radius: var(--radius-sm); overflow-x: auto; font-size: 0.85rem; white-space: pre-wrap;">${JSON.stringify(data, null, 2)}</pre>
                </div>
            `;
            showToast('API conectada correctamente', 'success');
        } else if (response.status === 401) {
            resultDiv.innerHTML = `
                <div style="background: rgba(255, 152, 0, 0.1); border: 1px solid rgba(255, 152, 0, 0.3); border-radius: var(--radius-md); padding: var(--spacing-md); color: var(--brand-orange-light);">
                    <h4 style="margin-bottom: var(--spacing-sm);">🔐 API Funcional - Autenticación Requerida</h4>
                    <p>Estado: ${response.status}</p>
                    <p>La API está funcionando correctamente. Este endpoint requiere autenticación.</p>
                    <p>Para acceder a todos los datos, <a href="#" onclick="redirectToLogin()" style="color: var(--brand-green); text-decoration: underline;">inicie sesión en la plataforma</a>.</p>
                </div>
            `;
            showToast('API funcional - Se requiere autenticación', 'info');
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('Error testing API:', error);
        resultDiv.innerHTML = `
            <div style="background: rgba(244, 67, 54, 0.1); border: 1px solid rgba(244, 67, 54, 0.3); border-radius: var(--radius-md); padding: var(--spacing-md); color: #ff6b6b;">
                <h4 style="margin-bottom: var(--spacing-sm);">⚠️ Error de Conexión</h4>
                <p><strong>Error:</strong> ${error.message}</p>
                <p>Verifica que el backend esté ejecutándose en: <code style="background: var(--dark-bg); padding: 4px 8px; border-radius: 4px;">${CONFIG.BACKEND_URL}</code></p>
                <p style="margin-top: 1rem; font-size: 0.9rem;">Posibles causas:</p>
                <ul style="margin-left: 1.5rem; font-size: 0.9rem;">
                    <li>El backend no está en ejecución</li>
                    <li>Problemas de CORS</li>
                    <li>URL del backend incorrecta</li>
                    <li>Firewall o configuración de red</li>
                </ul>
            </div>
        `;
        showToast('Error al conectar con la API', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🧪 Probar API en Vivo';
    }
}

// ============================================
// STATISTICS COUNTER ANIMATION
// ============================================

/**
 * Animate numbers when they come into view
 */
function initCounterAnimation() {
    const counters = document.querySelectorAll('.stat-value, .hero-stat-value');
    
    const counterObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = entry.target;
                const text = target.textContent;
                const number = parseFloat(text.replace(/[^\d.]/g, ''));
                
                if (!isNaN(number)) {
                    animateCounter(target, 0, number, 2000);
                }
                
                counterObserver.unobserve(target);
            }
        });
    }, { threshold: 0.5 });
    
    counters.forEach(counter => {
        counterObserver.observe(counter);
    });
}

/**
 * Animate a counter from start to end
 */
function animateCounter(element, start, end, duration) {
    const originalText = element.textContent;
    const suffix = originalText.replace(/[\d.]/g, '').trim();
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const current = start + (end - start) * easeOutQuad(progress);
        const decimals = end % 1 !== 0 ? 2 : 0;
        
        element.textContent = current.toFixed(decimals) + (suffix ? ' ' + suffix : '');
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

/**
 * Easing function for smooth animation
 */
function easeOutQuad(t) {
    return t * (2 - t);
}

// ============================================
// SESSION MANAGEMENT
// ============================================

/**
 * Check if user is logged in
 */
function checkUserSession() {
    const token = localStorage.getItem('accessToken');
    const loginButtons = document.querySelectorAll('[onclick*="redirectToLogin"]');
    
    if (token) {
        debugLog('User is logged in');
        loginButtons.forEach(btn => {
            btn.textContent = btn.textContent.includes('Iniciar') ? 'Ir al Dashboard' : btn.textContent;
            btn.onclick = redirectToDashboard;
        });
    } else {
        debugLog('User is not logged in');
    }
}

// ============================================
// INITIALIZATION
// ============================================

/**
 * Initialize all functionality when DOM is ready
 */
function init() {
    debugLog('Initializing Agrotech Landing Page...');
    
    // Initialize all features
    initMobileMenu();
    initHeaderScroll();
    initScrollToTop();
    initSmoothScroll();
    initRevealAnimations();
    initCounterAnimation();
    checkUserSession();
    
    // Make functions globally available
    window.redirectToLogin = redirectToLogin;
    window.redirectToDashboard = redirectToDashboard;
    window.scrollToTop = scrollToTop;
    window.testAPI = testAPI;
    
    // Log initialization complete
    console.log('%c🌱 Agrotech Digital - Landing Page Initialized', 'color: #4CAF50; font-size: 16px; font-weight: bold;');
    console.log('%cVersion 2.0.0 | Neumorphic Dark Theme', 'color: #FF6F00; font-size: 12px;');
    
    debugLog('Initialization complete');
}

// Run initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
