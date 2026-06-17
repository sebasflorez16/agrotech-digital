"""
ViewSets para zonificación de manejo (precision farming).

Endpoints:
  GET    /api/parcel-zonifications/?parcel=<id>      → lista zonificaciones de una parcela
  POST   /api/parcel-zonifications/                  → crea una zonificación (manual o disparador)
  GET    /api/parcel-zonifications/<id>/             → detalle con zonas
  POST   /api/parcel-zonifications/<id>/generate/    → dispara clustering K-means (stub)
  GET    /api/parcel-zonifications/<id>/geojson/     → FeatureCollection listo para Leaflet
  GET    /api/parcel-zones/?zonification=<id>        → zonas planas
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ParcelZonification, ParcelZone
from .zone_serializers import ParcelZonificationSerializer, ParcelZoneSerializer
from .zonification_pipeline import run_zonification


class ParcelZonificationViewSet(viewsets.ModelViewSet):
    serializer_class = ParcelZonificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ParcelZonification.objects.select_related('parcel').prefetch_related('zones').all()
        parcel_id = self.request.query_params.get('parcel') or self.request.query_params.get('parcela')
        if parcel_id:
            qs = qs.filter(parcel_id=parcel_id)
        return qs

    @action(detail=True, methods=['get'])
    def geojson(self, request, pk=None):
        """Devuelve un FeatureCollection GeoJSON listo para renderizar en Leaflet."""
        zonification = self.get_object()
        features = []
        for zone in zonification.zones.all():
            if not zone.geometry_geojson:
                continue
            features.append({
                'type': 'Feature',
                'geometry': zone.geometry_geojson,
                'properties': {
                    'cluster_id': zone.cluster_id,
                    'label': zone.label,
                    'category': zone.category,
                    'pixel_count': zone.pixel_count,
                    'area_ha': zone.area_ha,
                    'ndvi_mean': zone.ndvi_mean,
                    'ndmi_mean': zone.ndmi_mean,
                    'savi_mean': zone.savi_mean,
                    'ndre_mean': zone.ndre_mean,
                    'recomendacion': zone.recomendacion,
                },
            })
        return Response({
            'type': 'FeatureCollection',
            'features': features,
            'metadata': {
                'parcel_id': zonification.parcel_id,
                'scene_date': zonification.scene_date,
                'method': zonification.method,
                'k_zones': zonification.k_zones,
                'index_base': zonification.index_base,
            },
        })

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """
        Ejecuta el pipeline de zonificación (síncrono).

        Body opcional:
          { "k_zones": 3..5, "index_base": "ndvi|ndmi|savi|ndre" }
        """
        zonification = self.get_object()
        k_zones = request.data.get('k_zones')
        index_base = request.data.get('index_base')
        update_fields = []
        if k_zones:
            try:
                zonification.k_zones = max(2, min(int(k_zones), 5))
                update_fields.append('k_zones')
            except (TypeError, ValueError):
                pass
        if index_base in ('ndvi', 'ndmi', 'savi', 'ndre'):
            zonification.index_base = index_base
            update_fields.append('index_base')
        if update_fields:
            zonification.save(update_fields=update_fields + ['updated_at'])

        result = run_zonification(zonification)
        zonification.refresh_from_db()

        if not result.get('ok'):
            return Response(
                {
                    'detail': result.get('reason', 'No se pudo generar la zonificación.'),
                    'zonification_id': zonification.id,
                    'status': zonification.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(zonification)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='generate-for-parcel')
    def generate_for_parcel(self, request):
        """Atajo: crea (o reutiliza pendiente) una zonificación y la ejecuta en un paso.

        Body: { "parcel": <id>, "k_zones": 3..5, "index_base": "ndvi", "scene_date": "YYYY-MM-DD" }
        """
        from datetime import date
        parcel_id = request.data.get('parcel')
        if not parcel_id:
            return Response({'detail': 'parcel es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            k_zones = max(2, min(int(request.data.get('k_zones', 5)), 5))
        except (TypeError, ValueError):
            k_zones = 5
        index_base = request.data.get('index_base') or 'ndvi'
        if index_base not in ('ndvi', 'ndmi', 'savi', 'ndre'):
            index_base = 'ndvi'
        scene_date = request.data.get('scene_date') or date.today().isoformat()

        zonification = ParcelZonification.objects.create(
            parcel_id=parcel_id,
            scene_date=scene_date,
            index_base=index_base,
            method='kmeans',
            k_zones=k_zones,
            status='pending',
        )
        result = run_zonification(zonification)
        zonification.refresh_from_db()
        if not result.get('ok'):
            return Response(
                {
                    'detail': result.get('reason', 'No se pudo generar la zonificación.'),
                    'zonification_id': zonification.id,
                    'status': zonification.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(zonification)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ParcelZoneViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ParcelZoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ParcelZone.objects.select_related('zonification').all()
        zonif_id = self.request.query_params.get('zonification')
        if zonif_id:
            qs = qs.filter(zonification_id=zonif_id)
        return qs
