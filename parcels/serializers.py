from rest_framework import serializers
from .models import Parcel

# Serializador para Parcel con GeoJSON y área calculada (compatible EOSDA)
class ParcelSerializer(serializers.ModelSerializer):
    area_hectares = serializers.SerializerMethodField()

    class Meta:
        model = Parcel
        fields = [
            "id",
            "eosda_id",
            "name",
            "description",
            "field_type",
            "state",
            "geom",  # GeoJSON Polygon
            "created_on",
            "updated_on",
            "unique_id",
            "manager",
            "soil_type",
            "topography",
            "is_deleted",
            "sync_status",
            "sync_error",
            "area_hectares",  # Área en hectáreas, solo lectura
        ]
        read_only_fields = ("is_deleted", "area_hectares", "eosda_id", "sync_status", "sync_error")

    def get_area_hectares(self, obj):
        return obj.area_hectares()