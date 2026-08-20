from django.contrib import admin
from .models import LaborType, Labor, LaborPhoto, LaborPhase, LaborInput


@admin.register(LaborType)
class LaborTypeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')


@admin.register(Labor)
class LaborAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'estado', 'fecha_programada', 'costo_total')
    list_filter = ('estado', 'tipo', 'fecha_programada')
    search_fields = ('nombre',)


@admin.register(LaborPhoto)
class LaborPhotoAdmin(admin.ModelAdmin):
    list_display = ('labor', 'date', 'description')


@admin.register(LaborPhase)
class LaborPhaseAdmin(admin.ModelAdmin):
    list_display = ('labor', 'nombre', 'orden', 'estado', 'fecha_inicio', 'fecha_fin')
    list_filter = ('estado',)


@admin.register(LaborInput)
class LaborInputAdmin(admin.ModelAdmin):
    list_display = ('labor', 'crop', 'supply', 'quantity', 'unit', 'application_date')
    list_filter = ('labor', 'crop', 'application_date')
    search_fields = ('labor__nombre', 'crop__name', 'supply__name')
