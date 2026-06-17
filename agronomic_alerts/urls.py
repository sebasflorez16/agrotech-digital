"""Rutas API de la app `agronomic_alerts`."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"alertas", views.AlertaOperativaViewSet, basename="alerta")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "parcelas/<int:parcel_pk>/estado-hoy/",
        views.parcela_estado_hoy,
        name="parcela-estado-hoy",
    ),
]
