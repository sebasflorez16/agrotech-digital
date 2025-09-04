/**
 * Módulo para mostrar detalles del pronóstico del tiempo con animaciones Lottie
 * Este módulo mejora la visualización de datos meteorológicos con animaciones detalladas
 */

// Mapeo de condiciones climáticas a animaciones Lottie utilizando Assets de LottieFiles
const WEATHER_ANIMATIONS = {
    // Soleado
    sunny: "https://assets3.lottiefiles.com/packages/lf20_xlkxtmul.json",
    clear: "https://assets3.lottiefiles.com/packages/lf20_xlkxtmul.json",
    
    // Parcialmente nublado
    partly_cloudy: "https://assets3.lottiefiles.com/packages/lf20_trr3kzyu.json",
    
    // Nublado
    cloudy: "https://assets1.lottiefiles.com/packages/lf20_jh9gfdye.json",
    overcast: "https://assets1.lottiefiles.com/packages/lf20_jh9gfdye.json",
    
    // Lluvia
    rain: "https://assets8.lottiefiles.com/packages/lf20_bco9p3ju.json",
    showers: "https://assets8.lottiefiles.com/packages/lf20_bco9p3ju.json",
    
    // Tormenta
    thunderstorm: "https://assets10.lottiefiles.com/packages/lf20_kwtXhLVQNj.json",
    storm: "https://assets10.lottiefiles.com/packages/lf20_kwtXhLVQNj.json",
    
    // Nieve
    snow: "https://assets6.lottiefiles.com/packages/lf20_7fwvvesa.json",
    
    // Niebla
    fog: "https://assets10.lottiefiles.com/packages/lf20_xYfTVX.json",
    mist: "https://assets10.lottiefiles.com/packages/lf20_xYfTVX.json",
    
    // Default (sol y nubes)
    default: "https://assets3.lottiefiles.com/packages/lf20_trr3kzyu.json"
};

// Mapeo de condiciones climáticas a descripciones
const WEATHER_DESCRIPTIONS = {
    sunny: "Día soleado con cielos despejados. Excelentes condiciones para actividades al aire libre.",
    clear: "Cielo despejado. Ideal para observación del campo y trabajos agrícolas.",
    partly_cloudy: "Parcialmente nublado. Buenas condiciones generales con periodos de sol.",
    cloudy: "Predominantemente nublado. La reducción de luz solar puede afectar ligeramente a los cultivos.",
    overcast: "Cielo cubierto. La radiación solar será limitada durante el día.",
    rain: "Precipitaciones. Buen aporte hídrico para los cultivos, monitoree para evitar encharcamientos.",
    showers: "Chubascos intermitentes. Verifique el sistema de drenaje para evitar acumulaciones excesivas de agua.",
    thunderstorm: "Tormentas eléctricas. Precaución con equipos eléctricos y posibles daños por fuertes vientos.",
    storm: "Condiciones de tormenta. Considere medidas de protección para cultivos sensibles.",
    snow: "Nevada. Proteja cultivos sensibles a heladas y bajas temperaturas.",
    fog: "Presencia de niebla. La visibilidad será reducida, especialmente en horas de la mañana.",
    mist: "Ambiente brumoso. La humedad ambiental es alta, favorable para ciertos cultivos.",
    default: "Condiciones variables. Monitoree los cambios durante el día para ajustar las actividades agrícolas."
};

/**
 * Determina el tipo de condición climática basado en los datos meteorológicos
 * @param {Object} dayData - Datos meteorológicos del día
 * @returns {String} - Clave de la condición climática
 */
