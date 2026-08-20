from rest_framework import serializers
from .models import Labor, LaborPhoto, LaborPhase, LaborType, LaborInput
from parcels.models import Parcel
from RRHH.models import Employee
from inventario.models import Machinery


class LaborPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaborPhoto
        fields = '__all__'


class LaborPhaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaborPhase
        fields = '__all__'
        read_only_fields = ['creado_en']


class LaborInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaborInput
        fields = '__all__'


class LaborSerializer(serializers.ModelSerializer):
    """
    Serializador para la gestion de labores agricolas.
    Incluye relaciones con parcelas y responsables.
    Acepta tipo como string o ID de LaborType.
    """

    parcelas = serializers.PrimaryKeyRelatedField(many=True, queryset=Parcel.objects.all(), required=False, allow_empty=True)
    responsables = serializers.PrimaryKeyRelatedField(many=True, queryset=Employee.objects.all(), required=False, allow_empty=True)
    maquinaria = serializers.PrimaryKeyRelatedField(many=True, queryset=Machinery.objects.all(), required=False, allow_empty=True)
    tipo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    progreso = serializers.SerializerMethodField()
    fases = LaborPhaseSerializer(many=True, read_only=True)
    parcelas_nombres = serializers.SerializerMethodField()
    responsables_nombres = serializers.SerializerMethodField()
    tipo_nombre = serializers.SerializerMethodField()
    insumos = LaborInputSerializer(many=True, read_only=True)
    fotos = LaborPhotoSerializer(many=True, read_only=True)
    costo_insumos = serializers.SerializerMethodField()
    costo_total = serializers.SerializerMethodField()

    def get_parcelas_nombres(self, obj):
        return [p.name for p in obj.parcelas.all()]

    def get_responsables_nombres(self, obj):
        return [f"{e.first_name} {e.last_name}" for e in obj.responsables.all()]

    def get_tipo_nombre(self, obj):
        return obj.tipo.nombre if obj.tipo else None

    def get_progreso(self, obj):
        return obj.progreso

    def get_costo_insumos(self, obj):
        return obj.calcular_costo_insumos() if hasattr(obj, 'calcular_costo_insumos') else None

    def get_costo_total(self, obj):
        return obj.calcular_costo_total() if hasattr(obj, 'calcular_costo_total') else None

    def _resolve_tipo(self, value):
        if value is None or value == '':
            return None
        if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
            return LaborType.objects.get_or_create(nombre=value)[0]
        tipo, _ = LaborType.objects.get_or_create(nombre=value.strip())
        return tipo

    def create(self, validated_data):
        tipo_raw = self.initial_data.get('tipo')
        if tipo_raw:
            validated_data['tipo'] = self._resolve_tipo(tipo_raw)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        tipo_raw = self.initial_data.get('tipo')
        if tipo_raw is not None:
            validated_data['tipo'] = self._resolve_tipo(tipo_raw)
        return super().update(instance, validated_data)


    class Meta:
        model = Labor
        fields = '__all__'
        extra_fields = [
            'parcelas_nombres', 'responsables_nombres', 'tipo_nombre', 'progreso', 'fases',
            'insumos', 'fotos', 'costo_insumos', 'costo_total'
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['parcelas_nombres'] = self.get_parcelas_nombres(instance)
        rep['responsables_nombres'] = self.get_responsables_nombres(instance)
        rep['tipo_nombre'] = self.get_tipo_nombre(instance)
        rep['progreso'] = self.get_progreso(instance)
        rep['fases'] = LaborPhaseSerializer(instance.fases.all(), many=True).data
        rep['insumos'] = LaborInputSerializer(instance.insumos.all(), many=True).data
        rep['fotos'] = LaborPhotoSerializer(instance.fotos.all(), many=True).data
        rep['costo_insumos'] = self.get_costo_insumos(instance)
        rep['costo_total'] = self.get_costo_total(instance)
        return rep
