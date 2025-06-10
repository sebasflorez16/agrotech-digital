from rest_framework import viewsets
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from RRHH.models import Employee, TemporaryEmployee, ContractorEmployee, Department, Position
from RRHH.serializers import EmployeeSerializer, TemporaryEmployeeSerializer, ContractorEmployeeSerializer, PositionSerializer, DepartmentSerializer, PaymentMethodSerializer
from base_agrotech.models import PaymentMethod


class PaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'patch', 'put'] # El patch nos ayuda a modificar algunos campos y no todos, es mas flexible

class DepartamentoViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']

class PosicionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']


#Listar y Crear empleados
class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']


# CRUD para Empleados Temporales
class TemporaryViewSet(viewsets.ModelViewSet):
    queryset = TemporaryEmployee.objects.all()
    serializer_class = TemporaryEmployeeSerializer
    permission_classes = [IsAuthenticated]
    

# CRUD para Contratistas
class ContractorViewSet(viewsets.ModelViewSet):
    queryset = ContractorEmployee.objects.all()
    serializer_class = ContractorEmployeeSerializer
    permission_classes = [IsAuthenticated]


# CRUD para Empleados Contratistas
class ContractorEmployeeViewSet(viewsets.ModelViewSet):
    queryset = ContractorEmployee.objects.all()
    serializer_class = ContractorEmployeeSerializer
    permission_classes = [IsAuthenticated]



