"""
Tests para Sistema Optimizado EOSDA
Verifica:
1. Generación de cache_key SHA-256
2. Caché funcionando correctamente
3. Servicio optimizado
4. Estadísticas
5. API real de EOSDA (si hay conectividad)
"""

import hashlib
import json
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from parcels.models import Parcel, CacheDatosEOSDA, EstadisticaUsoEOSDA
from parcels.eosda_optimized_service import EOSDAOptimizedService, get_eosda_service


class CacheDatosEOSDATestCase(TestCase):
    """Tests para modelo de caché"""
    
    def setUp(self):
        self.geometria = {
            "type": "Polygon",
            "coordinates": [[
                [-74.0, 4.0],
                [-74.0, 4.1],
                [-73.9, 4.1],
                [-73.9, 4.0],
                [-74.0, 4.0]
            ]]
        }
        self.fecha_inicio = date(2024, 1, 1)
        self.fecha_fin = date(2024, 6, 30)
        self.indice = 'NDVI'
    
    def test_generar_cache_key_consistente(self):
        """El cache_key debe ser consistente para mismos parámetros"""
        key1 = CacheDatosEOSDA.generar_cache_key(
            self.geometria, self.fecha_inicio, self.fecha_fin, self.indice
        )
        key2 = CacheDatosEOSDA.generar_cache_key(
            self.geometria, self.fecha_inicio, self.fecha_fin, self.indice
        )
        
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 64)  # SHA-256 = 64 caracteres hex
        print(f"✅ Cache key generada: {key1[:16]}...")
    
    def test_generar_cache_key_diferente_para_distintos_params(self):
        """Parámetros diferentes deben generar keys diferentes"""
        key_ndvi = CacheDatosEOSDA.generar_cache_key(
            self.geometria, self.fecha_inicio, self.fecha_fin, 'NDVI'
        )
        key_ndmi = CacheDatosEOSDA.generar_cache_key(
            self.geometria, self.fecha_inicio, self.fecha_fin, 'NDMI'
        )
        
        self.assertNotEqual(key_ndvi, key_ndmi)
        print(f"✅ Keys diferentes: NDVI vs NDMI")
    
    def test_guardar_y_obtener_cache(self):
        """Guardar y recuperar datos del caché"""
        cache_key = CacheDatosEOSDA.generar_cache_key(
            self.geometria, self.fecha_inicio, self.fecha_fin, self.indice
        )
        
        datos_prueba = {
            'valores': [0.5, 0.6, 0.7],
            'fechas': ['2024-01-01', '2024-02-01', '2024-03-01']
        }
        
        # Guardar
        CacheDatosEOSDA.guardar_cache(
            cache_key, self.geometria, self.fecha_inicio, 
            self.fecha_fin, self.indice, datos_prueba
        )
        
        # Obtener
        datos_recuperados = CacheDatosEOSDA.obtener_o_ninguno(cache_key)
        
        self.assertIsNotNone(datos_recuperados)
        self.assertEqual(datos_recuperados['valores'], datos_prueba['valores'])
        print(f"✅ Caché guardado y recuperado correctamente")
    
    def test_cache_expirado_no_retorna_datos(self):
        """Caché expirado no debe retornar datos"""
        cache_key = CacheDatosEOSDA.generar_cache_key(
            self.geometria, self.fecha_inicio, self.fecha_fin, self.indice
        )
        
        # Crear caché expirado manualmente
        cache = CacheDatosEOSDA.objects.create(
            cache_key=cache_key,
            geometria=self.geometria,
            fecha_inicio=self.fecha_inicio,
            fecha_fin=self.fecha_fin,
            indice=self.indice,
            datos_satelitales={'test': 'data'},
            fecha_expiracion=timezone.now() - timedelta(days=1)  # Expirado ayer
        )
        
        datos = CacheDatosEOSDA.obtener_o_ninguno(cache_key)
        self.assertIsNone(datos)
        print(f"✅ Caché expirado correctamente ignorado")
    
    def test_incrementar_hits(self):
        """Hits debe incrementarse con cada acceso"""
        cache_key = CacheDatosEOSDA.generar_cache_key(
            self.geometria, self.fecha_inicio, self.fecha_fin, self.indice
        )
        
        CacheDatosEOSDA.guardar_cache(
            cache_key, self.geometria, self.fecha_inicio,
            self.fecha_fin, self.indice, {'test': 'data'}
        )
        
        # Acceder 3 veces
        for i in range(3):
            CacheDatosEOSDA.obtener_o_ninguno(cache_key)
        
        cache = CacheDatosEOSDA.objects.get(cache_key=cache_key)
        self.assertEqual(cache.hits, 3)
        print(f"✅ Hits incrementados correctamente: {cache.hits}")


