"""
Cliente central de EOSDA.

Única puerta de entrada a EOSDA para todo el proyecto. Aplica en orden:
  1. Cache + deduplicación (django.core.cache + lock por clave)
  2. Rate limiter global (token bucket, espera bloqueante)
  3. HTTP (POST/GET con `x-api-key`)
  4. Registro de consumo (UsageMetrics.eosda_requests + EosdaRequestLog)

Los cache hits NO cuentan consumo ni se registran. Solo las llamadas reales
a EOSDA incrementan la cuota y escriben EosdaRequestLog.

La cuota REAL de EOSDA es global (una sola API Key): la impone el rate limiter
(8 req/min). `UsageMetrics.eosda_requests` es la contabilidad MENSUAL por tenant;
`EosdaRequestLog` (tabla en schema public) es el registro GLOBAL de Agrotech.
"""

import logging
import threading
import time

import requests
from django.conf import settings
from django.core.cache import cache

from .eosda_rate_limiter import eosda_rate_limiter

logger = logging.getLogger("eosda")


class EosdaRateLimitError(requests.exceptions.RequestException):
    """Se agotó la espera en el rate limiter global.

    Subclase de RequestException para que los `except requests.exceptions.RequestException`
    ya existentes en las vistas la capturen (evita 500 no controlados).
    """


