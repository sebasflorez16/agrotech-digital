"""
Rate limiter global para EOSDA.

Token bucket / ventana deslizante con espera bloqueante acotada.

- En producción (Redis configurado): usa un sorted set + script Lua atómico
  para que N procesos/workers respeten el límite global sin pasarse.
- En local (sin Redis): fallback en memoria con `threading.Lock` (single-process).

Las peticiones se ENCOLAN (esperan) en vez de rechazarse; solo se rinden
cuando se agota `EOSDA_MAX_QUEUE_WAIT_SECONDS`.
"""

import time
import uuid
import logging
import threading
from collections import deque

from django.conf import settings

logger = logging.getLogger("eosda")


class EosdaRateLimiter:
    """Limita las llamadas a EOSDA a `per_min` requests por minuto (global)."""

    WINDOW_SECONDS = 60.0
    REDIS_KEY = "eosda:rate:sliding"

    def __init__(self, per_min=None, max_wait_seconds=None):
        self.per_min = per_min or getattr(settings, "EOSDA_RATE_LIMIT_PER_MIN", 8)
        self.max_wait = max_wait_seconds or getattr(settings, "EOSDA_MAX_QUEUE_WAIT_SECONDS", 60)

        self._redis = None
        self._redis_error_logged = False
        self._local_lock = threading.Lock()
        self._local_timestamps = deque()

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from django_redis import get_redis_connection
            self._redis = get_redis_connection("default")
        except Exception:
            # Sin Redis configurado (local) -> fallback in-memory
            self._redis = False
        return self._redis

    def acquire(self):
        """
        Espera (bloquea) hasta conseguir un token.

        Retorna True si obtuvo token, False si se agotó el tiempo de espera.
        """
        deadline = time.monotonic() + self.max_wait
        while True:
            if self._try_acquire():
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning(
                    "[EOSDA RATE LIMITER] Espera agotada (%ss) al límite %s/min",
                    self.max_wait, self.per_min,
                )
                return False
            time.sleep(min(1.0, remaining))

    def _try_acquire(self):
        redis_conn = self._get_redis()
        if redis_conn:
            try:
                return self._redis_acquire(redis_conn)
            except Exception as exc:
                if not self._redis_error_logged:
                    logger.warning(
                        "[EOSDA RATE LIMITER] Redis falló, degradando a in-memory: %s", exc
                    )
                    self._redis_error_logged = True
        return self._local_acquire()

    def _redis_acquire(self, redis_conn):
        now = time.time()
        window_start = now - self.WINDOW_SECONDS
        member = f"{now}-{uuid.uuid4().hex}"

        script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window_start = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        local member = ARGV[4]
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
        local count = redis.call('ZCARD', key)
        if count < limit then
            redis.call('ZADD', key, now, member)
            redis.call('EXPIRE', key, 70)
            return 1
        end
        return 0
        """
        result = redis_conn.eval(script, 1, self.REDIS_KEY, now, window_start, self.per_min, member)
        return result == 1

    def _local_acquire(self):
        now = time.monotonic()
        with self._local_lock:
            while self._local_timestamps and self._local_timestamps[0] <= now - self.WINDOW_SECONDS:
                self._local_timestamps.popleft()
            if len(self._local_timestamps) < self.per_min:
                self._local_timestamps.append(now)
                return True
        return False


# Instancia global compartida (un solo embudo).
eosda_rate_limiter = EosdaRateLimiter()