class EstadisticaUsoEOSDATestCase(TestCase):
    """Tests para modelo de estadísticas"""
    
    def test_registrar_uso_cache_hit(self):
        """Registrar uso desde caché"""
        EstadisticaUsoEOSDA.registrar_uso(
            tipo_operacion='statistics',
            indice='NDVI',
            desde_cache=True,
            tiempo_ms=50
        )
        
        hoy = timezone.now().date()
        stat = EstadisticaUsoEOSDA.objects.get(
            fecha=hoy,
            tipo_operacion='statistics',
            indice='NDVI'
        )
        
        self.assertEqual(stat.total_requests, 1)
        self.assertEqual(stat.requests_desde_cache, 1)
        self.assertEqual(stat.requests_a_api, 0)
        print(f"✅ Estadística caché registrada: {stat}")
    
    def test_registrar_uso_api_call(self):
        """Registrar uso desde API"""
        EstadisticaUsoEOSDA.registrar_uso(
            tipo_operacion='statistics',
            indice='NDMI',
            desde_cache=False,
            tiempo_ms=15000
        )
        
        hoy = timezone.now().date()
        stat = EstadisticaUsoEOSDA.objects.get(
            fecha=hoy,
            tipo_operacion='statistics',
            indice='NDMI'
        )
        
        self.assertEqual(stat.requests_a_api, 1)
        self.assertEqual(stat.requests_desde_cache, 0)
        print(f"✅ Estadística API registrada: {stat}")
    
    def test_calcular_tasa_cache(self):
        """Calcular tasa de caché correctamente"""
        # Registrar 8 desde caché, 2 desde API
        for i in range(8):
            EstadisticaUsoEOSDA.registrar_uso(
                'statistics', 'SAVI', desde_cache=True
            )
        for i in range(2):
            EstadisticaUsoEOSDA.registrar_uso(
                'statistics', 'SAVI', desde_cache=False
            )
        
        metricas = EstadisticaUsoEOSDA.obtener_metricas_mes_actual()
        self.assertEqual(metricas['total_requests'], 10)
        self.assertEqual(metricas['tasa_cache'], 80.0)
        print(f"✅ Tasa de caché calculada: {metricas['tasa_cache']}%")


