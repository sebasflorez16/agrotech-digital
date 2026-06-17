"""
Módulo de preparación de datos para Machine Learning.

Exporta datos estructurados desde el sistema actual para que futuros modelos
de ML puedan entrenarse sin depender de la base de datos transaccional.

NO implementa IA — solo estructura los datos para que estén listos cuando
se implemente el pipeline de ML.
"""
import csv
import io
from datetime import date, timedelta
from django.db.models import Avg, Min, Max, Q
from parcels.models import Parcel, ParcelSceneCache, CropHealthStatus
from .models import CropCycle, CropCatalog, PhenologicalStage


def export_alert_training_dataset(tenant_id=None, output_format="json"):
    """
    Exporta el dataset etiquetado de alertas agronómicas para entrenar
    un clasificador que reduzca falsos positivos.

    Cada fila incluye:
    - Features: índices satelitales, etapa fenológica, cultivo, severidad
    - Label: feedback del agricultor (útil / no_útil / falso_positivo)

    Returns:
        list[dict] si output_format="json"
        str (CSV) si output_format="csv"
    """
    # Lazy import para no depender de INSTALLED_APPS al cargar el módulo
    from agronomic_alerts.models import AlertaOperativa
    qs = AlertaOperativa.objects.filter(feedback__isnull=False).exclude(feedback="")
    if tenant_id:
        qs = qs.filter(parcel__tenant_id=tenant_id)

    rows = []
    for alerta in qs.select_related("parcel", "crop_cycle__crop_catalog"):
        contexto = alerta.contexto or {}
        row = {
            "alert_uuid": str(alerta.uuid),
            "tipo": alerta.tipo,
            "severidad": alerta.severidad,
            "indice_afectado": alerta.indice_afectado,
            "valor_observado": alerta.valor_observado,
            "valor_umbral_min": alerta.valor_umbral_min,
            "valor_umbral_max": alerta.valor_umbral_max,
            "desviacion_pct": alerta.desviacion_pct,
            "etapa_fenologica": contexto.get("stage", {}).get("name", ""),
            "is_etapa_critica": contexto.get("stage", {}).get("is_critical", False),
            "necesidad_hidrica": contexto.get("stage", {}).get("water_need", 0),
            "cultivo": contexto.get("crop", {}).get("name", ""),
            "categoria_cultivo": contexto.get("crop", {}).get("category", ""),
            "dias_desde_siembra": contexto.get("days_since_planting", 0),
            "progreso_pct": contexto.get("progress_percent", 0),
            "label": alerta.feedback,
            "fecha_escena": str(alerta.fecha_escena_origen),
            "fecha_feedback": str(alerta.fecha_feedback) if alerta.fecha_feedback else None,
        }
        rows.append(row)

    if output_format == "csv":
        if not rows:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    return rows


