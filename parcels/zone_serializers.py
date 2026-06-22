"""Serializers para zonificación de manejo (precision farming)."""
from rest_framework import serializers
from .models import ParcelZonification, ParcelZone


class ParcelZoneSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = ParcelZone
        fields = [
            'id', 'cluster_id', 'label', 'category', 'category_display',
            'pixel_count', 'area_ha',
            'ndvi_mean', 'ndvi_std', 'ndvi_min', 'ndvi_max',
            'ndmi_mean', 'ndmi_std',
            'savi_mean', 'savi_std',
            'ndre_mean', 'ndre_std',
            'geometry_geojson', 'recomendacion',
        ]


class ParcelZonificationSerializer(serializers.ModelSerializer):
    zones = ParcelZoneSerializer(many=True, read_only=True)
    parcel_name = serializers.SerializerMethodField()
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ParcelZonification
        fields = [
            'id', 'parcel_id', 'parcel_name', 'scene_date',
            'index_base', 'method', 'method_display',
            'k_zones', 'status', 'status_display',
            'total_pixels', 'pixel_resolution_m',
            'notes', 'created_at', 'updated_at',
            'zones',
        ]
        read_only_fields = ['created_at', 'updated_at', 'status', 'total_pixels']

    def get_parcel_name(self, obj):
        try:
            from .models import Parcel
            return Parcel.objects.filter(id=obj.parcel_id).values_list('name', flat=True).first() or ''
        except Exception:
            return ''
