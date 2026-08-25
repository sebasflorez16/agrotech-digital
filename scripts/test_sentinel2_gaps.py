"""Prueba de los 3 gaps: lista de escenas + estadísticas + recomendación óptica/radar."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django
django.setup()

from parcels.sentinel2 import (
    search_sentinel2_scenes, get_index_statistics, get_observation_recommendation,
)

geometry = {
    "type": "Polygon",
    "coordinates": [[
        [-73.40, 4.10], [-73.38, 4.10],
        [-73.38, 4.13], [-73.40, 4.13],
        [-73.40, 4.10],
    ]],
}
scene_date = "2026-08-12"

print("=== 1. Lista de escenas (nubosidad) ===")
scenes = search_sentinel2_scenes(geometry, scene_date, max_results=5)
for s in scenes:
    print(f"  {s['date']} · nubes {s['cloud_cover']:.1f}% · {s['id']}")

print("=== 2. Estadísticas (promedio por índice) ===")
stats = get_index_statistics(geometry, scene_date)
for k, v in stats.items():
    print(f"  {k}: mean={v['mean']} min={v['min']} max={v['max']}")

print("=== 3. Recomendación óptica vs radar ===")
rec = get_observation_recommendation(geometry, scene_date)
print(f"  satellite={rec['satellite']} cloud={rec['cloud_cover']}")
print(f"  mensaje: {rec['message']}")
