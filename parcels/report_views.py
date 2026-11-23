"""
Reporte PDF ejecutivo por parcela / ciclo de cultivo.

GET /api/parcels/parcel/<parcel_id>/report/
GET /api/parcels/parcel/<parcel_id>/report/<crop_cycle_id>/

Feature gated: 'pdf_reports' (plan Pro+).

Diseño:
- Encabezado y pie de marca en todas las páginas (paginación incluida)
- Tarjetas KPI (área, cultivo, etapa, estado, NDVI, NDMI)
- Mapa de vigor NDVI (imagen Sentinel-2 real) + leyenda
- Sectorización por zonas (si existe)
- Estado de salud, interpretación agronómica, datos generales
- Observaciones recientes filtrando nubosidad > 60%
"""

import base64
import io
import logging
from datetime import date

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from billing.decorators import require_feature
from parcels.models import (
    Parcel, CropHealthStatus, ParcelZonification,
)

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        CondPageBreak, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer,
        Table, TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ─────────────────────────────────────────────────────────────
#  Paleta de marca
# ─────────────────────────────────────────────────────────────
VERDE_OSCURO = colors.HexColor('#0B3D2E')
VERDE = colors.HexColor('#145A32')
VERDE_CLARO = colors.HexColor('#E8F5E9')
ACENTO = colors.HexColor('#2FB344')
GRIS = colors.HexColor('#4B5563')
GRIS_SUAVE = colors.HexColor('#F6F8F6')
GRIS_LINEA = colors.HexColor('#DDE7DD')
ROJO = colors.HexColor('#C0392B')
NARANJA = colors.HexColor('#E67E22')
AMARILLO = colors.HexColor('#F1C40F')

NDVI_LEGEND = [
    ('#af372d', 'Atención'),
    ('#f46d43', 'Bajo'),
    ('#fee08b', 'Intermedio'),
    ('#a1d76a', 'Bueno'),
    ('#006d2c', 'Excelente'),
]


