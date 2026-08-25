/**
 * Scene Cache — localStorage + TTL para analytics e imágenes satelitales.
 * Persiste entre recargas, respeta límites de plan de suscripción.
 * Sin fallbacks: si no hay datos, se llama a la API.
 */

window.SceneCache = (function() {
    const PREFIX = 'agro_scene_';
    const STATS_TTL = 7200000;  // 2 horas
    const IMAGE_TTL = 7200000;  // 2 horas
    const HISTORY_KEY = PREFIX + 'history';
    const REQUEST_COUNT_KEY = PREFIX + 'request_count';
    const REQUEST_DATE_KEY = PREFIX + 'request_date';

    function _now() { return Date.now(); }
    function _today() { return new Date().toISOString().split('T')[0]; }

    function _cacheKey(type, viewId, sceneDate, indexType) {
        return PREFIX + type + '_' + viewId + '_' + sceneDate + '_' + indexType;
    }

    function _imageKey(fieldId, viewId, indexType) {
        return PREFIX + 'img_' + fieldId + '_' + viewId + '_' + indexType;
    }

    function _loadJSON(key) {
        try {
            const raw = localStorage.getItem(key);
            return raw ? JSON.parse(raw) : null;
        } catch { return null; }
    }

    function _saveJSON(key, data) {
        try { localStorage.setItem(key, JSON.stringify(data)); } catch { /* cuota llena */ }
    }

    // ── Plan limits ──
    function getPlanLimits() {
        try {
            const userData = JSON.parse(localStorage.getItem('userData') || '{}');
            const planName = userData.subscription_plan || userData.plan || 'free';
            const limits = {
                free:      { history: 5,  export: false, compare: false },
                basic:     { history: 50, export: true,  compare: 2 },
                pro:       { history: 500, export: true, compare: 99 },
                Explorador:{ history: 5,  export: false, compare: false },
                Agricultor:{ history: 50, export: true,  compare: 2 },
                Empresarial:{ history: 500, export: true, compare: 99 },
            };
            return limits[planName] || limits.free;
        } catch { return { history: 5, export: false, compare: false }; }
    }

    // ── Stats cache ──
    function getStats(viewId, sceneDate, indexType) {
        const entry = _loadJSON(_cacheKey('stats', viewId, sceneDate, indexType));
        if (!entry) return null;
        if (_now() - entry._ts > STATS_TTL) {
            localStorage.removeItem(_cacheKey('stats', viewId, sceneDate, indexType));
            return null;
        }
        return entry.data;
    }

    function setStats(viewId, sceneDate, indexType, data) {
        _saveJSON(_cacheKey('stats', viewId, sceneDate, indexType), {
            data: data,
            _ts: _now()
        });
    }

    // ── Image cache ──
    function getImage(fieldId, viewId, indexType) {
        const entry = _loadJSON(_imageKey(fieldId, viewId, indexType));
        if (!entry) return null;
        if (_now() - entry._ts > IMAGE_TTL) {
            localStorage.removeItem(_imageKey(fieldId, viewId, indexType));
            return null;
        }
        return entry.data;
    }

    function setImage(fieldId, viewId, indexType, base64) {
        _saveJSON(_imageKey(fieldId, viewId, indexType), {
            data: base64,
            _ts: _now()
        });
    }

    // ── History ──
    function getHistory() {
        return _loadJSON(HISTORY_KEY) || [];
    }

    function addToHistory(entry) {
        const limits = getPlanLimits();
        let history = getHistory();

        // Evitar duplicados
        history = history.filter(e =>
            !(e.viewId === entry.viewId && e.sceneDate === entry.sceneDate && e.indexType === entry.indexType)
        );

        history.unshift({
            viewId: entry.viewId,
            sceneDate: entry.sceneDate,
            indexType: entry.indexType || 'ndvi',
            parcelId: entry.parcelId,
            parcelName: entry.parcelName || '',
            value: entry.value,
            status: entry.status || _valueStatus(entry.value),
            _ts: _now()
        });

        // FIFO según límite del plan
        if (history.length > limits.history) {
            history = history.slice(0, limits.history);
        }

        _saveJSON(HISTORY_KEY, history);
    }

    function removeFromHistory(viewId, sceneDate, indexType) {
        let history = getHistory();
        history = history.filter(e =>
            !(e.viewId === viewId && e.sceneDate === sceneDate && e.indexType === indexType)
        );
        _saveJSON(HISTORY_KEY, history);
    }

    function _valueStatus(value) {
        if (value == null) return 'unknown';
        if (value >= 0.7) return 'high';
        if (value >= 0.4) return 'mid';
        return 'low';
    }

    // ── Cache age badge ──
    function getCacheAge(viewId, sceneDate, indexType) {
        const entry = _loadJSON(_cacheKey('stats', viewId, sceneDate, indexType));
        if (!entry) return { label: 'Sin cache', cls: 'cache-none' };
        const age = _now() - entry._ts;
        if (age < 1800000) return { label: 'En vivo', cls: 'cache-live' };
        if (age < 7200000) return { label: 'Cache', cls: 'cache-stale' };
        return { label: 'Expirado', cls: 'cache-expired' };
    }

    // ── Request counter ──
    function incrementRequestCount() {
        const today = _today();
        const lastDate = localStorage.getItem(REQUEST_DATE_KEY);
        if (lastDate !== today) {
            localStorage.setItem(REQUEST_DATE_KEY, today);
            localStorage.setItem(REQUEST_COUNT_KEY, '1');
            return 1;
        }
        const count = parseInt(localStorage.getItem(REQUEST_COUNT_KEY) || '0') + 1;
        localStorage.setItem(REQUEST_COUNT_KEY, String(count));
        return count;
    }

    function getRequestCount() {
        const today = _today();
        const lastDate = localStorage.getItem(REQUEST_DATE_KEY);
        if (lastDate !== today) return 0;
        return parseInt(localStorage.getItem(REQUEST_COUNT_KEY) || '0');
    }

    // ── Clear expired ──
    function clearExpired() {
        const keys = Object.keys(localStorage).filter(k => k.startsWith(PREFIX));
        for (const key of keys) {
            if (key === HISTORY_KEY || key === REQUEST_COUNT_KEY || key === REQUEST_DATE_KEY) continue;
            const entry = _loadJSON(key);
            if (entry && entry._ts && _now() - entry._ts > STATS_TTL) {
                localStorage.removeItem(key);
            }
        }
    }

    // Auto-limpieza cada 10 min
    setInterval(clearExpired, 600000);
    clearExpired();

    return {
        getStats, setStats,
        getImage, setImage,
        getHistory, addToHistory, removeFromHistory,
        getCacheAge,
        incrementRequestCount, getRequestCount,
        getPlanLimits,
        clearExpired,
    };
})();
