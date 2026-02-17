from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from .models import CropType, Crop, CropStage, CropProgressPhoto, CropInput, LaborInput, CropEvent, CropCatalog, PhenologicalStage, CropCycle
from .serializers import (
    CropTypeSerializer, CropSerializer, CropStageSerializer,
    CropProgressPhotoSerializer, CropInputSerializer, LaborInputSerializer, CropEventSerializer,
    CropCatalogSerializer, CropCatalogListSerializer, PhenologicalStageSerializer,
    CropCycleSerializer, IndexInterpretationSerializer
)

# Create your views here.

class CropTypeViewSet(viewsets.ModelViewSet):
    queryset = CropType.objects.all()
    serializer_class = CropTypeSerializer
    permission_classes = [IsAuthenticated]

    # Permite crear uno o varios tipos de cultivo en una sola petición POST
    # Si el body es una lista, usa many=True en el serializer
    def create(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)

class CropViewSet(viewsets.ModelViewSet):
    queryset = Crop.objects.all()
    serializer_class = CropSerializer
    permission_classes = [IsAuthenticated]

class CropStageViewSet(viewsets.ModelViewSet):
    queryset = CropStage.objects.all()
    serializer_class = CropStageSerializer
    permission_classes = [IsAuthenticated]

class CropProgressPhotoViewSet(viewsets.ModelViewSet):
    queryset = CropProgressPhoto.objects.all()
    serializer_class = CropProgressPhotoSerializer
    permission_classes = [IsAuthenticated]

class CropInputViewSet(viewsets.ModelViewSet):
    queryset = CropInput.objects.all()
    serializer_class = CropInputSerializer
    permission_classes = [IsAuthenticated]

class LaborInputViewSet(viewsets.ModelViewSet):
    queryset = LaborInput.objects.all()
    serializer_class = LaborInputSerializer
    permission_classes = [IsAuthenticated]

class CropEventViewSet(viewsets.ModelViewSet):
    queryset = CropEvent.objects.all()
    serializer_class = CropEventSerializer
    permission_classes = [IsAuthenticated]


# =============================================================================
# VIEWSETS PARA CATALOGO DE CULTIVOS Y CICLOS DE CULTIVO
# =============================================================================

class CropCatalogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para el catálogo de cultivos.
    El catálogo es gestionado por admin/management commands, no por usuarios.
    
    GET /api/crop/catalog/        -> Lista de cultivos (ligero)
    GET /api/crop/catalog/<id>/   -> Detalle con etapas fenológicas
    GET /api/crop/catalog/<id>/stages/ -> Solo etapas del cultivo
    """
    queryset = CropCatalog.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return CropCatalogListSerializer
        return CropCatalogSerializer

    @action(detail=True, methods=['get'])
    def stages(self, request, pk=None):
        """Retorna las etapas fenológicas de un cultivo del catálogo."""
        catalog = self.get_object()
        stages = catalog.stages.all().order_by('order')
        serializer = PhenologicalStageSerializer(stages, many=True)
        return Response(serializer.data)


class CropCycleViewSet(viewsets.ModelViewSet):
    """
    CRUD completo para ciclos de cultivo por parcela.
    Aislado por tenant automáticamente (django-tenants).
    
    GET    /api/crop/cycles/                    -> Lista ciclos
    POST   /api/crop/cycles/                    -> Crear ciclo
    GET    /api/crop/cycles/<id>/               -> Detalle ciclo
    PUT    /api/crop/cycles/<id>/               -> Actualizar ciclo
    DELETE /api/crop/cycles/<id>/               -> Eliminar ciclo
    GET    /api/crop/cycles/by-parcel/?parcel_id=<id> -> Ciclos de una parcela
    POST   /api/crop/cycles/<id>/interpret/     -> Interpretar índice satelital
    """
    serializer_class = CropCycleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CropCycle.objects.select_related(
            'parcel', 'crop_catalog'
        ).all()
        
        # Filtrar por parcela si se pasa como query param
        parcel_id = self.request.query_params.get('parcel_id')
        if parcel_id:
            queryset = queryset.filter(parcel_id=parcel_id)
        
        # Filtrar por estado
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset

    @action(detail=False, methods=['get'], url_path='by-parcel')
    def by_parcel(self, request):
        """
        Retorna ciclos de cultivo de una parcela específica.
        Query param: parcel_id (requerido)
        """
        parcel_id = request.query_params.get('parcel_id')
        if not parcel_id:
            return Response(
                {'error': 'Se requiere el parámetro parcel_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cycles = self.get_queryset().filter(parcel_id=parcel_id)
        serializer = self.get_serializer(cycles, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='active')
    def active_cycles(self, request):
        """
        Retorna solo los ciclos activos. Opcionalmente filtra por parcel_id.
        """
        cycles = self.get_queryset().filter(status='active')
        parcel_id = request.query_params.get('parcel_id')
        if parcel_id:
            cycles = cycles.filter(parcel_id=parcel_id)
        serializer = self.get_serializer(cycles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def interpret(self, request, pk=None):
        """
        Interpreta un valor de índice satelital según la etapa fenológica actual.
        
        POST body: { "index_type": "ndvi"|"ndmi"|"savi", "value": 0.65 }
        """
        cycle = self.get_object()
        
        input_serializer = IndexInterpretationSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        
        index_type = input_serializer.validated_data['index_type']
        value = input_serializer.validated_data['value']
        
        interpretation = cycle.get_index_interpretation(index_type, value)
        return Response(interpretation)
