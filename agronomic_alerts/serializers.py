"""Serializers DRF de alertas agronómicas."""

from rest_framework import serializers

from .models import (
    AlertaOperativa,
    AlertFeedback,
    AlertSeverity,
    AlertStatus,
    AlertType,
)


class AlertaOperativaSerializer(serializers.ModelSerializer):
    severidad_label = serializers.CharField(source="get_severidad_display", read_only=True)
    tipo_label = serializers.CharField(source="get_tipo_display", read_only=True)
    estado_label = serializers.CharField(source="get_estado_display", read_only=True)
    indice_label = serializers.CharField(source="get_indice_afectado_display", read_only=True)
    parcel_name = serializers.CharField(source="parcel.name", read_only=True)
    cultivo = serializers.SerializerMethodField()

    class Meta:
        model = AlertaOperativa
        fields = (
            "id", "uuid",
            "parcel", "parcel_name",
            "tipo", "tipo_label",
            "severidad", "severidad_label",
            "indice_afectado", "indice_label",
            "titulo", "zona",
            "causa_probable", "recomendacion",
            "ventana_dias",
            "valor_observado", "valor_umbral_min", "valor_umbral_max",
            "desviacion_pct",
            "fecha_escena_origen", "fecha_deteccion",
            "estado", "estado_label",
            "feedback", "feedback_comentario", "fecha_feedback",
            "cultivo", "contexto",
        )
        read_only_fields = fields  # Las mutaciones van por las @actions específicas.

    def get_cultivo(self, obj):
        ctx = obj.contexto or {}
        return ctx.get("cultivo") or (obj.crop_cycle.crop_catalog.name if obj.crop_cycle else None)


class AlertaOperativaListSerializer(serializers.ModelSerializer):
    """Versión liviana para listados."""

    severidad_label = serializers.CharField(source="get_severidad_display", read_only=True)
    tipo_label = serializers.CharField(source="get_tipo_display", read_only=True)
    parcel_name = serializers.CharField(source="parcel.name", read_only=True)

    class Meta:
        model = AlertaOperativa
        fields = (
            "id", "uuid",
            "parcel", "parcel_name",
            "tipo", "tipo_label",
            "severidad", "severidad_label",
            "indice_afectado",
            "titulo", "zona",
            "ventana_dias",
            "fecha_escena_origen", "fecha_deteccion",
            "estado",
        )


class AtenderAlertaSerializer(serializers.Serializer):
    feedback = serializers.ChoiceField(
        choices=AlertFeedback.choices, required=False, allow_blank=True,
    )
    comentario = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class PosponerAlertaSerializer(serializers.Serializer):
    dias = serializers.IntegerField(min_value=1, max_value=60, default=7)


class DescartarAlertaSerializer(serializers.Serializer):
    comentario = serializers.CharField(required=False, allow_blank=True, max_length=2000)