function determineWeatherCondition(dayData) {
    // Usar valores calculados si están disponibles, sino usar lógica de extracción
    let precipitation = dayData.calculated_precipitation;
    if (precipitation === null || precipitation === undefined) {
        precipitation = parseFloat(dayData.Precip_total || dayData.precipitation || dayData.precip_mm || dayData.precip || dayData.rainfall || 0);
    }
    
    let windSpeed = dayData.calculated_wind_speed;
    if (windSpeed === null || windSpeed === undefined) {
        windSpeed = parseFloat(dayData.Wind_speed || dayData.wind_speed || dayData.wind_speed_avg || 0);
    }
    
    // Otros campos que no se calculan, usar lógica de extracción original
    const cloudCover = parseFloat(dayData.Cloud_cover || dayData.cloud_cover || dayData.cloudiness || dayData.cloud_pct || 0);
    const humidity = parseFloat(dayData.Rel_humidity || dayData.humidity || dayData.humidity_avg || 0);
    
    // Si hay un campo explícito para el estado del tiempo, úsalo primero
    if (dayData.weather_condition || dayData.weathercode || dayData.condition) {
        const condition = dayData.weather_condition || dayData.weathercode || dayData.condition;
        
        // Comprobar palabras clave comunes en el texto de condición
        if (typeof condition === 'string') {
            const condLower = condition.toLowerCase();
            if (condLower.includes('thunder') || condLower.includes('tormenta') || condLower.includes('storm')) return 'thunderstorm';
            if (condLower.includes('rain') || condLower.includes('lluvia')) return 'rain';
            if (condLower.includes('shower') || condLower.includes('chubascos')) return 'showers';
            if (condLower.includes('snow') || condLower.includes('nieve')) return 'snow';
            if (condLower.includes('fog') || condLower.includes('niebla') || condLower.includes('mist')) return 'fog';
            if (condLower.includes('overcast') || condLower.includes('cubierto')) return 'overcast';
            if (condLower.includes('cloud') || condLower.includes('nublado')) return 'cloudy';
            if (condLower.includes('clear') || condLower.includes('despejado') || condLower.includes('sunny') || condLower.includes('soleado')) return 'sunny';
        } 
        // Si es un código numérico, intentar interpretarlo
        else if (typeof condition === 'number') {
            // Códigos comunes de condiciones meteorológicas (formato simplificado)
            if (condition >= 200 && condition < 300) return 'thunderstorm';
            if (condition >= 300 && condition < 500) return 'showers';
            if (condition >= 500 && condition < 600) return 'rain';
            if (condition >= 600 && condition < 700) return 'snow';
            if (condition >= 700 && condition < 800) return 'fog';
            if (condition === 800) return 'sunny';
            if (condition > 800 && condition < 900) return 'partly_cloudy';
        }
    }
    
    // Lógica basada en valores numéricos de parámetros meteorológicos
    // Primero tormenta/lluvia que son más impactantes
    if (precipitation > 30) return 'thunderstorm';
    if (precipitation > 10) return 'rain';
    if (precipitation > 0) return 'showers';
    
    // Luego condiciones de nubosidad
    if (cloudCover > 85) return 'overcast';
    if (cloudCover > 60) return 'cloudy';
    if (cloudCover > 15) return 'partly_cloudy';
    
    // Condiciones de visibilidad reducida
    if (humidity > 90 && windSpeed < 10) return 'fog';
    
    // Por defecto, si hay poco nublado y sin precipitación, es soleado
    return 'sunny';
}

/**
 * Obtiene la URL de la animación Lottie para una condición climática
 * @param {String} condition - Condición climática
 * @returns {String} - URL de la animación Lottie
 */
function getLottieAnimation(condition) {
    return WEATHER_ANIMATIONS[condition] || WEATHER_ANIMATIONS.default;
}

/**
 * Obtiene la descripción para una condición climática
 * @param {String} condition - Condición climática
 * @returns {String} - Descripción textual
 */
function getWeatherDescription(condition) {
    return WEATHER_DESCRIPTIONS[condition] || WEATHER_DESCRIPTIONS.default;
}

/**
 * Muestra el modal con detalles meteorológicos y animación
 * @param {Object} dayData - Datos meteorológicos del día seleccionado
 */
