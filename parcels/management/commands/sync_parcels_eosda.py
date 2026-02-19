"""
Comando para sincronizar parcelas existentes con EOSDA.

Uso:
    python manage.py sync_parcels_eosda
    
Este comando:
1. Obtiene todas las parcelas que no tienen eosda_id o tienen uno inválido
2. Crea el campo correspondiente en EOSDA
3. Actualiza el eosda_id en la base de datos local
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import json
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza las parcelas existentes con EOSDA (crea campos y actualiza eosda_id)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar resincronización de todas las parcelas (incluso las que ya tienen eosda_id)',
        )
        parser.add_argument(
            '--parcel-id',
            type=int,
            help='Sincronizar solo una parcela específica por su ID',
        )

    def handle(self, *args, **options):
        from parcels.models import Parcel
        
        self.stdout.write(self.style.NOTICE('🔄 Sincronizando parcelas con EOSDA...'))
        self.stdout.write(f'   API Key: {settings.EOSDA_API_KEY[:20]}...')
        
        # Filtrar parcelas
        parcels = Parcel.objects.filter(is_deleted=False)
        
        if options['parcel_id']:
            parcels = parcels.filter(pk=options['parcel_id'])
            self.stdout.write(f'   Sincronizando solo parcela ID: {options["parcel_id"]}')
        elif not options['force']:
            # Solo parcelas sin eosda_id válido
            parcels = parcels.filter(eosda_id__isnull=True) | parcels.filter(eosda_id='')
            self.stdout.write('   Sincronizando parcelas sin eosda_id...')
        else:
            self.stdout.write('   FORZANDO resincronización de TODAS las parcelas...')
        
        if not parcels.exists():
            self.stdout.write(self.style.WARNING('⚠️ No hay parcelas para sincronizar'))
            
            # Verificar si hay parcelas con eosda_id que pueden estar desactualizadas
            all_parcels = Parcel.objects.filter(is_deleted=False)
            if all_parcels.exists():
                self.stdout.write('')
                self.stdout.write('   Parcelas existentes con eosda_id:')
                for p in all_parcels[:5]:
                    self.stdout.write(f'      - {p.name} (ID: {p.id}, EOSDA: {p.eosda_id})')
                self.stdout.write('')
                self.stdout.write('   💡 Usa --force para resincronizar todas las parcelas')
            return
        
        success_count = 0
        error_count = 0
        
        for parcel in parcels:
            self.stdout.write(f'\n   Procesando: {parcel.name} (ID: {parcel.id})')
            
            # Verificar que tiene geometría
            geom = parcel.geom
            if not geom:
                self.stdout.write(self.style.WARNING(f'      ⚠️ Sin geometría, saltando...'))
                continue
            
            try:
                # Preparar GeoJSON para EOSDA
                if hasattr(geom, 'geojson'):
                    # Si es un objeto GEOSGeometry de Django
                    geojson = json.loads(geom.geojson)
                elif isinstance(geom, dict):
                    geojson = geom
                else:
                    geojson = json.loads(str(geom))
                
                # Crear campo en EOSDA usando el endpoint correcto
                # Documentación: https://doc.eos.com/docs/field-management-api/field-management/
                eosda_url = "https://api-connect.eos.com/field-management"
                headers = {
                    "x-api-key": settings.EOSDA_API_KEY,
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "type": "Feature",
                    "properties": {
                        "name": parcel.name or f"Parcela {parcel.id}",
                    },
                    "geometry": geojson
                }
                
                self.stdout.write(f'      Enviando a EOSDA...')
                
                response = requests.post(eosda_url, json=payload, headers=headers)
                
                if response.status_code == 201:
                    data = response.json()
                    new_eosda_id = data.get('id')
                    
                    if new_eosda_id:
                        old_id = parcel.eosda_id
                        parcel.eosda_id = str(new_eosda_id)
                        parcel.save(update_fields=['eosda_id'])
                        
                        self.stdout.write(self.style.SUCCESS(
                            f'      ✅ Creado en EOSDA: {new_eosda_id} (anterior: {old_id})'
                        ))
                        success_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(
                            f'      ❌ Respuesta sin ID: {data}'
                        ))
                        error_count += 1
                        
                elif response.status_code == 400:
                    # Puede ser que el campo ya existe con esta geometría
                    error_data = response.json()
                    self.stdout.write(self.style.WARNING(
                        f'      ⚠️ Error 400: {error_data}'
                    ))
                    
                    # Intentar buscar campo existente
                    if 'already exists' in str(error_data).lower():
                        self.stdout.write('      Intentando buscar campo existente...')
                        # TODO: Implementar búsqueda de campo existente
                    error_count += 1
                    
                elif response.status_code == 402:
                    self.stdout.write(self.style.ERROR(
                        f'      ❌ Límite de API excedido. Deteniendo sincronización.'
                    ))
                    break
                    
                else:
                    self.stdout.write(self.style.ERROR(
                        f'      ❌ Error {response.status_code}: {response.text}'
                    ))
                    error_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'      ❌ Excepción: {str(e)}'
                ))
                error_count += 1
        
        # Resumen
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('📊 Resumen de sincronización'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'   ✅ Exitosas: {success_count}')
        self.stdout.write(f'   ❌ Errores: {error_count}')
        self.stdout.write('')
        
        if success_count > 0:
            self.stdout.write(self.style.SUCCESS(
                '🎉 Las parcelas sincronizadas ahora pueden usar imágenes satelitales EOSDA'
            ))
