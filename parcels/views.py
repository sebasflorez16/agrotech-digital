
# --- IMPORTS ORDENADOS ---
import logging
import requests
import json
import math
import numpy as np
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsAdminOrReadOnly
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from .models import Parcel, ParcelSceneCache, CropHealthStatus, MonitoringEvent, ParcelZonification
from .serializers import ParcelSerializer
from .eosda_client import get_eosda_client
from billing.decorators import check_eosda_limit

logger = logging.getLogger(__name__)

# --- WEATHER FORECAST API ---
from .metereological import WeatherForecastView

class ParcelScenesByDateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    @check_eosda_limit
    def get(self, request, parcel_id):
        """
        GET /api/parcels/parcel/<parcel_id>/scenes/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
        Retorna: { "scenes": [...], "request_id": ..., "eosda_raw": ... }
        
        OPTIMIZACIÓN: Primero busca en cache de base de datos antes de llamar a EOSDA.
        El cache se guarda por 7 días para minimizar llamadas a la API.
        """
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        logger.info(f"[SCENES_BY_DATE] Parámetros recibidos: parcel_id={parcel_id}, start_date={start_date}, end_date={end_date}")
        
        if not start_date or not end_date:
            logger.error("[SCENES_BY_DATE] Faltan parámetros start_date y end_date.")
            return Response({"error": "Faltan parámetros start_date y end_date."}, status=400)
        
        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
        field_id = getattr(parcel, "eosda_id", None)
        logger.info(f"[SCENES_BY_DATE] field_id de parcela: {field_id}")
        
        if not field_id:
            logger.error("[SCENES_BY_DATE] La parcela no tiene un field_id satelital válido.")
            return Response({"error": "La parcela no tiene un identificador satelital válido."}, status=404)
        
        # ============ CACHE EN BASE DE DATOS ============
        # Verificar si tenemos escenas cacheadas para este rango de fechas
        cache_key = f"scenes_{field_id}_{start_date}_{end_date}"
        
        # Buscar en cache de Django (memoria/redis)
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.info(f"[SCENES_BY_DATE] ✅ CACHE HIT (memoria): Retornando {len(cached_response.get('scenes', []))} escenas cacheadas")
            return Response(cached_response, status=200)
        
        # Buscar escenas en la base de datos (ParcelSceneCache)
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            cached_scenes = ParcelSceneCache.objects.filter(
                parcel=parcel,
                date__gte=start_dt,
                date__lte=end_dt
            ).order_by('-date')
            
            if cached_scenes.exists():
                # Verificar si el cache no ha expirado (7 días)
                oldest_cache = cached_scenes.order_by('created_at').first()
                cache_age = timezone.now() - oldest_cache.created_at
                
                if cache_age < timedelta(days=7):
                    # Convertir a formato de respuesta
                    scenes_list = []
                    for sc in cached_scenes:
                        scene_data = {
                            'view_id': sc.scene_id,
                            'date': sc.date.isoformat(),
                            'cloudCoverage': sc.metadata.get('cloudCoverage', 0) if sc.metadata else 0,
                        }
                        if sc.metadata:
                            scene_data.update(sc.metadata)
                        scenes_list.append(scene_data)
                    
                    response_data = {
                        "request_id": None,
                        "scenes": scenes_list,
                        "from_cache": True,
                        "cache_age_hours": int(cache_age.total_seconds() / 3600)
                    }
                    
                    # Guardar en cache de memoria por 1 hora
                    cache.set(cache_key, response_data, 3600)
                    
                    logger.info(f"[SCENES_BY_DATE] ✅ CACHE HIT (DB): Retornando {len(scenes_list)} escenas cacheadas (edad: {cache_age})")
                    return Response(response_data, status=200)
                else:
                    logger.info(f"[SCENES_BY_DATE] Cache expirado (edad: {cache_age}), consultando EOSDA...")
        except Exception as cache_error:
            logger.warning(f"[SCENES_BY_DATE] Error al buscar en cache: {cache_error}")
        
        # ============ LLAMADA A EOSDA ============
        # Llamar a EOSDA scene-search filtrando por fechas
        client = get_eosda_client()
        request_url = f"https://api-connect.eos.com/scene-search/for-field/{field_id}"
        headers = {
            "x-api-key": settings.EOSDA_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "params": {
                "date_start": start_date,
                "date_end": end_date,
                "data_source": ["sentinel2"]
            }
        }
        logger.info(f"[SCENES_BY_DATE] URL: {request_url}")
        logger.info(f"[SCENES_BY_DATE] Payload enviado: {payload}")
        # NOTA: No loguear headers para no exponer la API key
        import time
        try:
            req_response = client.post(request_url, payload, headers=headers)
            logger.info(f"[SCENES_BY_DATE] POST Status: {req_response.status_code}")
            logger.info(f"[SCENES_BY_DATE] POST Response: {req_response.text}")
            
            # Manejo específico de error 402 (límite de requests excedido)
            if req_response.status_code == 402:
                error_data = req_response.json() if req_response.content else {}
                logger.error(f"[SCENES_BY_DATE] Límite de requests EOSDA excedido: {error_data}")
                return Response({
                    "error": "API Satelital: Límite de consultas excedido",
                    "message": "Se ha alcanzado el límite mensual de consultas al proveedor de datos satelitales. Contacte al administrador.",
                    "error_code": "SATELITAL_LIMIT_EXCEEDED",
                    "limit_info": error_data
                }, status=402)
                
            # Manejo específico de error 404 (campo no encontrado)
            if req_response.status_code == 404:
                error_data = req_response.json() if req_response.content else {}
                logger.error(f"[SCENES_BY_DATE] Campo no encontrado en EOSDA: {error_data}")
                return Response({
                    "error": "API Satelital: Campo no encontrado",
                    "message": f"El campo con ID {field_id} no existe en el proveedor de datos satelitales. Verifique que el campo esté correctamente registrado.",
                    "error_code": "SATELITAL_FIELD_NOT_FOUND",
                    "field_id": field_id,
                    "details": error_data
                }, status=404)
            
            req_response.raise_for_status()
            req_data = req_response.json()
            request_id = req_data.get('request_id')
            # Si hay request_id, hacer GET con polling para obtener escenas reales
            if request_id:
                logger.info(f"[SCENES_BY_DATE] request_id recibido: {request_id}")
                scenes_url = f"https://api-connect.eos.com/scene-search/for-field/{field_id}/{request_id}"
                scenes_headers = {
                    "x-api-key": settings.EOSDA_API_KEY
                }
                max_attempts = 10
                delay_seconds = 3
                for attempt in range(max_attempts):
                    scenes_response = client.get(scenes_url, headers=scenes_headers)
                    logger.info(f"[SCENES_BY_DATE] GET intento {attempt+1}/{max_attempts}: status={scenes_response.status_code}")
                    print(f"[SCENES_BY_DATE] Intento {attempt+1}/{max_attempts} GET status: {scenes_response.status_code}")
                    scenes_response.raise_for_status()
                    scenes_data = scenes_response.json()
                    if scenes_data.get('status') != 'pending':
                        scenes = scenes_data.get('result', [])
                        logger.info(f"[SCENES_BY_DATE] Escenas recibidas (GET): {len(scenes)} escenas")
                        
                        # ============ GUARDAR EN CACHE ============
                        self._save_scenes_to_cache(parcel, scenes, cache_key)
                        
                        client.record(getattr(request, 'tenant', None), operation="scenes", parcel_id=parcel_id, user=getattr(request, 'user', None))
                        return Response({"request_id": request_id, "scenes": scenes, "eosda_raw": scenes_data}, status=200)
                    time.sleep(delay_seconds)
                # Si tras los intentos sigue en pending, informar al usuario
                logger.warning(f"[SCENES_BY_DATE] EOSDA sigue en pending tras {max_attempts} intentos.")
                print(f"[SCENES_BY_DATE] EOSDA sigue en pending tras {max_attempts} intentos.")
                return Response({"request_id": request_id, "scenes": [], "eosda_raw": scenes_data, "status": "pending", "message": "La consulta está en proceso. Intenta nuevamente en unos minutos."}, status=202)
            else:
                # Si no hay request_id, usar las escenas del POST
                scenes = req_data.get('result', [])
                logger.info(f"[SCENES_BY_DATE] Escenas recibidas (POST directo): {len(scenes)} escenas")
                
                # ============ GUARDAR EN CACHE ============
                self._save_scenes_to_cache(parcel, scenes, cache_key)
                
                client.record(getattr(request, 'tenant', None), operation="scenes", parcel_id=parcel_id, user=getattr(request, 'user', None))
                return Response({"request_id": None, "scenes": scenes, "eosda_raw": req_data}, status=200)
        except requests.exceptions.RequestException as e:
            logger.error(f"[SCENES_BY_DATE] Error en la petición a EOSDA: {str(e)}")
            print(f"[SCENES_BY_DATE] Error en la petición a EOSDA: {str(e)}")
            
            # Manejo específico de errores HTTP
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 402:
                    return Response({
                        "error": "API Satelital: Límite de consultas excedido",
                        "message": "Se ha alcanzado el límite mensual de consultas al proveedor de datos satelitales. Contacte al administrador.",
                        "error_code": "SATELITAL_LIMIT_EXCEEDED"
                    }, status=402)
            
            return Response({"error": str(e)}, status=500)

    def _save_scenes_to_cache(self, parcel, scenes, cache_key):
        """Guarda las escenas en cache (base de datos y memoria)"""
        from datetime import datetime
        from django.utils import timezone
        
        try:
            # Guardar en cache de memoria por 1 hora
            response_data = {"request_id": None, "scenes": scenes, "from_cache": False}
            cache.set(cache_key, response_data, 3600)
            
            # Guardar cada escena en la base de datos
            for scene in scenes:
                try:
                    scene_id = scene.get('view_id') or scene.get('id') or scene.get('scene_id')
                    if not scene_id:
                        continue
                    
                    # Parsear fecha
                    date_str = scene.get('date', '')
                    if date_str:
                        if 'T' in date_str:
                            scene_date = datetime.strptime(date_str.split('T')[0], "%Y-%m-%d").date()
                        else:
                            scene_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    else:
                        continue
                    
                    # Crear o actualizar cache de escena
                    ParcelSceneCache.objects.update_or_create(
                        parcel=parcel,
                        scene_id=scene_id,
                        index_type='NDVI',  # Por defecto, las escenas son genéricas
                        defaults={
                            'date': scene_date,
                            'metadata': {
                                'cloudCoverage': scene.get('cloudCoverage', scene.get('cloud', 0)),
                                'satellite': scene.get('satellite', 'sentinel2'),
                            },
                            'raw_response': scene,
                            'expires_at': timezone.now() + timezone.timedelta(days=7)
                        }
                    )
                except Exception as scene_error:
                    logger.warning(f"[CACHE] Error guardando escena {scene}: {scene_error}")
            
            logger.info(f"[CACHE] ✅ {len(scenes)} escenas guardadas en cache")

            # Actualizar estado de salud (Monitoreo Continuo Fase 2)
            if scenes:
                try:
                    best_scene = min(scenes, key=lambda s: s.get('cloudCoverage', s.get('cloud', 100)))
                    health = CropHealthStatus.get_or_create_for_parcel(parcel)
                    scene_date = best_scene.get('date')
                    if scene_date:
                        from datetime import datetime
                        if 'T' in str(scene_date):
                            image_date = datetime.strptime(str(scene_date).split('T')[0], '%Y-%m-%d').date()
                        else:
                            image_date = datetime.strptime(str(scene_date), '%Y-%m-%d').date()
                        health.update_from_observation(
                            image_date=image_date,
                            cloud_cover=best_scene.get('cloudCoverage', best_scene.get('cloud', 0))
                        )
                        logger.info(f"[HEALTH] Estado actualizado para {parcel.name}")
                except Exception as he:
                    logger.warning(f"[HEALTH] Error actualizando estado: {he}")

        except Exception as e:
            logger.warning(f"[CACHE] Error guardando escenas en cache: {e}")

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.db.models import Sum
from .models import Parcel, ParcelSceneCache
from .serializers import ParcelSerializer
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
import requests
import logging
from django.shortcuts import render
import json

logger = logging.getLogger(__name__)


class ParcelViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de parcelas con verificación ESTRICTA de límites de hectáreas.
    
    Los límites se verifican contra el plan de suscripción del tenant antes de
    permitir crear o actualizar parcelas.
    """
    serializer_class = ParcelSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        qs = Parcel.objects.filter(is_deleted=False)
        request = getattr(self, 'request', None)
        if request is not None and hasattr(request, 'tenant') and request.tenant:
            qs = qs.filter(tenant_id=request.tenant.id)
        return qs

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant_id=tenant.id if tenant else None)

    def _get_current_hectares(self, exclude_parcel_id=None):
        """Calcula el total de hectáreas actuales del tenant."""
        qs = self.get_queryset()
        if exclude_parcel_id:
            qs = qs.exclude(pk=exclude_parcel_id)
        
        total = 0
        for parcel in qs:
            total += parcel.area_hectares() or 0
        return total

    def _calculate_parcel_area(self, geom_data):
        """Calcula el área en hectáreas de un polígono GeoJSON (fuente única)."""
        from .geometry import calculate_area_hectares
        return calculate_area_hectares(geom_data)

    def _verify_hectare_limit(self, request, new_hectares, exclude_parcel_id=None):
        """
        Verifica que la operación no exceda el límite de hectáreas del plan.
        
        Returns:
            tuple: (is_allowed: bool, error_response: Response or None)
        """
        subscription = getattr(request, 'subscription', None)
        
        if not subscription:
            # 🛡️ MODO DESARROLLADOR: bypass para superusuarios con toggle activo
            from config.devmode import is_dev_mode_active
            if is_dev_mode_active(request):
                logger.info(f"[ParcelViewSet] 🔓 DEVELOPER MODE: {request.user.username} creando parcela sin suscripción")
                return True, None

            logger.warning("Intento de crear parcela sin suscripción activa")
            return False, Response({
                'error': 'No tienes una suscripción activa',
                'code': 'no_subscription',
                'message': 'Debes tener un plan activo para crear o modificar parcelas.',
                'upgrade_url': '/billing/plans/'
            }, status=402)
        
        current_hectares = self._get_current_hectares(exclude_parcel_id)
        total_hectares = current_hectares + new_hectares
        
        is_within, limit = subscription.check_limit('hectares', total_hectares)
        
        if not is_within:
            logger.warning(
                f"Límite de hectáreas excedido: tenant={getattr(request, 'tenant', 'unknown')}, "
                f"current={current_hectares:.2f}, new={new_hectares:.2f}, limit={limit}"
            )
            return False, Response({
                'error': 'Límite de hectáreas excedido',
                'code': 'hectares_limit_exceeded',
                'current': round(current_hectares, 2),
                'new': round(new_hectares, 2),
                'total': round(total_hectares, 2),
                'limit': limit,
                'plan': subscription.plan.name,
                'message': f'Tu plan {subscription.plan.name} permite hasta {limit} hectáreas. '
                           f'Actualmente tienes {current_hectares:.2f} ha registradas. '
                           f'Al agregar {new_hectares:.2f} ha superarías el límite permitido.',
                'suggestions': [
                    'Mejora a un plan con más hectáreas disponibles',
                    'Elimina parcelas que ya no uses para liberar espacio',
                    'Reduce el tamaño de la parcela que intentas crear'
                ],
                'upgrade_url': '/billing/upgrade/'
            }, status=403)
        
        # Actualizar métricas de uso
        try:
            from billing.models import UsageMetrics
            tenant = getattr(request, 'tenant', None)
            if tenant:
                metrics = UsageMetrics.get_or_create_current(tenant)
                metrics.hectares_used = total_hectares
                metrics.save()
        except Exception as e:
            logger.warning(f"No se pudo actualizar métricas de hectáreas: {e}")
        
        return True, None

    def create(self, request, *args, **kwargs):
        """
        Crea una nueva parcela verificando ESTRICTAMENTE el límite de hectáreas y parcelas.
        """
        # 1. Verificar límite de parcelas
        subscription = getattr(request, 'subscription', None)
        if subscription:
            current_parcels = self.get_queryset().count()
            is_within, limit = subscription.check_limit('parcels', current_parcels + 1)
            if not is_within:
                logger.warning(
                    f"Límite de parcelas excedido: current={current_parcels}, limit={limit}, "
                    f"plan={subscription.plan.name}"
                )
                return Response({
                    'error': 'Límite de parcelas excedido',
                    'code': 'parcels_limit_exceeded',
                    'current': current_parcels,
                    'limit': limit,
                    'plan': subscription.plan.name,
                    'message': f'Tu plan {subscription.plan.name} permite hasta {limit} parcelas. '
                               f'Actualmente tienes {current_parcels}.',
                    'suggestions': [
                        'Mejora tu plan para crear más parcelas',
                        'Elimina parcelas que ya no uses',
                    ],
                    'upgrade_url': '/billing/upgrade/'
                }, status=403)

        # 2. Verificar límite de hectáreas
        geom_data = request.data.get('geom')
        new_hectares = self._calculate_parcel_area(geom_data)
        
        is_allowed, error_response = self._verify_hectare_limit(request, new_hectares)
        if not is_allowed:
            return error_response
        
        logger.info(f"Creando parcela de {new_hectares:.2f} ha - Límites verificados OK")
        response = super().create(request, *args, **kwargs)

        # ── Onboarding asistido: enriquecer la respuesta con guía y contexto del plan ──
        try:
            data = response.data if hasattr(response, 'data') else None
            if isinstance(data, dict):
                from billing.models import UsageMetrics

                onboarding = {'area_hectares': round(new_hectares, 2)}
                subscription = getattr(request, 'subscription', None)
                if subscription:
                    plan = subscription.plan
                    metrics = None
                    try:
                        tenant = getattr(request, 'tenant', None)
                        if tenant:
                            metrics = UsageMetrics.get_or_create_current(tenant)
                    except Exception:
                        metrics = None

                    parcela_limit = plan.get_limit('parcels', 0)
                    total_parcelas_actuales = Parcel.objects.filter(is_deleted=False).count()
                    onboarding['plan'] = {
                        'tier': plan.tier,
                        'name': plan.name,
                        'remaining_hectares': max(
                            float(plan.get_limit('hectares', 0)) - float(new_hectares), 0
                        ) if plan.get_limit('hectares', 0) != 'unlimited' else 'unlimited',
                        'remaining_parcels': max(
                            int(parcela_limit) - total_parcelas_actuales, 0
                        ) if parcela_limit != 'unlimited' else 'unlimited',
                        'eosda_requests_used': metrics.eosda_requests if metrics else 0,
                        'eosda_requests_limit': plan.get_limit('eosda_requests', 0),
                    }

                # Guía de siguientes pasos para el agricultor
                onboarding['next_steps'] = [
                    {
                        'step': 1,
                        'title': 'Dibuja o selecciona tu parcela en el mapa',
                        'detail': 'Verifica que el polígono corresponda al lote real.',
                    },
                    {
                        'step': 2,
                        'title': 'Ejecuta tu primer análisis satelital NDVI',
                        'detail': 'El análisis muestra el vigor de tu cultivo y toma ~30 segundos.',
                    },
                    {
                        'step': 3,
                        'title': 'Crea un ciclo de cultivo',
                        'detail': 'Vincular un cultivo activa la interpretación agronómica automática.',
                    },
                    {
                        'step': 4,
                        'title': 'Activa el Monitoreo Continuo (Pro)',
                        'detail': 'Recibe el estado de salud de tu cultivo con cada nueva imagen satelital.',
                    },
                ]
                data['onboarding'] = onboarding
        except Exception as onboarding_err:
            logger.warning(f"[ONBOARDING] No se pudo enriquecer la respuesta: {onboarding_err}")

        return response

    def update(self, request, *args, **kwargs):
        """
        Actualiza una parcela verificando que el nuevo tamaño no exceda el límite.
        """
        instance = self.get_object()
        geom_data = request.data.get('geom', instance.geom)
        new_hectares = self._calculate_parcel_area(geom_data)
        
        # Excluimos la parcela actual del cálculo ya que la estamos actualizando
        is_allowed, error_response = self._verify_hectare_limit(
            request, new_hectares, exclude_parcel_id=instance.pk
        )
        if not is_allowed:
            return error_response
        
        logger.info(f"Actualizando parcela {instance.pk} a {new_hectares:.2f} ha - Límite verificado OK")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """
        Actualización parcial con verificación de límites si se modifica el geometría.
        """
        if 'geom' in request.data:
            instance = self.get_object()
            geom_data = request.data.get('geom')
            new_hectares = self._calculate_parcel_area(geom_data)
            
            is_allowed, error_response = self._verify_hectare_limit(
                request, new_hectares, exclude_parcel_id=instance.pk
            )
            if not is_allowed:
                return error_response
        
        return super().partial_update(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data = {
            "cesium_token": settings.CESIUM_ACCESS_TOKEN,
            "parcels": response.data
        }
        return response

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        qs = self.get_queryset()
        total = qs.count()
        total_area = 0
        activas = qs.filter(state=True).count()
        inactivas = qs.filter(state=False).count()
        tipos = {}
        suelos = {}
        topografias = {}
        last_parcel = None
        last_date = None
        for p in qs:
            total_area += p.area_hectares()
            # Tipos de campo
            if p.field_type:
                tipos[p.field_type] = tipos.get(p.field_type, 0) + 1
            # Suelos
            if p.soil_type:
                suelos[p.soil_type] = suelos.get(p.soil_type, 0) + 1
            # Topografía
            if p.topography:
                topografias[p.topography] = topografias.get(p.topography, 0) + 1
            # Última parcela
            if not last_date or (p.created_on and p.created_on > last_date):
                last_parcel = p
                last_date = p.created_on
        # Top 3 tipos de campo
        top_tipos = sorted(tipos.items(), key=lambda x: x[1], reverse=True)[:3]
        area_promedio = round(total_area / total, 2) if total > 0 else 0
        # Cambiar el límite a 300 hectáreas
        AREA_LIMIT = 300  # en hectáreas
        area_restante = max(AREA_LIMIT - total_area, 0)  # en hectáreas

        # Datos satelitales REALES (nunca simulados):
        # - ndvi_data: observaciones reales por mes desde el cache de escenas EOSDA
        # - latest_ndvi: último NDVI real registrado por CropHealthStatus
        MESES_ES = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
        }
        ndvi_data = {}
        latest_scene_date = None
        try:
            scenes_qs = ParcelSceneCache.objects.filter(
                parcel__is_deleted=False
            ).order_by('date')
            for scene in scenes_qs.iterator():
                month_key = MESES_ES.get(scene.date.month, scene.date.strftime('%m'))
                ndvi_data[month_key] = ndvi_data.get(month_key, 0) + 1
                if latest_scene_date is None or scene.date > latest_scene_date:
                    latest_scene_date = scene.date
        except Exception as cache_err:
            logger.warning(f"[SUMMARY] No se pudo leer cache de escenas: {cache_err}")

        # Último NDVI real conocido por parcela (Monitoreo Continuo)
        latest_ndvi = None
        latest_ndvi_parcel = None
        try:
            health_qs = CropHealthStatus.objects.filter(parcel__is_deleted=False)
            best = None
            for health in health_qs.iterator():
                if health.ndvi_last is None:
                    continue
                if best is None or health.ndvi_last > best['ndvi']:
                    best = {'ndvi': health.ndvi_last, 'parcel': health.parcel.name,
                            'date': health.last_image_date or health.last_observation_date}
            if best:
                latest_ndvi = round(best['ndvi'], 3)
                latest_ndvi_parcel = best['parcel']
        except Exception as health_err:
            logger.warning(f"[SUMMARY] No se pudo leer estado de salud: {health_err}")

        ndvi_available = len(ndvi_data) > 0
        if not ndvi_available:
            ndvi_message = (
                "Aún no hay observaciones satelitales. "
                "Ejecuta un análisis en la sección Parcelas para ver tu primer NDVI real."
            )
        else:
            ndvi_message = (
                f"Observaciones satelitales reales por mes. "
                f"Última escena: {latest_scene_date}."
            )

        return Response({
            "total": total,
            "total_area": round(total_area, 2),
            "activas": activas,
            "inactivas": inactivas,
            "area_promedio": area_promedio,
            "top_tipos": top_tipos,
            "last_parcel": last_parcel.name if last_parcel else None,
            "last_parcel_date": last_parcel.created_on.strftime('%d/%m/%Y %H:%M') if last_parcel and last_parcel.created_on else None,
            "area_restante": round(area_restante, 2),
            "ndvi_data": ndvi_data,
            "ndvi_available": ndvi_available,
            "ndvi_message": ndvi_message,
            "latest_ndvi": latest_ndvi,
            "latest_ndvi_parcel": latest_ndvi_parcel,
            "latest_scene_date": latest_scene_date.isoformat() if latest_scene_date else None,
        })

    @action(detail=False, methods=["post"], url_path="ndvi-historical")
    def ndvi_historical(self, request):
        """
        Endpoint para obtener los promedios mensuales de NDVI de una parcela usando EOSDA.
        Recibe un polígono (GeoJSON) y un rango de fechas (start_date, end_date).
        
        PROTEGIDO: Verifica límite de requests EOSDA antes de procesar.
        """
        # === VERIFICACIÓN DE LÍMITE EOSDA ===
        from billing.models import UsageMetrics
        from config.devmode import is_dev_mode_active
        subscription = getattr(request, 'subscription', None)
        tenant = getattr(request, 'tenant', None)
        dev_mode = is_dev_mode_active(request)

        if not subscription and not dev_mode:
            return Response({
                'error': 'No tienes una suscripción activa',
                'code': 'no_subscription'
            }, status=402)

        if dev_mode:
            logger.info(f"[ParcelViewSet] 🔓 DEVELOPER MODE: {request.user.username} — EOSDA ndvi sin límites")
        elif subscription and tenant:
            metrics = UsageMetrics.get_or_create_current(tenant)
            is_within, limit = subscription.check_limit('eosda_requests', metrics.eosda_requests + 1)

            if not is_within:
                from django.utils import timezone
                now = timezone.now()
                next_month = now.replace(day=1) + timezone.timedelta(days=32)
                reset_date = next_month.replace(day=1)

                return Response({
                    'error': 'Límite de análisis satelitales excedido',
                    'code': 'eosda_limit_exceeded',
                    'used': metrics.eosda_requests,
                    'limit': limit,
                    'plan': subscription.plan.name,
                    'reset_date': reset_date.strftime('%Y-%m-%d'),
                    'upgrade_url': '/billing/upgrade/'
                }, status=429)
        # === FIN VERIFICACIÓN ===
        
        logger.debug(f"Request data: {request.data}")
        polygon = request.data.get("polygon")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        if not polygon or not start_date or not end_date:
            return Response({"error": "Faltan parámetros obligatorios (polygon, start_date, end_date)."}, status=400)

        eosda_url = "https://api-connect.eos.com/v1/indices/ndvi"
        headers = {
            "x-api-key": settings.EOSDA_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "geometry": polygon,
            "start_date": start_date,
            "end_date": end_date
        }
        logger.debug(f"Payload: {payload}")
        logger.debug(f"Headers: {headers}")

        try:
            response = get_eosda_client().post(eosda_url, payload, headers=headers)
            response.raise_for_status()
            ndvi_data = response.json()
            
            # Registro de consumo real (incrementa cuota + EosdaRequestLog)
            get_eosda_client().record(tenant, operation="index", index_type="NDVI", user=getattr(request, 'user', None))
                
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Error al conectar con el servicio satelital: {str(e)}"}, status=500)

        return Response(ndvi_data, status=200)

    @action(detail=False, methods=["post"], url_path="water-stress-historical")
    def water_stress_historical(self, request):
        """
        Endpoint para obtener los promedios mensuales de estrés hídrico de una parcela usando EOSDA.
        Recibe un polígono (GeoJSON) y un rango de fechas (start_date, end_date).
        
        PROTEGIDO: Verifica límite de requests EOSDA antes de procesar.
        """
        # === VERIFICACIÓN DE LÍMITE EOSDA ===
        from billing.models import UsageMetrics
        from config.devmode import is_dev_mode_active
        subscription = getattr(request, 'subscription', None)
        tenant = getattr(request, 'tenant', None)
        dev_mode = is_dev_mode_active(request)

        if not subscription and not dev_mode:
            return Response({
                'error': 'No tienes una suscripción activa',
                'code': 'no_subscription'
            }, status=402)

        if dev_mode:
            logger.info(f"[ParcelViewSet] 🔓 DEVELOPER MODE: {request.user.username} — EOSDA water_stress sin límites")
        elif subscription and tenant:
            metrics = UsageMetrics.get_or_create_current(tenant)
            is_within, limit = subscription.check_limit('eosda_requests', metrics.eosda_requests + 1)

            if not is_within:
                from django.utils import timezone
                now = timezone.now()
                next_month = now.replace(day=1) + timezone.timedelta(days=32)
                reset_date = next_month.replace(day=1)

                return Response({
                    'error': 'Límite de análisis satelitales excedido',
                    'code': 'eosda_limit_exceeded',
                    'used': metrics.eosda_requests,
                    'limit': limit,
                    'plan': subscription.plan.name,
                    'reset_date': reset_date.strftime('%Y-%m-%d'),
                    'upgrade_url': '/billing/upgrade/'
                }, status=429)
        # === FIN VERIFICACIÓN ===

        logger.debug(f"Request data: {request.data}")
        polygon = request.data.get("polygon")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        if not polygon or not start_date or not end_date:
            return Response({"error": "Faltan parámetros obligatorios (polygon, start_date, end_date)."}, status=400)

        eosda_url = "https://api-connect.eos.com/v1/indices/ndmi"  # NDMI para estrés hídrico
        headers = {
            "x-api-key": settings.EOSDA_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "geometry": polygon,
            "start_date": start_date,
            "end_date": end_date
        }
        logger.debug(f"Payload: {payload}")
        logger.debug(f"Headers: {headers}")

        try:
            response = get_eosda_client().post(eosda_url, payload, headers=headers)
            response.raise_for_status()
            ndmi_data = response.json()
            
            # Registro de consumo real (incrementa cuota + EosdaRequestLog)
            get_eosda_client().record(tenant, operation="index", index_type="NDMI", user=getattr(request, 'user', None))
                
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Error al conectar con el servicio satelital: {str(e)}"}, status=500)

        return Response(ndmi_data, status=200)

    @action(detail=False, methods=["get"], url_path="list-parcels")
    def list_parcels(self, request):
        """
        Endpoint para listar todas las parcelas con sus polígonos y nombres.
        """
        qs = self.get_queryset()
        parcels_data = [
            {
                "id": parcel.id,
                "name": parcel.name,
                "polygon": parcel.geom  # Ahora es un dict (GeoJSON)
            }
            for parcel in qs
        ]
        return Response(parcels_data, status=200)

    @action(detail=True, methods=['post'], url_path='sync-eosda')
    def sync_eosda(self, request, pk=None):
        """
        Reintenta la sincronización de la parcela con EOSDA (crea el campo en
        field-management si aún no tiene eosda_id).
        """
        parcel = self.get_object()
        if parcel.eosda_id:
            return Response({
                'message': 'La parcela ya está sincronizada.',
                'eosda_id': parcel.eosda_id,
                'sync_status': parcel.sync_status,
            }, status=200)
        if not parcel.geom:
            return Response({'error': 'La parcela no tiene geometría.', 'code': 'no_geometry'}, status=400)

        parcel._sync_to_eosda()
        parcel.save(update_fields=['eosda_id', 'sync_status', 'sync_error', 'updated_on'])

        return Response({
            'eosda_id': parcel.eosda_id,
            'sync_status': parcel.sync_status,
            'sync_error': parcel.sync_error,
        }, status=200)

    @action(detail=True, methods=['get'], url_path='fusion-assessment')
    def fusion_assessment(self, request, pk=None):
        """Fusion Engine — evalúa el estado del cultivo combinando óptico + radar + clima"""
        from .fusion_engine import quick_assessment
        parcel = self.get_object()
        return Response(quick_assessment(parcel))

    @action(detail=True, methods=['get'], url_path='radar-changes')
    def radar_changes(self, request, pk=None):
        """Sentinel-1 — detección de cambios vía radar (penetra nubes)"""
        from .sentinel1 import get_crop_status_from_radar
        parcel = self.get_object()
        if not parcel.geom:
            return Response({'error': 'Parcela sin geometría', 'code': 'no_geometry'}, status=400)
        result = get_crop_status_from_radar(parcel.geom, days_back=30)
        return Response(result)

    # Esta acción fue eliminada para evitar conflictos con la implementación en metereological.py
    # La API de pronóstico del tiempo ahora está implementada en WeatherForecastView
        
        print(f"[WEATHER_FORECAST] Cache miss, generando nuevos datos...")
        
        # Obtener coordenadas del centroide de la parcela
        if hasattr(parcel.geom, 'centroid'):
            centroid = parcel.geom.centroid
            lat = centroid.y





# ENDPOINTS ALINEADOS CON EL FLUJO EOSDA Y EL FRONTEND

# --- EOSDA Scenes & Image API ---
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import requests
import json
from billing.decorators import check_eosda_limit, require_feature

class EosdaScenesView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    @check_eosda_limit
    def post(self, request):
        """
        POST /api/parcels/eosda-scenes/
        Recibe: { "field_id": "..." }
        Retorna: { "request_id": "...", "scenes": [...] }
        
        OPTIMIZACIÓN: Cache de escenas por field_id para evitar requests duplicados a EOSDA
        """
        field_id = request.data.get("field_id")
        if not field_id:
            return Response({"error": "Falta el parámetro field_id."}, status=400)
        
        # Cache + deduplicación (requests idénticos simultáneos → 1 sola llamada a EOSDA)
        client = get_eosda_client()
        cache_key = f"eosda_scenes_{field_id}"

        def _fetch_scenes():
            from datetime import datetime, timedelta
            today = datetime.utcnow().date()
            date_end = today.isoformat()
            date_start = (today - timedelta(days=90)).isoformat()
            request_url = f"https://api-connect.eos.com/scene-search/for-field/{field_id}"
            headers = {
                "x-api-key": settings.EOSDA_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "params": {
                    "date_start": date_start,
                    "date_end": date_end,
                    "data_source": ["sentinel2"]
                }
            }
            req_response = client.post(request_url, payload, headers=headers)
            logger.info(f"EOSDA request POST status: {req_response.status_code}")
            req_response.raise_for_status()
            req_data = req_response.json()
            request_id = req_data.get('request_id')

            if not request_id:
                scenes = req_data.get('result', [])
                return {"request_id": None, "scenes": scenes}

            scenes_url = f"https://api-connect.eos.com/scene-search/for-field/{field_id}/{request_id}"
            scenes_headers = {"x-api-key": settings.EOSDA_API_KEY}
            import time
            max_attempts = 10
            delay_seconds = 3
            scenes = []
            for attempt in range(max_attempts):
                scenes_response = client.get(scenes_url, headers=scenes_headers)
                logger.info(f"EOSDA scenes GET intento {attempt+1}/{max_attempts}: status={scenes_response.status_code}")
                scenes_response.raise_for_status()
                scenes_data = scenes_response.json()
                if scenes_data.get('status') != 'pending':
                    scenes = scenes_data.get('result', [])
                    logger.info(f"EOSDA scenes GET completado: {len(scenes)} escenas encontradas")
                    break
                logger.info(f"EOSDA scenes GET: aún pendiente, esperando {delay_seconds}s...")
                time.sleep(delay_seconds)
            else:
                logger.warning(f"EOSDA scenes GET: se agotaron {max_attempts} intentos de polling, aún pendiente")
            return {"request_id": request_id, "scenes": scenes}

        try:
            response_data, source = client.cached(cache_key, _fetch_scenes, ttl=21600)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en la petición a EOSDA: {str(e)}")
            return Response({"error": str(e)}, status=500)

        if source == "eosda":
            client.record(getattr(request, 'tenant', None), operation="scenes", user=getattr(request, 'user', None))
        logger.info(f"[{'CACHE HIT' if source == 'cache' else 'EOSDA'}] Escenas para field_id {field_id}: {len(response_data.get('scenes', []))}")
        return Response(response_data, status=200)

class EosdaImageView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    @check_eosda_limit
    def post(self, request):
        """
        POST /api/parcels/eosda-image/
        Recibe: { "field_id": "...", "view_id": "...", "type": "ndvi" | "ndmi" | "evi", "format": "png" }
        Retorna: { "request_id": "..." }
        
        OPTIMIZACIÓN: Cache de request_id por combinación field_id+view_id+type para evitar requests duplicados
        RESTRICCIÓN: Los índices disponibles dependen del plan del usuario
        """
        try:
            field_id = request.data.get("field_id")
            view_id = request.data.get("view_id")
            index_type = request.data.get("type")
            img_format = request.data.get("format", "png")
            logger.info(f"[EOSDA_IMAGE] Payload recibido: field_id={field_id}, view_id={view_id}, type={index_type}, format={img_format}")
            
            # Validación de parámetros - NDVI, NDMI, EVI, SAVI y NDRE
            if not field_id or not view_id or index_type not in ["ndvi", "ndmi", "evi", "savi", "ndre"]:
                logger.error(f"[EOSDA_IMAGE] Parámetros inválidos: field_id={field_id}, view_id={view_id}, type={index_type}")
                return Response({"error": "Parámetros inválidos."}, status=400)
            
            # ── Restricción de índices por plan ──
            from config.devmode import is_dev_mode_active
            if not is_dev_mode_active(request):
                subscription = getattr(request, 'subscription', None)
                if subscription:
                    allowed_indices = subscription.plan.features_included or []
                    if index_type not in allowed_indices:
                        plan_name = subscription.plan.name
                        index_names = {
                            'ndvi': 'NDVI',
                            'savi': 'SAVI',
                            'ndmi': 'NDMI',
                            'evi': 'EVI',
                            'ndre': 'NDRE',
                        }
                        logger.warning(
                            f"[EOSDA_IMAGE] Índice '{index_type}' no permitido en plan {plan_name}. "
                            f"Permitidos: {allowed_indices}"
                        )
                        return Response({
                            'error': f'El índice {index_names.get(index_type, index_type.upper())} no está disponible en tu plan',
                            'code': 'index_not_available',
                            'index': index_type,
                            'allowed_indices': [i for i in allowed_indices if i in ['ndvi', 'savi', 'ndmi', 'evi', 'ndre']],
                            'plan': plan_name,
                            'message': f'Tu plan {plan_name} no incluye análisis {index_names.get(index_type, index_type.upper())}. '
                                       f'Mejora tu plan para acceder a más índices satelitales.',
                            'upgrade_url': '/billing/upgrade/'
                        }, status=403)
            
            # Verificar cache de request_id por combinación field_id+view_id+type (cache por 30 minutos)
            cache_key = f"eosda_image_request_{field_id}_{view_id}_{index_type}"
            cached_request_id = cache.get(cache_key)
            if cached_request_id:
                logger.info(f"[CACHE HIT] request_id encontrado en cache: {cached_request_id}")
                return Response({"request_id": cached_request_id}, status=200)
            
            eosda_url = f"https://api-connect.eos.com/field-imagery/indicies/{field_id}"
            headers = {
                "x-api-key": settings.EOSDA_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "params": {
                    "view_id": view_id,
                    "index": index_type.upper(),
                    "format": img_format
                }
            }
            logger.info(f"[EOSDA_IMAGE] URL: {eosda_url}")
            logger.info(f"[EOSDA_IMAGE] Headers: {headers}")
            logger.info(f"[EOSDA_IMAGE] Payload enviado: {payload}")
            
            client = get_eosda_client()
            response = client.post(eosda_url, payload, headers=headers)
            logger.info(f"[EOSDA_IMAGE] Status: {response.status_code}")
            logger.info(f"[EOSDA_IMAGE] Response: {response.text}")
            response.raise_for_status()
            data = response.json()
            request_id = data.get("request_id")
            if not request_id:
                logger.error(f"[EOSDA_IMAGE] No se encontró el request_id en la respuesta: {data}")
                return Response({"error": "No se encontró el request_id."}, status=404)
            
            # Guardar request_id en cache por 30 minutos
            cache.set(cache_key, request_id, 1800)  # 30 minutos
            logger.info(f"[CACHE SET] request_id guardado en cache: {request_id}")
            logger.info(f"[EOSDA_IMAGE] request_id recibido: {request_id}")
            client.record(getattr(request, 'tenant', None), operation="image", index_type=index_type, user=getattr(request, 'user', None))
            return Response({"request_id": request_id}, status=200)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[EOSDA_IMAGE] Error en la petición a EOSDA: {str(e)}")
            return Response({"error": f"Error de conexión con el servicio satelital: {str(e)}"}, status=500)
        except Exception as e:
            logger.error(f"[EOSDA_IMAGE] Error inesperado: {str(e)}")
            logger.error(f"[EOSDA_IMAGE] Tipo de error: {type(e).__name__}")
            import traceback
            logger.error(f"[EOSDA_IMAGE] Traceback: {traceback.format_exc()}")
            return Response({"error": f"Error interno del servidor: {str(e)}"}, status=500)

class EosdaImageResultView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    @check_eosda_limit
    def get(self, request):
        """
        GET /api/parcels/eosda-image-result/?field_id=...&request_id=...
        Retorna: { "image_base64": "..." }
        
        OPTIMIZACIÓN: Cache dual de imágenes (por request_id y por field+view+type) para evitar downloads duplicados
        """
        import base64
        field_id = request.query_params.get("field_id")
        request_id = request.query_params.get("request_id")
        index_type = request.query_params.get("type", "ndvi")
        view_id = request.query_params.get("view_id", "")
        logger.info(f"[EOSDA_IMAGE_RESULT] Params recibidos: field_id={field_id}, request_id={request_id}, type={index_type}")
        if not field_id or not request_id:
            logger.error(f"[EOSDA_IMAGE_RESULT] Parámetros inválidos: field_id={field_id}, request_id={request_id}")
            return Response({"error": "Parámetros inválidos."}, status=400)
        
        # Verificar cache dual: por request_id Y por combinación field+view+type (cache por 1 hora)
        image_cache_key = f"eosda_image_{request_id}"
        composite_cache_key = f"eosda_image_composite_{field_id}_{view_id}_{index_type}"
        
        # Intentar cache por request_id primero
        cached_image = cache.get(image_cache_key)
        if cached_image:
            logger.info(f"[CACHE HIT] Imagen encontrada en cache por request_id: {request_id}")
            return Response({"image_base64": cached_image}, status=200)
        
        # Intentar cache composite si view_id disponible
        if view_id:
            cached_image = cache.get(composite_cache_key)
            if cached_image:
                logger.info(f"[CACHE HIT] Imagen encontrada en cache composite: {composite_cache_key}")
                return Response({"image_base64": cached_image}, status=200)
        
        eosda_url = f"https://api-connect.eos.com/field-imagery/{field_id}/{request_id}"
        headers = {
            "x-api-key": settings.EOSDA_API_KEY
        }
        logger.info(f"[EOSDA_IMAGE_RESULT] URL: {eosda_url}")
        logger.info(f"[EOSDA_IMAGE_RESULT] Headers: {headers}")
        try:
            client = get_eosda_client()
            response = client.get(eosda_url, headers=headers)
            logger.info(f"[EOSDA_IMAGE_RESULT] Status: {response.status_code}")
            content_type = response.headers.get('Content-Type', '')
            # Si la respuesta es imagen, convertir a base64 y retornar
            if content_type.startswith('image/'):
                try:
                    image_base64 = base64.b64encode(response.content).decode('utf-8')
                    logger.info(f"[EOSDA_IMAGE_RESULT] Imagen recibida y convertida a base64.")
                    # Guardar imagen en cache dual por 1 hora
                    cache.set(image_cache_key, image_base64, 3600)  # Por request_id
                    if view_id:
                        cache.set(composite_cache_key, image_base64, 3600)  # Por field+view+type
                    logger.info(f"[CACHE SET] Imagen guardada en cache dual para request_id: {request_id}")
                    client.record(getattr(request, 'tenant', None), operation="image_result", index_type=index_type, user=getattr(request, 'user', None))
                    return Response({"image_base64": image_base64}, status=200)
                except Exception as e:
                    logger.error(f"[EOSDA_IMAGE_RESULT] Error al convertir imagen a base64: {e}")
                    return Response({"error": "Error al procesar la imagen recibida."}, status=500)
            # Si la respuesta es JSON, analizar el estado y errores específicos
            elif content_type.startswith('application/json') or content_type.startswith('text/json'):
                try:
                    data = response.json()
                    logger.error(f"[EOSDA_IMAGE_RESULT] Respuesta no es imagen: {data}")
                    # Imagen aún en proceso
                    if data.get("status") == "created":
                        return Response({"error": "La imagen aún está en proceso. Intenta nuevamente en unos minutos."}, status=202)
                    # Error específico de AOI fuera de cobertura
                    error_msg = None
                    if isinstance(data, dict):
                        if 'error_message' in data and isinstance(data['error_message'], dict):
                            error_msg = data['error_message'].get('error')
                        elif 'error_message' in data and isinstance(data['error_message'], str):
                            error_msg = data['error_message']
                    if error_msg and 'AOI is out of image extent' in error_msg:
                        logger.warning(f"[EOSDA_IMAGE_RESULT] AOI fuera de cobertura: {error_msg}")
                        return Response({"error": "La parcela está fuera de la cobertura de la imagen seleccionada. Selecciona otra escena o ajusta el polígono."}, status=404)
                    # Otros errores
                    return Response({"error": "No se recibió una imagen.", "details": data}, status=400)
                except Exception as e:
                    logger.error(f"[EOSDA_IMAGE_RESULT] Error al parsear JSON: {e}")
                    return Response({"error": "Respuesta inesperada del servicio satelital."}, status=500)
            # Si la respuesta es binaria pero no tiene content-type correcto, intentar detectar PNG/JPG
            elif response.content[:8] == b'\x89PNG\r\n\x1a\n' or response.content[:2] == b'\xff\xd8':
                try:
                    image_base64 = base64.b64encode(response.content).decode('utf-8')
                    logger.info(f"[EOSDA_IMAGE_RESULT] Imagen binaria detectada y convertida a base64.")
                    # Guardar imagen en cache dual por 1 hora
                    cache.set(image_cache_key, image_base64, 3600)  # Por request_id
                    if view_id:
                        cache.set(composite_cache_key, image_base64, 3600)  # Por field+view+type
                    logger.info(f"[CACHE SET] Imagen binaria guardada en cache dual para request_id: {request_id}")
                    client.record(getattr(request, 'tenant', None), operation="image_result", index_type=index_type, user=getattr(request, 'user', None))
                    return Response({"image_base64": image_base64}, status=200)
                except Exception as e:
                    logger.error(f"[EOSDA_IMAGE_RESULT] Error al convertir binario a base64: {e}")
                    return Response({"error": "Error al procesar la imagen binaria recibida."}, status=500)
            # Si no es imagen ni JSON, devolver texto plano para depuración
            else:
                text = response.text
                logger.error(f"[EOSDA_IMAGE_RESULT] Respuesta inesperada, no es imagen ni JSON. Texto: {text}")
                return Response({"error": text}, status=500)
        except requests.exceptions.RequestException as e:
            logger.error(f"[EOSDA_IMAGE_RESULT] Error en la petición a EOSDA: {str(e)}")
            return Response({"error": str(e)}, status=500)

class EosdaSceneAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    @check_eosda_limit
    def post(self, request):
        """
        POST /api/parcels/eosda-scene-analytics/
        Body: {
            "field_id": "string",
            "view_id": "string", 
            "scene_date": "YYYY-MM-DD",
            "indices": ["ndvi"]  # opcional, por defecto solo NDVI para optimizar requests
        }
        
        Retorna: {
            "scene_info": {...},
            "analytics": {
                "ndvi": {"mean": 0.65, "std": 0.15, ...},
                "ndmi": {"mean": 0.42, "std": 0.12, ...},
                "evi": {"mean": 0.38, "std": 0.11, ...}
            }
        }
        
        OPTIMIZACIÓN: Cache por field_id+view_id+date (cache por 2 horas)
        """
        field_id = request.data.get("field_id")
        view_id = request.data.get("view_id")
        scene_date = request.data.get("scene_date")
        indices = request.data.get("indices", ["ndvi", "ndmi", "evi"])
        
        logger.info(f"[SCENE_ANALYTICS] Params: field_id={field_id}, view_id={view_id}, scene_date={scene_date}")
        
        # Validación de parámetros
        if not field_id or not view_id:
            logger.error(f"[SCENE_ANALYTICS] Parámetros inválidos: field_id={field_id}, view_id={view_id}")
            return Response({"error": "Faltan parámetros obligatorios: field_id, view_id."}, status=400)
        
        valid_indices = ["ndvi", "ndmi", "evi", "ndre", "savi", "lai", "fpar", "fcover"]
        indices = [idx for idx in indices if idx in valid_indices]
        if not indices:
            indices = ["ndvi"]  # Por defecto solo NDVI para optimizar requests (usuario puede solicitar más explícitamente)
        
        # Cache + deduplicación (requests idénticos simultáneos → 1 sola llamada a EOSDA)
        cache_key = f"eosda_analytics_{field_id}_{view_id}_{scene_date}"
        
        # EOSDA API: El endpoint /v1/analytics no existe, usaremos /v1/indices para obtener datos estadísticos
        # Convertir scene_date a rango de un día para simular analytics de escena específica
        from datetime import datetime, timedelta
        try:
            date_obj = datetime.strptime(scene_date, "%Y-%m-%d")
            start_date = date_obj.strftime("%Y-%m-%d")
            end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            logger.error(f"[SCENE_ANALYTICS] Fecha inválida: {scene_date}")
            return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}, status=400)
        
        # Obtener polígono de la parcela para la consulta
        try:
            from .models import Parcel
            parcel = Parcel.objects.get(eosda_id=field_id)
            if not parcel.geom:
                return Response({"error": "La parcela no tiene geometría definida"}, status=400)
            
            # Convertir geometría a GeoJSON - manejo flexible para diferentes tipos
            import json
            from django.contrib.gis.geos import GEOSGeometry
            
            geom = parcel.geom
            logger.info(f"[SCENE_ANALYTICS] Geometría tipo: {type(geom)}, valor: {geom}")
            
            # Manejar diferentes tipos de geometría
            if isinstance(geom, dict):
                # Ya es GeoJSON dict
                polygon_geojson = geom
                logger.info(f"[SCENE_ANALYTICS] Geometría ya es dict GeoJSON")
            elif isinstance(geom, str):
                # String GeoJSON, parsear a dict
                try:
                    polygon_geojson = json.loads(geom)
                    logger.info(f"[SCENE_ANALYTICS] Geometría parseada desde string JSON")
                except json.JSONDecodeError:
                    # String WKT, convertir a GEOS y luego GeoJSON
                    geos_geom = GEOSGeometry(geom)
                    polygon_geojson = json.loads(geos_geom.geojson)
                    logger.info(f"[SCENE_ANALYTICS] Geometría convertida desde WKT")
            else:
                # Objeto GEOS Geometry
                polygon_geojson = json.loads(geom.geojson)
                logger.info(f"[SCENE_ANALYTICS] Geometría convertida desde objeto GEOS")
        except Parcel.DoesNotExist:
            return Response({"error": "Parcela no encontrada"}, status=404)
        except Exception as e:
            logger.error(f"[SCENE_ANALYTICS] Error obteniendo geometría: {e}")
            return Response({"error": "Error obteniendo geometría de la parcela"}, status=500)
        
        client = get_eosda_client()

        def _fetch_analytics():
            analytics_result = {}
            for index_name in indices:
                eosda_url = f"https://api-connect.eos.com/v1/indices/{index_name}"
                headers = {
                    "x-api-key": settings.EOSDA_API_KEY,
                    "Content-Type": "application/json"
                }
                payload = {
                    "geometry": polygon_geojson,
                    "start_date": start_date,
                    "end_date": end_date
                }
                response = client.post(eosda_url, payload, headers=headers)
                logger.info(f"[SCENE_ANALYTICS] Status {index_name}: {response.status_code}")
                if response.status_code == 200:
                    index_data = response.json()
                    if 'data' in index_data and index_data['data']:
                        latest_point = index_data['data'][-1]
                        analytics_result[index_name] = {
                            "mean": latest_point.get("mean"),
                            "median": latest_point.get("median"),
                            "std": latest_point.get("std_dev"),
                            "min": latest_point.get("min"),
                            "max": latest_point.get("max"),
                            "date": latest_point.get("date"),
                            "source": "eosda_indices_api"
                        }
                    else:
                        analytics_result[index_name] = {
                            "error": "No hay datos disponibles para esta fecha",
                            "source": "eosda_indices_api"
                        }
                else:
                    logger.warning(f"[SCENE_ANALYTICS] Error en {index_name}: {response.status_code}")
                    analytics_result[index_name] = {
                        "error": f"Error HTTP {response.status_code}",
                        "source": "eosda_indices_api"
                    }
            return {
                "scene_info": {
                    "field_id": field_id,
                    "view_id": view_id,
                    "date": scene_date,
                    "indices_requested": indices,
                    "date_range_used": f"{start_date} to {end_date}"
                },
                "analytics": analytics_result,
                "metadata": {
                    "source": "eosda_indices_api_workaround",
                    "note": "Analytics obtenidos usando endpoint de índices históricos con rango de 1 día",
                    "cached_at": None,
                    "cache_key": cache_key
                }
            }

        try:
            response_data, source = client.cached(cache_key, _fetch_analytics, ttl=7200)
        except requests.exceptions.RequestException as e:
            logger.error(f"[SCENE_ANALYTICS] Error en petición a EOSDA: {str(e)}")
            return Response({"error": f"Error al obtener analytics: {str(e)}"}, status=500)

        if source == "eosda":
            client.record(getattr(request, 'tenant', None), operation="scene_analytics", parcel_id=parcel.id, user=getattr(request, 'user', None))
        return Response(response_data, status=200)

class EosdaAdvancedStatisticsView(APIView):
    """
    Vista que utiliza la nueva EOSDA Statistics API (type: mt_stats) para obtener
    estadísticas avanzadas por escena: mean, median, std, min, max, percentiles, variance, etc.
    
    Esta API es superior al workaround anterior porque:
    - Proporciona estadísticas más precisas y completas
    - Incluye percentiles (p10, p90), quartiles (q1, q3), variance
    - Admite filtrado por cobertura de nubes
    - Proporciona estadísticas específicas por escena/fecha
    - Es la API oficial recomendada para analytics de vegetación
    """
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    @check_eosda_limit
    def post(self, request):
        """
        POST /api/parcels/eosda-advanced-statistics/
        Body: {
            "field_id": "string",
            "view_id": "string", 
            "scene_date": "YYYY-MM-DD",
            "indices": ["ndvi", "ndmi", "evi"],  # opcional, por defecto ["ndvi"]
            "max_cloud_cover": 50,  # opcional, por defecto 10
            "sensors": ["S2"]  # opcional, por defecto ["S2", "L8"]
        }
        
        Retorna: {
            "task_id": "uuid",
            "status": "created|started|finished",
            "scene_info": {...},
            "statistics": {
                "ndvi": {
                    "mean": 0.65, "median": 0.62, "std": 0.15,
                    "min": 0.1, "max": 0.9, "variance": 0.023,
                    "q1": 0.55, "q3": 0.75, "p10": 0.45, "p90": 0.82,
                    "cloud_coverage": 5.2, "date": "2024-01-15",
                    "scene_id": "...", "view_id": "..."
                }
            }
        }
        
        OPTIMIZACIÓN: Cache por field_id+view_id+date+indices (cache por 24 horas)
        """
        field_id = request.data.get("field_id")
        view_id = request.data.get("view_id")
        scene_date = request.data.get("scene_date")
        indices = request.data.get("indices", ["ndvi"])
        max_cloud_cover = request.data.get("max_cloud_cover", 10)
        sensors = request.data.get("sensors", ["S2", "L8"])
        
        logger.info(f"[ADVANCED_STATS] Params: field_id={field_id}, view_id={view_id}, scene_date={scene_date}")
        
        # Validación de parámetros
        if not field_id or not view_id or not scene_date:
            logger.error(f"[ADVANCED_STATS] Parámetros inválidos: field_id={field_id}, view_id={view_id}, scene_date={scene_date}")
            return Response({"error": "Faltan parámetros obligatorios: field_id, view_id, scene_date."}, status=400)
        
        # Validar índices soportados por EOSDA Statistics API
        # NOTA: Statistics API soporta bandas espectrales, no índices calculados
        valid_indices = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B10", "B11", "B12"]  # Bandas Sentinel-2
        indices = [idx for idx in indices if idx in valid_indices]
        if not indices:
            indices = ["B04", "B08", "B03"]  # Bandas por defecto (Red, NIR, Green)
        
        # Solo procesamos hasta 3 bandas por vez (limitación de EOSDA)
        if len(indices) > 3:
            indices = indices[:3]
            logger.warning(f"[ADVANCED_STATS] Solo se procesarán las primeras 3 bandas: {indices}")
        
        # Verificar cache de statistics por combinación field_id+view_id+date+indices (cache por 24 horas)
        cache_key = f"eosda_advanced_stats_{field_id}_{view_id}_{scene_date}_{'_'.join(sorted(indices))}"
        cached_stats = cache.get(cache_key)
        if cached_stats:
            logger.info(f"[CACHE HIT] Advanced statistics encontradas en cache: {cache_key}")
            return Response(cached_stats, status=200)
        
        # Convertir scene_date a rango (±1 día para capturar la escena específica)
        from datetime import datetime, timedelta
        import json
        try:
            date_obj = datetime.strptime(scene_date, "%Y-%m-%d")
            # Rango de ±1 día para asegurar que capturamos la escena específica
            start_date = (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            logger.error(f"[ADVANCED_STATS] Fecha inválida: {scene_date}")
            return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}, status=400)
        
        # Obtener polígono de la parcela para la consulta
        try:
            from .models import Parcel
            parcel = Parcel.objects.get(eosda_id=field_id)
            if not parcel.geom:
                return Response({"error": "La parcela no tiene geometría definida"}, status=400)
            
            # Convertir geometría a GeoJSON - manejo flexible para diferentes tipos
            import json
            from django.contrib.gis.geos import GEOSGeometry
            
            geom = parcel.geom
            logger.info(f"[ADVANCED_STATS] Geometría tipo: {type(geom)}, valor: {geom}")
            
            # Manejar diferentes tipos de geometría
            if isinstance(geom, dict):
                # Ya es GeoJSON dict
                polygon_geojson = geom
                logger.info(f"[ADVANCED_STATS] Geometría ya es dict GeoJSON")
            elif isinstance(geom, str):
                # String GeoJSON, parsear a dict
                try:
                    polygon_geojson = json.loads(geom)
                    logger.info(f"[ADVANCED_STATS] Geometría parseada desde string JSON")
                except json.JSONDecodeError:
                    # String WKT, convertir a GEOS y luego GeoJSON
                    geos_geom = GEOSGeometry(geom)
                    polygon_geojson = json.loads(geos_geom.geojson)
                    logger.info(f"[ADVANCED_STATS] Geometría convertida desde WKT")
            else:
                # Objeto GEOS Geometry
                polygon_geojson = json.loads(geom.geojson)
                logger.info(f"[ADVANCED_STATS] Geometría convertida desde objeto GEOS")
                
            logger.info(f"[ADVANCED_STATS] GeoJSON final: {polygon_geojson}")
            
        except Parcel.DoesNotExist:
            return Response({"error": "Parcela no encontrada"}, status=404)
        except Exception as e:
            logger.error(f"[ADVANCED_STATS] Error obteniendo geometría: {e}")
            logger.error(f"[ADVANCED_STATS] Tipo de geometría: {type(parcel.geom) if 'parcel' in locals() else 'parcel no definido'}")
            return Response({"error": "Error obteniendo geometría de la parcela"}, status=500)
        
        logger.info(f"[ADVANCED_STATS] Creando tarea para {len(indices)} índices: {indices}")
        logger.info(f"[ADVANCED_STATS] Rango de fechas: {start_date} - {end_date}")
        
        # Crear tarea en EOSDA Statistics API
        try:
            eosda_url = "https://api-connect.eos.com/api/gdw/api"
            headers = {
                "x-api-key": settings.EOSDA_API_KEY,
                "Content-Type": "application/json"
            }
            
            # Preparar payload para Statistics API
            payload = {
                "type": "mt_stats",
                "params": {
                    "bm_type": indices,  # Lista de índices a calcular (máximo 3)
                    "date_start": start_date,
                    "date_end": end_date,
                    "geometry": polygon_geojson,
                    "sensors": sensors,
                    "max_cloud_cover_in_aoi": max_cloud_cover,
                    "exclude_cover_pixels": True,  # Excluir píxeles con nubes
                    "cloud_masking_level": 2,  # Nivel medio+alto de detección de nubes
                    "reference": f"agrotech_{field_id}_{view_id}_{scene_date}",
                    "limit": 100  # Máximo de escenas a considerar
                }
            }
            
            logger.info(f"[ADVANCED_STATS] URL: {eosda_url}")
            logger.info(f"[ADVANCED_STATS] Payload: {json.dumps(payload, indent=2)}")
            
            # Crear tarea
            client = get_eosda_client()
            response = client.post(eosda_url, payload, headers=headers)
            logger.info(f"[ADVANCED_STATS] Status Code: {response.status_code}")
            logger.info(f"[ADVANCED_STATS] Response: {response.text}")
            
            # EOSDA devuelve 202 (Accepted) para tareas creadas exitosamente
            if response.status_code in [200, 202]:
                task_data = response.json()
                task_id = task_data.get("task_id")
                status = task_data.get("status", "created")
                
                logger.info(f"[ADVANCED_STATS] Tarea creada exitosamente: {task_id}")
                
                # Estructurar respuesta inicial
                response_data = {
                    "task_id": task_id,
                    "status": status,
                    "scene_info": {
                        "field_id": field_id,
                        "view_id": view_id,
                        "date": scene_date,
                        "indices_requested": indices,
                        "date_range_used": f"{start_date} to {end_date}",
                        "max_cloud_cover": max_cloud_cover,
                        "sensors": sensors
                    },
                    "statistics": None,  # Se llenará cuando la tarea esté completa
                    "metadata": {
                        "source": "eosda_statistics_api",
                        "api_type": "mt_stats",
                        "task_timeout": task_data.get("task_timeout", 3600),
                        "req_id": task_data.get("req_id"),
                        "cache_key": cache_key,
                        "created_at": datetime.now().isoformat()
                    }
                }
                
                # Guardar respuesta inicial en cache por 1 hora (mientras se procesa)
                cache.set(cache_key, response_data, 3600)  # 1 hora
                logger.info(f"[CACHE SET] Advanced statistics task guardada en cache: {cache_key}")
                
                client.record(getattr(request, 'tenant', None), operation="advanced_statistics", parcel_id=parcel.id, user=getattr(request, 'user', None))
                return Response(response_data, status=200)
            else:
                logger.error(f"[ADVANCED_STATS] Error creando tarea: {response.status_code} - {response.text}")
                return Response({
                    "error": f"Error creando tarea de estadísticas: {response.status_code}",
                    "details": response.text
                }, status=500)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[ADVANCED_STATS] Error en petición a EOSDA: {str(e)}")
            return Response({"error": f"Error al crear la tarea de estadísticas: {str(e)}"}, status=500)


class EosdaStatisticsTaskStatusView(APIView):
    """
    Vista para consultar el estado de una tarea de Statistics API y obtener los resultados
    cuando esté completa.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get(self, request, task_id):
        """
        GET /api/parcels/eosda-statistics-task/{task_id}/
        
        Retorna el estado actual de la tarea y los resultados si están disponibles.
        """
        logger.info(f"[STATS_TASK_STATUS] Consultando estado de tarea: {task_id}")
        
        try:
            eosda_url = f"https://api-connect.eos.com/api/gdw/api/{task_id}"
            headers = {
                "x-api-key": settings.EOSDA_API_KEY
            }
            
            client = get_eosda_client()
            response = client.get(eosda_url, headers=headers)
            logger.info(f"[STATS_TASK_STATUS] Status Code: {response.status_code}")
            
            if response.status_code == 200:
                task_result = response.json()
                
                # Verificar si hay errores en la respuesta
                errors = task_result.get("errors", [])
                results = task_result.get("result", [])
                status = task_result.get("status", "unknown")
                task_type = task_result.get("task_type", "")
                error_message = task_result.get("error_message", {})
                
                # Manejar caso cuando results es None
                if results is None:
                    results = []
                
                logger.info(f"[STATS_TASK_STATUS] Status: {status}, Task Type: {task_type}, Errors: {len(errors)}, Results: {len(results)}")
                logger.info(f"[STATS_TASK_STATUS] Error Message: {error_message}")
                logger.info(f"[STATS_TASK_STATUS] Full response: {json.dumps(task_result, indent=2)}")
                
                # Verificar si la tarea tiene errores (task_type: "error" o error_message presente)
                if task_type == "error" or error_message:
                    error_detail = error_message.get("error", "Error desconocido") if error_message else "Error en la tarea"
                    logger.error(f"[STATS_TASK_STATUS] Tarea {task_id} falló: {error_detail}")
                    return Response({
                        "task_id": task_id,
                        "status": "failed",
                        "error": error_detail,
                        "message": f"La tarea falló: {error_detail}",
                        "metadata": {
                            "source": "eosda_statistics_api",
                            "task_type": task_type,
                            "full_error": error_message,
                            "retrieved_at": datetime.now().isoformat()
                        }
                    }, status=200)
                
                # Si el status indica que está completada, procesar independientemente de si hay results
                if status in ["finished", "completed", "success"]:
                    if results:
                        # Procesar resultados y organizarlos por índice
                        processed_stats = self._process_statistics_results(results)
                        
                        response_data = {
                            "task_id": task_id,
                            "status": "finished",
                            "statistics": processed_stats,
                            "errors": errors,
                            "metadata": {
                                "source": "eosda_statistics_api",
                                "total_scenes": len(results),
                                "total_errors": len(errors),
                                "retrieved_at": datetime.now().isoformat()
                            }
                        }
                        
                        return Response(response_data, status=200)
                    else:
                        # Tarea completada pero sin resultados
                        logger.warning(f"[STATS_TASK_STATUS] Tarea {task_id} completada pero sin resultados")
                        return Response({
                            "task_id": task_id,
                            "status": "finished_no_results",
                            "statistics": {},
                            "errors": errors,
                            "message": "Tarea completada pero no se encontraron datos para los parámetros especificados.",
                            "metadata": {
                                "source": "eosda_statistics_api",
                                "total_errors": len(errors),
                                "retrieved_at": datetime.now().isoformat()
                            }
                        }, status=200)
                
                elif results:
                    # Hay resultados aunque el status no sea explícitamente "finished"
                    processed_stats = self._process_statistics_results(results)
                    
                    response_data = {
                        "task_id": task_id,
                        "status": "finished",
                        "statistics": processed_stats,
                        "errors": errors,
                        "metadata": {
                            "source": "eosda_statistics_api",
                            "total_scenes": len(results),
                            "total_errors": len(errors),
                            "retrieved_at": datetime.now().isoformat()
                        }
                    }
                    
                    return Response(response_data, status=200)
                    
                elif errors:
                    logger.warning(f"[STATS_TASK_STATUS] Tarea completada con errores: {errors}")
                    return Response({
                        "task_id": task_id,
                        "status": "finished_with_errors",
                        "statistics": {},
                        "errors": errors,
                        "metadata": {
                            "source": "eosda_statistics_api",
                            "total_errors": len(errors),
                            "retrieved_at": datetime.now().isoformat()
                        }
                    }, status=200)
                    
                else:
                    # Tarea aún en proceso
                    return Response({
                        "task_id": task_id,
                        "status": "processing",
                        "statistics": None,
                        "message": "Tarea aún en proceso. Intente nuevamente en unos momentos."
                    }, status=202)  # Accepted
                    
            else:
                logger.error(f"[STATS_TASK_STATUS] Error consultando tarea: {response.status_code} - {response.text}")
                return Response({
                    "error": f"Error consultando estado de tarea: {response.status_code}",
                    "details": response.text
                }, status=500)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[STATS_TASK_STATUS] Error en petición a EOSDA: {str(e)}")
            return Response({"error": f"Error al consultar estado de tarea: {str(e)}"}, status=500)
    
    def _process_statistics_results(self, results):
        """
        Procesa los resultados de la Statistics API y los organiza por índice.
        
        Input: Lista de resultados de EOSDA con estadísticas por escena
        Output: Diccionario organizado por índice con estadísticas agregadas
        """
        processed = {}
        
        # Agrupar resultados por scene/date si hay múltiples índices
        for result in results:
            scene_id = result.get("scene_id")
            view_id = result.get("view_id")
            date = result.get("date")
            cloud = result.get("cloud")
            
            # Los resultados de mt_stats vienen organizados por escena
            # Cada resultado contiene estadísticas para todos los índices solicitados
            
            # Para este caso, tomamos el primer resultado (escena más cercana a la fecha solicitada)
            if not processed:  # Primera escena encontrada
                processed = {
                    "scene_id": scene_id,
                    "view_id": view_id,
                    "date": date,
                    "cloud_coverage": cloud,
                    "statistics": {
                        "mean": result.get("average"),
                        "median": result.get("median"),
                        "std": result.get("std"),
                        "min": result.get("min"),
                        "max": result.get("max"),
                        "variance": result.get("variance"),
                        "q1": result.get("q1"),  # Primer quartil
                        "q3": result.get("q3"),  # Tercer quartil
                        "p10": result.get("p10"),  # Percentil 10
                        "p90": result.get("p90"),  # Percentil 90
                        "notes": result.get("notes", [])
                    }
                }
                
        return processed

