from django.core.cache import cache
from django.conf import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EosdaRequestMonitor:
    """
    Monitor de requests a EOSDA API para controlar consumo y alertar antes del límite.
    """
    
    MONTHLY_LIMIT = 1000  # Límite mensual de EOSDA
    WARNING_THRESHOLD = 800  # Alerta cuando se llega a 800 requests
    CRITICAL_THRESHOLD = 950  # Bloquear cuando se llega a 950 requests
    
    @classmethod
    def get_current_month_key(cls):
        """Genera clave de cache para el mes actual"""
        now = datetime.now()
        return f"eosda_requests_{now.year}_{now.month:02d}"
    
    @classmethod
    def increment_requests(cls, count=1):
        """
        Incrementa el contador de requests del mes actual
        
        Args:
            count (int): Número de requests a incrementar
            
        Returns:
            dict: Estado actual del consumo
        """
        cache_key = cls.get_current_month_key()
        current_count = cache.get(cache_key, 0)
        new_count = current_count + count
        
        # Guardar en cache hasta fin de mes
        days_to_end_month = 32 - datetime.now().day  # Aproximado
        cache_timeout = days_to_end_month * 24 * 3600
        cache.set(cache_key, new_count, cache_timeout)
        
        logger.info(f"[EOSDA_MONITOR] Requests incrementados: +{count}, Total: {new_count}/{cls.MONTHLY_LIMIT}")
        
        # Verificar alertas
        status = cls._check_status(new_count)
        if status['alert']:
            logger.warning(f"[EOSDA_MONITOR] {status['message']}")
        
        return status
    
    @classmethod
    def get_current_usage(cls):
        """
        Obtiene el uso actual de requests del mes
        
        Returns:
            dict: Estado actual del consumo
        """
        cache_key = cls.get_current_month_key()
        current_count = cache.get(cache_key, 0)
        return cls._check_status(current_count)
    
    @classmethod
    def _check_status(cls, current_count):
        """
        Verifica el estado actual del consumo
        
        Args:
            current_count (int): Número actual de requests
            
        Returns:
            dict: Estado con alertas y recomendaciones
        """
        percentage = (current_count / cls.MONTHLY_LIMIT) * 100
        remaining = cls.MONTHLY_LIMIT - current_count
        
        status = {
            "current_count": current_count,
            "monthly_limit": cls.MONTHLY_LIMIT,
            "remaining": remaining,
            "percentage": round(percentage, 2),
            "alert": False,
            "block": False,
            "level": "safe",
            "message": f"Uso normal: {current_count}/{cls.MONTHLY_LIMIT} requests ({percentage:.1f}%)"
        }
        
        if current_count >= cls.CRITICAL_THRESHOLD:
            status.update({
                "alert": True,
                "block": True,
                "level": "critical",
                "message": f"CRÍTICO: {current_count}/{cls.MONTHLY_LIMIT} requests. Bloquear nuevas consultas."
            })
        elif current_count >= cls.WARNING_THRESHOLD:
            status.update({
                "alert": True,
                "level": "warning",
                "message": f"ADVERTENCIA: {current_count}/{cls.MONTHLY_LIMIT} requests. Reducir consultas."
            })
        
        return status
    
    @classmethod
    def reset_counter(cls):
        """Resetea el contador (solo para testing o nuevo mes)"""
        cache_key = cls.get_current_month_key()
        cache.delete(cache_key)
        logger.info("[EOSDA_MONITOR] Contador reseteado")
    
    @classmethod
    def should_block_request(cls):
        """
        Verifica si se debe bloquear la request por límite crítico
        
        Returns:
            bool: True si se debe bloquear
        """
        status = cls.get_current_usage()
        return status.get('block', False)
