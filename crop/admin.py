from django.contrib import admin
from .models import CropType, Crop, CropStage, CropProgressPhoto, CropInput, LaborInput, CropEvent

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
