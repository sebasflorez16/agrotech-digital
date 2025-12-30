"""
API Views para Servicio Optimizado EOSDA
Endpoints para usar el caché SHA-256 y Statistics API
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from datetime import datetime, date
import logging

from parcels.models import Parcel, CacheDatosEOSDA, EstadisticaUsoEOSDA
from parcels.eosda_optimized_service import get_eosda_service

logger = logging.getLogger(__name__)


class EOSDAOptimizedDataView(APIView):
    """
    Endpoint optimizado para obtener datos satelitales EOSDA
    
    GET /api/parcels/<parcel_id>/eosda-optimized/
    ?fecha_inicio=2024-01-01&fecha_fin=2024-06-30&indices=NDVI,NDMI,SAVI
    
    Reduce consumo en 90% usando caché SHA-256
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, parcel_id):
        try:
            # Obtener parcela
            parcela = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
            
            if not parcela.geom:
                return Response({
                    'error': 'La parcela no tiene geometría definida'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Parámetros
            fecha_inicio_str = request.query_params.get('fecha_inicio')
            fecha_fin_str = request.query_params.get('fecha_fin')
            indices_str = request.query_params.get('indices', 'NDVI')
            
            if not fecha_inicio_str or not fecha_fin_str:
                return Response({
                    'error': 'Parámetros fecha_inicio y fecha_fin son requeridos'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Convertir fechas
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            
            # Parsear índices
            indices = [idx.strip().upper() for idx in indices_str.split(',')]
            indices_validos = ['NDVI', 'NDMI', 'SAVI', 'EVI']
            indices = [idx for idx in indices if idx in indices_validos]
            
            if not indices:
                return Response({
                    'error': f'Índices válidos: {", ".join(indices_validos)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Obtener servicio optimizado
            service = get_eosda_service()
            
            # Consultar datos (usa caché automáticamente)
            datos = service.obtener_multi_indice(
                geometria=parcela.geom,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                indices=indices,
                parcela_id=parcela.id
            )
            
            # Obtener métricas
            metricas = EstadisticaUsoEOSDA.obtener_metricas_mes_actual()
            
            return Response({
                'success': True,
                'parcela': {
                    'id': parcela.id,
                    'nombre': parcela.name,
                    'area_ha': parcela.area_hectares()
                },
                'parametros': {
                    'fecha_inicio': fecha_inicio_str,
                    'fecha_fin': fecha_fin_str,
                    'indices': indices
                },
                'datos': datos,
                'metricas_mes': metricas
            }, status=status.HTTP_200_OK)
        
        except ValueError as e:
            return Response({
                'error': f'Formato de fecha inválido: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'[EOSDA_OPTIMIZED_ERROR] {str(e)}', exc_info=True)
            return Response({
                'error': f'Error al obtener datos: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EOSDAMetricsView(APIView):
    """
    GET /api/parcels/eosda-metrics/
    
    Retorna métricas de uso de EOSDA (caché, requests, tiempos)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            metricas = EstadisticaUsoEOSDA.obtener_metricas_mes_actual()
            
            # Datos adicionales
            total_cache_items = CacheDatosEOSDA.objects.count()
            cache_por_indice = {}
            
            for indice in ['NDVI', 'NDMI', 'SAVI', 'EVI']:
                count = CacheDatosEOSDA.objects.filter(indice=indice).count()
                cache_por_indice[indice] = count
            
            return Response({
                'success': True,
                'mes_actual': metricas,
                'cache': {
                    'total_items': total_cache_items,
                    'por_indice': cache_por_indice
                },
                'recomendaciones': self._generar_recomendaciones(metricas)
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f'[METRICS_ERROR] {str(e)}', exc_info=True)
            return Response({
                'error': f'Error al obtener métricas: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _generar_recomendaciones(self, metricas):
        """Genera recomendaciones basadas en las métricas"""
        recomendaciones = []
        
        tasa_cache = metricas.get('tasa_cache', 0)
        errores = metricas.get('errores', 0)
        
        if tasa_cache < 50:
            recomendaciones.append({
                'tipo': 'warning',
                'mensaje': f'Tasa de caché baja ({tasa_cache}%). Considere aumentar el período de validez del caché.'
            })
        elif tasa_cache >= 80:
            recomendaciones.append({
                'tipo': 'success',
                'mensaje': f'Excelente tasa de caché ({tasa_cache}%). Optimización funcionando correctamente.'
            })
        
        if errores > 10:
            recomendaciones.append({
                'tipo': 'error',
                'mensaje': f'Se detectaron {errores} errores este mes. Revisar logs de EOSDA API.'
            })
        
        return recomendaciones


class EOSDACacheClearView(APIView):
    """
    POST /api/parcels/eosda-cache/clear/
    
    Limpia caché expirado de EOSDA
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            eliminados = CacheDatosEOSDA.limpiar_expirados()
            
            return Response({
                'success': True,
                'mensaje': f'{eliminados} cachés expirados eliminados',
                'total_restante': CacheDatosEOSDA.objects.count()
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f'[CACHE_CLEAR_ERROR] {str(e)}', exc_info=True)
            return Response({
                'error': f'Error al limpiar caché: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
