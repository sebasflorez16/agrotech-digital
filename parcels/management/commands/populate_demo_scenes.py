"""
Comando para poblar escenas de demostración cuando EOSDA ha excedido el límite.

Uso:
    python manage.py populate_demo_scenes
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
import random
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Poblar escenas de demostración para pruebas cuando EOSDA ha excedido el límite'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Número de días hacia atrás para generar escenas (default: 90)'
        )

    def handle(self, *args, **options):
        from parcels.models import Parcel, ParcelSceneCache
        
        days_back = options['days']
        
        self.stdout.write(self.style.NOTICE(f'🛰️ Poblando escenas de demostración para los últimos {days_back} días...'))
        
        # Obtener todas las parcelas con EOSDA ID
        parcels = Parcel.objects.filter(is_deleted=False, eosda_id__isnull=False)
        
        if not parcels.exists():
            self.stdout.write(self.style.WARNING('⚠️ No hay parcelas con EOSDA ID configurado'))
            return
        
        total_scenes = 0
        
        for parcel in parcels:
            self.stdout.write(f'   Procesando parcela: {parcel.name} (EOSDA: {parcel.eosda_id})')
            
            # Generar escenas cada ~5 días (frecuencia típica de Sentinel-2)
            current_date = timezone.now().date()
            start_date = current_date - timedelta(days=days_back)
            
            scene_date = start_date
            parcel_scenes = 0
            
            while scene_date <= current_date:
                # Generar view_id único para cada escena
                view_id = f"S2_{parcel.eosda_id}_{scene_date.strftime('%Y%m%d')}_{random.randint(1000, 9999)}"
                
                # Nubosidad aleatoria (pero realista - más probabilidad de nubes bajas)
                cloud_coverage = random.choices(
                    [random.uniform(0, 15), random.uniform(15, 35), random.uniform(35, 60), random.uniform(60, 90)],
                    weights=[0.4, 0.3, 0.2, 0.1]
                )[0]
                
                try:
                    scene, created = ParcelSceneCache.objects.update_or_create(
                        parcel=parcel,
                        scene_id=view_id,
                        index_type='NDVI',
                        defaults={
                            'date': scene_date,
                            'metadata': {
                                'cloudCoverage': round(cloud_coverage, 2),
                                'satellite': 'sentinel2',
                                'demo': True  # Marcar como escena de demo
                            },
                            'raw_response': {
                                'view_id': view_id,
                                'date': scene_date.isoformat(),
                                'cloudCoverage': round(cloud_coverage, 2),
                                'data_source': 'sentinel2',
                                'demo': True
                            },
                            'expires_at': timezone.now() + timedelta(days=365)  # No expira pronto
                        }
                    )
                    
                    if created:
                        parcel_scenes += 1
                        total_scenes += 1
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   ❌ Error creando escena: {e}'))
                
                # Avanzar 5 días (frecuencia típica de Sentinel-2)
                scene_date += timedelta(days=5)
            
            self.stdout.write(self.style.SUCCESS(f'   ✅ {parcel_scenes} escenas creadas para {parcel.name}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS(f'🎉 {total_scenes} escenas de demostración creadas'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('⚠️ NOTA: Estas son escenas de DEMO.'))
        self.stdout.write('   Las imágenes NDVI/NDMI reales requerirán que EOSDA')
        self.stdout.write('   restablezca el límite de requests (1ro del mes)')
        self.stdout.write('   o que actualices tu plan en api-connect.eos.com')
