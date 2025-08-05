from rest_framework import serializers
from .models import Labor, LaborPhoto
from crop.models import LaborInput
from crop.serializers import LaborInputSerializer
from parcels.models import Parcel
from RRHH.models import Employee

class LaborPhotoSerializer(serializers.ModelSerializer):
    """
    Serializador para fotos de labor (máx. 3 por labor).
    """
    class Meta:
        model = LaborPhoto
        fields = '__all__'


class LaborSerializer(serializers.ModelSerializer):
    """
    Serializador para la gestión de labores agrícolas.
    Incluye relaciones con parcelas y responsables.
    """

    parcelas = serializers.PrimaryKeyRelatedField(many=True, queryset=Parcel.objects.all(), required=False, allow_empty=True)
    responsables = serializers.PrimaryKeyRelatedField(many=True, queryset=Employee.objects.all(), required=False, allow_empty=True)
    parcelas_nombres = serializers.SerializerMethodField()
    responsables_nombres = serializers.SerializerMethodField()
    insumos = LaborInputSerializer(many=True, read_only=True, source='insumos')
    fotos = LaborPhotoSerializer(many=True, read_only=True, source='fotos')
    costo_insumos = serializers.SerializerMethodField()
    costo_total = serializers.SerializerMethodField()

    def get_parcelas_nombres(self, obj):
        return [p.name for p in obj.parcelas.all()]

    def get_responsables_nombres(self, obj):
        return [f"{e.first_name} {e.last_name}" for e in obj.responsables.all()]

    def get_costo_insumos(self, obj):
        return obj.calcular_costo_insumos() if hasattr(obj, 'calcular_costo_insumos') else None

    def get_costo_total(self, obj):
        return obj.calcular_costo_total() if hasattr(obj, 'calcular_costo_total') else None


    class Meta:
        model = Labor
        fields = '__all__'
        extra_fields = [
            'parcelas_nombres', 'responsables_nombres', 'insumos', 'fotos', 'costo_insumos', 'costo_total'
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['parcelas_nombres'] = self.get_parcelas_nombres(instance)
        rep['responsables_nombres'] = self.get_responsables_nombres(instance)
        rep['insumos'] = LaborInputSerializer(instance.insumos.all(), many=True).data
        rep['fotos'] = LaborPhotoSerializer(instance.fotos.all(), many=True).data
        rep['costo_insumos'] = self.get_costo_insumos(instance)
        rep['costo_total'] = self.get_costo_total(instance)
        return rep
