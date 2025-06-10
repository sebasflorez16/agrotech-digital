from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from .models import Parcel


class ParcelSerializer(GeoFeatureModelSerializer):
    area_hectares = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Parcel
        geo_field = "geom" # Este campo se serializa como un objeto GeoJSON 
        fields = [
            "id",
            "name",
            "description",
            "field_type",
            "state",
            "geom",
            "created_on",
            "updated_on",
            "unique_id",
            "manager",
            "soil_type",
            "topography",
            "is_deleted",  # Saber si la parcela está eliminada (soft delete)
            "area_hectares",  # Área en hectáreas, solo lectura
        ]
        read_only_fields = ("is_deleted", "area_hectares")

    def get_area_hectares(self, obj):
        return obj.area_hectares()