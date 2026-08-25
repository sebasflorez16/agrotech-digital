from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action

from core.permissions import IsAdminOrReadOnly
from .models import (
    Supply, Warehouse, InventoryMovement, Machinery, Supplier, Company,
    Category, Subcategory, Person,
)
from .serializers import (
    SupplySerializer, WarehouseSerializer, InventoryMovementSerializer,
    MachinerySerializer, SupplierSerializer, CompanySerializer,
    CategorySerializer, SubcategorySerializer, PersonSerializer,
)


class InventoryMovementViewSet(viewsets.ModelViewSet):
    queryset = InventoryMovement.objects.all().order_by('-date')
    serializer_class = InventoryMovementSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Importar el servicio aquí para evitar problemas de importación circular
        from .services import InventoryService
        result = InventoryService.process_movement(data)
        if result.get('error'):
            return Response({'detail': result['error']}, status=result.get('status', status.HTTP_400_BAD_REQUEST))

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class PersonViewSet(viewsets.ModelViewSet):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    # Endpoint DRF para reporte de inventario visual
    @action(detail=True, methods=['get'], url_path='reporte')
    def reporte(self, request, pk=None):
        from django.utils import timezone
        from .models import Supply
        warehouse = self.get_object()
        supplies = Supply.objects.filter(warehouse=warehouse).select_related('category', 'subcategory')
        supplies_list = []
        for s in supplies:
            supplies_list.append({
                'name': s.name,
                'category': s.category.name if s.category else '',
                'subcategory': s.subcategory.name if s.subcategory else '',
                'quantity': s.quantity,
                'unit_display': s.get_unit_display() if hasattr(s, 'get_unit_display') else s.unit,
                'unit_value': s.unit_value,
                'total_value': (s.quantity or 0) * (s.unit_value or 0),
                'description': s.description or ''
            })
        # Renderiza el mismo template pero desde DRF
        from django.shortcuts import render
        return render(request, 'inventario/warehouse_report.html', {
            'warehouse': warehouse,
            'supplies': supplies_list,
            'fecha': timezone.now(),
        })


class SupplyViewSet(viewsets.ModelViewSet):
    queryset = Supply.objects.all()
    serializer_class = SupplySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    # Permite crear uno o varios insumos (semillas) en una sola petición POST
    # Si el body es una lista, usa many=True en el serializer
    def create(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)


class MachineryViewSet(viewsets.ModelViewSet):
    queryset = Machinery.objects.all()
    serializer_class = MachinerySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]


class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.all()
    serializer_class = SubcategorySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
