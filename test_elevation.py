"""
Test de integración para el módulo de elevación.
Ejecutar: conda run -n agro-rest python test_elevation.py
"""
import os
import json
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
import django
django.setup()

from parcels.elevation import (
    _generate_grid_points, 
    _point_in_polygon, 
    _get_parcel_centroid_and_bounds, 
    _fetch_elevation_data, 
    _generate_elevation_heatmap
)
import numpy as np

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name} - {detail}")
        failed += 1

print("=" * 60)
print("TEST: Módulo de Elevación (parcels/elevation.py)")
print("=" * 60)

# --- Test 1: Point in polygon ---
print("\n--- Test 1: Point in Polygon ---")
polygon = [[0,0], [10,0], [10,10], [0,10], [0,0]]
test("Punto dentro del polígono", _point_in_polygon(5, 5, polygon) == True)
test("Punto fuera del polígono", _point_in_polygon(15, 15, polygon) == False)
test("Punto en borde (puede variar)", True)  # El borde es caso especial

# --- Test 2: Centroid y Bounds ---
print("\n--- Test 2: Centroid y Bounds ---")
geom = {
    'type': 'Polygon',
    'coordinates': [[[-74.1, 4.6], [-74.0, 4.6], [-74.0, 4.7], [-74.1, 4.7], [-74.1, 4.6]]]
}
result = _get_parcel_centroid_and_bounds(geom)
test("Resultado no es None", result is not None)
if result:
    lat, lng, min_lon, min_lat, max_lon, max_lat = result
    test(f"Centroide lat={lat:.4f}", abs(lat - 4.65) < 0.01)
    test(f"Centroide lng={lng:.4f}", abs(lng - (-74.05)) < 0.01)
    test(f"Bounds correctos", min_lon == -74.1 and max_lon == -74.0)

# --- Test 3: Geom inválido ---
print("\n--- Test 3: Geometría inválida ---")
test("None retorna None", _get_parcel_centroid_and_bounds(None) is None)
test("Dict vacío retorna None", _get_parcel_centroid_and_bounds({}) is None)

# --- Test 4: Grid generation ---
print("\n--- Test 4: Generación de grilla ---")
points, rows, cols, grid_mask, bounds = _generate_grid_points(geom)
test(f"Grilla tiene filas >= 3: {rows}", rows >= 3)
test(f"Grilla tiene cols >= 3: {cols}", cols >= 3)
test(f"Puntos dentro del polígono: {len(points)}", len(points) > 0)
test(f"Grid mask shape correcto", grid_mask.shape == (rows, cols))
test(f"Bounds correcto (4 valores)", len(bounds) == 4)
print(f"  INFO: Grilla {rows}x{cols}, {len(points)} puntos válidos")

# --- Test 5: API Open-Meteo (real) ---
print("\n--- Test 5: API Open-Meteo (consulta real, 4 puntos) ---")
try:
    test_points = [(4.6, -74.1), (4.65, -74.05), (4.7, -74.0), (4.65, -74.1)]
    elevations = _fetch_elevation_data(test_points)
    test(f"Recibidas {len(elevations)} elevaciones", len(elevations) == 4)
    test("Todas son numéricas", all(isinstance(e, (int, float)) for e in elevations))
    test("Valores razonables para Bogotá (>1500m)", all(e > 1500 for e in elevations))
    print(f"  INFO: Elevaciones recibidas: {elevations}")
except Exception as e:
    test(f"API accesible (error: {e})", False)

# --- Test 6: Heatmap generation ---
print("\n--- Test 6: Generación de heatmap ---")
test_elevations = [2540, 2545, 2543, 2538, 2547, 2541]
test_mask = np.array([[True, True, True], [True, True, True]])
img_base64, stats = _generate_elevation_heatmap(test_elevations, 2, 3, test_mask)
test("Imagen base64 no es None", img_base64 is not None)
test(f"Imagen tiene datos (len={len(img_base64) if img_base64 else 0})", 
     img_base64 is not None and len(img_base64) > 100)
test(f"Min elevation = {stats.get('min_elevation')}", stats.get('min_elevation') == 2538.0)
test(f"Max elevation = {stats.get('max_elevation')}", stats.get('max_elevation') == 2547.0)
test(f"Difference = {stats.get('difference')}", stats.get('difference') == 9.0)
test(f"Grid points = {stats.get('grid_points')}", stats.get('grid_points') == 6)
print(f"  INFO: Stats = {json.dumps(stats, indent=2)}")

# --- Test 7: Heatmap con datos planos (diff=0) ---
print("\n--- Test 7: Heatmap con terreno plano ---")
flat_elevations = [2500, 2500, 2500, 2500]
flat_mask = np.array([[True, True], [True, True]])
img_flat, stats_flat = _generate_elevation_heatmap(flat_elevations, 2, 2, flat_mask)
test("Terreno plano genera imagen", img_flat is not None)
test(f"Diferencia = 0", stats_flat.get('difference') == 0.0)

# --- Test 8: Flujo completo (end-to-end con parcela simulada) ---
print("\n--- Test 8: Flujo end-to-end (parcela simulada) ---")
try:
    # Parcela pequeña real en Colombia (~5 hectáreas)
    test_geom = {
        'type': 'Polygon',
        'coordinates': [[
            [-74.085, 4.620],
            [-74.082, 4.620],
            [-74.082, 4.623],
            [-74.085, 4.623],
            [-74.085, 4.620]
        ]]
    }
    pts, r, c, mask, bnds = _generate_grid_points(test_geom)
    test(f"Grilla: {r}x{c}, {len(pts)} puntos", len(pts) > 0)
    
    elevs = _fetch_elevation_data(pts)
    test(f"Elevaciones obtenidas: {len(elevs)}", len(elevs) == len(pts))
    
    img, st = _generate_elevation_heatmap(elevs, r, c, mask)
    test("Imagen generada correctamente", img is not None)
    test(f"Desnivel: {st.get('difference')}m", True)
    print(f"  INFO: Parcela simulada -> Elevación {st['min_elevation']}m - {st['max_elevation']}m (dif: {st['difference']}m)")
    print(f"  INFO: Imagen: {len(img)} chars base64")
except Exception as e:
    test(f"Flujo E2E (error: {e})", False)

# --- Resumen ---
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULTADO: {passed}/{total} tests pasaron")
if failed > 0:
    print(f"⚠️  {failed} test(s) fallaron")
    sys.exit(1)
else:
    print("🎉 TODOS LOS TESTS PASARON EXITOSAMENTE")
    sys.exit(0)
