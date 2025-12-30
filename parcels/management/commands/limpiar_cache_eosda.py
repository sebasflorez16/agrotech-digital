"""
Comando Django para limpiar caché EOSDA expirado
Ejecutar con: python manage.py limpiar_cache_eosda

Para automatizar, agregar a crontab:
0 2 * * * cd /ruta/proyecto && python manage.py limpiar_cache_eosda
(Ejecuta diariamente a las 2 AM)
"""

from django.core.management.base import BaseCommand
from parcels.models import CacheDatosEOSDA, EstadisticaUsoEOSDA


class Command(BaseCommand):
    help = 'Limpia cachés EOSDA expirados y muestra estadísticas'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Mostrar estadísticas detalladas',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🧹 Iniciando limpieza de caché EOSDA...'))
        
        # Limpiar expirados
        eliminados = CacheDatosEOSDA.limpiar_expirados()
        
        if eliminados > 0:
            self.stdout.write(self.style.SUCCESS(f'✅ {eliminados} cachés expirados eliminados'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ No hay cachés expirados'))
        
        # Estadísticas actuales
        total_cache = CacheDatosEOSDA.objects.count()
        self.stdout.write(f'📊 Cachés activos: {total_cache}')
        
        if options['stats']:
            self._mostrar_estadisticas_detalladas()
    
    def _mostrar_estadisticas_detalladas(self):
        """Muestra estadísticas detalladas de uso"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.HTTP_INFO('📈 ESTADÍSTICAS DETALLADAS EOSDA'))
        self.stdout.write('='*50 + '\n')
        
        # Caché por índice
        self.stdout.write(self.style.HTTP_INFO('Caché por índice:'))
        for indice in ['NDVI', 'NDMI', 'SAVI', 'EVI']:
            count = CacheDatosEOSDA.objects.filter(indice=indice).count()
            self.stdout.write(f'  {indice}: {count} items')
        
        # Métricas del mes
        metricas = EstadisticaUsoEOSDA.obtener_metricas_mes_actual()
        
        self.stdout.write('\n' + self.style.HTTP_INFO('Métricas del mes actual:'))
        self.stdout.write(f'  Total requests: {metricas["total_requests"]}')
        self.stdout.write(f'  Desde caché: {metricas["requests_cache"]} ({metricas["tasa_cache"]}%)')
        self.stdout.write(f'  A API: {metricas["requests_api"]}')
        self.stdout.write(f'  Errores: {metricas["errores"]}')
        self.stdout.write(f'  Tiempo promedio: {metricas["tiempo_promedio_ms"]}ms')
        
        # Interpretación
        self.stdout.write('\n' + self.style.HTTP_INFO('Interpretación:'))
        tasa = metricas["tasa_cache"]
        if tasa >= 80:
            self.stdout.write(self.style.SUCCESS(f'  ✅ Excelente optimización ({tasa}% caché)'))
        elif tasa >= 50:
            self.stdout.write(self.style.WARNING(f'  ⚠️  Optimización moderada ({tasa}% caché)'))
        else:
            self.stdout.write(self.style.ERROR(f'  ❌ Baja optimización ({tasa}% caché)'))
        
        # Ahorro estimado
        requests_ahorrados = metricas["requests_cache"]
        ahorro_estimado = requests_ahorrados * 0.05  # Asumiendo $0.05 por request
        self.stdout.write(f'\n💰 Ahorro estimado este mes: ${ahorro_estimado:.2f} USD')
        self.stdout.write('='*50)
