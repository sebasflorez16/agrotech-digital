"""
Management command para optimizar índices de base de datos.

Uso:
    python manage.py optimize_database_indexes
"""
from django.core.management.base import BaseCommand
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Optimiza índices de base de datos y sugiere mejoras'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Aplicar optimizaciones sugeridas',
        )
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='Analizar tablas después de optimizar',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Analizando base de datos...'))
        
        # Índices sugeridos para modelos críticos
        suggested_indexes = self._get_suggested_indexes()
        
        if options['apply']:
            self.stdout.write(self.style.WARNING('⚙️  Aplicando optimizaciones...'))
            self._apply_optimizations(suggested_indexes)
        else:
            self.stdout.write(self.style.NOTICE('📊 Modo análisis (usa --apply para aplicar cambios)'))
            self._show_suggestions(suggested_indexes)
        
        if options['analyze']:
            self.stdout.write(self.style.SUCCESS('📈 Analizando tablas...'))
            self._analyze_tables()
        
        self.stdout.write(self.style.SUCCESS('✅ Optimización completada'))

    def _get_suggested_indexes(self):
        """Retorna índices sugeridos basados en queries comunes."""
        return [
            # Parcels
            {
                'table': 'parcels_parcel',
                'name': 'idx_parcel_manager_deleted',
                'columns': ['manager_id', 'is_deleted'],
                'reason': 'Filtrado común por manager y estado de eliminación'
            },
            {
                'table': 'parcels_parcel',
                'name': 'idx_parcel_eosda_id',
                'columns': ['eosda_id'],
                'reason': 'Búsquedas frecuentes por EOSDA ID',
                'unique': True
            },
            {
                'table': 'parcels_cachedatoseosda',
                'name': 'idx_cache_parcel_tipo_hash',
                'columns': ['parcel_id', 'tipo_dato', 'hash_parametros'],
                'reason': 'Búsqueda de cache por parcela y parámetros'
            },
            {
                'table': 'parcels_cachedatoseosda',
                'name': 'idx_cache_expira_en',
                'columns': ['expira_en'],
                'reason': 'Limpieza de cache expirado'
            },
            
            # Crops
            {
                'table': 'crop_crop',
                'name': 'idx_crop_parcel_deleted',
                'columns': ['parcel_id', 'is_deleted'],
                'reason': 'Listado de cultivos por parcela activos'
            },
            {
                'table': 'crop_crop',
                'name': 'idx_crop_sowing_date',
                'columns': ['sowing_date'],
                'reason': 'Ordenamiento por fecha de siembra'
            },
            
            # Labores
            {
                'table': 'labores_labor',
                'name': 'idx_labor_estado_fecha',
                'columns': ['estado', 'fecha_programada'],
                'reason': 'Filtrado de labores pendientes por fecha'
            },
            
            # Inventario
            {
                'table': 'inventario_supply',
                'name': 'idx_supply_quantity',
                'columns': ['quantity'],
                'reason': 'Alertas de stock bajo'
            },
            
            # Users
            {
                'table': 'users_user',
                'name': 'idx_user_role_active',
                'columns': ['role', 'is_active'],
                'reason': 'Filtrado de usuarios por rol y estado'
            },
            {
                'table': 'users_user',
                'name': 'idx_user_email',
                'columns': ['email'],
                'reason': 'Login por email',
                'unique': True
            },
        ]

    def _show_suggestions(self, indexes):
        """Muestra sugerencias de optimización."""
        self.stdout.write('\n📋 Índices sugeridos:\n')
        
        for idx in indexes:
            self.stdout.write(f"\n  Tabla: {idx['table']}")
            self.stdout.write(f"  Nombre: {idx['name']}")
            self.stdout.write(f"  Columnas: {', '.join(idx['columns'])}")
            self.stdout.write(f"  Razón: {idx['reason']}")
            
            # Verificar si ya existe
            exists = self._check_index_exists(idx['table'], idx['name'])
            if exists:
                self.stdout.write(self.style.SUCCESS('  ✅ Ya existe'))
            else:
                self.stdout.write(self.style.WARNING('  ⚠️  No existe'))

    def _apply_optimizations(self, indexes):
        """Aplica los índices sugeridos."""
        with connection.cursor() as cursor:
            for idx in indexes:
                if self._check_index_exists(idx['table'], idx['name']):
                    self.stdout.write(f"  ⏭️  Saltando {idx['name']} (ya existe)")
                    continue
                
                # Construir SQL para crear índice
                unique = 'UNIQUE ' if idx.get('unique', False) else ''
                columns = ', '.join(idx['columns'])
                sql = f"""
                    CREATE {unique}INDEX CONCURRENTLY IF NOT EXISTS {idx['name']}
                    ON {idx['table']} ({columns})
                """
                
                try:
                    self.stdout.write(f"  🔨 Creando índice {idx['name']}...")
                    cursor.execute(sql)
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Creado: {idx['name']}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ Error: {e}"))

    def _check_index_exists(self, table_name, index_name):
        """Verifica si un índice existe."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 1
                FROM pg_indexes
                WHERE tablename = %s AND indexname = %s
            """, [table_name, index_name])
            return cursor.fetchone() is not None

    def _analyze_tables(self):
        """Ejecuta ANALYZE en tablas principales."""
        tables = [
            'parcels_parcel',
            'parcels_cachedatoseosda',
            'crop_crop',
            'labores_labor',
            'inventario_supply',
            'users_user',
        ]
        
        with connection.cursor() as cursor:
            for table in tables:
                try:
                    self.stdout.write(f"  Analizando {table}...")
                    cursor.execute(f"ANALYZE {table}")
                    self.stdout.write(self.style.SUCCESS(f"  ✅ {table}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ {table}: {e}"))
