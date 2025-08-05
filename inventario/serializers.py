from rest_framework import serializers
from .models import Supply, Warehouse, InventoryMovement, Machinery, Supplier, Company, Category, Subcategory, Person

class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = '__all__'

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = '__all__'

class SupplySerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    subcategory_name = serializers.SerializerMethodField()
    warehouse = WarehouseSerializer(read_only=True)
    warehouse_id = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all(), source='warehouse', write_only=True)
    suppliers = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all(), many=True, required=False)
    image = serializers.ImageField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    attachments = serializers.FileField(required=False, allow_null=True)
    class Meta:
        model = Supply
        fields = [
            'id', 'name', 'unit_value', 'quantity', 'unit', 'unit_amount', 'unit_custom',
            'warehouse', 'warehouse_id', 'description', 'category', 'subcategory',
            'category_name', 'subcategory_name',
            'suppliers', 'image', 'notes', 'attachments',
            'created', 'updated'
        ]

    def get_category_name(self, obj):
        # Retorna el nombre de la categoría o vacío
        if obj.category and hasattr(obj.category, 'name'):
            return obj.category.name
        return ''

    def get_subcategory_name(self, obj):
        # Retorna el nombre de la subcategoría o vacío
        if obj.subcategory and hasattr(obj.subcategory, 'name'):
            return obj.subcategory.name
        return ''

from django.contrib.contenttypes.models import ContentType

class InventoryMovementSerializer(serializers.ModelSerializer):
    content_type = serializers.PrimaryKeyRelatedField(queryset=ContentType.objects.all())
    asset_id = serializers.IntegerField(source='object_id')
    class Meta:
        model = InventoryMovement
        fields = [
            'id', 'content_type', 'asset_id', 'movement_type', 'quantity', 'unit_value',
            'origin_location', 'destination_location', 'date', 'notes', 'user', 'document', 'created', 'updated'
        ]

class MachinerySerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    subcategory_name = serializers.SerializerMethodField()
    warehouse = WarehouseSerializer(read_only=True)
    warehouse_id = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all(), source='warehouse', write_only=True)
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all(), allow_null=True, required=False)
    image_url = serializers.SerializerMethodField()
    class Meta:
        model = Machinery
        fields = [
            'id', 'name', 'brand', 'model', 'serial_number', 'year', 'description',
            'warehouse', 'warehouse_id', 'category', 'subcategory',
            'category_name', 'subcategory_name', 'image', 'image_url',
            'status', 'acquisition_date', 'purchase_value', 'current_value', 'supplier',
            'location', 'usage_hours', 'last_maintenance', 'next_maintenance', 'responsible', 'notes',
            'created', 'updated'
        ]

    def get_category_name(self, obj):
        if obj.category and hasattr(obj.category, 'name'):
            return obj.category.name
        return ''

    def get_subcategory_name(self, obj):
        if obj.subcategory and hasattr(obj.subcategory, 'name'):
            return obj.subcategory.name
        return ''

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return ''

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class SubcategorySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    # Asignar categoría por ID (solo escritura)
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category', write_only=True)
    class Meta:
        model = Subcategory
        fields = '__all__'