function showWeatherDetailModal(dayData) {
    console.log('[WEATHER_DETAIL] Mostrando modal para:', dayData);
    
    // Obtener elementos del DOM
    const modal = document.getElementById('weatherDetailModal');
    const modalTitle = document.getElementById('weatherDetailDate');
    const animationContainer = document.getElementById('weatherAnimationContainer');
    const conditionTitle = document.getElementById('weatherConditionTitle');
    const weatherDescription = document.getElementById('weatherDescription');
    
    // Extraer fecha del objeto
    let dateStr = dayData.date || dayData.Date || '';
    const date = new Date(dateStr);
    const formattedDate = date.toLocaleDateString('es-ES', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });
    
    // Actualizar título del modal
    modalTitle.textContent = formattedDate;
    
    // Determinar condición climática y obtener animación
    const weatherCondition = determineWeatherCondition(dayData);
    const lottieUrl = getLottieAnimation(weatherCondition);
    
    // Actualizar título de condición climática
    switch(weatherCondition) {
        case 'sunny':
        case 'clear':
            conditionTitle.textContent = 'Soleado';
            break;
        case 'partly_cloudy':
            conditionTitle.textContent = 'Parcialmente nublado';
            break;
        case 'cloudy':
        case 'overcast':
            conditionTitle.textContent = 'Nublado';
            break;
        case 'rain':
        case 'showers':
            conditionTitle.textContent = 'Lluvioso';
            break;
        case 'thunderstorm':
        case 'storm':
            conditionTitle.textContent = 'Tormenta';
            break;
        case 'snow':
            conditionTitle.textContent = 'Nevada';
            break;
        case 'fog':
        case 'mist':
            conditionTitle.textContent = 'Niebla';
            break;
        default:
            conditionTitle.textContent = 'Variable';
    }
    
    // Configurar la animación Lottie con manejo mejorado de errores
    try {
        // Limpiar el contenedor por si tenía una animación previa
        animationContainer.innerHTML = '';
        
        // Crear y configurar el elemento lottie-player
        const lottiePlayer = document.createElement('lottie-player');
        lottiePlayer.setAttribute('src', lottieUrl);
        lottiePlayer.setAttribute('background', 'transparent');
        lottiePlayer.setAttribute('speed', '1');
        lottiePlayer.style.width = '220px';
        lottiePlayer.style.height = '220px';
        lottiePlayer.setAttribute('loop', '');
        lottiePlayer.setAttribute('autoplay', '');
        lottiePlayer.setAttribute('data-condition', weatherCondition);
        lottiePlayer.setAttribute('aria-label', `Animación del clima: ${conditionTitle.textContent}`);
        
        // Manejar errores de carga
        lottiePlayer.addEventListener('error', () => {
            console.warn('No se pudo cargar la animación Lottie, mostrando alternativa');
            mostrarIconoAlternativo();
        });
        
        // No hay necesidad de usar timeout con un event listener para 'load'
        // Solo usamos un flag para rastrear si se cargó
        let lottieLoaded = false;
        
        // Listener para cuando la animación se carga correctamente
        lottiePlayer.addEventListener('load', () => {
            lottieLoaded = true;
            console.log('Animación Lottie cargada correctamente');
        });
        
        // Listener para cuando la animación está lista para reproducirse
        lottiePlayer.addEventListener('ready', () => {
            lottieLoaded = true;
        });
        
        // Solo usamos un timeout corto para verificar si Lottie está funcionando
        setTimeout(() => {
            if (!lottieLoaded) {
                console.log('Usando alternativa para la animación');
                mostrarIconoAlternativo();
            }
        }, 2000);
        
        // Añadir al contenedor
        animationContainer.appendChild(lottiePlayer);
    } catch (err) {
        console.error('Error al inicializar la animación Lottie:', err);
        mostrarIconoAlternativo();
    }
    
    // Función para mostrar un icono alternativo cuando falla la animación
    function mostrarIconoAlternativo(condition = weatherCondition) {
        // Usar el contenedor de animación si existe o buscar el contenedor por ID
        const container = animationContainer || document.getElementById('weatherAnimationContainer');
        if (!container) return;
        
        // Mapeo de condiciones a iconos de Font Awesome
        const iconMap = {
            'rain': 'cloud-rain',
            'showers': 'cloud-rain',
            'thunderstorm': 'bolt',
            'storm': 'bolt',
            'snow': 'snowflake',
            'fog': 'smog',
            'mist': 'smog',
            'cloudy': 'cloud',
            'overcast': 'cloud',
            'partly_cloudy': 'cloud-sun',
            'sunny': 'sun',
            'clear': 'sun',
            'default': 'sun'
        };
        
        // Obtener el icono adecuado
        const icon = iconMap[condition] || 'sun';
        
        // Crear el HTML con el icono
        container.innerHTML = `<div class="p-4 text-center">
            <i class="fas fa-${icon}" 
               style="font-size: 100px; color: #FF9800; animation: pulse 2s infinite;"
               aria-hidden="true"></i>
            <p class="mt-2">Condición: ${conditionTitle ? conditionTitle.textContent : condition}</p>
        </div>`;
    }
    
    // Actualizar descripción del tiempo
    weatherDescription.textContent = getWeatherDescription(weatherCondition);
    
    // === CAMPOS DISPONIBLES EN EOSDA ===
    console.log("[WEATHER_DETAIL] Campos disponibles en dayData:", Object.keys(dayData));
    
    // Temperaturas del aire - usar los nombres de campos reales de EOSDA
    const tempMax = dayData.temperature_max || dayData.Temp_air_max;
    const tempMin = dayData.temperature_min || dayData.Temp_air_min;
    
    document.getElementById('detailTempMax').textContent = tempMax ? `${parseFloat(tempMax).toFixed(1)}°C` : 'N/A';
    document.getElementById('detailTempMin').textContent = tempMin ? `${parseFloat(tempMin).toFixed(1)}°C` : 'N/A';
    
    console.log("[WEATHER_DETAIL] Temperaturas - Max:", tempMax, "Min:", tempMin);
    
    // Temperaturas del suelo (usar los nombres de campos de EOSDA si están disponibles)
    if (document.getElementById('detailTempLandMax')) {
        const tempLandMax = dayData.Temp_land_max;
        document.getElementById('detailTempLandMax').textContent = tempLandMax ? `${parseFloat(tempLandMax).toFixed(1)}°C` : 'N/A';
    }
    if (document.getElementById('detailTempLandMin')) {
        const tempLandMin = dayData.Temp_land_min;
        document.getElementById('detailTempLandMin').textContent = tempLandMin ? `${parseFloat(tempLandMin).toFixed(1)}°C` : 'N/A';
    }
    
    // Humedad relativa - usar los nombres de campos reales de EOSDA
    const humidityValue = dayData.humidity || dayData.Rel_humidity;
    document.getElementById('detailHumidity').textContent = humidityValue ? `${parseFloat(humidityValue).toFixed(0)}%` : 'N/A';
    
    console.log("[WEATHER_DETAIL] Humedad:", humidityValue);
    
    // Precipitación - usar campos reales de EOSDA
    let precipTotal = dayData.precipitation || dayData.calculated_precipitation || 0;
    
    // Si no hay valor directo, intentar sumar valores horarios de Rain
    if (precipTotal === 0 && dayData.Rain && typeof dayData.Rain === 'object') {
        Object.values(dayData.Rain).forEach(val => precipTotal += parseFloat(val) || 0);
    }
    document.getElementById('detailPrecipitation').textContent = precipTotal >= 0 ? `${precipTotal.toFixed(1)} mm` : 'N/A';
    
    console.log("[WEATHER_DETAIL] Precipitación:", precipTotal);
    
    // Velocidad del viento - usar campos reales de EOSDA
    let windAvg = dayData.wind_speed || dayData.calculated_wind_speed;
    
    // Si no hay valor directo, intentar calcular promedio de valores horarios de Windspeed
    if ((windAvg === null || windAvg === undefined) && dayData.Windspeed && typeof dayData.Windspeed === 'object') {
        const windVals = Object.values(dayData.Windspeed)
            .map(val => parseFloat(val))
            .filter(val => !isNaN(val));
        if (windVals.length > 0) {
            windAvg = windVals.reduce((a, b) => a + b, 0) / windVals.length;
        }
    }
    
    console.log("[WEATHER_DETAIL] Viento promedio:", windAvg);
    document.getElementById('detailWindSpeed').textContent = (windAvg !== null && windAvg !== undefined) ? `${windAvg.toFixed(1)} km/h` : 'N/A';
    
    // Profundidad de nieve (si está disponible en el HTML)
    if (document.getElementById('detailSnowDepth'))
        document.getElementById('detailSnowDepth').textContent = dayData.Snow_depth ? `${parseFloat(dayData.Snow_depth).toFixed(1)} cm` : '0.0 cm';
    
    // === OCULTAR CAMPOS NO DISPONIBLES EN EOSDA ===
    // Estos campos NO están disponibles en la respuesta de EOSDA y deben ocultarse
    hideUnavailableFields();
    
    // Actualizar la barra de humedad usando el valor ya obtenido
    const humidityBarValue = parseFloat(humidityValue || 0);
    if (humidityBarValue > 0) {
        // Ya se actualizó el texto arriba, solo actualizar la barra
        document.getElementById('humidityProgressBar').style.width = `${humidityBarValue}%`;
        
        // Colorear la barra de humedad según el valor
        const humidityBar = document.getElementById('humidityProgressBar');
        if (humidityBar) {
            if (humidityBarValue > 80) {
                humidityBar.className = "progress-bar bg-primary"; // Azul para muy húmedo
            } else if (humidityBarValue > 60) {
                humidityBar.className = "progress-bar bg-info"; // Celeste para húmedo normal
            } else if (humidityBarValue > 40) {
                humidityBar.className = "progress-bar bg-success"; // Verde para humedad moderada
            } else if (humidityBarValue > 20) {
                humidityBar.className = "progress-bar bg-warning"; // Amarillo para seco
            } else {
                humidityBar.className = "progress-bar bg-danger"; // Rojo para muy seco
            }
        }
    } else {
        document.getElementById('humidityProgressBar').style.width = '0%';
    }
    
    // Mostrar el modal
    const modalInstance = new bootstrap.Modal(modal, {
        keyboard: true,
        focus: true,
        backdrop: true
    });
    modalInstance.show();
    
    // Asegurar que el contenido del modal tenga un buen contraste para accesibilidad
    const modalContent = modal.querySelector('.modal-content');
    if (modalContent) {
        modalContent.style.color = '#212529';  // Color oscuro para contraste
    }
    
    console.log('[WEATHER_DETAIL] Modal configurado y mostrado con datos EOSDA únicamente');
}

