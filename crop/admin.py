from django.contrib import admin
from .models import CropType, Crop, CropStage, CropProgressPhoto, CropInput, LaborInput, CropEvent, CropCatalog, PhenologicalStage, CropCycle

@admin.register(CropType)
class CropTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)

@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ("name", "crop_type", "variety", "parcel", "area", "sowing_date", "harvest_date", "manager")
    list_filter = ("crop_type", "parcel", "sowing_date", "harvest_date")
    search_fields = ("name", "variety__name", "parcel__name")

@admin.register(CropStage)
class CropStageAdmin(admin.ModelAdmin):
    list_display = ("name", "crop", "start_date", "end_date")
    list_filter = ("crop", "start_date", "end_date")
    search_fields = ("name", "crop__name")

@admin.register(CropProgressPhoto)
class CropProgressPhotoAdmin(admin.ModelAdmin):
    list_display = ("crop", "stage", "date", "user")
    list_filter = ("crop", "stage", "date")
    search_fields = ("crop__name", "stage__name")

@admin.register(CropInput)
class CropInputAdmin(admin.ModelAdmin):
    list_display = ("crop", "supply", "input_type", "quantity", "unit", "application_date")
    list_filter = ("crop", "input_type", "application_date")
    search_fields = ("crop__name", "supply__name")

@admin.register(LaborInput)
class LaborInputAdmin(admin.ModelAdmin):
    list_display = ("labor", "crop", "supply", "quantity", "unit", "application_date")
    list_filter = ("labor", "crop", "application_date")
    search_fields = ("labor__nombre", "crop__name", "supply__name")

@admin.register(CropEvent)
class CropEventAdmin(admin.ModelAdmin):
    list_display = ("crop", "event_type", "event_date", "user")
    list_filter = ("crop", "event_type", "event_date")
    search_fields = ("crop__name", "event_type")


# =============================================================================
# ADMIN PARA CATALOGO DE CULTIVOS Y CICLOS
# =============================================================================

class PhenologicalStageInline(admin.TabularInline):
    """Inline para gestionar etapas fenológicas desde el catálogo."""
    model = PhenologicalStage
    extra = 0
    ordering = ['order']
    fields = (
        'name', 'order', 'day_start', 'day_end',
        'ndvi_min', 'ndvi_max', 'ndvi_optimal',
        'ndmi_min', 'ndmi_max', 'ndmi_optimal',
        'savi_min', 'savi_max', 'savi_optimal',
        'water_need', 'is_critical',
    )


@admin.register(CropCatalog)
class CropCatalogAdmin(admin.ModelAdmin):
    list_display = ('name', 'scientific_name', 'category', 'family', 'cycle_days_min', 'cycle_days_max', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'scientific_name', 'family')
    list_editable = ('is_active',)
    inlines = [PhenologicalStageInline]


@admin.register(PhenologicalStage)
class PhenologicalStageAdmin(admin.ModelAdmin):
    list_display = ('crop_catalog', 'name', 'order', 'day_start', 'day_end', 'ndvi_optimal', 'ndmi_optimal', 'is_critical')
    list_filter = ('crop_catalog', 'is_critical')
    search_fields = ('name', 'crop_catalog__name')
    ordering = ['crop_catalog', 'order']


@admin.register(CropCycle)
class CropCycleAdmin(admin.ModelAdmin):
    list_display = ('crop_catalog', 'parcel', 'variety', 'planting_date', 'status', 'estimated_harvest_date', 'progress_percent')
    list_filter = ('status', 'crop_catalog', 'planting_date')
    search_fields = ('crop_catalog__name', 'parcel__name', 'variety')
    list_editable = ('status',)
    readonly_fields = ('days_since_planting', 'current_stage', 'progress_percent', 'created_at', 'updated_at')
    date_hierarchy = 'planting_date'

    def current_stage(self, obj):
        stage = obj.current_stage
        return stage.name if stage else 'Sin etapa'
    current_stage.short_description = 'Etapa actual'
