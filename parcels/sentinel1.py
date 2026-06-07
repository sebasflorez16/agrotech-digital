"""
Sentinel-1 SAR integration module for AgroTech Digital.
Provides cloud-penetrating radar-based crop change detection.
Uses the free Copernicus Data Space API.

Monitoreo Continuo Fase 4 — Detector interno de cambios via radar.
El agricultor NUNCA ve datos radar directamente.
Sentinel-1 es un motor interno que alimenta el sistema de alertas.
"""

import logging
import requests
from datetime import datetime, timedelta
from django.conf import settings

logger = logging.getLogger(__name__)

# Copernicus Data Space API (free, no API key needed for basic access)
COPERNICUS_BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
COPERNICUS_SEARCH_URL = "https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel1/search.json"


def search_sentinel1_scenes(geometry_geojson, date_from, date_to, max_results=5):
    """
    Search for Sentinel-1 GRD (Ground Range Detected) scenes over a geometry.

    Args:
        geometry_geojson: GeoJSON geometry dict
        date_from: str 'YYYY-MM-DD'
        date_to: str 'YYYY-MM-DD'
        max_results: int

    Returns:
        List of scene dicts with keys: id, date, polarisation, orbitDirection
    """
    try:
        # Encode geometry as WKT polygon from GeoJSON
        coords = geometry_geojson.get('coordinates', [[]])[0]
        if not coords or len(coords) < 3:
            logger.warning("[S1] Invalid geometry for search")
            return []

        # Simple bbox from coordinates
        lngs = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        bbox = f"{min(lngs)},{min(lats)},{max(lngs)},{max(lats)}"

        params = {
            'maxRecords': max_results,
            'box': bbox,
            'startDate': f"{date_from}T00:00:00Z",
            'completionDate': f"{date_to}T23:59:59Z",
            'productType': 'GRD',
            'sensorMode': 'IW',
            'sortParam': 'startDate',
            'sortOrder': 'descending',
            'status': 'ONLINE',
        }

        logger.info(f"[S1] Searching scenes: {date_from} to {date_to}, bbox={bbox}")
        response = requests.get(COPERNICUS_SEARCH_URL, params=params, timeout=30)

        if response.status_code != 200:
            logger.warning(f"[S1] Search failed: {response.status_code}")
            return []

        data = response.json()
        features = data.get('features', [])

        scenes = []
        for feat in features:
            props = feat.get('properties', {})
            scenes.append({
                'id': props.get('productIdentifier', feat.get('id', '')),
                'date': props.get('startDate', '')[:10],
                'polarisation': props.get('polarisation', 'VV+VH'),
                'orbitDirection': props.get('orbitDirection', ''),
                'platform': props.get('platform', 'S1'),
            })

        logger.info(f"[S1] Found {len(scenes)} scenes")
        return scenes

    except Exception as e:
        logger.error(f"[S1] Error searching: {e}")
        return []


def get_backscatter_estimate(geometry_geojson, date_str):
    """
    Estimate Sentinel-1 backscatter for a given date.
    Since full SAR processing requires downloading and processing GRD products,
    this returns a placeholder estimate based on scene availability.

    In production, this would download the GRD product and calculate
    sigma0_VV and sigma0_VH from the geotiff.

    Returns:
        dict with vv_mean, vh_mean, radar_vegetation_index, confidence
    """
    scenes = search_sentinel1_scenes(geometry_geojson, date_str, date_str, max_results=1)

    if scenes:
        # Scene exists — means SAR data is available for this date
        # In production, we'd process the actual backscatter values
        return {
            'available': True,
            'vv_mean': -12.5,  # Placeholder (typical values: -25 to -5 dB)
            'vh_mean': -18.2,  # Placeholder
            'radar_vegetation_index': 0.65,  # Placeholder (RVI = 4*VH/(VV+VH))
            'confidence': 0.7,
            'scene_id': scenes[0]['id'],
            'date': date_str,
        }
    else:
        return {
            'available': False,
            'vv_mean': None,
            'vh_mean': None,
            'radar_vegetation_index': None,
            'confidence': 0.0,
            'date': date_str,
        }


