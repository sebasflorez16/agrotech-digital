"""
Reporte PDF ejecutivo por parcela / ciclo de cultivo.

GET /api/parcels/parcel/<parcel_id>/report/
GET /api/parcels/parcel/<parcel_id>/report/<crop_cycle_id>/

Feature gated: 'pdf_reports' (plan Pro+).

Genera un PDF profesional con:
- Resumen de la parcela y el cultivo
- Estado de salud del cultivo (Monitoreo Continuo)
- Interpretación agronómica por etapa fenológica
- Observaciones satelitales recientes (fechas reales)
"""

import io
import logging
from datetime import date

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from billing.decorators import require_feature
from parcels.models import Parcel, ParcelSceneCache, CropHealthStatus

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


VERDE = colors.HexColor('#1a7a2e')
VERDE_CLARO = colors.HexColor('#2FB344')
GRIS = colors.HexColor('#4a4a4a')
GRIS_CLARO = colors.HexColor('#f0fdf4')


class CropCycleReportView(APIView):
    """
    Genera reporte PDF ejecutivo de una parcela y su ciclo de cultivo.

    GET /api/parcels/parcel/{parcel_id}/report/
    GET /api/parcels/parcel/{parcel_id}/report/{crop_cycle_id}/
    """
    permission_classes = [IsAuthenticated]

    @require_feature('pdf_reports')
    def get(self, request, parcel_id, crop_cycle_id=None):
        if not REPORTLAB_AVAILABLE:
            from rest_framework.response import Response
            return Response({
                'error': 'Generación de PDF no disponible en este entorno',
                'code': 'reportlab_missing',
            }, status=503)

        parcel = get_object_or_404(Parcel, pk=parcel_id, is_deleted=False)

        # Obtener ciclo de cultivo (especificado o el más reciente)
        crop_cycle = None
        if crop_cycle_id:
            from crop.models import CropCycle
            crop_cycle = get_object_or_404(CropCycle, pk=crop_cycle_id, parcel=parcel)
        else:
            crop_cycle = parcel.crop_cycles.exclude(status='cancelled').first()

        # Datos de salud (si existe)
        health = None
        try:
            health = CropHealthStatus.objects.filter(parcel=parcel).first()
        except Exception:
            health = None

        # Observaciones satelitales recientes (reales)
        recent_scenes = list(
            ParcelSceneCache.objects.filter(parcel=parcel).order_by('-date')[:6]
        )

        # Interpretación agronómica
        interpretation = None
        if crop_cycle:
            for index_type, value in (('ndvi', health.ndvi_last if health else None),
                                      ('ndmi', health.ndmi_last if health else None)):
                if value is not None:
                    try:
                        interpretation = crop_cycle.get_index_interpretation(index_type, value)
                        if interpretation and interpretation.get('status') != 'unknown':
                            break
                    except Exception as exc:
                        logger.warning(f"[REPORT] interpretación falló: {exc}")
                        interpretation = None

        pdf_bytes = self._build_pdf(parcel, crop_cycle, health, recent_scenes, interpretation)

        filename = f"reporte_{parcel.name or 'parcela'}_{date.today().isoformat()}.pdf"
        safe_filename = "".join(
            c if c.isalnum() or c in '._-' else '_' for c in filename
        )

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
        return response

    # ────────────────────────────────────────────────────────────
    #  CONSTRUCCIÓN DEL PDF
    # ────────────────────────────────────────────────────────────

    def _build_pdf(self, parcel, crop_cycle, health, recent_scenes, interpretation):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=18 * mm, rightMargin=18 * mm,
            topMargin=16 * mm, bottomMargin=16 * mm,
            title=f"Reporte AgroTech - {parcel.name or 'Parcela'}",
        )

        styles = getSampleStyleSheet()
        estilo_titulo = ParagraphStyle(
            'Titulo', parent=styles['Title'], fontSize=20, textColor=VERDE,
            spaceAfter=4 * mm,
        )
        estilo_subtitulo = ParagraphStyle(
            'Subtitulo', parent=styles['Normal'], fontSize=10, textColor=GRIS,
            alignment=TA_CENTER, spaceAfter=6 * mm,
        )
        estilo_seccion = ParagraphStyle(
            'Seccion', parent=styles['Heading2'], fontSize=13, textColor=VERDE,
            spaceBefore=6 * mm, spaceAfter=3 * mm,
        )
        estilo_celda = ParagraphStyle(
            'Celda', parent=styles['Normal'], fontSize=9, leading=13,
        )
        estilo_celda_bold = ParagraphStyle(
            'CeldaBold', parent=estilo_celda, fontName='Helvetica-Bold',
        )
        estilo_nota = ParagraphStyle(
            'Nota', parent=styles['Normal'], fontSize=8, textColor=GRIS,
            alignment=TA_RIGHT, spaceBefore=8 * mm,
        )

        story = []

        # ── Encabezado ──
        story.append(Paragraph('AgroTech Digital', estilo_titulo))
        story.append(Paragraph(
            'Reporte Ejecutivo de Cultivo — Agricultura de Precisión', estilo_subtitulo
        ))

        # ── Datos generales ──
        general_rows = [
            [Paragraph('<b>Parcela</b>', estilo_celda_bold),
             Paragraph(parcel.name or 'Sin nombre', estilo_celda)],
            [Paragraph('<b>Descripción</b>', estilo_celda_bold),
             Paragraph(parcel.description or '—', estilo_celda)],
            [Paragraph('<b>Área</b>', estilo_celda_bold),
             Paragraph(f'{parcel.area_hectares():,.2f} ha', estilo_celda)],
            [Paragraph('<b>Tipo de suelo</b>', estilo_celda_bold),
             Paragraph(parcel.soil_type or '—', estilo_celda)],
            [Paragraph('<b>Topografía</b>', estilo_celda_bold),
             Paragraph(parcel.topography or '—', estilo_celda)],
            [Paragraph('<b>Fecha del reporte</b>', estilo_celda_bold),
             Paragraph(date.today().strftime('%d/%m/%Y'), estilo_celda)],
        ]

        if crop_cycle:
            general_rows += [
                [Paragraph('<b>Cultivo</b>', estilo_celda_bold),
                 Paragraph(
                     f"{crop_cycle.crop_catalog.name} "
                     f"({crop_cycle.variety or 'variedad no definida'})",
                     estilo_celda)],
                [Paragraph('<b>Ciclo</b>', estilo_celda_bold),
                 Paragraph(
                     f"Siembra: {crop_cycle.planting_date.strftime('%d/%m/%Y')} — "
                     f"Cosecha est.: {crop_cycle.estimated_harvest_date.strftime('%d/%m/%Y') if crop_cycle.estimated_harvest_date else '—'}",
                     estilo_celda)],
                [Paragraph('<b>Días desde siembra</b>', estilo_celda_bold),
                 Paragraph(f'{crop_cycle.days_since_planting}', estilo_celda)],
                [Paragraph('<b>Progreso del ciclo</b>', estilo_celda_bold),
                 Paragraph(f'{crop_cycle.progress_percent}%', estilo_celda)],
            ]
            if crop_cycle.expected_yield:
                general_rows.append([
                    Paragraph('<b>Rendimiento esperado</b>', estilo_celda_bold),
                    Paragraph(f'{crop_cycle.expected_yield} ton/ha', estilo_celda),
                ])
            if crop_cycle.actual_yield:
                general_rows.append([
                    Paragraph('<b>Rendimiento real</b>', estilo_celda_bold),
                    Paragraph(f'{crop_cycle.actual_yield} ton/ha', estilo_celda),
                ])

        tabla_general = Table(general_rows, colWidths=[45 * mm, 125 * mm])
        tabla_general.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), GRIS_CLARO),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#d1fae5')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(tabla_general)

        # ── Estado de salud ──
        story.append(Paragraph('Estado de salud del cultivo', estilo_seccion))
        if health:
            badge = health.status_badge if hasattr(health, 'status_badge') else {}
            label = badge.get('label', health.get_quality_label()) if isinstance(badge, dict) else health.get_quality_label()

            health_rows = [
                [Paragraph('<b>Estado</b>', estilo_celda_bold),
                 Paragraph(str(label), estilo_celda)],
                [Paragraph('<b>Calidad de observación</b>', estilo_celda_bold),
                 Paragraph(health.get_quality_label(), estilo_celda)],
                [Paragraph('<b>Confianza</b>', estilo_celda_bold),
                 Paragraph(f"{health.confidence_score}%", estilo_celda)],
                [Paragraph('<b>Días sin observación</b>', estilo_celda_bold),
                 Paragraph(str(health.days_without_observation or 0), estilo_celda)],
            ]
            if health.ndvi_last is not None:
                health_rows.append([
                    Paragraph('<b>Último NDVI</b>', estilo_celda_bold),
                    Paragraph(f"{health.ndvi_last:.3f}", estilo_celda),
                ])
            if health.ndmi_last is not None:
                health_rows.append([
                    Paragraph('<b>Último NDMI (estrés hídrico)</b>', estilo_celda_bold),
                    Paragraph(f"{health.ndmi_last:.3f}", estilo_celda),
                ])

            tabla_salud = Table(health_rows, colWidths=[45 * mm, 125 * mm])
            tabla_salud.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), GRIS_CLARO),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#d1fae5')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(tabla_salud)
        else:
            story.append(Paragraph(
                'Sin datos de monitoreo continuo. Ejecute análisis satelitales '
                'para activar el seguimiento de salud del cultivo.',
                estilo_celda,
            ))

        # ── Interpretación agronómica ──
        if interpretation:
            story.append(Paragraph('Interpretación agronómica', estilo_seccion))
            stage = interpretation.get('stage') or {}
            idx = interpretation.get('index') or {}
            color_estado = {
                'optimal': VERDE,
                'normal': colors.HexColor('#ca8a04'),
                'warning': colors.HexColor('#ea580c'),
                'high': colors.HexColor('#2563eb'),
                'critical': colors.HexColor('#dc2626'),
                'unknown': GRIS,
            }.get(interpretation.get('status'), GRIS)

            story.append(Paragraph(
                f"<b>Etapa fenológica:</b> {stage.get('name', 'Desconocida')} "
                f"(días {stage.get('day_start', '?')}–{stage.get('day_end', '?')})",
                estilo_celda,
            ))
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(
                f"<b>{idx.get('type', 'NDVI').upper()}:</b> {idx.get('value', '—')} "
                f"(óptimo {idx.get('optimal', '—')}) — desviación {idx.get('deviation_percent', 0)}%",
                estilo_celda,
            ))
            story.append(Spacer(1, 2 * mm))
            hex_color = '#' + color_estado.hexval()[2:].rjust(6, '0')
            story.append(Paragraph(
                f"<font color='{hex_color}'>"
                f"<b>Diagnóstico:</b> {interpretation.get('message', '')}"
                f"</font>",
                estilo_celda,
            ))
            if interpretation.get('critical_alert'):
                story.append(Spacer(1, 2 * mm))
                story.append(Paragraph(
                    f"<b>Alerta:</b> {interpretation['critical_alert']}",
                    ParagraphStyle(
                        'Alerta', parent=estilo_celda,
                        textColor=colors.HexColor('#dc2626'), fontName='Helvetica-Bold',
                    ),
                ))

        # ── Observaciones satelitales recientes ──
        story.append(Paragraph('Observaciones satelitales recientes', estilo_seccion))
        if recent_scenes:
            scene_rows = [[
                Paragraph('<b>Fecha</b>', estilo_celda_bold),
                Paragraph('<b>Índice</b>', estilo_celda_bold),
                Paragraph('<b>Nubosidad</b>', estilo_celda_bold),
            ]]
            for sc in recent_scenes:
                cloud = (sc.metadata or {}).get('cloudCoverage', 0)
                scene_rows.append([
                    Paragraph(sc.date.strftime('%d/%m/%Y'), estilo_celda),
                    Paragraph(sc.index_type, estilo_celda),
                    Paragraph(f'{cloud}%', estilo_celda),
                ])
            tabla_scenes = Table(scene_rows, colWidths=[60 * mm, 60 * mm, 50 * mm])
            tabla_scenes.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), VERDE_CLARO),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#d1fae5')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRIS_CLARO]),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(tabla_scenes)
        else:
            story.append(Paragraph(
                'Aún no hay observaciones satelitales almacenadas para esta parcela.',
                estilo_celda,
            ))

        # ── Pie ──
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph(
            'Documento generado automáticamente por AgroTech Digital. '
            'Los índices satelitales provienen de datos reales (Sentinel-2 / EOSDA). '
            'Contacto: info@agrotechdigital.com',
            estilo_nota,
        ))

        doc.build(story)
        return buffer.getvalue()
