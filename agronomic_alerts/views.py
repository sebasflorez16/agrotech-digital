"""
Views REST de Alertas Agronómicas.

Endpoints principales:
- `GET    /api/agronomic-alerts/alertas/`                 → listado filtrable
- `GET    /api/agronomic-alerts/alertas/<id>/`            → detalle
- `POST   /api/agronomic-alerts/alertas/<id>/atender/`    → marcar atendida + feedback
- `POST   /api/agronomic-alerts/alertas/<id>/posponer/`   → posponer ventana
- `POST   /api/agronomic-alerts/alertas/<id>/descartar/`  → descartar (falso positivo)
- `GET    /api/agronomic-alerts/parcelas/<pk>/estado-hoy/`→ resumen para dashboard
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from parcels.models import Parcel

from .indices import (
    INDEX_EXPLAINER,
    explain_index,
    preferred_indices_for_crop,
)
from .models import AlertaOperativa, AlertSeverity, AlertStatus
from .serializers import (
    AlertaOperativaListSerializer,
    AlertaOperativaSerializer,
    AtenderAlertaSerializer,
    DescartarAlertaSerializer,
    PosponerAlertaSerializer,
)


SEVERIDAD_RANK = {
    AlertSeverity.INFO: 0,
    AlertSeverity.WARNING: 1,
    AlertSeverity.CRITICAL: 2,
}


class AlertaOperativaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet de alertas con acciones de feedback como POST.

    Filtros (query params):
    - `parcel`        : ID de parcela
    - `severidad`     : info|warning|critical
    - `estado`        : activa|atendida|posponer|descartada (default: activa)
    - `tipo`          : humedad|vigor|cobertura|anomalia
    - `desde`         : ISO date — fecha_escena_origen >=
    - `hasta`         : ISO date — fecha_escena_origen <=
    """

    permission_classes = [IsAuthenticated]
    queryset = AlertaOperativa.objects.select_related("parcel", "crop_cycle").all()

    def get_serializer_class(self):
        if self.action == "list":
            return AlertaOperativaListSerializer
        return AlertaOperativaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        parcel = params.get("parcel")
        if parcel:
            qs = qs.filter(parcel_id=parcel)

        severidad = params.get("severidad")
        if severidad:
            qs = qs.filter(severidad=severidad)

        estado = params.get("estado", AlertStatus.ACTIVA)
        if estado and estado.lower() != "todas":
            qs = qs.filter(estado=estado)

        tipo = params.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)

        desde = params.get("desde")
        if desde:
            qs = qs.filter(fecha_escena_origen__gte=desde)
        hasta = params.get("hasta")
        if hasta:
            qs = qs.filter(fecha_escena_origen__lte=hasta)

        return qs.order_by("-fecha_deteccion")

    # ---- Acciones de feedback ----
    @action(detail=True, methods=["post"], url_path="atender")
    def atender(self, request, pk=None):
        alerta = self.get_object()
        ser = AtenderAlertaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        alerta.marcar_atendida(
            usuario=request.user,
            feedback=ser.validated_data.get("feedback") or None,
            comentario=ser.validated_data.get("comentario") or "",
        )
        return Response(AlertaOperativaSerializer(alerta).data)

    @action(detail=True, methods=["post"], url_path="posponer")
    def posponer(self, request, pk=None):
        alerta = self.get_object()
        ser = PosponerAlertaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        alerta.posponer(dias=ser.validated_data["dias"])
        return Response(AlertaOperativaSerializer(alerta).data)

    @action(detail=True, methods=["post"], url_path="descartar")
    def descartar(self, request, pk=None):
        alerta = self.get_object()
        ser = DescartarAlertaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        alerta.descartar(
            usuario=request.user,
            comentario=ser.validated_data.get("comentario") or "",
        )
        return Response(AlertaOperativaSerializer(alerta).data)


# ---------------------------------------------------------------------------
# Endpoint "estado-hoy" — alimenta el dashboard del frontend
# ---------------------------------------------------------------------------

