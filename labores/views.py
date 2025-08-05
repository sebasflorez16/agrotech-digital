from rest_framework import viewsets, permissions
from .models import Labor, LaborPhoto
from .serializers import LaborSerializer, LaborPhotoSerializer
from crop.models import LaborInput
from crop.serializers import LaborInputSerializer
from parcels.models import Parcel
from RRHH.models import Employee

from rest_framework import filters

class LaborViewSet(viewsets.ModelViewSet):
    """
    ViewSet protegido para la gestión de labores agrícolas.
    Solo usuarios autenticados pueden acceder.
    """
    queryset = Labor.objects.all()
    serializer_class = LaborSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'descripcion', 'estado', 'tipo__nombre', 'responsables__first_name', 'responsables__last_name', 'cultivos__name']
    ordering_fields = ['fecha_programada', 'fecha_realizada', 'estado', 'costo_total']
    ordering = ['-fecha_programada']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtros profesionales por query params
        cultivo = self.request.query_params.get('cultivo')
        responsable = self.request.query_params.get('responsable')
        estado = self.request.query_params.get('estado')
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin = self.request.query_params.get('fecha_fin')
        if cultivo:
            queryset = queryset.filter(cultivos__id=cultivo)
        if responsable:
            queryset = queryset.filter(responsables__id=responsable)
        if estado:
            queryset = queryset.filter(estado=estado)
        if fecha_inicio:
            queryset = queryset.filter(fecha_programada__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_programada__lte=fecha_fin)
        return queryset.distinct()
# --- RUTA FIRME: ViewSet para fotos de labor (CRUD básico, no el foco principal) ---
from rest_framework import mixins

class LaborPhotoViewSet(mixins.CreateModelMixin,
                        mixins.DestroyModelMixin,
                        mixins.UpdateModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    queryset = LaborPhoto.objects.all()
    serializer_class = LaborPhotoSerializer
    permission_classes = [permissions.IsAuthenticated]

# --- RUTA FIRME: ViewSet para insumos de labor (CRUD profesional) ---
class LaborInputViewSet(viewsets.ModelViewSet):
    queryset = LaborInput.objects.all()
    serializer_class = LaborInputSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['supply__name', 'notes', 'unit']
    ordering_fields = ['application_date', 'quantity']
    ordering = ['-application_date']
    def get_queryset(self):
        queryset = super().get_queryset()
        labor = self.request.query_params.get('labor')
        if labor:
            queryset = queryset.filter(labor__id=labor)
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_serializer(self, *args, **kwargs):
        # Inyecta los querysets para relaciones ManyToMany
        kwargs['context'] = self.get_serializer_context()
        serializer_class = self.get_serializer_class()
        kwargs['context']['parcelas_queryset'] = Parcel.objects.all()
        kwargs['context']['responsables_queryset'] = Employee.objects.all()
        return serializer_class(*args, **kwargs)
