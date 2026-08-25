"""
Comparación REAL: EOSDA vs Sentinel-2 gratis (Planetary Computer).

Ejercicio de validación honesta (sin copiar datos de un lado a otro):
- Crea el polígono, lo sincroniza a EOSDA (crea "field").
- EOSDA: busca escena con poca nubosidad y genera la imagen NDVI.
- Sentinel-2 gratis: busca su propia escena y genera su imagen NDVI.
- Guarda ambos PNG y escribe un documento con los datos reales de cada lado.
"""
import os
import sys
import json
import time
import base64
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django
django.setup()

import requests
from django.conf import settings

from parcels.sentinel2 import get_index_images, get_index_statistics, search_sentinel2_scenes

EOSDA_BASE = "https://api-connect.eos.com"
EOSDA_HEADERS = {"x-api-key": settings.EOSDA_API_KEY, "Content-Type": "application/json"}
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "comparison_output")
os.makedirs(OUT_DIR, exist_ok=True)

GEOMETRY = {
    "type": "Polygon",
    "coordinates": [[
        [-73.40, 4.10], [-73.38, 4.10],
        [-73.38, 4.12], [-73.40, 4.12],
        [-73.40, 4.10],
    ]],
}
SCENE_DATE = "2026-08-02"
DATE_START = "2026-07-01"
DATE_END = "2026-08-15"

resultados = {}


def log(msg):
    print(msg)


def eosda_create_field(geometry):
    payload = {
        "type": "Feature",
        "properties": {"name": "Comparacion NDVI EOSDA vs S2"},
        "geometry": geometry,
    }
    r = requests.post(f"{EOSDA_BASE}/field-management", headers=EOSDA_HEADERS, json=payload, timeout=60)
    log(f"[EOSDA field] status={r.status_code} resp={r.text[:300]}")
    if r.status_code in (200, 201):
        return r.json().get("id")
    return None


def eosda_search_scenes(field_id):
    payload = {"params": {"date_start": DATE_START, "date_end": DATE_END, "data_source": ["sentinel2"]}}
    r = requests.post(f"{EOSDA_BASE}/scene-search/for-field/{field_id}", headers=EOSDA_HEADERS, json=payload, timeout=60)
    log(f"[EOSDA scenes POST] status={r.status_code} resp={r.text[:200]}")
    req_id = None
    try:
        req_id = r.json().get("request_id")
    except Exception:
        pass
    if not req_id:
        # a veces la respuesta trae escenas directo
        try:
            return r.json().get("scenes") or r.json().get("results") or []
        except Exception:
            return []

    for attempt in range(12):
        time.sleep(3)
        rr = requests.get(
            f"{EOSDA_BASE}/scene-search/for-field/{field_id}/{req_id}",
            headers={"x-api-key": settings.EOSDA_API_KEY}, timeout=60,
        )
        if rr.status_code == 200:
            data = rr.json()
            scenes = data.get("result") or data.get("scenes") or data.get("results") or data.get("data") or []
            if scenes:
                return scenes
        log(f"[EOSDA scenes poll {attempt+1}] status={rr.status_code} resp={rr.text[:150]}")
    return []


def eosda_generate_ndvi_image(field_id, view_id):
    payload = {"params": {"view_id": view_id, "index": "NDVI", "format": "png"}}
    r = requests.post(f"{EOSDA_BASE}/field-imagery/indicies/{field_id}", headers=EOSDA_HEADERS, json=payload, timeout=60)
    log(f"[EOSDA image POST] status={r.status_code} resp={r.text[:200]}")
    req_id = None
    try:
        req_id = r.json().get("request_id")
    except Exception:
        pass
    if not req_id:
        return None

    for attempt in range(20):
        time.sleep(3)
        rr = requests.get(
            f"{EOSDA_BASE}/field-imagery/{field_id}/{req_id}",
            headers={"x-api-key": settings.EOSDA_API_KEY}, timeout=60,
        )
        ct = rr.headers.get("Content-Type", "")
        if ct.startswith("image/") or rr.content[:8] == b"\x89PNG\r\n\x1a\n":
            return rr.content
        try:
            j = rr.json()
            if j.get("status") not in ("created", "in_progress", "processing", None):
                log(f"[EOSDA image poll {attempt+1}] resp={j}")
        except Exception:
            pass
        if rr.status_code not in (200, 202):
            log(f"[EOSDA image poll {attempt+1}] status={rr.status_code} resp={rr.text[:150]}")
    return None


def save_png(data, path):
    with open(path, "wb") as f:
        f.write(data)
    log(f"PNG guardado: {path} ({len(data)} bytes)")