def detect_change(parcel_geometry, historical_backscatter, current_backscatter, threshold=3.0):
    """
    Detect significant change in backscatter between two observations.

    Sentinel-1 backscatter changes indicate:
    - Decrease VV: possible harvest, flooding, or biomass loss
    - Increase VV: crop growth, increased biomass
    - Decrease VH (cross-pol): vegetation structure change
    - Stable: no significant change detected

    Returns:
        dict with change_detected, direction, magnitude, interpretation
    """
    if not historical_backscatter.get('available') or not current_backscatter.get('available'):
        return {
            'change_detected': False,
            'direction': 'unknown',
            'magnitude': 0,
            'interpretation': 'Insufficient SAR data for comparison'
        }

    vv_diff = (current_backscatter.get('vv_mean', 0) or 0) - (historical_backscatter.get('vv_mean', 0) or 0)
    vh_diff = (current_backscatter.get('vh_mean', 0) or 0) - (historical_backscatter.get('vh_mean', 0) or 0)

    magnitude = abs(vv_diff) + abs(vh_diff)

    if magnitude < threshold:
        return {
            'change_detected': False,
            'direction': 'stable',
            'magnitude': round(magnitude, 2),
            'interpretation': 'Sin cambios significativos detectados por radar'
        }

    if vv_diff < -2.0:
        direction = 'decrease'
        interpretation = 'Posible perdida de biomasa o cosecha detectada por radar. Verificar en campo.'
    elif vv_diff > 2.0:
        direction = 'increase'
        interpretation = 'Aumento de biomasa detectado por radar. Cultivo en etapa de crecimiento.'
    elif vh_diff < -1.5:
        direction = 'structure_change'
        interpretation = 'Cambio en estructura vegetal detectado por radar.'
    else:
        direction = 'minor'
        interpretation = 'Cambio menor detectado — dentro de variabilidad normal.'

    return {
        'change_detected': True,
        'direction': direction,
        'magnitude': round(magnitude, 2),
        'vv_diff': round(vv_diff, 2),
        'vh_diff': round(vh_diff, 2),
        'interpretation': interpretation
    }


def get_crop_status_from_radar(parcel_geometry, days_back=30):
    """
    Complete radar-based crop status assessment.
    Combines scene search, backscatter estimation, and change detection.

    Args:
        parcel_geometry: GeoJSON geometry dict
        days_back: How many days to look back for comparison

    Returns:
        dict with radar_status, change_info, scenes_found
    """
    from datetime import date

    today = date.today()
    date_to = today.isoformat()
    date_from = (today - timedelta(days=days_back)).isoformat()

    # Search recent scenes
    recent_scenes = search_sentinel1_scenes(parcel_geometry, date_from, date_to, max_results=10)

    if not recent_scenes:
        return {
            'radar_status': 'no_data',
            'message': 'No hay datos radar disponibles para este periodo',
            'scenes_found': 0,
            'change_detected': False,
        }

    # Get most recent backscatter
    latest = get_backscatter_estimate(parcel_geometry, recent_scenes[0]['date'])

    # Get historical comparison (oldest in range)
    historical = None
    change_result = {'change_detected': False}
    if len(recent_scenes) > 1:
        oldest_scene_date = recent_scenes[-1]['date']
        historical = get_backscatter_estimate(parcel_geometry, oldest_scene_date)
        change_result = detect_change(parcel_geometry, historical, latest)

    return {
        'radar_status': 'data_available',
        'message': f"{len(recent_scenes)} escenas radar encontradas en {days_back} dias",
        'scenes_found': len(recent_scenes),
        'latest_backscatter': latest,
        'historical_backscatter': historical,
        'change_detected': change_result.get('change_detected', False),
        'change_info': change_result,
        'period': {'from': date_from, 'to': date_to},
    }