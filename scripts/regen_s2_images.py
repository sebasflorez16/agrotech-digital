"""Regenera las imágenes de índice en resolución nativa y muestra sus dimensiones."""
import os
import sys
import base64
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django
django.setup()

from PIL import Image
from parcels.sentinel2 import get_index_images, get_index_statistics

geometry = {
    "type": "Polygon",
    "coordinates": [[
        [-73.40, 4.10], [-73.38, 4.10],
        [-73.38, 4.12], [-73.40, 4.12],
        [-73.40, 4.10],
    ]],
}
scene_date = "2026-08-02"
out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "comparison_output")

images = get_index_images(geometry, scene_date)
if not images:
    print("SIN IMÁGENES")
else:
    for name, b64 in images.items():
        data = base64.b64decode(b64)
        img = Image.open(io.BytesIO(data))
        path = os.path.join(out_dir, f"sentinel2_{name}.png")
        with open(path, "wb") as f:
            f.write(data)
        print(f"{name}: {img.size[0]}x{img.size[1]} px ({len(data)} bytes) -> {path}")

stats = get_index_statistics(geometry, scene_date)
print("NDVI stats:", stats.get("ndvi") if stats else None)
