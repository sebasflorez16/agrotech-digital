"""
Seed de variedades profesionales para los cultivos del catálogo.

Datos reales de fichas técnicas públicas:
  - Arroz: Fedearroz (Colombia)
  - Maíz: CIMMYT / ICA
  - Café: Cenicafé (Colombia)
  - Palma: Cenipalma
  - Caña: Cenicaña

Uso:
  python manage.py tenant_command seed_crop_varieties --schema=prueba
"""
from django.core.management.base import BaseCommand
from crop.models import CropCatalog, CropVariety


VARIETIES = {
    # ---------------------------- ARROZ ----------------------------
    'Arroz': [
        {
            'name': 'Fedearroz 67',
            'casa_registradora': 'Fedearroz',
            'pais_origen': 'Colombia', 'year_liberacion': 2014,
            'tipo_variedad': 'mejorada',
            'cycle_days': 125, 'dias_a_floracion': 85, 'dias_a_maduracion': 120,
            'altura_promedio_cm': 95,
            'densidad_siembra_kg_ha': 110, 'distancia_surcos_cm': 20,
            'profundidad_siembra_cm': 3, 'lamina_riego_mm': 850,
            'fertilizacion_npk': '120-60-80 kg/ha',
            'rendimiento_promedio_t_ha': 7.5,
            'rendimiento_conservador_t_ha': 6.0,
            'rendimiento_potencial_t_ha': 9.0,
            'calidad_grano': 'Largo fino, 65% molinería entera',
            'resistencia_enfermedades': 'Tolerante a Pyricularia oryzae y añublo bacterial',
            'resistencia_plagas': 'Tolerante a sogata',
            'tolerancia_sequia': 'media',
            'altitud_min_msnm': 0, 'altitud_max_msnm': 1300,
            'regiones_recomendadas': 'Llanos Orientales, Centro, Bajo Cauca',
            'tipos_suelo': 'Franco-arcillosos con buen drenaje',
            'fuente': 'Ficha técnica Fedearroz 67 - Fedearroz',
        },
        {
            'name': 'Fedearroz 2000',
            'casa_registradora': 'Fedearroz',
            'pais_origen': 'Colombia', 'year_liberacion': 1999,
            'tipo_variedad': 'mejorada',
            'cycle_days': 122, 'dias_a_floracion': 82, 'dias_a_maduracion': 118,
            'altura_promedio_cm': 100,
            'densidad_siembra_kg_ha': 100, 'distancia_surcos_cm': 20,
            'profundidad_siembra_cm': 3, 'lamina_riego_mm': 900,
            'rendimiento_promedio_t_ha': 7.0,
            'rendimiento_conservador_t_ha': 5.5,
            'rendimiento_potencial_t_ha': 8.5,
            'calidad_grano': 'Largo fino, 62% molinería entera',
            'resistencia_enfermedades': 'Tolerante a virus de la hoja blanca',
            'tolerancia_sequia': 'media',
            'altitud_min_msnm': 0, 'altitud_max_msnm': 1200,
            'regiones_recomendadas': 'Tolima, Huila, Llanos',
            'fuente': 'Boletín Fedearroz',
        },
        {
            'name': 'Fedearroz 174',
            'casa_registradora': 'Fedearroz',
            'pais_origen': 'Colombia', 'year_liberacion': 2020,
            'tipo_variedad': 'mejorada',
            'cycle_days': 118, 'dias_a_floracion': 80,
            'altura_promedio_cm': 90,
            'densidad_siembra_kg_ha': 100,
            'rendimiento_promedio_t_ha': 8.0,
            'rendimiento_potencial_t_ha': 10.0,
            'rendimiento_conservador_t_ha': 6.5,
            'resistencia_enfermedades': 'Alta tolerancia a Pyricularia',
            'altitud_min_msnm': 0, 'altitud_max_msnm': 1300,
            'fuente': 'Fedearroz 174 - ficha técnica',
        },
    ],
    # ---------------------------- MAÍZ ----------------------------
    'Maiz': [
        {
            'name': 'ICA V-305',
            'casa_registradora': 'ICA (Instituto Colombiano Agropecuario)',
            'pais_origen': 'Colombia', 'year_liberacion': 1995,
            'tipo_variedad': 'mejorada',
            'cycle_days': 120, 'dias_a_floracion': 60, 'dias_a_maduracion': 115,
            'altura_promedio_cm': 220,
            'densidad_siembra_kg_ha': 22, 'distancia_surcos_cm': 80,
            'profundidad_siembra_cm': 5, 'lamina_riego_mm': 600,
            'fertilizacion_npk': '150-80-100 kg/ha',
            'rendimiento_promedio_t_ha': 5.5,
            'rendimiento_conservador_t_ha': 4.0,
            'rendimiento_potencial_t_ha': 7.0,
            'tolerancia_sequia': 'alta',
            'altitud_min_msnm': 0, 'altitud_max_msnm': 1500,
            'regiones_recomendadas': 'Costa Atlántica, Valle, Tolima',
            'fuente': 'ICA - boletín técnico V-305',
        },
        {
            'name': 'Pioneer 30F35',
            'casa_registradora': 'Corteva / Pioneer',
            'pais_origen': 'Estados Unidos', 'year_liberacion': 2010,
            'tipo_variedad': 'hibrida',
            'cycle_days': 125, 'dias_a_floracion': 62,
            'altura_promedio_cm': 250,
            'densidad_siembra_kg_ha': 25, 'distancia_surcos_cm': 75,
            'fertilizacion_npk': '180-90-120 kg/ha',
            'rendimiento_promedio_t_ha': 9.0,
            'rendimiento_conservador_t_ha': 6.5,
            'rendimiento_potencial_t_ha': 12.0,
            'tolerancia_sequia': 'media',
            'altitud_min_msnm': 0, 'altitud_max_msnm': 1800,
            'fuente': 'Catálogo Pioneer Colombia',
        },
    ],
    # ---------------------------- CAFÉ ----------------------------
    'Cafe Arabica': [
        {
            'name': 'Castillo',
            'casa_registradora': 'Cenicafé',
            'pais_origen': 'Colombia', 'year_liberacion': 2005,
            'tipo_variedad': 'mejorada',
            'cycle_days': 730,  # 2 años a primera cosecha
            'altura_promedio_cm': 200,
            'densidad_siembra_kg_ha': 5,  # ~5500 plantas/ha
            'distancia_surcos_cm': 150,
            'rendimiento_promedio_t_ha': 1.8,  # kg pergamino seco
            'rendimiento_conservador_t_ha': 1.2,
            'rendimiento_potencial_t_ha': 2.5,
            'calidad_grano': 'Taza limpia, buen cuerpo, acidez media',
            'resistencia_enfermedades': 'Resistente a roya (Hemileia vastatrix)',
            'altitud_min_msnm': 1200, 'altitud_max_msnm': 2000,
            'regiones_recomendadas': 'Eje cafetero, Antioquia, Huila, Nariño',
            'tipos_suelo': 'Francos, profundos, bien drenados, pH 5.0-5.5',
            'fuente': 'Cenicafé - Variedad Castillo',
        },
        {
            'name': 'Cenicafé 1',
            'casa_registradora': 'Cenicafé',
            'pais_origen': 'Colombia', 'year_liberacion': 2016,
            'tipo_variedad': 'mejorada',
            'cycle_days': 700,
            'altura_promedio_cm': 180,
            'rendimiento_promedio_t_ha': 2.0,
            'rendimiento_conservador_t_ha': 1.4,
            'rendimiento_potencial_t_ha': 2.8,
            'resistencia_enfermedades': 'Resistente a roya y CBD',
            'altitud_min_msnm': 1200, 'altitud_max_msnm': 2000,
            'fuente': 'Cenicafé - Boletín 470',
        },
        {
            'name': 'Caturra',
            'casa_registradora': 'Origen brasilero',
            'pais_origen': 'Brasil', 'year_liberacion': 1940,
            'tipo_variedad': 'mejorada',
            'cycle_days': 730,
            'altura_promedio_cm': 200,
            'rendimiento_promedio_t_ha': 1.5,
            'rendimiento_conservador_t_ha': 1.0,
            'rendimiento_potencial_t_ha': 2.2,
            'calidad_grano': 'Taza de alta calidad, dulzura',
            'resistencia_enfermedades': 'Susceptible a roya',
            'altitud_min_msnm': 1300, 'altitud_max_msnm': 2000,
            'fuente': 'Cenicafé - histórico',
        },
    ],
}


class Command(BaseCommand):
    help = 'Sembrar variedades profesionales para cultivos del catálogo'

    def handle(self, *args, **options):
        total_created = 0
        total_skipped = 0

        for crop_name, varieties in VARIETIES.items():
            catalog = CropCatalog.objects.filter(name__iexact=crop_name).first()
            if not catalog:
                self.stdout.write(self.style.WARNING(
                    f"⚠ Cultivo '{crop_name}' no encontrado en catálogo, omitido"
                ))
                continue

            for v in varieties:
                obj, created = CropVariety.objects.get_or_create(
                    name=v['name'],
                    crop_catalog=catalog,
                    defaults=v,
                )
                if created:
                    total_created += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ {catalog.name} → {obj.name}"
                    ))
                else:
                    total_skipped += 1
                    self.stdout.write(f"  • {catalog.name} → {obj.name} (ya existe)")

        self.stdout.write(self.style.SUCCESS(
            f"\nCompletado. Creadas: {total_created}, ya existentes: {total_skipped}"
        ))