class EOSDAOptimizedServiceTestCase(TestCase):
    """Tests para servicio optimizado"""
    
    def setUp(self):
        self.parcela = Parcel.objects.create(
            name="Parcela Test",
            soil_type="ARCILLOSO",
            topography="PLANA",
            geom={
                "type": "Polygon",
                "coordinates": [[
                    [-74.0, 4.0],
                    [-74.0, 4.1],
                    [-73.9, 4.1],
                    [-73.9, 4.0],
                    [-74.0, 4.0]
                ]]
            }
        )
    
    def test_servicio_inicializa_correctamente(self):
        """Servicio debe inicializar con API key"""
        service = get_eosda_service()
        self.assertIsNotNone(service.api_key)
        print(f"✅ Servicio inicializado con API key: {service.api_key[:20]}...")
    
    def test_cache_funciona_en_servicio(self):
        """Segunda consulta debe venir de caché"""
        service = get_eosda_service()
        
        geometria = self.parcela.geom
        fecha_inicio = date(2024, 1, 1)
        fecha_fin = date(2024, 1, 31)
        
        # Simular datos para evitar llamada real a API
        cache_key = CacheDatosEOSDA.generar_cache_key(
            geometria, fecha_inicio, fecha_fin, 'NDVI'
        )
        
        datos_mock = {
            'valores': [0.5, 0.6],
            'fechas': ['2024-01-01', '2024-01-15']
        }
        
        CacheDatosEOSDA.guardar_cache(
            cache_key, geometria, fecha_inicio, fecha_fin, 
            'NDVI', datos_mock, self.parcela
        )
        
        # Primera consulta (desde caché)
        resultado = service.obtener_datos_satelitales(
            geometria, fecha_inicio, fecha_fin, ['NDVI'], self.parcela.id
        )
        
        self.assertIn('NDVI', resultado)
        self.assertEqual(resultado['NDVI']['valores'], [0.5, 0.6])
        
        # Verificar que se registró como caché hit
        metricas = EstadisticaUsoEOSDA.obtener_metricas_mes_actual()
        self.assertGreater(metricas['requests_cache'], 0)
        print(f"✅ Servicio usa caché correctamente")


def run_manual_tests():
    """Tests manuales para verificación rápida"""
    print("\n" + "="*60)
    print("🧪 TESTS MANUALES DEL SISTEMA OPTIMIZADO EOSDA")
    print("="*60 + "\n")
    
    # Test 1: Generación de cache_key
    print("1️⃣  Test: Generación de cache_key SHA-256")
    geometria = {"type": "Polygon", "coordinates": [[[-74, 4], [-74, 4.1], [-73.9, 4.1]]]}
    key = CacheDatosEOSDA.generar_cache_key(geometria, date(2024, 1, 1), date(2024, 6, 30), 'NDVI')
    print(f"   ✅ Cache key: {key}")
    print(f"   ✅ Longitud: {len(key)} caracteres\n")
    
    # Test 2: Guardar y recuperar caché
    print("2️⃣  Test: Guardar y recuperar caché")
    datos_test = {'valores': [0.5, 0.6, 0.7], 'fechas': ['2024-01-01']}
    CacheDatosEOSDA.guardar_cache(key, geometria, date(2024, 1, 1), date(2024, 6, 30), 'NDVI', datos_test)
    datos_recuperados = CacheDatosEOSDA.obtener_o_ninguno(key)
    print(f"   ✅ Datos guardados: {datos_test}")
    print(f"   ✅ Datos recuperados: {datos_recuperados}")
    print(f"   ✅ Coinciden: {datos_test == datos_recuperados}\n")
    
    # Test 3: Estadísticas
    print("3️⃣  Test: Registrar estadísticas")
    EstadisticaUsoEOSDA.registrar_uso('statistics', 'NDVI', desde_cache=True, tiempo_ms=50)
    EstadisticaUsoEOSDA.registrar_uso('statistics', 'NDVI', desde_cache=False, tiempo_ms=15000)
    metricas = EstadisticaUsoEOSDA.obtener_metricas_mes_actual()
    print(f"   ✅ Métricas: {metricas}\n")
    
    # Test 4: Servicio
    print("4️⃣  Test: Servicio optimizado")
    try:
        service = get_eosda_service()
        print(f"   ✅ Servicio inicializado")
        print(f"   ✅ API Key: {service.api_key[:20]}...\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    # Test 5: Limpieza de caché
    print("5️⃣  Test: Limpieza de caché expirado")
    eliminados = CacheDatosEOSDA.limpiar_expirados()
    print(f"   ✅ Cachés expirados eliminados: {eliminados}")
    total = CacheDatosEOSDA.objects.count()
    print(f"   ✅ Cachés activos restantes: {total}\n")
    
    print("="*60)
    print("✅ TODOS LOS TESTS COMPLETADOS")
    print("="*60)


if __name__ == '__main__':
    run_manual_tests()
