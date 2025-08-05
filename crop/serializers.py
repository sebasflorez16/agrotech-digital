from rest_framework import serializers
from .models import CropType, Crop, CropStage, CropProgressPhoto, CropInput, LaborInput, CropEvent

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
