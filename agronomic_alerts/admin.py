from django.contrib import admin

from .models import AlertaOperativa, AlertNotification


@admin.register(AlertaOperativa)
class AlertaOperativaAdmin(admin.ModelAdmin):
    list_display = (
        "titulo", "parcel", "tipo", "severidad",
        "indice_afectado", "estado", "fecha_escena_origen", "fecha_deteccion",
    )
    list_filter = ("severidad", "estado", "tipo", "indice_afectado")
    search_fields = ("titulo", "causa_probable", "recomendacion", "parcel__name")
    readonly_fields = ("uuid", "fingerprint", "fecha_deteccion", "contexto")
    date_hierarchy = "fecha_deteccion"


@admin.register(AlertNotification)
class AlertNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "alerta", "canal", "destinatario", "estado",
        "intentos", "enviado_en", "creado_en",
    )
    list_filter = ("canal", "estado")
    search_fields = ("destinatario", "alerta__titulo")
    readonly_fields = ("creado_en", "actualizado_en", "enviado_en")
