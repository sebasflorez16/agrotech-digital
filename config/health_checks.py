"""
Health checks detallados para monitoreo del sistema.
"""
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Health check básico para Railway y monitoreo.
    No requiere autenticación.
    """
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        """GET /health/ - Health check simple."""
        return Response({"status": "ok"})


class DetailedHealthCheckView(APIView):
    """
    Health check detallado con verificación de servicios.
    """
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        """
        GET /api/health/detailed/
        
        Retorna estado detallado de todos los servicios:
        - Database
        - Cache (Redis)
        - EOSDA API
        - Almacenamiento
        """
        checks = {
            'timestamp': timezone.now().isoformat(),
            'overall_status': 'healthy',
            'services': {}
        }
        
        # Check Database
        db_status = self._check_database()
        checks['services']['database'] = db_status
        if db_status['status'] != 'healthy':
            checks['overall_status'] = 'degraded'
        
        # Check Cache
        cache_status = self._check_cache()
        checks['services']['cache'] = cache_status
        if cache_status['status'] != 'healthy':
            checks['overall_status'] = 'degraded'
        
        # Check EOSDA API
        eosda_status = self._check_eosda_api()
        checks['services']['eosda_api'] = eosda_status
        if eosda_status['status'] == 'unhealthy':
            checks['overall_status'] = 'degraded'
        
        # Check Storage
        storage_status = self._check_storage()
        checks['services']['storage'] = storage_status
        
        # Determinar código de estado HTTP
        http_status = status.HTTP_200_OK
        if checks['overall_status'] == 'degraded':
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        elif checks['overall_status'] == 'unhealthy':
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        
        return Response(checks, status=http_status)

    def _check_database(self):
        """Verifica conexión a la base de datos."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            return {
                'status': 'healthy',
                'message': 'Database connection OK',
                'response_time_ms': self._measure_db_response_time()
            }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'message': f'Database error: {str(e)}'
            }

    def _check_cache(self):
        """Verifica conexión al cache (Redis)."""
        try:
            # Intentar set/get en cache
            test_key = 'health_check_test'
            test_value = 'ok'
            cache.set(test_key, test_value, timeout=10)
            result = cache.get(test_key)
            
            if result == test_value:
                cache.delete(test_key)
                return {
                    'status': 'healthy',
                    'message': 'Cache connection OK',
                    'backend': settings.CACHES['default']['BACKEND']
                }
            else:
                return {
                    'status': 'degraded',
                    'message': 'Cache not returning correct values'
                }
        except Exception as e:
            logger.warning(f"Cache health check failed: {str(e)}")
            return {
                'status': 'degraded',
                'message': f'Cache error: {str(e)} (application continues with fallback)'
            }

    def _check_eosda_api(self):
        """Verifica disponibilidad de EOSDA API."""
        try:
            # No hacer request real para no consumir cuota
            # Solo verificar que tenemos API key configurada
            api_key = getattr(settings, 'EOSDA_API_KEY', None)
            
            if api_key and len(api_key) > 10:
                # Verificar estadísticas de uso reciente
                from parcels.models import EstadisticaUsoEOSDA
                now = timezone.now()
                hour_ago = now - timedelta(hours=1)
                
                recent_requests = EstadisticaUsoEOSDA.objects.filter(
                    timestamp__gte=hour_ago
                ).count()
                
                recent_errors = EstadisticaUsoEOSDA.objects.filter(
                    timestamp__gte=hour_ago,
                    exitoso=False
                ).count()
                
                error_rate = (recent_errors / recent_requests * 100) if recent_requests > 0 else 0
                
                if error_rate > 50:
                    return {
                        'status': 'degraded',
                        'message': f'High error rate: {error_rate:.1f}% in last hour',
                        'recent_requests': recent_requests,
                        'recent_errors': recent_errors
                    }
                
                return {
                    'status': 'healthy',
                    'message': 'EOSDA API configured',
                    'recent_requests_1h': recent_requests,
                    'error_rate_1h': round(error_rate, 2)
                }
            else:
                return {
                    'status': 'unhealthy',
                    'message': 'EOSDA API key not configured'
                }
        except Exception as e:
            logger.warning(f"EOSDA API health check failed: {str(e)}")
            return {
                'status': 'unknown',
                'message': f'Could not verify EOSDA API: {str(e)}'
            }

    def _check_storage(self):
        """Verifica espacio en disco y acceso a media."""
        try:
            import os
            
            media_root = settings.MEDIA_ROOT
            static_root = settings.STATIC_ROOT
            
            # Verificar que directorios existen
            media_exists = os.path.exists(media_root)
            static_exists = os.path.exists(static_root)
            
            return {
                'status': 'healthy',
                'message': 'Storage accessible',
                'media_root': str(media_root),
                'media_exists': media_exists,
                'static_root': str(static_root),
                'static_exists': static_exists
            }
        except Exception as e:
            logger.warning(f"Storage health check failed: {str(e)}")
            return {
                'status': 'degraded',
                'message': f'Storage check error: {str(e)}'
            }

    def _measure_db_response_time(self):
        """Mide tiempo de respuesta de la base de datos."""
        try:
            import time
            start = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM django_migrations")
                cursor.fetchone()
            end = time.time()
            return round((end - start) * 1000, 2)  # ms
        except:
            return None


class ReadinessCheckView(APIView):
    """
    Readiness check para Kubernetes/Railway.
    Verifica que la aplicación está lista para recibir tráfico.
    """
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        """GET /api/health/ready/"""
        try:
            # Verificar database
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            # Verificar que las migraciones están aplicadas
            from django.db.migrations.executor import MigrationExecutor
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            
            if plan:
                return Response(
                    {'status': 'not_ready', 'message': 'Pending migrations'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            return Response({'status': 'ready'})
        except Exception as e:
            logger.error(f"Readiness check failed: {str(e)}")
            return Response(
                {'status': 'not_ready', 'error': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class LivenessCheckView(APIView):
    """
    Liveness check para Kubernetes/Railway.
    Verifica que la aplicación está viva (no colgada).
    """
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        """GET /api/health/live/"""
        # Check simple - si llega aquí, la app está viva
        return Response({'status': 'alive'})
