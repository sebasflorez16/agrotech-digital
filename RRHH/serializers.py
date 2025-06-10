from rest_framework import serializers
from .models import Employee, TemporaryEmployee, ContractorEmployee, Department, Position
from base_agrotech.models import PaymentMethod

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'

class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    position_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    class Meta:
        model = Employee
        fields = '__all__'

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    def get_position_name(self, obj):
        return obj.position.name if obj.position else None
    
    def get_department_name(self, obj):
        return obj.department.name if obj.department else None

# Todo esto se hace para que el serializer devuelva el nombre del departamento y el cargo por que como son modelos separados se vean en el frontentd    

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ['id', 'name']

class TemporaryEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemporaryEmployee
        fields = '__all__'

class ContractorEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractorEmployee
        fields = '__all__'
