"""
Fusion Engine for AgroTech Digital — Monitoreo Continuo Fase 5.
Combines Sentinel-2 (optical), Sentinel-1 (radar), weather, and field records
into a unified crop state assessment.
"""

import logging
from datetime import date, timedelta
from .models import CropHealthStatus

logger = logging.getLogger(__name__)


class CropStateEngine:
    """
    Motor de estado del cultivo — fusiona multiples fuentes de datos
    para mantener una evaluacion continua de la salud del cultivo.

    Fuentes combinadas:
    1. Sentinel-2 (optico) — NDVI/NDMI/EVI via EOSDA API
    2. Sentinel-1 (radar) — deteccion de cambios via Copernicus
    3. Clima — precipitacion, temperatura via EOSDA Weather
    4. Registros de campo — labores, siembra, fertilizacion

    El agricultor ve solo el resultado final: un badge y recomendaciones.
    """

    @staticmethod
    def assess(parcel, weather_data=None):
        """
        Realiza una evaluacion completa del estado del cultivo.
        Combina datos opticos, radar, clima y registros de campo.

        Args:
            parcel: Parcel instance
            weather_data: dict with weather metrics (optional)

        Returns:
            dict with assessment results
        """
        health = CropHealthStatus.get_or_create_for_parcel(parcel)
        assessment = {
            'parcel_id': parcel.id,
            'parcel_name': parcel.name,
            'optical_status': CropStateEngine._assess_optical(health),
            'radar_status': CropStateEngine._assess_radar(parcel),
            'weather_context': CropStateEngine._assess_weather(weather_data),
            'overall_status': None,
            'recommendations': [],
        }

        # Determine overall status
        assessment['overall_status'] = CropStateEngine._determine_overall(assessment)
        assessment['recommendations'] = CropStateEngine._generate_recommendations(assessment)

        return assessment

    @staticmethod
    def _assess_optical(health):
        """Assess based on last known optical indices."""
        if not health.ndvi_last:
            return {'status': 'unknown', 'message': 'Sin datos opticos disponibles', 'confidence': 0}

        ndvi = health.ndvi_last
        if ndvi > 0.7:
            status = 'healthy'
            message = f'Cultivo saludable (NDVI: {ndvi:.2f})'
        elif ndvi > 0.5:
            status = 'moderate'
            message = f'Cultivo en estado moderado (NDVI: {ndvi:.2f})'
        elif ndvi > 0.3:
            status = 'stressed'
            message = f'Cultivo con posible estres (NDVI: {ndvi:.2f})'
        else:
            status = 'critical'
            message = f'Cultivo en estado critico (NDVI: {ndvi:.2f})'

        return {
            'status': status,
            'message': message,
            'confidence': health.confidence_score,
            'ndvi': ndvi,
            'days_since_observation': health.days_without_observation,
        }

    @staticmethod
    def _assess_radar(parcel):
        """Assess based on Sentinel-1 radar data (if available)."""
        try:
            from .sentinel1 import get_crop_status_from_radar
            if parcel.geom:
                radar = get_crop_status_from_radar(parcel.geom, days_back=30)
                return radar
        except ImportError:
            logger.debug("[FUSION] Sentinel-1 module not available")
        except Exception as e:
            logger.warning(f"[FUSION] Radar assessment error: {e}")

        return {'radar_status': 'unavailable', 'message': 'Modulo radar no disponible'}

    @staticmethod
    def _assess_weather(weather_data):
        """Assess recent weather conditions."""
        if not weather_data:
            return {'status': 'unknown', 'message': 'Sin datos climaticos'}

        total_rain = weather_data.get('total_precipitation', 0)
        avg_temp = weather_data.get('avg_temperature', 25)
        days_rain = weather_data.get('days_with_rain', 0)

        if total_rain < 50:
            rain_status = 'dry'
            rain_msg = 'Periodo seco — considerar riego'
        elif total_rain > 300:
            rain_status = 'wet'
            rain_msg = 'Precipitacion abundante — monitorear drenaje'
        else:
            rain_status = 'normal'
            rain_msg = 'Precipitacion dentro de rangos normales'

        return {
            'status': rain_status,
            'message': rain_msg,
            'total_rain_mm': total_rain,
            'avg_temp_c': round(avg_temp, 1),
            'days_with_rain': days_rain,
        }

    @staticmethod
    def _determine_overall(assessment):
        """Determine the overall crop status by fusing all sources."""
        optical = assessment['optical_status']
        radar = assessment['radar_status']
        weather = assessment['weather_context']

        # Optical is the primary source
        if optical['status'] == 'critical':
            return {'level': 'critical', 'emoji': '🔴', 'label': 'Critico',
                    'message': 'Se requiere atencion inmediata. NDVI critico.'}

        if optical['status'] == 'stressed':
            if radar.get('change_detected'):
                return {'level': 'warning', 'emoji': '🟠', 'label': 'Alerta',
                        'message': 'Estres detectado por optico y cambio confirmado por radar.'}
            return {'level': 'warning', 'emoji': '🟡', 'label': 'Atencion',
                    'message': 'Posible estres en el cultivo. Monitorear.'}

        if optical['status'] == 'moderate':
            return {'level': 'moderate', 'emoji': '🟡', 'label': 'Moderado',
                    'message': 'Cultivo en estado moderado. Continuar monitoreo.'}

        if optical['status'] == 'healthy':
            if weather.get('status') == 'dry':
                return {'level': 'good', 'emoji': '🟢', 'label': 'Saludable',
                        'message': 'Cultivo saludable pero clima seco. Mantener riego.'}
            return {'level': 'excellent', 'emoji': '🟢', 'label': 'Excelente',
                    'message': 'Cultivo en optimas condiciones.'}

        return {'level': 'unknown', 'emoji': '⚪', 'label': 'Desconocido',
                'message': 'Datos insuficientes para evaluacion.'}

    @staticmethod
    def _generate_recommendations(assessment):
        """Generate actionable recommendations based on assessment."""
        recs = []
        optical = assessment['optical_status']
        weather = assessment['weather_context']
        radar = assessment['radar_status']

        if optical['status'] in ('critical', 'stressed'):
            recs.append('Realizar inspeccion en campo para verificar estado del cultivo.')
            recs.append('Considerar analisis de suelo para descartar deficiencias nutricionales.')

        if weather.get('status') == 'dry':
            recs.append('Programar riego suplementario — baja precipitacion acumulada.')

        if weather.get('status') == 'wet' and optical.get('ndvi') and optical['ndvi'] < 0.5:
            recs.append('Verificar drenaje — exceso de humedad puede estar afectando el cultivo.')

        if radar.get('change_detected'):
            recs.append(f"Cambio detectado por radar: {radar.get('change_info', {}).get('interpretation', '')}")

        if optical.get('days_since_observation', 0) > 14:
            recs.append('Sin observacion optica reciente — los datos pueden estar desactualizados.')

        if not recs:
            recs.append('No se requieren acciones inmediatas. Continuar monitoreo regular.')

        return recs[:6]  # Max 6 recommendations


def quick_assessment(parcel):
    """
    Convenience function for quick crop assessment.
    Returns a simple dict suitable for API responses.
    """
    engine = CropStateEngine()
    return engine.assess(parcel)