def export_cycle_yield_dataset(tenant_id=None, output_format="json"):
    """
    Exporta datos de ciclos de cultivo para entrenar un modelo de regresión
    que prediga rendimiento (ton/ha) a partir de índices satelitales por etapa.

    Features:
    - NDVI promedio por etapa fenológica
    - NDMI promedio por etapa
    - Duración real del ciclo
    - Días desde siembra
    - Cultivo, categoría
    - Área de la parcela

    Target:
    - actual_yield (rendimiento real en ton/ha)
    - expected_yield (rendimiento esperado, para baseline)

    Returns:
        list[dict] si output_format="json"
        str (CSV) si output_format="csv"
    """
    qs = CropCycle.objects.filter(
        status="harvested",
        actual_yield__isnull=False,
    ).select_related("parcel", "crop_catalog")

    if tenant_id:
        qs = qs.filter(parcel__tenant_id=tenant_id)

    rows = []
    for cycle in qs:
        # Buscar escenas NDVI en el rango del ciclo
        start = cycle.planting_date
        end = cycle.actual_harvest_date or cycle.estimated_harvest_date or start + timedelta(days=120)

        ndvi_scenes = ParcelSceneCache.objects.filter(
            parcel=cycle.parcel,
            index_type="NDVI",
            date__gte=start,
            date__lte=end,
        ).order_by("date")

        ndmi_scenes = ParcelSceneCache.objects.filter(
            parcel=cycle.parcel,
            index_type="NDMI",
            date__gte=start,
            date__lte=end,
        ).order_by("date")

        # NDVI stats per stage
        ndvi_by_stage = {}
        ndmi_by_stage = {}
        stages = cycle.crop_catalog.stages.all() if cycle.crop_catalog else []

        for stage in stages:
            stage_start = start + timedelta(days=stage.day_start)
            stage_end = start + timedelta(days=stage.day_end)

            stage_ndvi = ndvi_scenes.filter(date__gte=stage_start, date__lte=stage_end)
            if stage_ndvi.exists():
                agg = stage_ndvi.aggregate(avg=Avg("metadata__ndvi_mean"), min_val=Min("metadata__ndvi_mean"), max_val=Max("metadata__ndvi_mean"))
                ndvi_by_stage[stage.name] = {
                    "promedio": round(agg["avg"], 4) if agg["avg"] else None,
                    "min": round(agg["min_val"], 4) if agg["min_val"] else None,
                    "max": round(agg["max_val"], 4) if agg["max_val"] else None,
                }

            stage_ndmi = ndmi_scenes.filter(date__gte=stage_start, date__lte=stage_end)
            if stage_ndmi.exists():
                agg = stage_ndmi.aggregate(avg=Avg("metadata__ndmi_mean"))
                ndmi_by_stage[stage.name] = round(agg["avg"], 4) if agg["avg"] else None

        # NDVI trend (slope simple)
        ndvi_values = [(s.date, (s.metadata or {}).get("ndvi_mean")) for s in ndvi_scenes if (s.metadata or {}).get("ndvi_mean")]
        ndvi_values = [v for v in ndvi_values if v[1] is not None]
        ndvi_trend = 0.0
        if len(ndvi_values) >= 2:
            first = ndvi_values[0]
            last = ndvi_values[-1]
            days_diff = (last[0] - first[0]).days
            if days_diff > 0:
                ndvi_trend = round((last[1] - first[1]) / days_diff, 6)

        total_days = (end - start).days

        row = {
            "cycle_id": cycle.id,
            "parcel_id": cycle.parcel.id,
            "cultivo": cycle.crop_catalog.name if cycle.crop_catalog else "",
            "categoria": cycle.crop_catalog.category if cycle.crop_catalog else "",
            "variedad": cycle.variety or "",
            "fecha_siembra": str(cycle.planting_date),
            "fecha_cosecha": str(cycle.actual_harvest_date or cycle.estimated_harvest_date),
            "duracion_dias": total_days,
            "area_ha": cycle.parcel.area_hectares(),
            "densidad_siembra": cycle.planting_density,
            "cantidad_semilla_kg_ha": cycle.seed_amount,
            "rendimiento_esperado_ton_ha": float(cycle.expected_yield) if cycle.expected_yield else None,
            "rendimiento_real_ton_ha": float(cycle.actual_yield) if cycle.actual_yield else None,
            "ndvi_promedio_ciclo": round(
                ndvi_scenes.aggregate(avg=Avg("metadata__ndvi_mean"))["avg"], 4
            ) if ndvi_scenes.exists() and ndvi_scenes.aggregate(avg=Avg("metadata__ndvi_mean"))["avg"] else None,
            "ndvi_tendencia_diaria": ndvi_trend,
            "num_escenas_ndvi": ndvi_scenes.count(),
            "num_escenas_ndmi": ndmi_scenes.count(),
            "ndvi_por_etapa": ndvi_by_stage,
            "ndmi_por_etapa": ndmi_by_stage,
            "suelo_tipo": cycle.parcel.soil_type,
            "topografia": cycle.parcel.topography,
        }
        rows.append(row)

    if output_format == "csv":
        # Flatten for CSV
        if not rows:
            return ""
        flat_rows = []
        for r in rows:
            flat = {
                "cycle_id": r["cycle_id"],
                "parcel_id": r["parcel_id"],
                "cultivo": r["cultivo"],
                "categoria": r["categoria"],
                "variedad": r["variedad"],
                "fecha_siembra": r["fecha_siembra"],
                "duracion_dias": r["duracion_dias"],
                "area_ha": r["area_ha"],
                "densidad_siembra": r["densidad_siembra"],
                "cantidad_semilla_kg_ha": r["cantidad_semilla_kg_ha"],
                "rendimiento_esperado_ton_ha": r["rendimiento_esperado_ton_ha"],
                "rendimiento_real_ton_ha": r["rendimiento_real_ton_ha"],
                "ndvi_promedio_ciclo": r["ndvi_promedio_ciclo"],
                "ndvi_tendencia_diaria": r["ndvi_tendencia_diaria"],
                "num_escenas_ndvi": r["num_escenas_ndvi"],
                "suelo_tipo": r["suelo_tipo"],
                "topografia": r["topografia"],
            }
            flat_rows.append(flat)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=flat_rows[0].keys())
        writer.writeheader()
        writer.writerows(flat_rows)
        return output.getvalue()

    return rows


def get_dataset_stats(tenant_id=None):
    """
    Retorna estadísticas de los datasets disponibles para ML.
    Útil para saber si hay suficientes datos para entrenar.
    """
    # Lazy import
    from agronomic_alerts.models import AlertaOperativa
    alert_qs = AlertaOperativa.objects.filter(feedback__isnull=False).exclude(feedback="")
    cycle_qs = CropCycle.objects.filter(status="harvested", actual_yield__isnull=False)

    if tenant_id:
        alert_qs = alert_qs.filter(parcel__tenant_id=tenant_id)
        cycle_qs = cycle_qs.filter(parcel__tenant_id=tenant_id)

    return {
        "alertas_etiquetadas": alert_qs.count(),
        "alertas_utiles": alert_qs.filter(feedback="util").count(),
        "alertas_no_utiles": alert_qs.filter(feedback="no_util").count(),
        "alertas_falsos_positivos": alert_qs.filter(feedback="falso_positivo").count(),
        "ciclos_cosechados": cycle_qs.count(),
        "ciclos_con_rendimiento": cycle_qs.filter(actual_yield__gt=0).count(),
        "listo_para_clasificador": alert_qs.count() >= 50,
        "listo_para_regresion": cycle_qs.count() >= 20,
    }