from django.contrib import admin
from .models import Parcel

class ParcelAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'manager', 'field_type', 'soil_type', 'topography', 'state', 'created_on', 'is_deleted', 'geom'
    )
    list_filter = ('state', 'is_deleted', 'manager', 'field_type', 'soil_type', 'topography')
    search_fields = ('name', 'description', 'manager__first_name', 'manager__last_name')
    readonly_fields = ('created_on', 'updated_on', 'deleted_at')
    date_hierarchy = 'created_on'
    ordering = ('-created_on',)

admin.site.register(Parcel, ParcelAdmin)

# Register your models here.

