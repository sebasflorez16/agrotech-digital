from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.utils import timezone

from labores.models import Labor, LaborType


@dataclass
class StageWindow:
    key: str
    label: str
    start_ratio: float
    end_ratio: float
    labor_types: list[str]
    priority: str


STAGE_WINDOWS = [
    StageWindow(
        key="establishment",
        label="Establecimiento",
        start_ratio=0.0,
        end_ratio=0.15,
        labor_types=["Preparacion de suelo", "Siembra", "Riego", "Monitoreo"],
        priority="alta",
    ),
    StageWindow(
        key="vegetative",
        label="Desarrollo vegetativo",
        start_ratio=0.15,
        end_ratio=0.45,
        labor_types=["Fertilizacion", "Riego", "Control fitosanitario", "Monitoreo"],
        priority="media",
    ),
    StageWindow(
        key="flowering",
        label="Floracion y cuajado",
        start_ratio=0.45,
        end_ratio=0.70,
        labor_types=["Riego", "Control fitosanitario", "Monitoreo", "Fertilizacion"],
        priority="alta",
    ),
    StageWindow(
        key="filling",
        label="Llenado y maduracion",
        start_ratio=0.70,
        end_ratio=0.90,
        labor_types=["Riego", "Monitoreo", "Control fitosanitario"],
        priority="media",
    ),
    StageWindow(
        key="harvest",
        label="Cosecha",
        start_ratio=0.90,
        end_ratio=1.00,
        labor_types=["Cosecha", "Postcosecha", "Monitoreo"],
        priority="alta",
    ),
]


def _resolve_stage(days_since_planting: int, cycle_days: int) -> StageWindow:
    if cycle_days <= 0:
        cycle_days = 120
    progress = min(max(days_since_planting / cycle_days, 0), 1)
    for stage in STAGE_WINDOWS:
        if stage.start_ratio <= progress <= stage.end_ratio:
            return stage
    return STAGE_WINDOWS[-1]


def build_crop_labor_suggestions(crop):
    if not crop.sowing_date:
        return {
            "ready": False,
            "message": "El cultivo no tiene fecha de siembra. No se pueden calcular sugerencias por tiempo.",
            "suggestions": [],
        }

    today: date = timezone.now().date()
    days_since_planting = max((today - crop.sowing_date).days, 0)
    cycle_days = (crop.variety.cycle_days if crop.variety and crop.variety.cycle_days else 120)
    stage = _resolve_stage(days_since_planting, cycle_days)

    start_day = int(stage.start_ratio * cycle_days)
    end_day = int(stage.end_ratio * cycle_days)

    active_assignment = crop.assignments.filter(is_active=True).select_related("parcel").first()
    parcel = active_assignment.parcel if active_assignment else None

    labor_type_map = {
        lt.nombre: lt
        for lt in LaborType.objects.filter(nombre__in=stage.labor_types)
    }

    existing_labors = Labor.objects.filter(cultivos=crop)
    if parcel:
        existing_labors = existing_labors.filter(parcelas=parcel)

    suggestions = []
    for labor_name in stage.labor_types:
        lt = labor_type_map.get(labor_name)
        matching = existing_labors.filter(tipo=lt) if lt else existing_labors.filter(nombre__iexact=labor_name)
        completed = matching.filter(estado="completada").exists()
        in_progress = matching.filter(estado__in=["pendiente", "en_progreso"]).exists()

        suggestions.append(
            {
                "labor_type_id": lt.id if lt else None,
                "labor_type_name": labor_name,
                "priority": stage.priority,
                "stage": stage.label,
                "window_days": {"start": start_day, "end": end_day},
                "reason": (
                    f"Recomendada para la etapa {stage.label.lower()} "
                    f"(dia {start_day} al {end_day} del ciclo)."
                ),
                "already_completed": completed,
                "already_scheduled": in_progress,
            }
        )

    return {
        "ready": True,
        "crop_id": crop.id,
        "crop_name": crop.name,
        "days_since_planting": days_since_planting,
        "cycle_days": cycle_days,
        "current_stage": stage.label,
        "parcel": {"id": parcel.id, "name": parcel.name} if parcel else None,
        "suggestions": suggestions,
    }