/**
 * Hace que las tarjetas del pronóstico sean clickeables
 */
function setupWeatherCardInteractivity() {
    // Cuando se complete el renderizado de las tarjetas
    document.addEventListener('weatherCardsRendered', function() {
        // Seleccionar todas las tarjetas de pronóstico
        const weatherCards = document.querySelectorAll('.weather-day-card');            // Añadir evento click a cada tarjeta
        weatherCards.forEach((card, index) => {
            // Añadir cursor pointer y efecto hover
            card.style.cursor = 'pointer';
            card.style.transition = 'transform 0.2s ease, box-shadow 0.2s ease';
            
            // Mejorar la accesibilidad de las tarjetas
            card.setAttribute('tabindex', '0');
            card.setAttribute('role', 'button');
            card.setAttribute('aria-label', `Ver detalles del pronóstico para el día ${index + 1}`);
            
            // Añadir efectos de hover
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-5px)';
                this.style.boxShadow = '0 10px 20px rgba(0,0,0,0.1)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '';
            });
            
            // Añadir eventos de foco para accesibilidad
            card.addEventListener('focus', function() {
                this.style.transform = 'translateY(-5px)';
                this.style.boxShadow = '0 10px 20px rgba(0,0,0,0.1)';
                this.style.outline = '2px solid #4CAF50';
            });
            
            card.addEventListener('blur', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '';
                this.style.outline = '';
            });
            
            // Añadir evento click y tecla Enter para accesibilidad
            card.addEventListener('click', function() {
                // Obtener el día correspondiente desde el arreglo global
                if (window.weatherForecastData && window.weatherForecastData[index]) {
                    showWeatherDetailModal(window.weatherForecastData[index]);
                }
            });
            
            // Soporte para teclado (accesibilidad)
            card.addEventListener('keydown', function(event) {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    if (window.weatherForecastData && window.weatherForecastData[index]) {
                        showWeatherDetailModal(window.weatherForecastData[index]);
                    }
                }
            });
        });
        
        console.log('[WEATHER_DETAIL] Interactividad de tarjetas configurada');
    });
}

