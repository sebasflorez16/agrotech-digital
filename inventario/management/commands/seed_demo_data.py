"""
Comando para sembrar datos de demostración realistas (arroz colombiano).

Crea: cargos, departamentos, empleados (encargados), tipos de cultivo,
variedades de arroz, almacenes, categorías, subcategorías, proveedores e
insumos con precios colombianos.

Uso:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --schema villa_lola
"""
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

from base_agrotech.models import Client


class Command(BaseCommand):
    help = 'Siembra datos de demostración (arroz colombiano) en los tenants activos.'

    def add_arguments(self, parser):
        parser.add_argument('--schema', type=str, default=None, help='Schema del tenant a sembrar (opcional).')

    def handle(self, *args, **options):
        tenants = Client.objects.exclude(schema_name='public')
        if options['schema']:
            tenants = tenants.filter(schema_name=options['schema'])
        if not tenants.exists():
            self.stdout.write(self.style.WARNING('No hay tenants activos (distintos de public).'))
            return

        for tenant in tenants:
            with schema_context(tenant.schema_name):
                self._seed(tenant)

    def _seed(self, tenant):
        from RRHH.models import Position, Department, Employee
        from crop.models import CropType, CropVariety
        from inventario.models import (
            Warehouse, Category, Subcategory, Supplier, Supply, Machinery,
        )

        tid = tenant.id
        hoy = date.today()

        # ── Cargos ─────────────────────────────────────────────
        cargos = {}
        for nombre in ['Agrónomo', 'Técnico de Campo', 'Supervisor de Producción', 'Administrador']:
            obj, _ = Position.objects.get_or_create(name=nombre, defaults={'tenant_id': tid})
            cargos[nombre] = obj

        # ── Departamentos ──────────────────────────────────────
        deptos = {}
        for nombre in ['Agronomía', 'Producción', 'Operaciones']:
            obj, _ = Department.objects.get_or_create(name=nombre, defaults={'tenant_id': tid})
            deptos[nombre] = obj

        # ── Empleados (encargados) ─────────────────────────────
        empleados = [
            ('Juan', 'Pérez', 1012345678, 'Agrónomo', 'Agronomía', 3001112233, 'Calle 10 #5-20, Villavicencio'),
            ('María', 'Rodríguez', 1012345679, 'Técnico de Campo', 'Producción', 3002223344, 'Carrera 15 #8-30, Granada'),
            ('Carlos', 'Gómez', 1012345680, 'Supervisor de Producción', 'Producción', 3003334455, 'Vereda La Esperanza, Lote Central'),
            ('Ana', 'Torres', 1012345681, 'Administrador', 'Operaciones', 3004445566, 'Avenida 40 #12-15, Villavicencio'),
        ]
        for nombre, apellido, cedula, cargo, depto, tel, direccion in empleados:
            Employee.objects.get_or_create(
                identification_number=cedula,
                defaults={
                    'tenant_id': tid,
                    'first_name': nombre,
                    'last_name': apellido,
                    'address': direccion,
                    'phone': tel,
                    'date_of_hire': hoy,
                    'position': cargos[cargo],
                    'department': deptos[depto],
                },
            )

        # ── Tipos de cultivo ───────────────────────────────────
        ct_arroz, _ = CropType.objects.get_or_create(
            name='Arroz', defaults={'tenant_id': tid, 'description': 'Arroz de riego (Oriza sativa)'}
        )
        CropType.objects.get_or_create(
            name='Maíz', defaults={'tenant_id': tid, 'description': 'Maíz tecnificado (Zea mays)'}
        )
        CropType.objects.get_or_create(
            name='Café', defaults={'tenant_id': tid, 'description': 'Café arábigo (Coffea arabica)'}
        )

        # ── Variedades de arroz (FEDEARROZ) ────────────────────
        variedades_arroz = [
            ('FEDEARROZ 67', 120, 'Alto potencial de rendimiento, resistente a piricularia.'),
            ('FEDEARROZ 473', 110, 'Ciclo corto, buena calidad molinera.'),
            ('FEDEARROZ 2000', 125, 'Tolerante a estrés hídrico.'),
            ('IR-64', 115, 'Variedad de referencia en los Llanos.'),
        ]
        for nombre, ciclo, desc in variedades_arroz:
            CropVariety.objects.get_or_create(
                name=nombre, crop_type=ct_arroz,
                defaults={'tenant_id': tid, 'cycle_days': ciclo, 'description': desc},
            )

        # ── Almacenes ──────────────────────────────────────────
        bodega, _ = Warehouse.objects.get_or_create(
            name='Bodega Principal',
            defaults={'tenant_id': tid, 'address': 'Vereda La Esperanza, Lote Central'},
        )
        agroq, _ = Warehouse.objects.get_or_create(
            name='Almacén de Agroquímicos',
            defaults={'tenant_id': tid, 'address': 'Zona técnica, junto a la bodega'},
        )

        # ── Categorías ─────────────────────────────────────────
        cat_fert, _ = Category.objects.get_or_create(name='Fertilizantes', defaults={'tenant_id': tid})
        cat_herb, _ = Category.objects.get_or_create(name='Herbicidas', defaults={'tenant_id': tid})
        cat_inse, _ = Category.objects.get_or_create(name='Insecticidas', defaults={'tenant_id': tid})
        cat_fung, _ = Category.objects.get_or_create(name='Fungicidas', defaults={'tenant_id': tid})
        cat_sem, _ = Category.objects.get_or_create(name='Semillas', defaults={'tenant_id': tid})

        # ── Subcategorías ──────────────────────────────────────
        Subcategory.objects.get_or_create(name='Nitrogenados', category=cat_fert, defaults={'tenant_id': tid})
        Subcategory.objects.get_or_create(name='Fosforados', category=cat_fert, defaults={'tenant_id': tid})
        Subcategory.objects.get_or_create(name='Compuestos', category=cat_fert, defaults={'tenant_id': tid})
        Subcategory.objects.get_or_create(name='Post-emergentes', category=cat_herb, defaults={'tenant_id': tid})
        Subcategory.objects.get_or_create(name='Sistémicos', category=cat_inse, defaults={'tenant_id': tid})
        Subcategory.objects.get_or_create(name='Preventivos', category=cat_fung, defaults={'tenant_id': tid})
        Subcategory.objects.get_or_create(name='Certificadas', category=cat_sem, defaults={'tenant_id': tid})

        # ── Empresas ───────────────────────────────────────────
        from inventario.models import Company
        Company.objects.get_or_create(
            name='AgroTech Colombia S.A.S.', defaults={
                'tenant_id': tid, 'rut': '901234567-8', 'address': 'Calle 40 #12-15, Villavicencio',
                'phone': '6085550001', 'email': 'contacto@agrotechcolombia.com',
                'website': 'https://agrotechcolombia.com', 'contact_person': 'Sebastián Flórez',
                'contact_phone': '3001234567', 'contact_email': 'juansebastianflorezescobar@gmail.com',
            }
        )
        Company.objects.get_or_create(
            name='Agroservicios del Meta Ltda.', defaults={
                'tenant_id': tid, 'rut': '900987654-3', 'address': 'Carrera 15 #8-30, Granada',
                'phone': '6085550002', 'email': 'info@agroserviciosmeta.com',
                'website': 'https://agroserviciosmeta.com', 'contact_person': 'Carlos Gómez',
            }
        )

        # ── Proveedores ────────────────────────────────────────
        prov_yara, _ = Supplier.objects.get_or_create(
            name='Yara Colombia', defaults={'tenant_id': tid, 'tax_id': '900123456-7', 'phone': '6015550101',
                                            'email': 'ventas@yara.com.co', 'contact': 'Andrés Rojas',
                                            'address': 'Bogotá, Colombia', 'website': 'https://yara.com.co'}
        )
        prov_fed, _ = Supplier.objects.get_or_create(
            name='FEDEARROZ', defaults={'tenant_id': tid, 'tax_id': '860012345-6', 'phone': '6015550102',
                                        'email': 'servicios@fedarroz.com.co', 'contact': 'María Fernández',
                                        'address': 'Bogotá, Colombia', 'website': 'https://federarroz.com.co'}
        )
        Supplier.objects.get_or_create(
            name='Monómeros Colombo Venezolanos', defaults={'tenant_id': tid, 'tax_id': '890098765-4', 'phone': '6015550103',
                                                            'email': 'agro@monomeros.com.co', 'contact': 'Luis Méndez',
                                                            'address': 'Barranquilla, Colombia', 'website': 'https://monomeros.com.co'}
        )
        Supplier.objects.get_or_create(
            name='Agroinsumos del Llano', defaults={'tenant_id': tid, 'tax_id': '900765432-1', 'phone': '6085550104',
                                                    'email': 'ventas@agroinsumosllano.com', 'contact': 'Pedro Castillo',
                                                    'address': 'Villavicencio, Meta'}
        )

        # ── Insumos (precios colombianos) ──────────────────────
        insumos = [
            # nombre, bodega, categoria, proveedor, unit, cantidad, valor_unitario
            ('Urea 46-0-0', bodega, cat_fert, prov_yara, 'bultos', 40, Decimal('155000')),
            ('DAP 18-46-0', bodega, cat_fert, prov_yara, 'bultos', 30, Decimal('180000')),
            ('KCl 0-0-60', bodega, cat_fert, prov_yara, 'bultos', 25, Decimal('165000')),
            ('NPK 15-15-15', bodega, cat_fert, prov_yara, 'bultos', 35, Decimal('160000')),
            ('Glifosato', agroq, cat_herb, prov_fed, 'litros', 20, Decimal('28000')),
            ('Propanil', agroq, cat_herb, prov_fed, 'litros', 15, Decimal('42000')),
            ('Bispiribac-sodio', agroq, cat_herb, prov_fed, 'litros', 10, Decimal('95000')),
            ('Cipermetrina', agroq, cat_inse, prov_fed, 'litros', 12, Decimal('32000')),
            ('Azoxistrobina', agroq, cat_fung, prov_fed, 'litros', 8, Decimal('85000')),
            ('Semilla FEDEARROZ 67', bodega, cat_sem, prov_fed, 'kilos', 200, Decimal('9500')),
            ('Semilla FEDEARROZ 473', bodega, cat_sem, prov_fed, 'kilos', 150, Decimal('9800')),
        ]
        for nombre, wh, cat, prov, unidad, cant, valor in insumos:
            Supply.objects.get_or_create(
                name=nombre, warehouse=wh,
                defaults={
                    'tenant_id': tid,
                    'category': cat,
                    'quantity': Decimal(cant),
                    'minimum_stock': Decimal('5'),
                    'unit_value': valor,
                    'unit': unidad,
                },
            )

        # ── Métodos de pago (nómina) ─────────────────────────
        from base_agrotech.models import PaymentMethod
        pago_map = {}
        for nombre, monto in [
            ('Quincenal', Decimal('1250000')),
            ('Mensual', Decimal('2500000')),
            ('Por Jornal', Decimal('45000')),
        ]:
            obj, _ = PaymentMethod.objects.get_or_create(name=nombre, defaults={'amount': monto})
            pago_map[nombre] = obj

        # Asignar método de pago a los empleados existentes
        asignacion = ['Quincenal', 'Mensual', 'Quincenal', 'Mensual']
        for emp, nombre_pago in zip(list(Employee.objects.order_by('id')), asignacion):
            if emp.salary is None:
                emp.salary = pago_map[nombre_pago]
                emp.save()

        # ── Contratistas ──────────────────────────────────────
        from RRHH.models import ContractorEmployee
        contratistas = [
            ('Pedro', 'Castillo', 1019988776, 3115556677, '123456789', 'Operador de maquinaria agrícola'),
            ('Luisa', 'Hernández', 1019988777, 3115556688, '987654321', 'Jornalera de siembra'),
        ]
        for nombre, apellido, cedula, tel, rut, desc in contratistas:
            ContractorEmployee.objects.get_or_create(
                identification_number=cedula,
                defaults={
                    'tenant_id': tid,
                    'first_name': nombre,
                    'last_name': apellido,
                    'address': 'Vereda La Esperanza',
                    'phone': tel,
                    'date_of_hire': hoy,
                    'rut': rut,
                    'description': desc,
                },
            )

        # ── Maquinaria ────────────────────────────────────────
        maquinaria = [
            ('Tractor John Deere 5075E', 'John Deere', '5075E', 'JD5075-001', 2020, bodega, 'nuevo', Decimal('185000000'), Decimal('150000000'), 1200),
            ('Fumigadora de Espalda', 'Stihl', 'SR 450', 'ST-450-01', 2022, agroq, 'usado', Decimal('2800000'), Decimal('1800000'), 300),
            ('Cosechadora Arroz', 'New Holland', 'TC 5090', 'NH-5090-01', 2021, bodega, 'usado', Decimal('420000000'), Decimal('360000000'), 900),
            ('Rastra de Discos', 'Agrometal', 'RD-24', 'RD-24-01', 2023, bodega, 'nuevo', Decimal('35000000'), Decimal('32000000'), 150),
        ]
        for nombre, marca, modelo, serial, anio, wh, estado, compra, actual, horas in maquinaria:
            Machinery.objects.get_or_create(
                name=nombre,
                defaults={
                    'tenant_id': tid,
                    'brand': marca,
                    'model': modelo,
                    'serial_number': serial,
                    'year': anio,
                    'warehouse': wh,
                    'status': estado,
                    'purchase_value': compra,
                    'current_value': actual,
                    'usage_hours': horas,
                },
            )

        # ── Movimientos de inventario ─────────────────────────
        from django.contrib.contenttypes.models import ContentType
        from inventario.models import InventoryMovement
        supply_ct = ContentType.objects.get_for_model(Supply)
        movimientos = [
            ('Urea 46-0-0', 'entrada', Decimal('40'), Decimal('140000'), 'Compra inicial a Yara Colombia'),
            ('Glifosato', 'entrada', Decimal('20'), Decimal('25000'), 'Compra a FEDEARROZ'),
            ('Semilla FEDEARROZ 67', 'entrada', Decimal('200'), Decimal('9000'), 'Compra de semilla certificada'),
            ('Semilla FEDEARROZ 67', 'salida', Decimal('10'), Decimal('9500'), 'Salida para siembra (prueba)'),
        ]
        for nombre_supply, tipo, cant, valor, nota in movimientos:
            supply = Supply.objects.filter(name=nombre_supply).first()
            if not supply:
                continue
            InventoryMovement.objects.get_or_create(
                content_type=supply_ct,
                object_id=supply.pk,
                movement_type=tipo,
                quantity=cant,
                notes=nota,
                defaults={
                    'tenant_id': tid,
                    'unit_value': valor,
                },
            )

        self.stdout.write(self.style.SUCCESS(
            f'✅ Datos de demo sembrados en tenant "{tenant.schema_name}" (id={tid}): '
            f'{len(cargos)} cargos, {len(empleados)} empleados, {len(contratistas)} contratistas, '
            f'{len(insumos)} insumos, {len(maquinaria)} maquinarias.'
        ))