class EosdaBulkAnalyticsView(APIView):
    """
    Vista para obtener analytics de múltiples escenas de una vez
    Útil para construir datasets históricos rápidamente
    """
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def post(self, request):
        """
        POST /api/parcels/eosda-bulk-analytics/
        Body: {
            "field_id": "string",
            "scenes": [
                {"view_id": "abc123", "date": "2024-01-15"},
                {"view_id": "def456", "date": "2024-01-20"}
            ],
            "indices": ["ndvi", "ndmi"]  # opcional
        }
        
        Retorna analytics de múltiples escenas de una vez
        """
        field_id = request.data.get("field_id")
        scenes = request.data.get("scenes", [])
        indices = request.data.get("indices", ["ndvi", "ndmi", "evi"])
        
        logger.info(f"[BULK_ANALYTICS] field_id={field_id}, {len(scenes)} escenas")
        
        if not field_id or not scenes:
            return Response({"error": "Faltan parámetros: field_id, scenes"}, status=400)
        
        results = []
        cache_misses = []
        
        # Verificar cache para cada escena
        for scene in scenes:
            view_id = scene.get("view_id")
            date = scene.get("date")
            cache_key = f"eosda_analytics_{field_id}_{view_id}_{date}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                results.append({
                    "view_id": view_id,
                    "date": date,
                    "data": cached_data,
                    "source": "cache"
                })
            else:
                cache_misses.append(scene)
        
        # Para las escenas que no están en cache, usar la API básica por ahora
        # En el futuro se puede implementar usando la Advanced Statistics API
        for scene in cache_misses:
            try:
                # Placeholder: por ahora devolver datos de ejemplo
                results.append({
                    "view_id": scene.get("view_id"),
                    "date": scene.get("date"),
                    "data": {
                        "analytics": {
                            "ndvi": {"mean": 0.65, "std": 0.15, "source": "bulk_placeholder"},
                            "ndmi": {"mean": 0.42, "std": 0.12, "source": "bulk_placeholder"},
                            "evi": {"mean": 0.38, "std": 0.11, "source": "bulk_placeholder"}
                        }
                    },
                    "source": "generated",
                    "note": "Datos de ejemplo - implementar con Advanced Statistics API"
                })
            except Exception as e:
                results.append({
                    "view_id": scene.get("view_id"),
                    "date": scene.get("date"),
                    "error": str(e),
                    "source": "error"
                })
        
        return Response({
            "field_id": field_id,
            "total_scenes": len(scenes),
            "cache_hits": len(scenes) - len(cache_misses),
            "cache_misses": len(cache_misses),
            "results": results,
            "note": "Implementación básica - mejorar con Advanced Statistics API para procesamiento en lote"
        }, status=200)