// Inicialización al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    setupWeatherCardInteractivity();
    console.log('[WEATHER_DETAIL] Módulo de detalles meteorológicos inicializado');
});

/**
 * Verifica si la librería Lottie está disponible y funciona correctamente
 * @returns {Promise<boolean>} - Promesa que se resuelve con true si Lottie está disponible
 */
function verificarLottieDisponible() {
    return new Promise((resolve) => {
        // Comprobar si ya existe lottie-player como elemento personalizado
        if (typeof customElements !== 'undefined' && customElements.get('lottie-player')) {
            console.log('[WEATHER_DETAIL] Lottie Player está disponible');
            resolve(true);
            return;
        }
        
        console.log('[WEATHER_DETAIL] Verificando disponibilidad de Lottie Player...');
        
        // Si no está disponible, intentamos cargar la librería
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/@lottiefiles/lottie-player@1.6.0/dist/lottie-player.js';
        script.async = true;
        
        // Listener para cuando el script carga correctamente
        script.onload = () => {
            console.log('[WEATHER_DETAIL] Lottie Player cargado correctamente');
            resolve(true);
        };
        
        // Listener para errores al cargar
        script.onerror = () => {
            console.warn('[WEATHER_DETAIL] Error al cargar Lottie Player, usando alternativas');
            resolve(false);
        };
        
        // Añadir el script al head
        document.head.appendChild(script);
        
        // Asegurar que siempre se resuelve después de un tiempo máximo
        setTimeout(() => {
            resolve(typeof customElements !== 'undefined' && customElements.get('lottie-player'));
        }, 2000);
    });
}

// No necesitamos el listener aquí ya que será llamado desde setupModalAccessibility

