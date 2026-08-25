"""Prueba de generación de imágenes de color NDVI/NDMI/SAVI/NDRE (Sentinel-2 real)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django
django.setup()

from parcels.sentinel2 import get_index_images

geometry = {
    "type": "Polygon",
    "coordinates": [[
        [-73.40, 4.10], [-73.38, 4.10],
        [-73.38, 4.13], [-73.40, 4.13],
        [-73.40, 4.10],
    ]],
}

images = get_index_images(geometry, "2026-08-12")
if not images:
    print("SIN IMÁGENES (no se encontró escena)")
else:
    for name, b64 in images.items():
        print(f"{name}: {len(b64)} chars (base64)")
    print("OK - 4 índices renderizados")
