"""
Dashboard de métricas y monitoreo de uso de EOSDA API.
"""
import logging
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from parcels.models import CacheDatosEOSDA, EstadisticaUsoEOSDA
from django.core.cache import cache

logger = logging.getLogger('parcels.eosda')


class EOSDAMetricsViewSet(viewsets.ViewSet):
    """
    ViewSet para métricas y monitoreo de uso de EOSDA API.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def usage_summary(self, request):
        """
        GET /api/metrics/eosda/usage_summary/
        
        Retorna resumen de uso de EOSDA API:
        - Total requests hoy, esta semana, este mes
        - Requests exitosos vs fallidos
        - Ahorro por cache
        - Tipos de requests más comunes
        """
        logger.info(f"Usuario {request.user.username} consultó métricas de uso EOSDA")
        
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Estadísticas de uso
        stats_today = EstadisticaUsoEOSDA.objects.filter(
            timestamp__date=today
        ).aggregate(
            total=Count('id'),
            exitosos=Count('id', filter=Q(exitoso=True)),
            fallidos=Count('id', filter=Q(exitoso=False))
        )
        
        stats_week = EstadisticaUsoEOSDA.objects.filter(
            timestamp__gte=week_ago
        ).aggregate(
            total=Count('id'),
            exitosos=Count('id', filter=Q(exitoso=True)),
            fallidos=Count('id', filter=Q(exitoso=False))
        )
        
        stats_month = EstadisticaUsoEOSDA.objects.filter(
            timestamp__gte=month_ago
        ).aggregate(
            total=Count('id'),
            exitosos=Count('id', filter=Q(exitoso=True)),
            fallidos=Count('id', filter=Q(exitoso=False))
        )
        
        # Cache hits vs misses
        cache_stats = EstadisticaUsoEOSDA.objects.filter(
            timestamp__gte=month_ago
        ).aggregate(
            cache_hits=Count('id', filter=Q(desde_cache=True)),
            cache_misses=Count('id', filter=Q(desde_cache=False))
        )
        
        total_requests = cache_stats['cache_hits'] + cache_stats['cache_misses']
        cache_hit_rate = (cache_stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0
        
        # Ahorro estimado (cada request a EOSDA cuenta como 1, cache es gratis)
        ahorro_requests = cache_stats['cache_hits']
        ahorro_porcentaje = cache_hit_rate
        
        # Tipos de requests más comunes
        tipos_requests = EstadisticaUsoEOSDA.objects.filter(
            timestamp__gte=month_ago
        ).values('tipo_request').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Endpoints más usados
        endpoints = EstadisticaUsoEOSDA.objects.filter(
            timestamp__gte=month_ago
        ).values('endpoint').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        response_data = {
            'periodo': {
                'inicio': month_ago.isoformat(),
                'fin': now.isoformat()
            },
            'resumen_hoy': stats_today,
            'resumen_semana': stats_week,
            'resumen_mes': stats_month,
            'cache': {
                'hits': cache_stats['cache_hits'],
                'misses': cache_stats['cache_misses'],
                'hit_rate_percent': round(cache_hit_rate, 2),
                'ahorro_requests': ahorro_requests,
                'ahorro_porcentaje': round(ahorro_porcentaje, 2)
            },
            'tipos_requests': list(tipos_requests),
            'endpoints_mas_usados': list(endpoints),
            'alertas': self._generar_alertas(stats_today, stats_week)
        }
        
        return Response(response_data)

    @action(detail=False, methods=['get'])
    def cache_efficiency(self, request):
        """
        GET /api/metrics/eosda/cache_efficiency/
        
        Retorna métricas de eficiencia del cache:
        - Entradas de cache activas
        - Tamaño promedio de datos cacheados
        - Tipos de datos más cacheados
        - Cache hits por tipo de dato
        """
        logger.info(f"Usuario {request.user.username} consultó eficiencia de cache")
        
        now = timezone.now()
        month_ago = now - timedelta(days=30)
        
        # Entradas de cache activas (no expiradas)
        cache_activo = CacheDatosEOSDA.objects.filter(
            expira_en__gt=now
        ).count()
        
        # Entradas de cache expiradas
        cache_expirado = CacheDatosEOSDA.objects.filter(
            expira_en__lte=now
        ).count()
        
        # Tipos de datos más cacheados
        tipos_cache = CacheDatosEOSDA.objects.filter(
            timestamp__gte=month_ago
        ).values('tipo_dato').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Tiempo promedio de vida del cache antes de expirar
        avg_cache_lifetime = CacheDatosEOSDA.objects.filter(
            timestamp__gte=month_ago,
            expira_en__gt=now
        ).count()
        
        response_data = {
            'cache_activo': cache_activo,
            'cache_expirado': cache_expirado,
            'total_entradas': cache_activo + cache_expirado,
            'tipos_datos_cacheados': list(tipos_cache),
            'recomendaciones': self._generar_recomendaciones_cache(cache_activo, cache_expirado)
        }
        
        return Response(response_data)

    @action(detail=False, methods=['get'])
    def error_analysis(self, request):
        """
        GET /api/metrics/eosda/error_analysis/
        
        Retorna análisis de errores de EOSDA API:
        - Errores más comunes
        - Tasa de error por endpoint
        - Errores recientes
        """
        logger.info(f"Usuario {request.user.username} consultó análisis de errores")
        
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        
        # Errores recientes
        errores_recientes = EstadisticaUsoEOSDA.objects.filter(
            exitoso=False,
            timestamp__gte=week_ago
        ).order_by('-timestamp')[:50]
        
        # Tipos de error más comunes
        errores_por_tipo = EstadisticaUsoEOSDA.objects.filter(
            exitoso=False,
            timestamp__gte=week_ago
        ).values('codigo_estado').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Endpoints con más errores
        endpoints_con_errores = EstadisticaUsoEOSDA.objects.filter(
            exitoso=False,
            timestamp__gte=week_ago
        ).values('endpoint').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        response_data = {
            'total_errores_semana': errores_recientes.count(),
            'errores_por_codigo': list(errores_por_tipo),
            'endpoints_con_errores': list(endpoints_con_errores),
            'errores_recientes': [
                {
                    'timestamp': e.timestamp.isoformat(),
                    'endpoint': e.endpoint,
                    'codigo_estado': e.codigo_estado,
                    'tipo_request': e.tipo_request
                }
                for e in errores_recientes[:10]
            ]
        }
        
        return Response(response_data)

    @action(detail=False, methods=['post'])
    def cleanup_expired_cache(self, request):
        """
        POST /api/metrics/eosda/cleanup_expired_cache/
        
        Limpia entradas de cache expiradas.
        Solo accesible para administradores.
        """
        if not request.user.is_staff:
            return Response(
                {'error': 'Solo administradores pueden limpiar cache'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        logger.warning(f"Admin {request.user.username} inició limpieza de cache expirado")
        
        now = timezone.now()
        deleted = CacheDatosEOSDA.objects.filter(
            expira_en__lt=now
        ).delete()
        
        logger.info(f"Cache limpiado: {deleted[0]} entradas eliminadas")
        
        return Response({
            'success': True,
            'entradas_eliminadas': deleted[0],
            'timestamp': now.isoformat()
        })

    def _generar_alertas(self, stats_today, stats_week):
        """Genera alertas basadas en uso anormal."""
        alertas = []
        
        # Alerta si hay muchos errores hoy
        if stats_today['total'] > 0:
            error_rate_today = stats_today['fallidos'] / stats_today['total'] * 100
            if error_rate_today > 20:
                alertas.append({
                    'nivel': 'warning',
                    'mensaje': f'Alta tasa de errores hoy: {error_rate_today:.1f}%',
                    'recomendacion': 'Revisar logs de EOSDA para identificar problemas'
                })
        
        # Alerta si se acerca al límite de requests
        if stats_today['total'] > 80:
            alertas.append({
                'nivel': 'critical',
                'mensaje': f'Uso alto de API EOSDA hoy: {stats_today["total"]} requests',
                'recomendacion': 'Posible proximidad al límite de API. Optimizar uso de cache.'
            })
        elif stats_today['total'] > 50:
            alertas.append({
                'nivel': 'warning',
                'mensaje': f'Uso moderado de API EOSDA hoy: {stats_today["total"]} requests',
                'recomendacion': 'Monitorear uso para evitar límites'
            })
        
        return alertas

    def _generar_recomendaciones_cache(self, cache_activo, cache_expirado):
        """Genera recomendaciones sobre el cache."""
        recomendaciones = []
        
        if cache_expirado > cache_activo * 0.5:
            recomendaciones.append({
                'tipo': 'limpieza',
                'mensaje': 'Alto número de entradas de cache expiradas',
                'accion': 'Ejecutar limpieza de cache con cleanup_expired_cache'
            })
        
        if cache_activo < 10:
            recomendaciones.append({
                'tipo': 'optimizacion',
                'mensaje': 'Bajo uso de cache',
                'accion': 'Verificar que el cache esté funcionando correctamente'
            })
        
        return recomendaciones