def _format_month(value):
    """'2026-09' → 'sep 2026'."""
    try:
        from datetime import datetime
        dt = datetime.strptime(str(value)[:7], '%Y-%m')
    except Exception:
        return str(value or '—')
    meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
    return f'{meses[dt.month - 1]} {dt.year}'


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

        # ── Ciclo de cultivo (especificado o el más reciente) ──
        crop_cycle = None
        if crop_cycle_id:
            from crop.models import CropCycle
            crop_cycle = get_object_or_404(CropCycle, pk=crop_cycle_id, parcel=parcel)
        else:
            crop_cycle = parcel.crop_cycles.exclude(status='cancelled').first()

        # ── Salud (monitoreo continuo) ──
        health = None
        try:
            health = CropHealthStatus.objects.filter(parcel=parcel).first()
        except Exception:
            health = None

        # ── Evolución mensual (Sentinel-2 real, últimos ~6 meses) ──
        monthly_series = []
        try:
            from .sentinel2 import get_index_time_series
            monthly_series = get_index_time_series(
                parcel.geom, days_back=180, max_scenes=6
            ) or []
        except Exception as exc:
            logger.warning(f"[REPORT] No se pudo leer la serie mensual: {exc}")

        # ── Interpretación agronómica ──
        interpretation = None
        if crop_cycle:
            for index_type, value in (
                ('ndvi', health.ndvi_last if health else None),
                ('ndmi', health.ndmi_last if health else None),
            ):
                if value is not None:
                    try:
                        interpretation = crop_cycle.get_index_interpretation(index_type, value)
                        if interpretation and interpretation.get('status') != 'unknown':
                            break
                    except Exception as exc:
                        logger.warning(f"[REPORT] interpretación falló: {exc}")
                        interpretation = None

        # ── Zonas (última sectorización lista) ──
        zones = []
        try:
            zon = (
                ParcelZonification.objects.filter(parcel=parcel, status='ready')
                .order_by('-created_at').first()
                or ParcelZonification.objects.filter(parcel=parcel).order_by('-created_at').first()
            )
            if zon:
                zones = list(zon.zones.all().order_by('cluster_id'))
        except Exception as exc:
            logger.warning(f"[REPORT] No se pudieron leer zonas: {exc}")

        # ── Imagen NDVI real (Sentinel-2) ──
        ndvi_image = None
        try:
            if parcel.geom:
                from .sentinel2 import _find_scene_and_arrays, get_index_images
                scene, arrays = _find_scene_and_arrays(
                    parcel.geom, str(date.today()), mask_clouds=False
                )
                if scene and arrays:
                    imgs = get_index_images(
                        parcel.geom, str(date.today()),
                        mode='contrast', smoothing='median', arrays=arrays,
                    )
                    b64 = (imgs or {}).get('ndvi')
                    if b64:
                        ndvi_image = {
                            'b64': b64,
                            'date': scene.get('date'),
                            'cloud': scene.get('cloud_cover'),
                        }
        except Exception as exc:
            logger.warning(f"[REPORT] No se pudo generar NDVI: {exc}")

        pdf_bytes = self._build_pdf(
            parcel, crop_cycle, health, monthly_series, interpretation,
            ndvi_image=ndvi_image, zones=zones,
        )

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

    def _build_pdf(self, parcel, crop_cycle, health, monthly_series,
                   interpretation, ndvi_image=None, zones=None):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=16 * mm, rightMargin=16 * mm,
            topMargin=34 * mm, bottomMargin=20 * mm,
            title=f"Reporte AgroTech - {parcel.name or 'Parcela'}",
            author='AgroTech Digital',
        )
        width = doc.width

        # ── Estilos ──
        h1 = ParagraphStyle(
            'H1', fontName='Helvetica-Bold', fontSize=19, leading=23,
            textColor=VERDE_OSCURO, spaceAfter=2 * mm,
        )
        subtitle = ParagraphStyle(
            'Sub', fontName='Helvetica', fontSize=9.5, leading=13,
            textColor=GRIS, spaceAfter=5 * mm,
        )
        body = ParagraphStyle(
            'Body', fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor('#1F2937'),
        )
        small = ParagraphStyle(
            'Small', fontName='Helvetica', fontSize=7.8, leading=10.5, textColor=GRIS,
        )
        small_right = ParagraphStyle('SmallR', parent=small, alignment=TA_RIGHT)
        cell = ParagraphStyle('Cell', fontName='Helvetica', fontSize=8.5, leading=11.5)
        cell_bold = ParagraphStyle('CellB', parent=cell, fontName='Helvetica-Bold')
        cell_white = ParagraphStyle('CellW', parent=cell_bold, textColor=colors.white)
        title_cell = ParagraphStyle('TitleCell', fontName='Helvetica-Bold', fontSize=8.5, leading=11.5, textColor=colors.white)
        kpi = ParagraphStyle('KPI', fontName='Helvetica', fontSize=8.2, leading=12.5)

        def section(title):
            t = Table([[Paragraph(title, title_cell)]], colWidths=[width])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), VERDE),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            # Evita que el título quede huérfano al pie de página.
            return [CondPageBreak(45 * mm), Spacer(1, 3 * mm), t, Spacer(1, 2.5 * mm)]

        def kv_table(rows, label_w=42 * mm):
            data = [[Paragraph(f'<b>{k}</b>', cell_bold), Paragraph(str(v), cell)] for k, v in rows]
            t = Table(data, colWidths=[label_w, width - label_w])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), VERDE_CLARO),
                ('GRID', (0, 0), (-1, -1), 0.4, GRIS_LINEA),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            return t

        story = []

        # ── Título ──
        story.append(Paragraph('Reporte Ejecutivo de Cultivo', h1))
        story.append(Paragraph(
            f"{parcel.name or 'Parcela'} · {date.today().strftime('%d/%m/%Y')}", subtitle
        ))

        # ── Resumen ejecutivo ──
        health_label = 'Sin datos'
        if health:
            badge = getattr(health, 'status_badge', None)
            health_label = (badge.get('label') if isinstance(badge, dict) else None) or health.get_quality_label()
        area_txt = f"{parcel.area_hectares():,.2f} ha"
        crop_txt = crop_cycle.crop_catalog.name if crop_cycle and crop_cycle.crop_catalog else '—'
        stage_txt = '—'
        if interpretation and interpretation.get('stage'):
            stage_txt = interpretation['stage'].get('name') or '—'
        ndvi_txt = f"{health.ndvi_last:.3f}" if health and health.ndvi_last is not None else '—'
        ndmi_txt = f"{health.ndmi_last:.3f}" if health and health.ndmi_last is not None else '—'

        kpi_data = [[
            Paragraph(f"<font size=7 color='#6B7280'>ÁREA</font><br/><font size=14 color='#145A32'><b>{area_txt}</b></font>", kpi),
            Paragraph(f"<font size=7 color='#6B7280'>CULTIVO</font><br/><font size=12 color='#145A32'><b>{crop_txt}</b></font>", kpi),
            Paragraph(f"<font size=7 color='#6B7280'>ETAPA</font><br/><font size=11 color='#145A32'><b>{stage_txt}</b></font>", kpi),
        ], [
            Paragraph(f"<font size=7 color='#6B7280'>ESTADO</font><br/><font size=11 color='#145A32'><b>{health_label}</b></font>", kpi),
            Paragraph(f"<font size=7 color='#6B7280'>ÚLTIMO NDVI</font><br/><font size=14 color='#145A32'><b>{ndvi_txt}</b></font>", kpi),
            Paragraph(f"<font size=7 color='#6B7280'>ÚLTIMO NDMI</font><br/><font size=14 color='#145A32'><b>{ndmi_txt}</b></font>", kpi),
        ]]
        kpi_table = Table(kpi_data, colWidths=[width / 3.0] * 3)
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GRIS_SUAVE),
            ('BOX', (0, 0), (-1, -1), 0.4, GRIS_LINEA),
            ('INNERGRID', (0, 0), (-1, -1), 0.4, GRIS_LINEA),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        story.append(kpi_table)

        # ── Mapa NDVI ──
        story += section('Mapa de vigor (NDVI)')
        if ndvi_image:
            try:
                raw = base64.b64decode(ndvi_image['b64'])
                img = Image(io.BytesIO(raw))
                max_w, max_h = 118 * mm, 92 * mm
                scale = min(max_w / img.imageWidth, max_h / img.imageHeight, 1.6)
                img.drawWidth = img.imageWidth * scale
                img.drawHeight = img.imageHeight * scale
                img.hAlign = 'CENTER'
                story.append(img)
                cloud = ndvi_image.get('cloud')
                cloud_txt = f" · nubes {cloud:.1f}%" if isinstance(cloud, (int, float)) else ''
                story.append(Paragraph(
                    f"NDVI · imagen Sentinel-2 del {ndvi_image.get('date') or '—'}{cloud_txt}",
                    ParagraphStyle('Caption', parent=small, alignment=TA_CENTER, spaceBefore=1.5 * mm),
                ))
                # Leyenda
                swatches = [[Paragraph(f"<font color='white' size=6> </font>", small) for _ in NDVI_LEGEND],
                            [Paragraph(f"<font size=7 color='#4B5563'>{lbl}</font>", ParagraphStyle('Lg', parent=small, alignment=TA_CENTER)) for _, lbl in NDVI_LEGEND]]
                legend = Table(swatches, colWidths=[width / 5.0] * 5)
                lstyle = [
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 1),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                    ('TOPPADDING', (0, 0), (-1, 0), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ]
                for i, (hexc, _) in enumerate(NDVI_LEGEND):
                    lstyle.append(('BACKGROUND', (i, 0), (i, 0), colors.HexColor(hexc)))
                legend.setStyle(TableStyle(lstyle))
                story.append(Spacer(1, 1.5 * mm))
                story.append(legend)
            except Exception as exc:
                logger.warning(f"[REPORT] No se pudo insertar la imagen NDVI: {exc}")
                story.append(Paragraph('No se pudo insertar la imagen NDVI en el reporte.', small))
        else:
            story.append(Paragraph(
                'No hay una imagen NDVI disponible para esta parcela en este momento. '
                'Ejecuta un análisis satelital y vuelve a generar el reporte.', small,
            ))

        # ── Zonas ──
        story += section('Sectorización (zonas de manejo)')
        if zones:
            zdata = [[
                Paragraph('Zona', cell_white), Paragraph('Área', cell_white),
                Paragraph('NDVI', cell_white), Paragraph('Brecha', cell_white),
                Paragraph('Prioridad', cell_white), Paragraph('Recomendación', cell_white),
            ]]
            prio_colors = {'alta': ROJO, 'media': NARANJA, 'baja': ACENTO}
            prio_labels = {'alta': 'Alta', 'media': 'Media', 'baja': 'Baja'}
            for z in zones:
                ndvi = f"{z.ndvi_mean:.2f}" if z.ndvi_mean is not None else '—'
                brecha = f"{z.brecha_pct:+.1f}%" if z.brecha_pct is not None else '—'
                prio = (z.priority or 'media').lower()
                rec = (z.recomendacion or '—')
                if len(rec) > 95:
                    rec = rec[:92] + '…'
                zdata.append([
                    Paragraph(z.label or f"Zona {z.cluster_id}", cell),
                    Paragraph(f"{z.area_ha:.2f} ha", cell),
                    Paragraph(ndvi, cell),
                    Paragraph(brecha, cell),
                    Paragraph(prio_labels.get(prio, prio), cell_bold),
                    Paragraph(rec, cell),
                ])
            zt = Table(zdata, colWidths=[22 * mm, 20 * mm, 16 * mm, 18 * mm, 20 * mm, width - 96 * mm])
            zstyle = [
                ('BACKGROUND', (0, 0), (-1, 0), VERDE),
                ('GRID', (0, 0), (-1, -1), 0.4, GRIS_LINEA),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRIS_SUAVE]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]
            for i, z in enumerate(zones, start=1):
                prio = (z.priority or 'media').lower()
                zstyle.append(('TEXTCOLOR', (4, i), (4, i), prio_colors.get(prio, GRIS)))
            zt.setStyle(TableStyle(zstyle))
            story.append(zt)
        else:
            story.append(Paragraph(
                'Aún no hay una sectorización generada para esta parcela. '
                'Usa "Sectorizar parcela (zonas)" en el dashboard.', small,
            ))

        # ── Estado de salud ──
        story += section('Estado de salud del cultivo')
        if health:
            rows = [
                ('Estado', health_label),
                ('Calidad de observación', health.get_quality_label()),
                ('Confianza', f"{health.confidence_score}%"),
                ('Días sin observación', str(health.days_without_observation or 0)),
            ]
            if health.ndvi_last is not None:
                rows.append(('Último NDVI', f"{health.ndvi_last:.3f}"))
            if health.ndmi_last is not None:
                rows.append(('Último NDMI (estrés hídrico)', f"{health.ndmi_last:.3f}"))
            story.append(kv_table(rows))
        else:
            story.append(Paragraph(
                'Sin datos de monitoreo continuo. Ejecuta análisis satelitales '
                'para activar el seguimiento de salud del cultivo.', small,
            ))

        # ── Interpretación agronómica ──
        if interpretation:
            story += section('Interpretación agronómica')
            stage = interpretation.get('stage') or {}
            idx = interpretation.get('index') or {}
            color_estado = {
                'optimal': VERDE,
                'normal': colors.HexColor('#CA8A04'),
                'warning': NARANJA,
                'high': colors.HexColor('#2563EB'),
                'critical': ROJO,
                'unknown': GRIS,
            }.get(interpretation.get('status'), GRIS)
            hex_color = '#' + color_estado.hexval()[2:].rjust(6, '0')
            rows = [
                ('Etapa fenológica', f"{stage.get('name', 'Desconocida')} (días {stage.get('day_start', '?')}–{stage.get('day_end', '?')})"),
                ('Índice', f"{idx.get('type', 'NDVI').upper()}: {idx.get('value', '—')}"),
                ('Óptimo', f"{idx.get('optimal', '—')}"),
                ('Desviación', f"{idx.get('deviation_percent', 0)}%"),
            ]
            story.append(kv_table(rows))
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(
                f"<font color='{hex_color}'><b>Diagnóstico:</b> {interpretation.get('message', '')}</font>",
                cell,
            ))
            if interpretation.get('critical_alert'):
                story.append(Spacer(1, 1.5 * mm))
                story.append(Paragraph(
                    f"<font color='#C0392B'><b>Alerta:</b> {interpretation['critical_alert']}</font>",
                    cell_bold,
                ))

        # ── Datos generales ──
        story += section('Datos generales')
        rows = [
            ('Parcela', parcel.name or 'Sin nombre'),
            ('Descripción', parcel.description or '—'),
            ('Área', f'{parcel.area_hectares():,.2f} ha'),
            ('Tipo de suelo', parcel.soil_type or '—'),
            ('Topografía', parcel.topography or '—'),
            ('Fecha del reporte', date.today().strftime('%d/%m/%Y')),
        ]
        if crop_cycle:
            rows += [
                ('Cultivo', f"{crop_cycle.crop_catalog.name} ({crop_cycle.variety or 'variedad no definida'})"),
                ('Ciclo', f"Siembra: {crop_cycle.planting_date.strftime('%d/%m/%Y')} — "
                          f"Cosecha est.: {crop_cycle.estimated_harvest_date.strftime('%d/%m/%Y') if crop_cycle.estimated_harvest_date else '—'}"),
                ('Días desde siembra', str(crop_cycle.days_since_planting)),
                ('Progreso del ciclo', f'{crop_cycle.progress_percent}%'),
            ]
            if crop_cycle.expected_yield:
                rows.append(('Rendimiento esperado', f'{crop_cycle.expected_yield} ton/ha'))
            if crop_cycle.actual_yield:
                rows.append(('Rendimiento real', f'{crop_cycle.actual_yield} ton/ha'))
        story.append(kv_table(rows))

        # ── Evolución mensual (Sentinel-2) ──
        story += section('Evolución mensual (Sentinel-2)')
        if monthly_series:
            col_w = (width - 52 * mm) / 4.0
            mdata = [[
                Paragraph('Mes', cell_white), Paragraph('Nubes', cell_white),
                Paragraph('NDVI', cell_white), Paragraph('NDMI', cell_white),
                Paragraph('SAVI', cell_white), Paragraph('NDRE', cell_white),
            ]]
            mstyle = [
                ('BACKGROUND', (0, 0), (-1, 0), VERDE),
                ('GRID', (0, 0), (-1, -1), 0.4, GRIS_LINEA),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRIS_SUAVE]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]
            for i, p in enumerate(monthly_series, start=1):
                cloud = p.get('cloud_cover')
                cloud_txt = f'{cloud:.1f}%' if isinstance(cloud, (int, float)) else '—'

                def val(key, _p=p):
                    v = _p.get(key)
                    return f'{v:.2f}' if isinstance(v, (int, float)) else '—'

                mdata.append([
                    Paragraph(_format_month(p.get('month') or p.get('date')), cell),
                    Paragraph(cloud_txt, cell),
                    Paragraph(val('ndvi_mean'), cell_bold),
                    Paragraph(val('ndmi_mean'), cell),
                    Paragraph(val('savi_mean'), cell),
                    Paragraph(val('ndre_mean'), cell),
                ])
                if isinstance(cloud, (int, float)):
                    mstyle.append(('TEXTCOLOR', (1, i), (1, i), ACENTO if cloud <= 15 else (NARANJA if cloud <= 40 else ROJO)))
            mt = Table(mdata, colWidths=[32 * mm, 20 * mm, col_w, col_w, col_w, col_w])
            mt.setStyle(TableStyle(mstyle))
            story.append(mt)
            story.append(Paragraph(
                'Promedio del lote por mes, calculado con los píxeles válidos (sin nubes) de Sentinel-2.',
                ParagraphStyle('NoteM', parent=small, spaceBefore=1.5 * mm),
            ))
        else:
            story.append(Paragraph(
                'No hay imágenes Sentinel-2 suficientes para construir la evolución mensual.', small,
            ))

        # ── Nota final ──
        story.append(Spacer(1, 5 * mm))
        has_valid = bool(health and health.last_observation_date)
        story.append(Paragraph(
            ('Los índices satelitales mostrados provienen de observaciones Sentinel-2 reales. '
             if has_valid else
             'No hay observaciones satelitales válidas registradas para esta parcela. ') +
            'Documento generado automáticamente por AgroTech Digital.',
            small_right,
        ))

        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
        return buffer.getvalue()

    # ────────────────────────────────────────────────────────────
    #  Encabezado y pie de página
    # ────────────────────────────────────────────────────────────
    @staticmethod
    def _header_footer(canvas, doc):
        canvas.saveState()
        w, h = A4
        # Banda superior
        canvas.setFillColor(VERDE_OSCURO)
        canvas.rect(0, h - 26 * mm, w, 26 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 15)
        canvas.drawString(16 * mm, h - 12.5 * mm, 'AgroTech Digital')
        canvas.setFont('Helvetica', 8.2)
        canvas.drawString(16 * mm, h - 18.2 * mm, 'Agricultura de precisión · Reporte ejecutivo de cultivo')
        canvas.setFont('Helvetica', 8.2)
        canvas.drawRightString(w - 16 * mm, h - 12.5 * mm, date.today().strftime('%d/%m/%Y'))
        canvas.drawRightString(w - 16 * mm, h - 18.2 * mm, 'Datos satelitales reales')
        # Línea de acento
        canvas.setFillColor(ACENTO)
        canvas.rect(0, h - 27.2 * mm, w, 1.2 * mm, stroke=0, fill=1)

        # Pie
        canvas.setStrokeColor(GRIS_LINEA)
        canvas.setLineWidth(0.5)
        canvas.line(16 * mm, 15 * mm, w - 16 * mm, 15 * mm)
        canvas.setFillColor(GRIS)
        canvas.setFont('Helvetica', 7.3)
        canvas.drawString(
            16 * mm, 10 * mm,
            'Documento generado automáticamente por AgroTech Digital · info@agrotechdigital.com',
        )
        canvas.drawRightString(w - 16 * mm, 10 * mm, f'Página {doc.page}')
        canvas.restoreState()