class ParcelHistoricalIndicesView(APIView):
    """
    Vista para obtener datos históricos de índices NDVI, NDMI y EVI 
    desde principio de año hasta la fecha actual para gráfico histórico
    """
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    @check_eosda_limit
    def get(self, request, parcel_id):
        """
        GET /api/parcels/parcel/<parcel_id>/historical-indices/
        Retorna datos históricos de NDVI, NDMI y EVI desde enero del año actual
        """
        logger.info(f"[HISTORICAL_INDICES] Iniciando consulta para parcela ID: {parcel_id}")
        
        try:
            # Obtener la parcela
            parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
            logger.info(f"[HISTORICAL_INDICES] Parcela encontrada: {parcel.name}")
            
            eosda_id = getattr(parcel, "eosda_id", None)
            logger.info(f"[HISTORICAL_INDICES] EOSDA ID: {eosda_id}")
            
            if not eosda_id:
                logger.error(f"[HISTORICAL_INDICES] Parcela {parcel_id} no tiene eosda_id")
                return Response({"error": "La parcela no tiene eosda_id configurado"}, status=400)
            
            # Configurar fechas: desde enero del año actual hasta hoy
            current_year = datetime.now().year
            start_date = f"{current_year}-01-01"
            end_date = datetime.now().strftime("%Y-%m-%d")
            
            # Cache key para datos históricos
            cache_key = f"historical_indices_{eosda_id}_{current_year}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.info(f"[HISTORICAL_INDICES] Cache hit: {cache_key}")
                return Response(cached_data)
            
            # Obtener geometría de la parcela
            if not parcel.geom:
                return Response({"error": "La parcela no tiene geometría definida"}, status=400)
            
            # Manejar geometría GeoJSON
            geom = parcel.geom
            logger.info(f"[HISTORICAL_INDICES] Tipo de geometría: {type(geom)}")
            
            if isinstance(geom, dict):
                # Ya es un diccionario GeoJSON
                polygon_geojson = geom
            elif isinstance(geom, str):
                # Es un string JSON, parsearlo
                polygon_geojson = json.loads(geom)
            else:
                # Podría ser un objeto GEOS, convertir
                polygon_geojson = json.loads(geom.geojson)
            
            logger.info(f"[HISTORICAL_INDICES] GeoJSON preparado: {polygon_geojson.get('type', 'unknown')}")
            
            logger.info(f"[HISTORICAL_INDICES] Obteniendo datos históricos para parcela {parcel_id}")
            logger.info(f"[HISTORICAL_INDICES] Período: {start_date} a {end_date}")
            
            # Índices a consultar
            indices = ["ndvi", "ndmi", "evi"]
            historical_data = {}
            unavailable_indices = []
            client = get_eosda_client()
            
            # Consultar cada índice a EOSDA usando Field Analytics API
            for index_name in indices:
                logger.info(f"[HISTORICAL_INDICES] Consultando {index_name}...")
                
                # Usar Field Analytics API para obtener trend histórico del índice
                eosda_url = f"https://api-connect.eos.com/field-analytics/trend/{eosda_id}"
                headers = {
                    "x-api-key": settings.EOSDA_API_KEY,
                    "Content-Type": "text/plain"
                }
                
                # Payload para obtener trend histórico de índice específico
                payload = {
                    "params": {
                        "date_start": start_date,
                        "date_end": end_date,
                        "index": index_name.upper(),  # NDVI, NDMI, EVI
                        "data_source": "S2"  # Sentinel-2
                    }
                }
                
                try:
                    # Paso 1: Crear tarea
                    response = client.post(eosda_url, payload, headers=headers, timeout=30)
                    
                    if response.status_code in [200, 202]:
                        task_data = response.json()
                        
                        if task_data.get("status") == "created":
                            request_id = task_data.get("request_id")
                            logger.info(f"[HISTORICAL_INDICES] Tarea creada para {index_name}: {request_id}")
                            
                            # Paso 2: Obtener resultado de la tarea
                            result_url = f"{eosda_url}/{request_id}"
                            
                            # Intentar obtener el resultado (puede requerir espera)
                            import time
                            max_attempts = 2  # reducido: cada intento es una request a EOSDA
                            wait_time = 5  # segundos
                            
                            for attempt in range(max_attempts):
                                try:
                                    result_response = client.get(result_url, headers=headers, timeout=30)
                                    
                                    if result_response.status_code == 200:
                                        result_data = result_response.json()
                                        
                                        if result_data.get("status") == "success":
                                            # Procesar datos reales de EOSDA
                                            raw_data = result_data.get("result", [])
                                            processed_data = []
                                            
                                            for point in raw_data:
                                                processed_data.append({
                                                    'date': point.get('date'),
                                                    'mean': round(point.get('average', 0), 3),
                                                    'median': round(point.get('median', 0), 3),
                                                    'std': round(point.get('std', 0), 3),
                                                    'min': round(point.get('min', 0), 3),
                                                    'max': round(point.get('max', 0), 3)
                                                })
                                            
                                            historical_data[index_name] = processed_data
                                            logger.info(f"[HISTORICAL_INDICES] Obtenidos {len(processed_data)} puntos reales para {index_name}")
                                            break
                                        elif result_data.get("status") == "processing":
                                            logger.info(f"[HISTORICAL_INDICES] Tarea {index_name} aún procesando, intento {attempt + 1}/{max_attempts}")
                                            time.sleep(wait_time)
                                            continue
                                        else:
                                            logger.error(f"[HISTORICAL_INDICES] Error en resultado {index_name}: {result_data}")
                                            break
                                    else:
                                        logger.error(f"[HISTORICAL_INDICES] Error obteniendo resultado {index_name}: {result_response.status_code}")
                                        break
                                        
                                except Exception as e:
                                    logger.error(f"[HISTORICAL_INDICES] Error en intento {attempt + 1} para {index_name}: {str(e)}")
                                    if attempt == max_attempts - 1:
                                        break
                                    time.sleep(wait_time)
                            
                            # No hay datos reales: NO inventar. Se marca como no disponible.
                            if index_name not in historical_data:
                                logger.warning(f"[HISTORICAL_INDICES] No hay datos reales para {index_name} (tarea pendiente/fallida)")
                                unavailable_indices.append(index_name)
                        else:
                            logger.error(f"[HISTORICAL_INDICES] Error creando tarea {index_name}: {task_data}")
                            unavailable_indices.append(index_name)
                            
                    else:
                        logger.error(f"[HISTORICAL_INDICES] Error {index_name}: {response.status_code} - {response.text}")
                        unavailable_indices.append(index_name)
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"[HISTORICAL_INDICES] Error de conexión {index_name}: {str(e)}")
                    unavailable_indices.append(index_name)
            
            # Estructurar respuesta
            response_data = {
                "parcel_info": {
                    "id": parcel_id,
                    "name": parcel.name,
                    "eosda_id": eosda_id
                },
                "period": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "historical_data": historical_data,
                "metadata": {
                    "total_points": sum(len(data) for data in historical_data.values()),
                    "indices_available": [idx for idx, data in historical_data.items() if len(data) > 0],
                    "indices_unavailable": unavailable_indices,
                    "data_source": "eosda",
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            # Guardar en cache por 6 horas
            cache.set(cache_key, response_data, 21600)
            logger.info(f"[HISTORICAL_INDICES] Datos guardados en cache: {cache_key}")

            # Actualizar estado de salud (Monitoreo Continuo Fase 2)
            try:
                health = CropHealthStatus.get_or_create_for_parcel(parcel)
                latest_ndvi = None
                latest_ndmi = None
                latest_evi = None
                if 'ndvi' in historical_data and historical_data['ndvi']:
                    latest_ndvi = historical_data['ndvi'][-1].get('mean')
                if 'ndmi' in historical_data and historical_data['ndmi']:
                    latest_ndmi = historical_data['ndmi'][-1].get('mean')
                if 'evi' in historical_data and historical_data['evi']:
                    latest_evi = historical_data['evi'][-1].get('mean')
                if latest_ndvi or latest_ndmi or latest_evi:
                    health.update_from_observation(
                        ndvi=latest_ndvi, ndmi=latest_ndmi, evi=latest_evi,
                        image_date=datetime.now().date()
                    )
                    logger.info(f"[HEALTH] Estado actualizado con indices historicos para {parcel.name}")
            except Exception as he:
                logger.warning(f"[HEALTH] Error: {he}")

            client.record(getattr(request, 'tenant', None), operation="historical_indices", parcel_id=parcel_id, user=getattr(request, 'user', None))
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"[HISTORICAL_INDICES] Error: {str(e)}")
            return Response({"error": f"Error obteniendo datos históricos: {str(e)}"}, status=500)

class ParcelNdviWeatherComparisonView(APIView):
    """
    Vista para obtener análisis comparativo entre índices NDVI históricos y datos meteorológicos.
    Combina datos de EOSDA (NDVI) con datos meteorológicos gratuitos de Open-Meteo.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    @check_eosda_limit
    def get(self, request, parcel_id):
        """
        GET /api/parcels/parcel/<parcel_id>/ndvi-weather-comparison/
        
        Retorna análisis comparativo NDVI vs datos meteorológicos para gráficos y correlaciones.
        """
        logger.info(f"[NDVI_WEATHER] Iniciando análisis comparativo para parcela {parcel_id}")
        
        try:
            # Obtener la parcela
            parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
            logger.info(f"[NDVI_WEATHER] Parcela encontrada: {parcel.name}")
            
            # Verificar cache de análisis comparativo
            current_year = datetime.now().year
            cache_key = f"ndvi_weather_comparison_{parcel_id}_{current_year}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.info(f"[NDVI_WEATHER] Cache hit: {cache_key}")
                return Response(cached_data)
            
            # Solo obtener datos meteorológicos (sin NDVI históricos para reducir requests)
            logger.info(f"[NDVI_WEATHER] Obteniendo solo datos meteorológicos...")
            
            # Obtener coordenadas de la parcela para consulta meteorológica
            if not parcel.geom:
                return Response({"error": "La parcela no tiene geometría definida"}, status=400)
                
            # Extraer centroide de la geometría para coordenadas meteorológicas
            geom = parcel.geom
            if isinstance(geom, dict):
                # Calcular centroide aproximado del polígono GeoJSON
                coordinates = geom.get('coordinates', [])
                if coordinates and len(coordinates) > 0:
                    # Para polígonos, tomar el primer anillo
                    coords = coordinates[0] if isinstance(coordinates[0], list) else coordinates
                    # Calcular centroide simple
                    avg_lng = sum(coord[0] for coord in coords) / len(coords)
                    avg_lat = sum(coord[1] for coord in coords) / len(coords)
                else:
                    return Response({"error": "Geometría inválida para obtener coordenadas"}, status=400)
            else:
                # Usar Django GIS para obtener centroide
                from django.contrib.gis.geos import GEOSGeometry
                if isinstance(geom, str):
                    geos_geom = GEOSGeometry(geom)
                else:
                    geos_geom = geom
                centroid = geos_geom.centroid
                avg_lng, avg_lat = centroid.coords
            
            logger.info(f"[NDVI_WEATHER] Coordenadas para meteorología: lat={avg_lat}, lng={avg_lng}")
            
            # Obtener datos meteorológicos de EOSDA Weather API
            logger.info(f"[NDVI_WEATHER] Consultando datos meteorológicos...")
            weather_data = self._get_weather_data(avg_lat, avg_lng)
            logger.info(f"[NDVI_WEATHER] Datos meteorológicos obtenidos: {len(weather_data)} días")

            # Sin datos reales NO inventar: devolver estado claro de "no disponible".
            if not weather_data:
                return Response({
                    "parcel_info": {"id": parcel_id, "name": parcel.name},
                    "synchronized_data": [],
                    "correlations": None,
                    "insights": None,
                    "metadata": {
                        "total_points": 0,
                        "weather_source": None,
                        "available": False,
                        "message": "Datos meteorológicos no disponibles en este momento.",
                        "generated_at": datetime.now().isoformat()
                    }
                }, status=200)
            
            # Para este endpoint solo retornamos datos meteorológicos puros (sin NDVI)
            logger.info(f"[NDVI_WEATHER] Procesando datos meteorológicos puros...")
            
            # Calcular métricas meteorológicas
            meteorological_metrics = self._calculate_meteorological_metrics(weather_data)
            logger.info(f"[NDVI_WEATHER] Métricas meteorológicas calculadas")
            
            # Generar insights meteorológicos
            insights = self._generate_meteorological_insights(weather_data, meteorological_metrics)
            
            # Estructurar respuesta solo con datos meteorológicos
            response_data = {
                "parcel_info": {
                    "id": parcel_id,
                    "name": parcel.name,
                    "coordinates": {
                        "latitude": avg_lat,
                        "longitude": avg_lng
                    }
                },
                "synchronized_data": weather_data,  # Solo datos meteorológicos
                "correlations": meteorological_metrics,
                "insights": insights,
                "metadata": {
                    "total_points": len(weather_data),
                    "weather_source": "open_meteo",
                    "available": True,
                    "generated_at": datetime.now().isoformat()
                }
            }
            
            # Guardar en cache por 4 horas
            cache.set(cache_key, response_data, 14400)
            logger.info(f"[NDVI_WEATHER] Análisis comparativo guardado en cache: {cache_key}")
            
            return Response(response_data)
            
        except Http404:
            raise
        except Exception as e:
            logger.error(f"[NDVI_WEATHER] Error: {str(e)}")
            return Response({"error": f"Error en análisis comparativo: {str(e)}"}, status=500)
    
    def _get_weather_data(self, latitude, longitude):
        """
        Obtiene datos meteorológicos históricos desde Open-Meteo Archive API.
        Gratuito, sin API key, desde inicio del año actual hasta hoy.
        """
        try:
            from datetime import datetime, timedelta
            end_date = datetime.now()
            current_year = end_date.year
            start_date = datetime(current_year, 1, 1)
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")

            meteo_url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,relative_humidity_2m_mean,pressure_msl_mean",
                "timezone": "America/Bogota",
            }

            logger.info(f"[WEATHER] Consultando Open-Meteo Archive: lat={latitude}, lng={longitude}")
            response = requests.get(meteo_url, params=params, timeout=30)
            logger.info(f"[WEATHER] Status: {response.status_code}")

            if response.status_code != 200 or not response.content:
                logger.warning(f"[WEATHER] Open-Meteo falló o respuesta vacía. Sin datos meteorológicos disponibles.")
                return []

            data = response.json()
            daily = data.get("daily", {})
            if not daily or "time" not in daily:
                logger.warning(f"[WEATHER] Respuesta sin datos daily. Sin datos meteorológicos disponibles.")
                return []

            weather_data = []
            days = daily["time"]
            for i, date_str in enumerate(days):
                t_max = daily.get("temperature_2m_max", [None])[i]
                t_min = daily.get("temperature_2m_min", [None])[i]
                if t_max is None or t_min is None:
                    continue
                weather_data.append({
                    "date": date_str,
                    "temperature": round((t_max + t_min) / 2, 1),
                    "temperature_max": round(t_max, 1),
                    "temperature_min": round(t_min, 1),
                    "precipitation": round(daily.get("precipitation_sum", [0])[i] or 0, 1),
                    "humidity": round(daily.get("relative_humidity_2m_mean", [0])[i] or 0, 1),
                    "wind_speed": round(daily.get("wind_speed_10m_max", [0])[i] or 0, 1),
                    "pressure": round(daily.get("pressure_msl_mean", [0])[i] or 0, 1),
                    "data_type": "open_meteo_archive",
                })

            logger.info(f"[WEATHER] Procesados {len(weather_data)} días históricos")
            return weather_data

        except Exception as e:
            logger.error(f"[WEATHER] Error: {str(e)}")
            return []

    def _synchronize_ndvi_weather_data(self, ndvi_data, weather_data):
        """
        Sincroniza datos NDVI (esporádicos) con datos meteorológicos (diarios)
        Implementa sincronización más precisa con interpolación
        """
        from datetime import datetime, timedelta
        
        synchronized = []
        
        # Crear diccionario de datos meteorológicos por fecha
        weather_dict = {item["date"]: item for item in weather_data}
        
        if not weather_dict:
            logger.warning(f"[SYNC] No hay datos meteorológicos disponibles")
            return []
        
        # Obtener rango de fechas meteorológicas para validación
        weather_dates = [datetime.strptime(date, "%Y-%m-%d") for date in weather_dict.keys()]
        min_weather_date = min(weather_dates)
        max_weather_date = max(weather_dates)
        
        logger.info(f"[SYNC] Rango meteorológico: {min_weather_date.strftime('%Y-%m-%d')} a {max_weather_date.strftime('%Y-%m-%d')}")
        logger.info(f"[SYNC] Datos NDVI disponibles: {len(ndvi_data)} puntos")
        
        for ndvi_point in ndvi_data:
            ndvi_date = ndvi_point["date"]
            ndvi_dt = datetime.strptime(ndvi_date, "%Y-%m-%d")
            
            # Verificar que la fecha NDVI esté en el rango meteorológico
            if ndvi_dt < min_weather_date or ndvi_dt > max_weather_date:
                logger.debug(f"[SYNC] Fecha NDVI {ndvi_date} fuera del rango meteorológico ({min_weather_date.strftime('%Y-%m-%d')} - {max_weather_date.strftime('%Y-%m-%d')})")
                continue
            
            # Buscar datos meteorológicos para la fecha exacta
            weather_point = weather_dict.get(ndvi_date)
            
            if not weather_point:
                # Interpolación lineal para fechas faltantes
                weather_point = self._interpolate_weather_data(ndvi_dt, weather_dict)
            
            if weather_point:
                # Calcular métricas agregadas de precipitación
                precip_7d = self._calculate_accumulated_precipitation(ndvi_date, weather_dict, days=7)
                precip_15d = self._calculate_accumulated_precipitation(ndvi_date, weather_dict, days=15)
                precip_30d = self._calculate_accumulated_precipitation(ndvi_date, weather_dict, days=30)
                
                # Calcular promedios de temperatura
                temp_avg_7d = self._calculate_average_temperature(ndvi_date, weather_dict, days=7)
                temp_avg_15d = self._calculate_average_temperature(ndvi_date, weather_dict, days=15)
                
                # Identificar si es dato histórico o pronóstico
                data_type = weather_point.get("data_type", "historical")
                
                synchronized.append({
                    "date": ndvi_date,
                    "ndvi": {
                        "mean": ndvi_point.get("mean", 0),
                        "std": ndvi_point.get("std", 0),
                        "min": ndvi_point.get("min", 0),
                        "max": ndvi_point.get("max", 0)
                    },
                    "weather": {
                        "temperature": weather_point.get("temperature", 0),
                        "temperature_max": weather_point.get("temperature_max", 0),
                        "temperature_min": weather_point.get("temperature_min", 0),
                        "precipitation_daily": weather_point.get("precipitation", 0),
                        "precipitation_accumulated_7d": precip_7d,
                        "precipitation_accumulated_15d": precip_15d,
                        "precipitation_accumulated_30d": precip_30d,
                        "humidity": weather_point.get("humidity", 0),
                        "wind_speed": weather_point.get("wind_speed", 0),
                        "solar_radiation": weather_point.get("solar_radiation", 0),
                        "temperature_avg_7d": temp_avg_7d,
                        "temperature_avg_15d": temp_avg_15d,
                        "data_type": data_type
                    }
                })
        
        # Ordenar por fecha
        synchronized.sort(key=lambda x: x["date"])
        
        logger.info(f"[SYNC] Sincronizados {len(synchronized)} puntos de {len(ndvi_data)} NDVI disponibles")
        return synchronized
    
    def _interpolate_weather_data(self, target_date, weather_dict):
        """
        Interpola datos meteorológicos para fechas faltantes
        """
        try:
            # Buscar fechas cercanas (±2 días)
            closest_dates = []
            for delta in range(1, 3):
                for direction in [-1, 1]:
                    check_date = (target_date + timedelta(days=delta * direction)).strftime("%Y-%m-%d")
                    if check_date in weather_dict:
                        closest_dates.append((delta, weather_dict[check_date]))
            
            if not closest_dates:
                return None
            
            # Usar la fecha más cercana (interpolación simple)
            closest_dates.sort(key=lambda x: x[0])
            return closest_dates[0][1]
            
        except Exception as e:
            logger.error(f"[INTERPOLATION] Error: {str(e)}")
            return None
    
    def _calculate_average_temperature(self, target_date, weather_dict, days=7):
        """
        Calcula temperatura promedio de los últimos N días
        """
        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            temperatures = []
            
            for i in range(days):
                check_date = (target_dt - timedelta(days=i)).strftime("%Y-%m-%d")
                weather_data = weather_dict.get(check_date)
                if weather_data and weather_data.get("temperature") is not None:
                    temperatures.append(weather_data["temperature"])
            
            return round(sum(temperatures) / len(temperatures), 1) if temperatures else 0
        except:
            return 0
    
    def _calculate_accumulated_precipitation(self, target_date, weather_dict, days=7):
        """
        Calcula precipitación acumulada de los últimos N días
        """
        from datetime import datetime, timedelta
        
        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            total_precip = 0
            
            for i in range(days):
                check_date = (target_dt - timedelta(days=i)).strftime("%Y-%m-%d")
                weather_data = weather_dict.get(check_date)
                if weather_data and weather_data.get("precipitation"):
                    total_precip += weather_data["precipitation"]
            
            return round(total_precip, 1)
        except:
            return 0
    
    def _calculate_correlations(self, synchronized_data):
        """
        Calcula correlaciones entre NDVI y todas las variables meteorológicas disponibles
        Incluye análisis de lag (retraso) para detectar correlaciones desfasadas
        """
        import numpy as np
        
        if len(synchronized_data) < 3:
            return {
                "ndvi_vs_precipitation_daily": 0,
                "ndvi_vs_precipitation_7d": 0,
                "ndvi_vs_precipitation_15d": 0,
                "ndvi_vs_precipitation_30d": 0,
                "ndvi_vs_temperature": 0,
                "ndvi_vs_temperature_max": 0,
                "ndvi_vs_temperature_min": 0,
                "ndvi_vs_humidity": 0,
                "ndvi_vs_wind_speed": 0,
                "ndvi_vs_solar_radiation": 0,
                "lag_analysis": {}
            }
        
        try:
            # Extraer arrays para correlación
            ndvi_values = [point["ndvi"]["mean"] for point in synchronized_data]
            precip_daily = [point["weather"]["precipitation_daily"] for point in synchronized_data]
            precip_7d = [point["weather"]["precipitation_accumulated_7d"] for point in synchronized_data]
            precip_15d = [point["weather"]["precipitation_accumulated_15d"] for point in synchronized_data]
            precip_30d = [point["weather"]["precipitation_accumulated_30d"] for point in synchronized_data]
            temperatures = [point["weather"]["temperature"] for point in synchronized_data]
            temp_max = [point["weather"]["temperature_max"] for point in synchronized_data]
            temp_min = [point["weather"]["temperature_min"] for point in synchronized_data]
            humidity_values = [point["weather"]["humidity"] for point in synchronized_data]
            wind_speed = [point["weather"]["wind_speed"] for point in synchronized_data]
            solar_radiation = [point["weather"]["solar_radiation"] for point in synchronized_data if point["weather"]["solar_radiation"] is not None]
            
            # Calcular correlaciones de Pearson
            correlations = {
                "ndvi_vs_precipitation_daily": self._safe_correlation(ndvi_values, precip_daily),
                "ndvi_vs_precipitation_7d": self._safe_correlation(ndvi_values, precip_7d),
                "ndvi_vs_precipitation_15d": self._safe_correlation(ndvi_values, precip_15d),
                "ndvi_vs_precipitation_30d": self._safe_correlation(ndvi_values, precip_30d),
                "ndvi_vs_temperature": self._safe_correlation(ndvi_values, temperatures),
                "ndvi_vs_temperature_max": self._safe_correlation(ndvi_values, temp_max),
                "ndvi_vs_temperature_min": self._safe_correlation(ndvi_values, temp_min),
                "ndvi_vs_humidity": self._safe_correlation(ndvi_values, humidity_values),
                "ndvi_vs_wind_speed": self._safe_correlation(ndvi_values, wind_speed),
                "ndvi_vs_solar_radiation": self._safe_correlation(ndvi_values[:len(solar_radiation)], solar_radiation) if len(solar_radiation) > 2 else 0
            }
            
            # Análisis de lag (correlaciones con retraso)
            lag_analysis = self._calculate_lag_correlations(ndvi_values, precip_7d, temperatures)
            correlations["lag_analysis"] = lag_analysis
            
            return correlations
            
        except Exception as e:
            logger.error(f"[CORRELATIONS] Error calculando correlaciones: {str(e)}")
            return {
                "ndvi_vs_precipitation_daily": 0,
                "ndvi_vs_precipitation_7d": 0,
                "ndvi_vs_precipitation_15d": 0,
                "ndvi_vs_precipitation_30d": 0,
                "ndvi_vs_temperature": 0,
                "ndvi_vs_temperature_max": 0,
                "ndvi_vs_temperature_min": 0,
                "ndvi_vs_humidity": 0,
                "ndvi_vs_wind_speed": 0,
                "ndvi_vs_solar_radiation": 0,
                "lag_analysis": {}
            }
    
    def _safe_correlation(self, x, y):
        """
        Calcula correlación de Pearson de forma segura manejando NaN y arrays de diferentes tamaños
        """
        import numpy as np
        
        try:
            # Asegurar que ambos arrays tengan el mismo tamaño
            min_len = min(len(x), len(y))
            x_trimmed = x[:min_len]
            y_trimmed = y[:min_len]
            
            # Filtrar valores None y NaN
            valid_pairs = [(xi, yi) for xi, yi in zip(x_trimmed, y_trimmed) if xi is not None and yi is not None and not np.isnan(xi) and not np.isnan(yi)]
            
            if len(valid_pairs) < 3:
                return 0
            
            x_clean, y_clean = zip(*valid_pairs)
            corr = np.corrcoef(x_clean, y_clean)[0, 1]
            
            return round(corr, 3) if not np.isnan(corr) else 0
        except:
            return 0
    
    def _calculate_lag_correlations(self, ndvi_values, precip_values, temp_values):
        """
        Calcula correlaciones con diferentes retrasos (lag) para detectar respuestas desfasadas
        """
        lag_results = {}
        
        try:
            # Probar lags de 1 a 3 períodos (considerando que los datos pueden ser semanales)
            for lag in range(1, 4):
                if len(ndvi_values) > lag + 2:
                    # NDVI vs precipitación con lag
                    ndvi_lagged = ndvi_values[lag:]
                    precip_lead = precip_values[:-lag]
                    precip_lag_corr = self._safe_correlation(ndvi_lagged, precip_lead)
                    
                    # NDVI vs temperatura con lag
                    temp_lead = temp_values[:-lag]
                    temp_lag_corr = self._safe_correlation(ndvi_lagged, temp_lead)
                    
                    lag_results[f"lag_{lag}"] = {
                        "precipitation": precip_lag_corr,
                        "temperature": temp_lag_corr
                    }
        except Exception as e:
            logger.error(f"[LAG_ANALYSIS] Error: {str(e)}")
        
        return lag_results
    
    def _generate_insights(self, synchronized_data, correlations):
        """
        Genera insights automáticos basados en correlaciones y patrones de todas las variables meteorológicas
        """
        insights = []
        
        # Análisis de correlación con precipitación acumulada (30 días es más indicativo)
        precip_30d_corr = correlations.get("ndvi_vs_precipitation_30d", 0)
        precip_7d_corr = correlations.get("ndvi_vs_precipitation_7d", 0)
        
        if precip_30d_corr > 0.6:
            insights.append(f"Correlación fuerte positiva entre NDVI y precipitación acumulada 30 días ({precip_30d_corr:.2f}). La vegetación responde eficientemente al agua disponible.")
        elif precip_30d_corr < -0.4:
            insights.append(f"Correlación negativa NDVI-precipitación 30d ({precip_30d_corr:.2f}). Posible saturación hídrica o problemas de drenaje afectando el cultivo.")
        elif abs(precip_7d_corr) > abs(precip_30d_corr) and abs(precip_7d_corr) > 0.4:
            insights.append(f"La vegetación responde más a precipitación reciente (7d: {precip_7d_corr:.2f}) que acumulada, indicando respuesta rápida al agua.")
        
        # Análisis de temperatura (máximas, mínimas y promedio)
        temp_corr = correlations.get("ndvi_vs_temperature", 0)
        temp_max_corr = correlations.get("ndvi_vs_temperature_max", 0)
        temp_min_corr = correlations.get("ndvi_vs_temperature_min", 0)
        
        if temp_max_corr < -0.5:
            insights.append(f"Las temperaturas máximas están limitando el crecimiento ({temp_max_corr:.2f}). Considerar sistemas de sombreo o riego de enfriamiento.")
        elif temp_min_corr > 0.4:
            insights.append(f"Las temperaturas mínimas favorecen el desarrollo vegetativo ({temp_min_corr:.2f}). Buen ambiente nocturno para el cultivo.")
        elif temp_corr > 0.4:
            insights.append(f"Condiciones térmicas favorables para el crecimiento ({temp_corr:.2f}). El rango de temperatura es óptimo.")
        elif temp_corr < -0.4:
            insights.append(f"Estrés térmico detectado ({temp_corr:.2f}). Evaluar estrategias de manejo de temperatura.")
        
        # Análisis de humedad relativa
        humidity_corr = correlations.get("ndvi_vs_humidity", 0)
        if humidity_corr > 0.5:
            insights.append(f"La humedad relativa favorece el desarrollo ({humidity_corr:.2f}). Ambiente húmedo óptimo para la fotosíntesis.")
        elif humidity_corr < -0.5:
            insights.append(f"La alta humedad puede estar afectando negativamente ({humidity_corr:.2f}). Posible riesgo de enfermedades fúngicas.")
        
        # Análisis de viento
        wind_corr = correlations.get("ndvi_vs_wind_speed", 0)
        if wind_corr < -0.4:
            insights.append(f"Vientos fuertes están afectando el cultivo ({wind_corr:.2f}). Considerar cortavientos o protecciones.")
        elif wind_corr > 0.3:
            insights.append(f"Ventilación moderada favorece el cultivo ({wind_corr:.2f}). Buena circulación de aire.")
        
        # Análisis de radiación solar
        solar_corr = correlations.get("ndvi_vs_solar_radiation", 0)
        if solar_corr > 0.4:
            insights.append(f"Radiación solar óptima para fotosíntesis ({solar_corr:.2f}). Excelente disponibilidad lumínica.")
        elif solar_corr < -0.3:
            insights.append(f"Exceso de radiación puede estar causando estrés ({solar_corr:.2f}). Evaluar necesidad de sombreo.")
        
        # Análisis de lag (respuestas desfasadas)
        lag_analysis = correlations.get("lag_analysis", {})
        best_lag = None
        best_lag_corr = 0
        
        for lag_period, lag_data in lag_analysis.items():
            precip_lag = lag_data.get("precipitation", 0)
            if abs(precip_lag) > abs(best_lag_corr):
                best_lag_corr = precip_lag
                best_lag = lag_period
        
        if best_lag and abs(best_lag_corr) > 0.4:
            lag_days = best_lag.replace("lag_", "")
            if best_lag_corr > 0:
                insights.append(f"La vegetación responde a precipitaciones con {lag_days} períodos de retraso ({best_lag_corr:.2f}). Respuesta típica de cultivos establecidos.")
            else:
                insights.append(f"Respuesta negativa desfasada a precipitación ({lag_days} períodos: {best_lag_corr:.2f}). Posible problema de drenaje o enfermedades.")
        
        # Análisis de tendencias estacionales y pronóstico
        if len(synchronized_data) > 10:
            recent_data = synchronized_data[-5:]
            historical_data = [point for point in synchronized_data if point["weather"]["data_type"] == "historical"]
            forecast_data = [point for point in synchronized_data if point["weather"]["data_type"] == "forecast"]
            
            if historical_data:
                recent_ndvi = [point["ndvi"]["mean"] for point in recent_data if point["weather"]["data_type"] == "historical"]
                early_ndvi = [point["ndvi"]["mean"] for point in historical_data[:5]]
                
                if recent_ndvi and early_ndvi:
                    recent_avg = sum(recent_ndvi) / len(recent_ndvi)
                    early_avg = sum(early_ndvi) / len(early_ndvi)
                    
                    if recent_avg > early_avg * 1.15:
                        insights.append("Tendencia muy positiva: El NDVI ha mejorado significativamente en mediciones recientes. Excelente evolución del cultivo.")
                    elif recent_avg > early_avg * 1.05:
                        insights.append("Tendencia positiva: Mejora gradual en el vigor vegetativo del cultivo.")
                    elif recent_avg < early_avg * 0.85:
                        insights.append("Tendencia decreciente preocupante: Disminución notable del NDVI. Se requiere evaluación urgente de condiciones de cultivo.")
                    elif recent_avg < early_avg * 0.95:
                        insights.append("Ligera tendencia decreciente: Monitorear evolución y condiciones de manejo.")
            
            # Análisis de datos de pronóstico si están disponibles
            if forecast_data:
                forecast_precip = sum(point["weather"]["precipitation_daily"] for point in forecast_data)
                forecast_temp_avg = sum(point["weather"]["temperature"] for point in forecast_data) / len(forecast_data)
                
                if forecast_precip > 50:
                    insights.append(f"Pronóstico: Se esperan {forecast_precip:.1f}mm de lluvia en próximos días. Condiciones favorables para crecimiento vegetativo.")
                elif forecast_precip < 5:
                    insights.append(f"Pronóstico: Período seco esperado ({forecast_precip:.1f}mm). Considerar riego suplementario.")
                
                if forecast_temp_avg > 30:
                    insights.append(f"Pronóstico: Temperaturas altas esperadas ({forecast_temp_avg:.1f}°C promedio). Monitorear estrés térmico.")
                elif forecast_temp_avg < 10:
                    insights.append(f"Pronóstico: Temperaturas bajas esperadas ({forecast_temp_avg:.1f}°C promedio). Evaluar protección contra frío.")
        
        # Recomendaciones basadas en NDVI promedio
        if synchronized_data:
            avg_ndvi = sum(point["ndvi"]["mean"] for point in synchronized_data) / len(synchronized_data)
            max_ndvi = max(point["ndvi"]["mean"] for point in synchronized_data)
            min_ndvi = min(point["ndvi"]["mean"] for point in synchronized_data)
            ndvi_variation = max_ndvi - min_ndvi
            
            if avg_ndvi < 0.3:
                insights.append(f"NDVI promedio muy bajo ({avg_ndvi:.2f}). Se requiere evaluación urgente de salud del cultivo, nutrición y manejo.")
            elif avg_ndvi < 0.5:
                insights.append(f"NDVI promedio bajo ({avg_ndvi:.2f}). Evaluar necesidades nutricionales y condiciones de crecimiento.")
            elif avg_ndvi > 0.8:
                insights.append(f"NDVI promedio excelente ({avg_ndvi:.2f}). Cultivo con vigor vegetativo óptimo.")
            elif avg_ndvi > 0.7:
                insights.append(f"NDVI promedio muy bueno ({avg_ndvi:.2f}). Cultivo saludable con buen desarrollo vegetativo.")
            
            if ndvi_variation > 0.4:
                insights.append(f"Alta variabilidad en NDVI ({ndvi_variation:.2f}). Evaluar uniformidad de manejo y condiciones del campo.")
        
        return insights[:8]  # Limitar a 8 insights más relevantes

    def _calculate_meteorological_metrics(self, weather_data):
        """
        Calcula métricas meteorológicas útiles para la agricultura
        """
        if not weather_data:
            return {}
        
        # Promedios del período
        temps = [d.get('temperature', 0) for d in weather_data if d.get('temperature')]
        temp_max = [d.get('temperature_max', 0) for d in weather_data if d.get('temperature_max')]
        precipitation = [d.get('precipitation', 0) for d in weather_data if d.get('precipitation')]
        humidity = [d.get('humidity', 0) for d in weather_data if d.get('humidity')]
        
        return {
            "avg_temperature": sum(temps) / len(temps) if temps else 0,
            "avg_temp_max": sum(temp_max) / len(temp_max) if temp_max else 0,
            "total_precipitation": sum(precipitation),
            "avg_humidity": sum(humidity) / len(humidity) if humidity else 0,
            "days_with_rain": len([p for p in precipitation if p > 0.1]),
            "heat_stress_days": len([t for t in temp_max if t > 35]),
        }

    def _generate_meteorological_insights(self, weather_data, metrics):
        """
        Genera insights basados en datos meteorológicos reales
        """
        insights = []
        
        if metrics.get('avg_temp_max', 0) > 35:
            insights.append('Temperaturas máximas altas detectadas. Considerar sistemas de sombra o riego de enfriamiento.')
        
        if metrics.get('total_precipitation', 0) < 100:
            insights.append('Precipitación total baja en el período. Evaluar necesidades de riego suplementario.')
        elif metrics.get('total_precipitation', 0) > 1000:
            insights.append('Precipitación abundante. Monitorear drenaje y posibles problemas de encharcamiento.')
        
        if metrics.get('days_with_rain', 0) < 10:
            insights.append('Pocos días con lluvia. Programar riego regular para mantener humedad del suelo.')
        
        if metrics.get('heat_stress_days', 0) > 5:
            insights.append(f'{metrics.get("heat_stress_days")} días con temperaturas extremas (>35°C). Implementar medidas de protección.')
        
        return insights


# --- CROP HEALTH STATUS (Monitoreo Continuo Fase 1) ---

class CropHealthAPIView(APIView):
    """
    Endpoint de salud del cultivo — Monitoreo Continuo Fase 1.
    GET /api/parcels/parcel/{id}/health/
    
    Retorna el ultimo estado conocido del cultivo con badge visual,
    incluso cuando no hay imagenes nuevas disponibles.
    
    Feature gated: 'continuous_monitoring' (planes Pro+).
    """
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    @require_feature('continuous_monitoring')
    def get(self, request, parcel_id):
        from django.utils import timezone as dj_timezone
        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)

        # Obtener estado de salud actual
        health = CropHealthStatus.get_or_create_for_parcel(parcel)

        # Actualizar dias sin observacion
        if health.last_observation_date:
            delta = dj_timezone.now() - health.last_observation_date
            health.days_without_observation = delta.days
            if health.days_without_observation > 0 and health.observation_quality == 'excellent':
                health.observation_quality = 'good'
                health.confidence_score = max(health.confidence_score - 10, 60)
            elif health.days_without_observation > 7 and health.observation_quality == 'good':
                health.observation_quality = 'limited'
                health.confidence_score = max(health.confidence_score - 20, 30)
            elif health.days_without_observation > 14:
                health.observation_quality = 'no_observation'
                health.confidence_score = max(health.confidence_score - 30, 10)
            health.save()

        # Buscar ultimas escenas cacheadas
        recent_scenes = ParcelSceneCache.objects.filter(
            parcel=parcel
        ).order_by('-date')[:5]

        scenes_data = []
        for sc in recent_scenes:
            scenes_data.append({
                'date': sc.date.isoformat(),
                'index_type': sc.index_type,
                'cloudCoverage': sc.metadata.get('cloudCoverage', 0) if sc.metadata else 0,
            })

        # Obtener actividad reciente del monitoreo
        recent_activity = MonitoringEvent.get_recent_activity_display(parcel, limit=5)

        # Construir respuesta
        badge = health.status_badge
        return Response({
            'parcel_id': parcel.id,
            'parcel_name': parcel.name,
            'status': {
                'badge': badge,
                'quality': health.observation_quality,
                'quality_label': health.get_quality_label(),
                'confidence_score': health.confidence_score,
                'days_without_observation': health.days_without_observation,
                'message': health.status_message,
            },
            'indices': {
                'ndvi': health.ndvi_last,
                'ndmi': health.ndmi_last,
                'evi': health.evi_last,
            },
            'last_observation': health.last_observation_date.isoformat() if health.last_observation_date else None,
            'last_image_date': health.last_image_date.isoformat() if health.last_image_date else None,
            'recent_scenes': scenes_data,
            'recent_activity': recent_activity,
            'alerts': health.active_alerts if health.active_alerts else [],
        }, status=200)


# ── SENTINEL-1 RADAR (Monitoreo Continuo Fase 4 - ahOra OPERATIVO) ──────

class RadarAssessmentView(APIView):
    """
    Monitoreo radar Sentinel-1 (vigilancia complementaria, no sustituye óptico).

    GET /api/parcels/parcel/{parcel_id}/radar/

    Feature gated: 'continuous_monitoring' (plan Pro+).

    Usa datos REALES de Sentinel-1 GRD (VV+VH). NUNCA genera backscatter simulado:
    si no hay datos reales, devuelve "Datos radar no disponibles para esta fecha".
    """
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    @require_feature('continuous_monitoring')
    def get(self, request, parcel_id):
        from .sentinel1 import get_radar_monitoring

        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
        if not parcel.geom:
            return Response({'error': 'Parcela sin geometria'}, status=400)

        result = get_radar_monitoring(parcel.geom, days_back=60)

        result['parcel_id'] = parcel.id
        result['parcel_name'] = parcel.name
        return Response(result)


class RadarLayersView(APIView):
    """
    Capas radar Sentinel-1 (mapa de colores) + cambio entre observaciones.

    GET /api/parcels/parcel/{parcel_id}/radar-layers/

    Devuelve heatmaps PNG (base64 + bounds) de sigma0 VV, VH y RVI, más el
    heatmap de cambio entre la última y la anterior observación (datos reales).
    """
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    @require_feature('continuous_monitoring')
    def get(self, request, parcel_id):
        from .sentinel1 import get_radar_layers
        from datetime import date, timedelta

        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
        if not parcel.geom:
            return Response({'error': 'Parcela sin geometría'}, status=400)

        days_back = getattr(settings, 'SENTINEL1_LOOKBACK_DAYS', 60)
        date_to = date.today().isoformat()
        date_from = (date.today() - timedelta(days=days_back)).isoformat()

        result = get_radar_layers(parcel.geom, date_from, date_to)
        result['parcel_id'] = parcel.id
        result['parcel_name'] = parcel.name
        return Response(result)


class FusionAssessmentView(APIView):
    """
    Evaluacion multi-fuente del cultivo (optico + radar + clima).
    GET /api/parcels/parcel/{parcel_id}/fusion-assessment/

    Feature gated: 'continuous_monitoring' (plan Pro+).
    """
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    @require_feature('continuous_monitoring')
    def get(self, request, parcel_id):
        from .fusion_engine import quick_assessment

        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
        assessment = quick_assessment(parcel)
        return Response(assessment)


# --- DASHBOARD HTML VIEW ---

def parcels_dashboard_view(request):
    """Renderiza el dashboard de parcelas con todos los modulos cargados."""
    return render(request, 'parcels/parcels-dashboard.html')


# --- GEOCODING PROXY ---

@api_view(['GET'])
def geocode_proxy(request):
    """
    Proxy para geocodificación usando Nominatim.
    """
    try:
        query = request.GET.get('q')
        if not query:
            return Response({"error": "Parámetro 'q' es requerido"}, status=400)

        headers = { 'User-Agent': 'AgroTechDigital/1.0 (internal-proxy)', 'Referer': 'https://agrotechcolombia.com' }
        url = "https://nominatim.openstreetmap.org/search"
        params = { 'q': query, 'format': 'json', 'limit': 5, 'addressdetails': 1, 'countrycodes': 'co', 'accept-language': 'es' }
        
        external_response = requests.get(url, params=params, headers=headers)
        if external_response.status_code != 200:
             logger.error(f"Error Nominatim: {external_response.status_code}")
             return Response({"error": "Error externo"}, status=502)
        
        return Response(external_response.json())
    except Exception as e:
        logger.error(f"Error geocode: {e}")
        return Response({"error": "Error interno"}, status=500)