def main():
    # ═══════ EOSDA ═══════
    log("=== EOSDA ===")
    field_id = eosda_create_field(GEOMETRY)
    resultados["eosda_field_id"] = field_id
    log(f"field_id: {field_id}")

    eosda_scenes = []
    if field_id:
        eosda_scenes = eosda_search_scenes(field_id)
        log(f"Escenas EOSDA: {len(eosda_scenes)}")
        for s in eosda_scenes[:5]:
            log(f"  {s}")

    eosda_best = None
    eosda_image = None
    if eosda_scenes:
        # elegir menor nubosidad
        def cloud_of(s):
            return s.get("cloud", s.get("cloudCoverage", s.get("cloud_cover", s.get("properties", {}).get("cloudCoverage", 100))))
        # Comparación justa: priorizar la MISMA escena que usa Sentinel-2 (SCENE_DATE)
        same_date = [s for s in eosda_scenes if s.get("date") == SCENE_DATE]
        pool = same_date if same_date else eosda_scenes
        eosda_best = min(pool, key=lambda s: (cloud_of(s) if cloud_of(s) is not None else 100))
        view_id = eosda_best.get("view_id") or eosda_best.get("id") or eosda_best.get("scene_id")
        log(f"Mejor escena EOSDA: date={eosda_best.get('date')} cloud={cloud_of(eosda_best)} view_id={view_id}")
        resultados["eosda_scene"] = {
            "date": eosda_best.get("date"),
            "cloudCoverage": cloud_of(eosda_best),
            "view_id": view_id,
        }
        if view_id:
            eosda_image = eosda_generate_ndvi_image(field_id, view_id)

    if eosda_image:
        save_png(eosda_image, os.path.join(OUT_DIR, "eosda_ndvi.png"))
        resultados["eosda_image_bytes"] = len(eosda_image)
    else:
        resultados["eosda_image_bytes"] = 0

    # ═══════ Sentinel-2 gratis ═══════
    log("=== Sentinel-2 gratis ===")
    s2_scenes = search_sentinel2_scenes(GEOMETRY, SCENE_DATE, max_results=5)
    s2_best = s2_scenes[0] if s2_scenes else None
    resultados["s2_scenes"] = [
        {"date": s["date"], "cloud_cover": round(s["cloud_cover"], 2) if s["cloud_cover"] is not None else None}
        for s in s2_scenes
    ]
    log(f"Mejor escena S2: {s2_best}")

    s2_images = get_index_images(GEOMETRY, SCENE_DATE)
    if s2_images and "ndvi" in s2_images:
        ndvi_png = base64.b64decode(s2_images["ndvi"])
        save_png(ndvi_png, os.path.join(OUT_DIR, "sentinel2_ndvi.png"))
        resultados["s2_image_bytes"] = len(ndvi_png)
    else:
        resultados["s2_image_bytes"] = 0

    s2_stats = get_index_statistics(GEOMETRY, SCENE_DATE)
    resultados["s2_ndvi_stats"] = s2_stats.get("ndvi") if s2_stats else None

    # ═══════ Documento ═══════
    doc_path = os.path.join(OUT_DIR, "RESULTADOS.md")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("# Comparación NDVI: EOSDA vs Sentinel-2 (Planetary Computer)\n\n")
        f.write(f"- Polígono: {json.dumps(GEOMETRY['coordinates'][0])}\n")
        f.write(f"- Rango de fechas: {DATE_START} a {DATE_END}\n\n")

        f.write("## EOSDA (pago)\n")
        f.write(f"- field_id: {resultados.get('eosda_field_id')}\n")
        esc = resultados.get("eosda_scene")
        if esc:
            f.write(f"- Escena: {esc.get('date')} · nubosidad {esc.get('cloudCoverage')}% · view_id {esc.get('view_id')}\n")
        f.write(f"- Imagen NDVI: {resultados.get('eosda_image_bytes')} bytes (eosda_ndvi.png)\n\n")

        f.write("## Sentinel-2 gratis (Planetary Computer)\n")
        if s2_best:
            f.write(f"- Escena: {s2_best['date']} · nubosidad {s2_best['cloud_cover']}% · id {s2_best['id']}\n")
        f.write(f"- Imagen NDVI: {resultados.get('s2_image_bytes')} bytes (sentinel2_ndvi.png)\n")
        st = resultados.get("s2_ndvi_stats")
        if st:
            f.write(f"- NDVI mean={st['mean']} min={st['min']} max={st['max']} std={st['std']}\n")
        f.write("\n## Escenas disponibles (S2 gratis, ordenadas por nubosidad)\n")
        for s in resultados.get("s2_scenes", []):
            f.write(f"- {s['date']} · {s['cloud_cover']}%\n")

    log(f"Documento: {doc_path}")
    log("=== FIN ===")


if __name__ == "__main__":
    main()
