from django.db import models
from simple_history.models import HistoricalRecords


# Define las categorías de insumos
class Category(models.Model):
    name = models.CharField("Nombre", max_length=100)
    description = models.TextField("Descripción", blank=True, null=True)
    created = models.DateTimeField("Fecha de creación", auto_now_add=True)
    updated = models.DateTimeField("Fecha de actualización", auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name

# Define las subcategorías de insumos
class Subcategory(models.Model):
    name = models.CharField("Nombre", max_length=100)
    description = models.TextField("Descripción", blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories', verbose_name="Categoría")
    created = models.DateTimeField("Fecha de creación", auto_now_add=True)
    updated = models.DateTimeField("Fecha de actualización", auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name

# Define las unidades de medida


# Define las empresas proveedoras
class Company(models.Model):
    name = models.CharField("Nombre", max_length=150)
    address = models.CharField("Dirección", max_length=255, blank=True, null=True)
    phone = models.CharField("Teléfono", max_length=30, blank=True, null=True)
    email = models.EmailField("Email", blank=True, null=True)
    rut = models.CharField("RUT", max_length=12, unique=True, blank=True, null=True)
    website = models.URLField("Sitio web", blank=True, null=True)
    contact_person = models.CharField("Persona de contacto", max_length=100, blank=True, null=True)
    contact_phone = models.CharField("Teléfono de contacto", max_length=30, blank=True, null=True)
    contact_email = models.EmailField("Email de contacto", blank=True, null=True)
    image = models.ImageField("Logo/Imagen", upload_to="company_images/", blank=True, null=True)
    notes = models.TextField("Notas", blank=True, null=True)
    created = models.DateTimeField("Fecha de creación", auto_now_add=True)
    updated = models.DateTimeField("Fecha de actualización", auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name

# Define los proveedores de insumos
class Supplier(models.Model):
    name = models.CharField("Nombre", max_length=150)
    contact = models.CharField("Persona de contacto", max_length=100, blank=True, null=True)
    phone = models.CharField("Teléfono", max_length=30, blank=True, null=True)
    email = models.EmailField("Email", blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Empresa")
    address = models.CharField("Dirección", max_length=255, blank=True, null=True)
    website = models.URLField("Sitio web", blank=True, null=True)
    tax_id = models.CharField("NIT/RUT", max_length=20, blank=True, null=True)
    is_active = models.BooleanField("Activo", default=True)
    image = models.ImageField("Foto/Imagen", upload_to="supplier_images/", blank=True, null=True)
    notes = models.TextField("Notas", blank=True, null=True)
    created = models.DateTimeField("Fecha de creación", auto_now_add=True)
    updated = models.DateTimeField("Fecha de actualización", auto_now=True)
    history = HistoricalRecords()
# Modelo para personas naturales/contactos simples
class Person(models.Model):
    name = models.CharField("Nombre", max_length=150)
    phone = models.CharField("Teléfono", max_length=30, blank=True, null=True)
    email = models.EmailField("Email", blank=True, null=True)
    image = models.ImageField("Foto", upload_to="person_images/", blank=True, null=True)
    notes = models.TextField("Notas", blank=True, null=True)
    created = models.DateTimeField("Fecha de creación", auto_now_add=True)
    updated = models.DateTimeField("Fecha de actualización", auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name

    def __str__(self):
        return self.name

# Define los insumos agrícolas
class Warehouse(models.Model):
    name = models.CharField("Nombre", max_length=100)
    address = models.CharField("Dirección", max_length=255, blank=True, null=True)
    location = models.CharField("Ubicación", max_length=255, blank=True, null=True)
    description = models.TextField("Descripción", blank=True, null=True)
    is_active = models.BooleanField("Activo", default=True)
    created = models.DateTimeField("Fecha de creación", auto_now_add=True)
    updated = models.DateTimeField("Fecha de actualización", auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name

class Supply(models.Model):
    UNIT_CHOICES = [
        ("litros", "Litros"),
        ("mililitros", "Mililitros"),
        ("galones", "Galones"),
        ("kilos", "Kilos"),
        ("gramos", "Gramos"),
        ("toneladas", "Toneladas"),
        ("libras", "Libras"),
        ("onzas", "Onzas"),
        ("bultos", "Bultos"),
        ("sacos", "Sacos"),
        ("unidades", "Unidades"),
        ("metros", "Metros"),
        ("centímetros", "Centímetros"),
        ("milímetros", "Milímetros"),
        ("hectáreas", "Hectáreas"),
        ("otros", "Otros")
    ]
    unit = models.CharField("Unidad de medida", max_length=20, choices=UNIT_CHOICES, default="unidades", blank=True, null=True)
    unit_amount = models.DecimalField("Cantidad de unidad de medida", max_digits=12, decimal_places=2, default=0, blank=True, null=True)
    unit_custom = models.CharField("Unidad personalizada", max_length=50, blank=True, null=True, help_text="Especifique la unidad si seleccionó 'Otros'.")
    name = models.CharField("Nombre", max_length=150)
    unit_value = models.DecimalField("Valor unitario", max_digits=12, decimal_places=2, blank=True, null=True)
    quantity = models.DecimalField("Cantidad", max_digits=12, decimal_places=2, default=0)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='supplies', verbose_name="Categoría",  blank=True, null=True)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE, related_name='supplies', verbose_name="Subcategoría", blank=True, null=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='supplies', verbose_name="Almacén")
    suppliers = models.ManyToManyField('Supplier', verbose_name="Proveedores", related_name="supplies", blank=True)
    image = models.ImageField("Imagen", upload_to="supply_images/", blank=True, null=True)
    description = models.TextField("Descripción", blank=True, null=True)
    notes = models.TextField("Notas", blank=True, null=True)
    attachments = models.FileField("Adjuntos", upload_to="supply_attachments/", blank=True, null=True)
    created = models.DateTimeField("Fecha de creación", auto_now_add=True)
    updated = models.DateTimeField("Fecha de actualización", auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name

    def get_total_value(self):
        return self.quantity * self.unit_value

class Machinery(models.Model):
    name = models.CharField("Nombre", max_length=150)
    brand = models.CharField("Marca", max_length=100, blank=True, null=True)
    model = models.CharField("Modelo", max_length=100, blank=True, null=True)
    serial_number = models.CharField("Serial", max_length=100, blank=True, null=True)
    year = models.PositiveIntegerField("Año", blank=True, null=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='machinery', verbose_name="Almacén", blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='machineries', verbose_name="Categoría", blank=True, null=True)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE, related_name='machineries', verbose_name="Subcategoría", blank=True, null=True)
    description = models.TextField("Descripción", blank=True, null=True)
    image = models.ImageField("Imagen", upload_to="machinery_images/", blank=True, null=True)
    # Campos extendidos para gestión profesional
    status = models.CharField("Estado", max_length=30, choices=[('nuevo','Nuevo'),('usado','Usado'),('en_reparacion','En reparación'),('fuera_servicio','Fuera de servicio')], default='nuevo')
    acquisition_date = models.DateField("Fecha de adquisición", blank=True, null=True)
    purchase_value = models.DecimalField("Valor de compra", max_digits=12, decimal_places=2, blank=True, null=True)
    current_value = models.DecimalField("Valor actual", max_digits=12, decimal_places=2, blank=True, null=True)
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Proveedor")
    location = models.CharField("Ubicación física", max_length=150, blank=True, null=True)
    usage_hours = models.PositiveIntegerField("Horas de uso", blank=True, null=True)
    last_maintenance = models.DateField("Último mantenimiento", blank=True, null=True)
    next_maintenance = models.DateField("Próximo mantenimiento", blank=True, null=True)
    responsible = models.CharField("Responsable actual", max_length=100, blank=True, null=True)
    notes = models.TextField("Observaciones", blank=True, null=True)
    created = models.DateTimeField("Fecha de creación", auto_now_add=True)
    updated = models.DateTimeField("Fecha de actualización", auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.name

# Define los movimientos de inventario
class InventoryMovement(models.Model):
    from django.contrib.contenttypes.fields import GenericForeignKey
    from django.contrib.contenttypes.models import ContentType
    MOVEMENT_TYPE_CHOICES = (
        ("entrada", "Entrada"),
        ("salida", "Salida"),
        ("transferencia", "Transferencia"),
        ("ajuste", "Ajuste"),
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name="Tipo de activo", null=True, blank=True)
    object_id = models.PositiveIntegerField("ID de activo", null=True, blank=True)
    asset = GenericForeignKey('content_type', 'object_id')
    movement_type = models.CharField("Tipo de movimiento", max_length=15, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.DecimalField("Cantidad", max_digits=12, decimal_places=2)
    unit_value = models.DecimalField("Valor unitario", max_digits=12, decimal_places=2, null=True, blank=True)
    origin_location = models.CharField("Ubicación/Almacén origen", max_length=100, blank=True, null=True)
    destination_location = models.CharField("Ubicación/Almacén destino", max_length=100, blank=True, null=True)
    date = models.DateTimeField("Fecha de movimiento", auto_now_add=True)
    notes = models.TextField("Notas", blank=True, null=True)
    user = models.CharField("Usuario", max_length=100, blank=True, null=True)
    document = models.FileField("Documento adjunto", upload_to='movements/', blank=True, null=True)
    created = models.DateTimeField("Fecha de creación", auto_now_add=True)
    updated = models.DateTimeField("Fecha de actualización", auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.content_type} #{self.object_id} ({self.quantity})"

    def get_total_value(self):
        value = self.unit_value if self.unit_value is not None else 0
        return self.quantity * value