class EosdaClient:
    """Cliente síncrono con cache, dedup, rate limiting y registro de consumo."""

    DEDUP_LOCK_TTL = 60          # segundos que dura el lock de dedup (>= tiempo de fetch)
    DEDUP_POLL_SECONDS = 0.1     # intervalo de espera de los "perdedores" del lock
    DEDUP_POLL_ATTEMPTS = 300    # ~30s máximo de espera por el resultado

    # Lock in-process (hilos del mismo worker). El lock cross-proceso lo da Redis vía cache.add.
    _local_locks = {}
    _local_locks_guard = threading.Lock()

    def __init__(self, api_key=None, limiter=None):
        self.api_key = api_key or getattr(settings, "EOSDA_API_KEY", "")
        self.limiter = limiter or eosda_rate_limiter

    # ------------------------------------------------------------------ headers
    @property
    def headers(self):
        return {"x-api-key": self.api_key, "Content-Type": "application/json"}

    # -------------------------------------------------------------------- cache
    @staticmethod
    def cache_key(tenant_id, parcel_id, operation, index_type="", date_ref=""):
        """Clave canónica de cache: eosda:{tenant}:{parcela}:{operacion}:{indice}:{fecha}."""
        return (
            f"eosda:{tenant_id or 0}:{parcel_id or 0}:{operation or ''}:"
            f"{index_type or ''}:{date_ref or ''}"
        )

    @staticmethod
    def get_cached(key):
        try:
            return cache.get(key)
        except Exception:
            return None

    @staticmethod
    def set_cached(key, value, ttl=None):
        ttl = ttl or getattr(settings, "EOSDA_CACHE_TTL_SECONDS", 86400)
        try:
            cache.set(key, value, ttl)
        except Exception:
            logger.warning("[EOSDA] No se pudo guardar en cache", exc_info=True)

    # ------------------------------------------------- deduplicación atómica
    @classmethod
    def _local_dedup_lock(cls, key):
        with cls._local_locks_guard:
            lock = cls._local_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                cls._local_locks[key] = lock
            return lock

    def _acquire_dedup_lock(self, key):
        """Intenta tomar el lock de dedup para `key`. True si lo conseguimos."""
        local = self._local_dedup_lock(key)
        if not local.acquire(blocking=False):
            return False
        # Lock cross-proceso (Redis). cache.add es atómico en Redis/LocMem.
        try:
            if cache.add(f"{key}:dedup", "1", self.DEDUP_LOCK_TTL):
                return True
        except Exception:
            return True  # sin cache utilizable -> solo lock local
        local.release()
        return False

    def _release_dedup_lock(self, key):
        try:
            cache.delete(f"{key}:dedup")
        except Exception:
            pass
        self._local_dedup_lock(key).release()

    def cached(self, key, fetch_fn, ttl=None):
        """
        Cache atómico + deduplicación de requests idénticos simultáneos.

        Devuelve (data, source) con source ∈ {"cache", "eosda"}.
        `fetch_fn()` se ejecuta UNA sola vez por clave aunque N hilos la pidan a la vez.
        """
        value = self.get_cached(key)
        if value is not None:
            return value, "cache"

        if not self._acquire_dedup_lock(key):
            # Otro request está generando el dato: esperamos y leemos cache.
            for _ in range(self.DEDUP_POLL_ATTEMPTS):
                time.sleep(self.DEDUP_POLL_SECONDS)
                value = self.get_cached(key)
                if value is not None:
                    return value, "cache"
            # Caso extremo (el generador falló/tardó): generamos nosotros.
            data = fetch_fn()
            self.set_cached(key, data, ttl)
            return data, "eosda"

        try:
            # Doble chequeo tras adquirir el lock.
            value = self.get_cached(key)
            if value is not None:
                return value, "cache"
            data = fetch_fn()
            self.set_cached(key, data, ttl)
            return data, "eosda"
        finally:
            self._release_dedup_lock(key)

    # ------------------------------------------------------- HTTP + rate limit
    def _acquire_or_raise(self):
        if not self.limiter.acquire():
            raise EosdaRateLimitError(
                "Límite global de consultas satelitales alcanzado. Intenta de nuevo en unos segundos."
            )

    def post(self, url, payload=None, rate_limit=True, **kwargs):
        if rate_limit:
            self._acquire_or_raise()
        kwargs.setdefault("timeout", 30)
        kwargs.setdefault("headers", self.headers)
        return requests.post(url, json=payload, **kwargs)

    def get(self, url, rate_limit=True, **kwargs):
        if rate_limit:
            self._acquire_or_raise()
        kwargs.setdefault("timeout", 30)
        kwargs.setdefault("headers", self.headers)
        return requests.get(url, **kwargs)

    # ------------------------------------------------------------ consumo/log
    def record(self, tenant, operation, index_type="", parcel_id=None,
               date_requested=None, user=None, increment_quota=True):
        """
        Registra UNA operación de análisis EOSDA (solo cuando salió de verdad a EOSDA).

        Definición única del contador interno de AgroTech:

        - `UsageMetrics.eosda_requests` (cuota mensual POR TENANT): cuenta
          **1 por cada invocación de un endpoint de análisis EOSDA** que realizó
          al menos una llamada HTTP real (cache miss). Ejemplos: generar imagen
          (`image`) = 1; descargar imagen (`image_result`) = 1; buscar escenas
          (`scenes`) = 1; analytics de una escena (varios índices) = 1.

        - `EosdaRequestLog` (registro global + por tenant): **1 fila** por cada
          `record()` (misma granularidad), con tenant, usuario, parcela,
          operación, índice, fecha y `source`.

        Operaciones NO-análisis (creación de campo `field`, tiles `render`) se
        registran en `EosdaRequestLog` pero NO incrementan `eosda_requests`
        (pasan `increment_quota=False`).

        NO confundir con el rate limiter, que cuenta **cada HTTP** (POST y cada
        GET de polling) a nivel global, ni con la facturación comercial de EOSDA
        (que no se asume igual y queda pendiente de confirmación del proveedor).

        Ambas escrituras van en try/except: nunca rompen el flujo de la vista.
        """
        if increment_quota:
            self._increment_metrics(tenant)
        self._log(tenant, operation, index_type=index_type, parcel_id=parcel_id,
                  date_requested=date_requested, user=user)

    def _increment_metrics(self, tenant):
        if tenant is None:
            return
        try:
            from billing.models import UsageMetrics
            metrics = UsageMetrics.get_or_create_current(tenant)
            metrics.eosda_requests += 1
            metrics.save()
            metrics.calculate_overages()
        except Exception:
            logger.warning("[EOSDA] No se pudo incrementar UsageMetrics.eosda_requests", exc_info=True)

    def _log(self, tenant, operation, index_type="", parcel_id=None,
             date_requested=None, user=None):
        try:
            from billing.models import EosdaRequestLog
            EosdaRequestLog.log(
                tenant=tenant,
                user=user,
                operation=operation,
                index_type=index_type,
                parcel_id=parcel_id,
                date_requested=date_requested,
                source="eosda",
            )
        except Exception:
            logger.warning("[EOSDA] No se pudo registrar EosdaRequestLog", exc_info=True)


# Instancia global compartida (un solo embudo).
_eosda_client = None


def get_eosda_client():
    global _eosda_client
    if _eosda_client is None:
        _eosda_client = EosdaClient()
    return _eosda_client
