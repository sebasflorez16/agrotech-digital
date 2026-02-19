from rest_framework import serializers
from .models import CropType, Crop, CropStage, CropProgressPhoto, CropInput, LaborInput, CropEvent, CropCatalog, PhenologicalStage, CropCycle

class CropTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropType
        fields = '__all__'

class CropSerializer(serializers.ModelSerializer):
    crop_type_name = serializers.SerializerMethodField()
    variety_name = serializers.SerializerMethodField()
    parcel_name = serializers.SerializerMethodField()
    manager_name = serializers.SerializerMethodField()
    seed_supplier_name = serializers.SerializerMethodField()

    class Meta:
        model = Crop
        fields = '__all__'
        extra_fields = [
            'crop_type_name', 'variety_name', 'parcel_name', 'manager_name', 'seed_supplier_name'
        ]

    def get_crop_type_name(self, obj):
        return obj.crop_type.name if obj.crop_type else None

    def get_variety_name(self, obj):
        return obj.variety.name if obj.variety else None

    def get_parcel_name(self, obj):
        return obj.parcel.name if obj.parcel else None

    def get_manager_name(self, obj):
        if obj.manager:
            return f"{obj.manager.first_name} {obj.manager.last_name}" if hasattr(obj.manager, 'first_name') else str(obj.manager)
        return None

    def get_seed_supplier_name(self, obj):
        return obj.seed_supplier.name if obj.seed_supplier else None

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['crop_type_name'] = self.get_crop_type_name(instance)
        rep['variety_name'] = self.get_variety_name(instance)
        rep['parcel_name'] = self.get_parcel_name(instance)
        rep['manager_name'] = self.get_manager_name(instance)
        rep['seed_supplier_name'] = self.get_seed_supplier_name(instance)
        return rep

class CropStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropStage
        fields = '__all__'

class CropProgressPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropProgressPhoto
        fields = '__all__'

class CropInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropInput
        fields = '__all__'

class LaborInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaborInput
        fields = '__all__'

class CropEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropEvent
        fields = '__all__'


# =============================================================================
# SERIALIZERS PARA CATALOGO DE CULTIVOS Y CICLOS
# =============================================================================

class PhenologicalStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhenologicalStage
        fields = '__all__'


class CropCatalogSerializer(serializers.ModelSerializer):
    stages = PhenologicalStageSerializer(many=True, read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = CropCatalog
        fields = '__all__'


class CropCatalogListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados (sin etapas)."""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    stages_count = serializers.IntegerField(source='stages.count', read_only=True)

    class Meta:
        model = CropCatalog
        fields = [
            'id', 'name', 'scientific_name', 'family', 'category',
            'category_display', 'cycle_days_min', 'cycle_days_max',
            'temp_min', 'temp_max', 'is_active', 'stages_count',
        ]


class CropCycleSerializer(serializers.ModelSerializer):
    crop_catalog_name = serializers.CharField(source='crop_catalog.name', read_only=True)
    crop_catalog_category = serializers.CharField(source='crop_catalog.category', read_only=True)
    parcel_name = serializers.CharField(source='parcel.name', read_only=True)
    days_since_planting = serializers.IntegerField(read_only=True)
    current_stage = serializers.SerializerMethodField()
    progress_percent = serializers.FloatField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = CropCycle
        fields = '__all__'

    def get_current_stage(self, obj):
        stage = obj.current_stage
        if stage:
            return PhenologicalStageSerializer(stage).data
        return None


class IndexInterpretationSerializer(serializers.Serializer):
    """Serializer para validar la peticion de interpretacion de indices."""
    index_type = serializers.ChoiceField(choices=['ndvi', 'ndmi', 'savi'])
    value = serializers.FloatField(min_value=-1.0, max_value=1.0)
