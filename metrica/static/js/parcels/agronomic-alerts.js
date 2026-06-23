/**
 * agronomic-alerts.js
 *
 * Capa visual de Alertas Agronómicas para el dashboard de parcelas.
 *
 * Responsabilidades:
 *   1. Consultar `/api/agronomic-alerts/parcelas/<id>/estado-hoy/` al
 *      seleccionar una parcela y renderizar:
 *        - Banner de estado del lote (verde/naranja/rojo + texto humano).
 *        - Tarjeta "Riesgo Activo" con qué pasa / qué hacer / cuándo +
 *          botones ✅ atendida / ⏸ posponer / ❌ descartar.
 *        - Lista resumida de alertas activas adicionales.
 *        - Indicador de frescura del dato (días desde última escena).
 *   2. Enviar feedback al backend (acciones del ViewSet) y refrescar.
 *
 * Diseño dark + liquid glass coherente con el resto del frontend.
 *
 * API expuesta:
 *   window.AgroAlerts.loadForParcel(parcelId)
 *   window.AgroAlerts.refresh()
 */

(function () {
    'use strict';

    const ENDPOINTS = {
        estadoHoy: (id) => `/api/agronomic-alerts/parcelas/${id}/estado-hoy/`,
        atender: (id) => `/api/agronomic-alerts/alertas/${id}/atender/`,
        posponer: (id) => `/api/agronomic-alerts/alertas/${id}/posponer/`,
        descartar: (id) => `/api/agronomic-alerts/alertas/${id}/descartar/`,
    };

    const STATE = {
        currentParcelId: null,
        lastResponse: null,
    };

    // ---- DOM helpers --------------------------------------------------------

    function el(tag, attrs = {}, children = []) {
        const node = document.createElement(tag);
        Object.entries(attrs).forEach(([k, v]) => {
            if (k === 'class') node.className = v;
            else if (k === 'style') node.setAttribute('style', v);
            else if (k === 'html') node.innerHTML = v;
            else if (k.startsWith('on') && typeof v === 'function') {
                node.addEventListener(k.slice(2).toLowerCase(), v);
            } else if (v !== null && v !== undefined) {
                node.setAttribute(k, v);
            }
        });
        (Array.isArray(children) ? children : [children]).forEach((c) => {
            if (c == null) return;
            node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
        });
        return node;
    }

    function ensureContainer() {
        let host = document.getElementById('agroAlertsContainer');
        if (host) return host;

        // Insertar al final del contenedor de parcelas, debajo del mapa
        const anchor = document.getElementById('parcelTableContainer');
        host = el('div', { id: 'agroAlertsContainer', class: 'agro-alerts-host' });
        if (anchor && anchor.parentNode) {
            anchor.parentNode.insertBefore(host, anchor);
        } else {
            const main = document.querySelector('#main-content') || document.body;
            main.appendChild(host);
        }
        return host;
    }

    // ---- HTTP ---------------------------------------------------------------

    function apiBase() {
        if (typeof window.getBackendUrl === 'function') return window.getBackendUrl();
        const h = window.location.hostname;
        const isLocal = h === 'localhost' || h === '127.0.0.1' || h.endsWith('.localhost');
        return isLocal ? `${window.location.protocol}//${h}:8000` : '';
    }

    function fullUrl(path) {
        if (/^https?:\/\//.test(path)) return path;
        return apiBase() + path;
    }

    function authHeaders() {
        const token = localStorage.getItem('accessToken')
            || localStorage.getItem('access_token')
            || sessionStorage.getItem('accessToken')
            || sessionStorage.getItem('access_token');
        const h = { 'Content-Type': 'application/json' };
        if (token) h['Authorization'] = `Bearer ${token}`;
        const csrf = document.cookie.split(';').find((c) => c.trim().startsWith('csrftoken='));
        if (csrf) h['X-CSRFToken'] = csrf.split('=')[1];
        return h;
    }

    async function apiGet(url) {
        const r = await fetch(fullUrl(url), { headers: authHeaders(), credentials: 'include' });
        if (r.status === 403) {
            const body = await r.json().catch(() => ({}));
            if (body && body.code === 'feature_not_available') return { __gated: body };
        }
        if (!r.ok) throw new Error(`GET ${url} → ${r.status}`);
        return r.json();
    }

    async function apiPost(url, body) {
        const r = await fetch(fullUrl(url), {
            method: 'POST',
            headers: authHeaders(),
            credentials: 'include',
            body: JSON.stringify(body || {}),
        });
        if (!r.ok) throw new Error(`POST ${url} → ${r.status}`);
        return r.json();
    }

    // ---- Render -------------------------------------------------------------

    const ESTADO_THEME = {
        sano: {
            color: '#22c55e',
            bg: 'linear-gradient(135deg, rgba(34,197,94,0.15), rgba(34,197,94,0.05))',
            icon: '✓',
            sub: 'Sin riesgos activos en este lote',
        },
        atencion: {
            color: '#f59e0b',
            bg: 'linear-gradient(135deg, rgba(245,158,11,0.18), rgba(245,158,11,0.05))',
            icon: '⚠',
            sub: 'Hay condiciones que requieren tu atención',
        },
        critico: {
            color: '#ef4444',
            bg: 'linear-gradient(135deg, rgba(239,68,68,0.22), rgba(239,68,68,0.06))',
            icon: '🚨',
            sub: 'Riesgo crítico — acción urgente recomendada',
        },
    };

    function renderBanner(estado, parcel, frescura) {
        const theme = ESTADO_THEME[estado.codigo] || ESTADO_THEME.sano;
        return el('div', {
            class: 'agro-alerts-banner',
            style: `background:${theme.bg};border-left:4px solid ${theme.color};`,
        }, [
            el('div', { class: 'agro-alerts-banner__icon', style: `color:${theme.color};` }, theme.icon),
            el('div', { class: 'agro-alerts-banner__body' }, [
                el('div', { class: 'agro-alerts-banner__title' }, [
                    el('span', { style: `color:${theme.color};font-weight:700;` }, estado.label),
                    el('span', { class: 'agro-alerts-banner__lote' }, ` · ${parcel.name || 'Lote'}`),
                ]),
                el('div', { class: 'agro-alerts-banner__sub' }, theme.sub),
                el('div', { class: 'agro-alerts-banner__meta' }, [
                    badge('Activas', estado.n_alertas_activas, '#0ea5e9'),
                    badge('Críticas', estado.n_criticas, '#ef4444'),
                    badge('Atención', estado.n_warning, '#f59e0b'),
                    frescuraBadge(frescura),
                ]),
            ]),
        ]);
    }

    function badge(label, value, color) {
        return el('span', {
            class: 'agro-alerts-badge',
            style: `border-color:${color};color:${color};`,
        }, `${label}: ${value ?? 0}`);
    }

    function frescuraBadge(frescura) {
        if (!frescura || frescura.dias_desde_ultima_escena == null) {
            return el('span', { class: 'agro-alerts-badge agro-alerts-badge--muted' },
                'Sin escenas registradas');
        }
        const d = frescura.dias_desde_ultima_escena;
        const txt = d === 0 ? 'Última escena: hoy'
            : d === 1 ? 'Última escena: ayer'
            : `Última escena: hace ${d} días`;
        const color = d <= 7 ? '#22c55e' : d <= 14 ? '#f59e0b' : '#ef4444';
        return el('span', {
            class: 'agro-alerts-badge',
            style: `border-color:${color};color:${color};`,
        }, txt);
    }

    const HELP_TEXT = {
        ndvi: 'NDVI — Vigor vegetativo. Mide qué tan verde y activa está la planta. Valores bajos = poca cobertura o estrés.',
        ndmi: 'NDMI — Humedad del cultivo. Indica el agua disponible en las hojas. Valores bajos = estrés hídrico.',
        savi: 'SAVI — Vigor ajustado al suelo. Útil cuando el cultivo aún no cubre todo el lote (etapas tempranas).',
        evi:  'EVI — Cobertura. Detecta vacíos o zonas sin cultivo aún en lotes muy verdes.',
        humedad: 'Alerta de humedad: el suelo o la planta tienen menos agua de la esperada para esta etapa.',
        vigor: 'Alerta de vigor: el cultivo no está creciendo como debería para su etapa fenológica.',
        cobertura: 'Alerta de cobertura: el lote tiene zonas vacías o sin desarrollo de cultivo.',
        anomalia: 'Anomalía detectada que no encaja con el comportamiento esperado de la etapa.',
    };

    function tipToolFor(key) {
        return HELP_TEXT[(key || '').toLowerCase()] || '';
    }

    function renderRiesgoActivo(alerta) {
        if (!alerta) {
            return el('div', { class: 'agro-alerts-card agro-alerts-card--empty' }, [
                el('div', { class: 'agro-alerts-card__title' }, '🌿 Lote sin riesgos activos'),
                el('div', { class: 'agro-alerts-card__body' },
                    'No detectamos condiciones agronómicas adversas en la última lectura satelital. Seguimos monitoreando.'),
            ]);
        }
        const sevColor = ESTADO_THEME[mapSevToCode(alerta.severidad)].color;
        return el('div', { class: 'agro-alerts-card', style: `border-color:${sevColor}55;` }, [
            el('div', { class: 'agro-alerts-card__head' }, [
                el('span', { class: 'agro-alerts-chip', style: `background:${sevColor};`, title: 'Nivel de severidad de la alerta' }, alerta.severidad_label),
                el('span', { class: 'agro-alerts-chip agro-alerts-chip--ghost', title: tipToolFor(alerta.tipo) }, alerta.tipo_label),
                el('span', { class: 'agro-alerts-chip agro-alerts-chip--ghost', title: tipToolFor(alerta.indice_afectado) }, alerta.indice_label),
            ]),
            el('div', { class: 'agro-alerts-card__title' }, alerta.titulo),
            section('🟢 QUÉ PASA', alerta.causa_probable),
            section('🛠 QUÉ HACER', alerta.recomendacion),
            section('⏱ CUÁNDO', `Inspeccionar dentro de los próximos ${alerta.ventana_dias} día(s).`),
            valorTecnico(alerta),
            renderFeedbackActions(alerta),
        ]);
    }

    function valorTecnico(a) {
        if (a.valor_observado == null) return null;
        const partes = [];
        partes.push(`Valor observado: <b>${Number(a.valor_observado).toFixed(2)}</b>`);
        if (a.valor_umbral_min != null && a.valor_umbral_max != null) {
            partes.push(`Rango esperado: ${Number(a.valor_umbral_min).toFixed(2)} – ${Number(a.valor_umbral_max).toFixed(2)}`);
        }
        if (a.fecha_escena_origen) partes.push(`Escena: ${a.fecha_escena_origen}`);
        return el('div', { class: 'agro-alerts-card__tech', html: partes.join(' &nbsp;·&nbsp; ') });
    }

    function section(label, text) {
        if (!text) return null;
        return el('div', { class: 'agro-alerts-card__section' }, [
            el('div', { class: 'agro-alerts-card__section-label' }, label),
            el('div', { class: 'agro-alerts-card__section-text' }, text),
        ]);
    }

    function renderFeedbackActions(alerta) {
        return el('div', { class: 'agro-alerts-actions' }, [
            el('button', {
                class: 'agro-alerts-btn agro-alerts-btn--ok',
                title: 'Marcar la alerta como atendida',
                onclick: () => doFeedback('atender', alerta.id, { feedback: 'util' }),
            }, '✅ Atendida'),
            el('button', {
                class: 'agro-alerts-btn agro-alerts-btn--snooze',
                title: 'Posponer 7 días',
                onclick: () => doFeedback('posponer', alerta.id, { dias: 7 }),
            }, '⏸ Posponer 7d'),
            el('button', {
                class: 'agro-alerts-btn agro-alerts-btn--bad',
                title: 'No aplica / falso positivo',
                onclick: () => doFeedback('descartar', alerta.id, {}),
            }, '❌ No aplica'),
        ]);
    }

    function renderAlertasRestantes(alertas) {
        if (!alertas || alertas.length <= 1) return null;
        const items = alertas.slice(1).map((a) => el('li', { class: 'agro-alerts-list__item' }, [
            el('span', { class: 'agro-alerts-list__sev', style: `background:${ESTADO_THEME[mapSevToCode(a.severidad)].color};` }, ''),
            el('span', { class: 'agro-alerts-list__title' }, a.titulo),
            el('span', { class: 'agro-alerts-list__date' }, a.fecha_escena_origen || ''),
        ]));
        return el('div', { class: 'agro-alerts-list' }, [
            el('div', { class: 'agro-alerts-list__head' }, `Otras alertas activas (${alertas.length - 1})`),
            el('ul', {}, items),
        ]);
    }

    function renderGate(body) {
        return el('div', { class: 'agro-alerts-card agro-alerts-card--gate' }, [
            el('div', { class: 'agro-alerts-card__title' }, '🔒 Alertas Agronómicas'),
            el('div', { class: 'agro-alerts-card__body' },
                body.message || 'Esta funcionalidad no está disponible en tu plan actual.'),
            el('a', {
                class: 'agro-alerts-btn agro-alerts-btn--cta',
                href: body.upgrade_url || '/billing/upgrade/',
            }, 'Ver planes disponibles'),
        ]);
    }

    function mapSevToCode(sev) {
        if (sev === 'critical') return 'critico';
        if (sev === 'warning') return 'atencion';
        return 'sano';
    }

    // ---- Acciones de feedback ----------------------------------------------

    async function doFeedback(action, alertaId, payload) {
        try {
            await apiPost(ENDPOINTS[action](alertaId), payload);
            await refresh();
            toast(`Alerta ${action === 'atender' ? 'marcada como atendida' :
                action === 'posponer' ? 'pospuesta' : 'descartada'} ✓`);
        } catch (err) {
            console.error('[AgroAlerts] feedback error:', err);
            toast('No se pudo registrar tu acción. Intenta de nuevo.', true);
        }
    }

    function toast(msg, isError = false) {
        const t = el('div', {
            class: 'agro-alerts-toast' + (isError ? ' agro-alerts-toast--error' : ''),
        }, msg);
        document.body.appendChild(t);
        setTimeout(() => t.classList.add('show'), 10);
        setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 3200);
    }

    // ---- Orquestación -------------------------------------------------------

    async function loadForParcel(parcelId) {
        if (!parcelId) return;
        STATE.currentParcelId = parcelId;
        const host = ensureContainer();
        host.classList.add('is-loading');
        host.innerHTML = '<div class="agro-alerts-skeleton">Cargando estado del lote…</div>';

        let data;
        try {
            data = await apiGet(ENDPOINTS.estadoHoy(parcelId));
        } catch (err) {
            console.error('[AgroAlerts] error:', err);
            host.innerHTML = '<div class="agro-alerts-error">No se pudo cargar el estado del lote.</div>';
            host.classList.remove('is-loading');
            return;
        }

        host.innerHTML = '';
        host.classList.remove('is-loading');

        if (data && data.__gated) {
            host.appendChild(renderGate(data.__gated));
            return;
        }

        STATE.lastResponse = data;
        host.appendChild(renderBanner(data.estado, data.parcel, data.frescura));
        host.appendChild(renderRiesgoActivo(data.riesgo_activo));
        const restantes = renderAlertasRestantes(data.alertas_activas);
        if (restantes) host.appendChild(restantes);
    }

    function refresh() {
        if (!STATE.currentParcelId) return Promise.resolve();
        return loadForParcel(STATE.currentParcelId);
    }

    // ---- Hook con el estado global -----------------------------------------
    // El resto del dashboard fija `window.AGROTECH_STATE.selectedParcelId` al
    // seleccionar una parcela. Observamos esa variable.

    function attachStateWatcher() {
        const stateObj = window.AGROTECH_STATE = window.AGROTECH_STATE || {};
        let last = stateObj.selectedParcelId || null;
        setInterval(() => {
            const cur = window.AGROTECH_STATE && window.AGROTECH_STATE.selectedParcelId;
            if (cur && cur !== last) {
                last = cur;
                loadForParcel(cur);
            }
        }, 600);
    }

    document.addEventListener('DOMContentLoaded', () => {
        attachStateWatcher();
        // Si ya hay una parcela seleccionada al cargar, pintar.
        const pid = window.AGROTECH_STATE && window.AGROTECH_STATE.selectedParcelId;
        if (pid) loadForParcel(pid);
    });

    window.AgroAlerts = { loadForParcel, refresh };
})();
