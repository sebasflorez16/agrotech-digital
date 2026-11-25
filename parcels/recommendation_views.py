"""Endpoint de recomendaciones agronómicas por parcela."""

import logging

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Parcel

logger = logging.getLogger(__name__)


class ParcelRecommendationsView(APIView):
    """
    Recomendaciones inteligentes para una parcela.

    POST /api/parcels/parcel/<parcel_id>/recommendations/
    Body opcional: { "statistics": {...}, "scene": {...} }

    Si el frontend ya cargó los índices de Sentinel-2, los envía para evitar
    releer la escena. Si no, se calculan desde Sentinel-2.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, parcel_id):
        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)
        data = request.data if isinstance(request.data, dict) else {}
        stats = data.get("statistics") or None
        scene = data.get("scene") or None

        from .recommendations import build_parcel_report
        try:
            report = build_parcel_report(parcel, stats=stats, scene=scene)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Recomendaciones fallaron para parcela %s: %s", parcel_id, exc)
            return Response({
                "error": "No se pudieron generar las recomendaciones.",
                "detail": str(exc),
            }, status=500)

        return Response(report)

    def get(self, request, parcel_id):
        return self.post(request, parcel_id)
