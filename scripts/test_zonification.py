"""Prueba funcional del pipeline de zonificación con la nueva estrategia de recomendación."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django
django.setup()

from datetime import date
from django.db import transaction
from django_tenants.utils import schema_context

from parcels.models import Parcel, ParcelZonification
from parcels.zonification_pipeline import run_zonification


class _Rollback(Exception):
    pass


try:
    with transaction.atomic():
        with schema_context("villa_lola"):
            parcel = Parcel.objects.create(
                name="TEST_ZONIF",
                eosda_id="eosda_zonif_test",
                soil_type="arcilloso",
                topography="plano",
                geom={
                    "type": "Polygon",
                    "coordinates": [[
                        [-73.40, 4.10], [-73.38, 4.10],
                        [-73.38, 4.13], [-73.40, 4.13],
                        [-73.40, 4.10],
                    ]],
                },
            )
            zonif = ParcelZonification.objects.create(
                parcel=parcel, scene_date=date.today(), index_base="ndvi", k_zones=3,
            )
            result = run_zonification(zonif)
            print("RESULT:", result)
            for z in zonif.zones.all().order_by("cluster_id"):
                print(f"  Zona {z.cluster_id} [{z.label}] brecha={z.brecha_pct}% prioridad={z.priority} drenaje={z.drainage_direction}")
                print(f"    -> {z.recomendacion}")
        raise _Rollback()
except _Rollback:
    print("OK - transacción revertida")