def _mapear_estado_global(alertas_activas) -> tuple[str, str]:
    """Devuelve (codigo, label) para el banner del lote."""
    if not alertas_activas:
        return "sano", "Sano"
    max_rank = max(SEVERIDAD_RANK.get(a.severidad, 0) for a in alertas_activas)
    if max_rank >= SEVERIDAD_RANK[AlertSeverity.CRITICAL]:
        return "critico", "Crítico"
    if max_rank >= SEVERIDAD_RANK[AlertSeverity.WARNING]:
        return "atencion", "Requiere atención"
    return "sano", "Sano"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def parcela_estado_hoy(request, parcel_pk: int):
    """
    Devuelve estado actual del lote para alimentar el dashboard:
    - banner verde/naranja/rojo con texto humano
    - alerta principal (la más severa y reciente)
    - lista resumida de alertas activas
    - frescura del dato (días desde la última escena)
    """
    parcel = get_object_or_404(Parcel, pk=parcel_pk, is_deleted=False)

    activas_qs = (
        AlertaOperativa.objects
        .select_related("crop_cycle")
        .filter(parcel=parcel, estado=AlertStatus.ACTIVA)
        .order_by("-severidad", "-fecha_deteccion")
    )
    activas = list(activas_qs[:20])
    estado_code, estado_label = _mapear_estado_global(activas)

    principal = activas[0] if activas else None
    principal_data = AlertaOperativaSerializer(principal).data if principal else None

    ultima_alerta = (
        AlertaOperativa.objects.filter(parcel=parcel)
        .order_by("-fecha_escena_origen").first()
    )
    if ultima_alerta:
        dias_desde_ultima_escena = (
            timezone.now().date() - ultima_alerta.fecha_escena_origen
        ).days
        fecha_ultima_escena = ultima_alerta.fecha_escena_origen
    else:
        dias_desde_ultima_escena = None
        fecha_ultima_escena = None

    ciclo_activo = (
        parcel.crop_cycles.filter(status="active").order_by("-planting_date").first()
        if hasattr(parcel, "crop_cycles") else None
    )
    cultivo_actual = None
    etapa_actual = None
    crop_catalog = None
    if ciclo_activo:
        crop_catalog = ciclo_activo.crop_catalog
        cultivo_actual = crop_catalog.name
        stage = ciclo_activo.current_stage if hasattr(ciclo_activo, "current_stage") else None
        etapa_actual = stage.name if stage else None

    indices_monitoreados = list(preferred_indices_for_crop(crop_catalog))
    indices_ficha = [
        {"clave": k, **explain_index(k)} for k in indices_monitoreados
    ]

    setup_required = None
    if not ciclo_activo:
        setup_required = {
            "razon": "sin_ciclo_de_cultivo",
            "mensaje": (
                "Asigna un cultivo y fecha de siembra al lote para activar "
                "alertas reales. Sin ciclo de cultivo no generamos alertas "
                "(no simulamos datos)."
            ),
            "accion": "Asignar cultivo",
            "indices_disponibles": list(INDEX_EXPLAINER.keys()),
        }

    return Response({
        "parcel": {
            "id": parcel.pk,
            "name": parcel.name,
            "area_ha": parcel.area_hectares() if hasattr(parcel, "area_hectares") else None,
            "cultivo_actual": cultivo_actual,
            "etapa_actual": etapa_actual,
        },
        "estado": {
            "codigo": estado_code,
            "label": estado_label,
            "n_alertas_activas": len(activas),
            "n_criticas": sum(1 for a in activas if a.severidad == AlertSeverity.CRITICAL),
            "n_warning": sum(1 for a in activas if a.severidad == AlertSeverity.WARNING),
        },
        "riesgo_activo": principal_data,
        "alertas_activas": AlertaOperativaListSerializer(activas, many=True).data,
        "frescura": {
            "fecha_ultima_escena": fecha_ultima_escena,
            "dias_desde_ultima_escena": dias_desde_ultima_escena,
        },
        "indices_monitoreados": indices_ficha,
        "setup_required": setup_required,
    })