/**
 * Configura el estilo del backdrop del modal
 */
function configurarBackdropModal() {
    // Buscar el modal
    const weatherModal = document.getElementById('weatherDetailModal');
    if (!weatherModal) return;
    
    // Configurar evento para personalizar el backdrop
    weatherModal.addEventListener('show.bs.modal', function () {
        setTimeout(() => {
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => {
                backdrop.style.opacity = '0.2';
                backdrop.style.background = 'linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05))';
            });
            
            // Mejorar el efecto en el modal
            const modalContent = weatherModal.querySelector('.modal-content');
            if (modalContent) {
                modalContent.style.boxShadow = '0 8px 32px rgba(31, 38, 135, 0.15)';
            }
        }, 10);
    });
    
    console.log('[WEATHER_DETAIL] Configuración de backdrop aplicada');
}

// Gestiona correctamente la accesibilidad y el scroll del modal
function setupModalAccessibility() {
    const weatherModal = document.getElementById('weatherDetailModal');
    if (!weatherModal) return;
    
    // Cuando el modal se muestra
    weatherModal.addEventListener('shown.bs.modal', function () {
        // Verificar Lottie de forma asíncrona
        verificarLottieDisponible().then(lottieAvailable => {
            // Si Lottie no está disponible, podemos mostrar alternativas inmediatamente
            if (!lottieAvailable) {
                const animContainer = document.getElementById('weatherAnimationContainer');
                if (animContainer && animContainer.querySelector('lottie-player')) {
                    // Reemplazar con icono estático si ya hay un lottie-player pero no está disponible
                    const condition = animContainer.querySelector('lottie-player').getAttribute('data-condition') || 'default';
                    mostrarIconoAlternativo(condition);
                }
            }
        });
        
        // Asegurar que el modal está accesible
        weatherModal.setAttribute('role', 'dialog');
        weatherModal.setAttribute('aria-modal', 'true');
        
        // Asegurar que el botón de cerrar tenga el foco para mejorar la accesibilidad
        const closeButton = weatherModal.querySelector('.btn-close');
        if (closeButton) {
            setTimeout(() => {
                closeButton.focus();
            }, 100);
        }
    });
    
    // Cuando el modal se oculta
    weatherModal.addEventListener('hidden.bs.modal', function () {
        // Restaurar el scroll del cuerpo del documento
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
        
        // Eliminar cualquier backdrop residual
        const backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(backdrop => {
            backdrop.remove();
        });
        
        // Devolver el foco a un elemento apropiado en la página principal
        const weatherCards = document.querySelectorAll('.weather-day-card');
        if (weatherCards && weatherCards.length > 0) {
            weatherCards[0].focus();
            weatherCards[0].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        
        // Emitir evento de restauración de foco
        document.dispatchEvent(new CustomEvent('modalClosed'));
    });
    
    console.log('[WEATHER_DETAIL] Configuración de accesibilidad del modal aplicada');
}

// Inicializar la configuración del backdrop y accesibilidad cuando se carga la página
document.addEventListener('DOMContentLoaded', function() {
    setupWeatherCardInteractivity();
    configurarBackdropModal();
    setupModalAccessibility();
    console.log('[WEATHER_DETAIL] Módulo de detalles meteorológicos inicializado');
});

/**
 * Función simplificada ya que los campos no disponibles están ocultos en el HTML
 * Solo verifica que los campos estén correctamente configurados
 */
function hideUnavailableFields() {
    // Los campos no disponibles ya están ocultos en el HTML con display: none !important
    // Solo agregamos mensaje informativo si no existe
    const modal = document.getElementById('weatherDetailModal');
    if (modal) {
        let infoMessage = modal.querySelector('.eosda-info-message');
        if (!infoMessage) {
            infoMessage = document.createElement('div');
            infoMessage.className = 'eosda-info-message';
            infoMessage.style.cssText = `
                background: #e3f2fd;
                border: 1px solid #bbdefb;
                border-radius: 4px;
                padding: 8px 12px;
                margin: 10px 0;
                font-size: 0.85em;
                color: #1565c0;
                text-align: center;
            `;
            infoMessage.innerHTML = '<i class="fas fa-satellite me-2"></i>Algunos datos pueden no estar disponibles en el momento.';
            
            const modalBody = modal.querySelector('.modal-body');
            if (modalBody) {
                modalBody.appendChild(infoMessage);
            }
        }
    }
    
    console.log('[WEATHER_DETAIL] Solo se muestran campos disponibles en EOSDA');
}
