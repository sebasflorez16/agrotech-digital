from django.db import models
from django.contrib import admin
from django_tenants.models import TenantMixin, DomainMixin
from simple_history.models import HistoricalRecords
from django_tenants.admin import TenantAdminMixin
import uuid # uuid4 es un identificador unico

# Create your models here.

class Client(TenantMixin):
    name = models.CharField(max_length=100)
    paid_until = models.DateField()
    on_trial = models.BooleanField()
    created_on = models.DateField(auto_now_add=True)
    auto_create_schema = True
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)  # Universal Unique Identifiquer
    historical = HistoricalRecords(inherit=True)  # Esto hace que los modelos que hereden de este sepa que es abstrac
    # y tambien para que hereden toda su funcionalidad


class Domain(DomainMixin):
    pass


class BaseModel(models.Model):
    id = models.AutoField(primary_key=True)
    state = models.BooleanField('Estado', default=True)
    created_date = models.DateField('Fecha de Creación', auto_now=False, auto_now_add=True)
    modified_date = models.DateField('Fecha de Modificacion', auto_now=True, auto_now_add=False)
    deleted_date = models.DateField('Fecha de Eliminacion', auto_now=True, auto_now_add=False)

    class Meta:
        abstract = True
        verbose_name = 'Modelo Base'
        verbose_name_plural = 'Modelos Bases'

    def __str__(self):
        pass

class PaymentMethod(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tipo de pago")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto")
    description = models.TextField(verbose_name="Descripción", blank=True, null=True)
    created_date = models.DateField(auto_now_add=True)
    modified_date = models.DateField(auto_now=True)

    class Meta:
        verbose_name = 'Método de Pago'
        verbose_name_plural = 'Métodos de Pago'

    def __str__(self):
        return f"{self.name} {self.amount}"

    def save(self, *args, **kwargs):
        if not self.id:
            self.created_date = self.modified_date = self.deleted_date = None
        super().save(*args, **kwargs)


class EmployeesBase(models.Model):
    
    id = models.AutoField(primary_key=True)
    identification_number = models.BigIntegerField('Número de Identificación', unique=True)
    identification_image = models.ImageField('Copia Cedula', upload_to='cv-contractor/', blank=True, null=True)
    first_name = models.CharField('Nombres', max_length=100)
    last_name = models.CharField('Apellidos', max_length=100)
    address = models.CharField('Dirección', max_length=200)
    phone = models.BigIntegerField('Teléfono')
    email = models.EmailField('Correo Electrónico', blank=True, null=True)
    state = models.BooleanField('Estado', default=True)
    is_staff = models.BooleanField('Staff', default=False)
    cv = models.ImageField('CV', upload_to='cv-contractor/', blank=True, null=True)
    professional_id = models.BigIntegerField('Numero Tarjeta Profesional', blank=True, null=True)
    professional_image = models.ImageField('Copia Tarjeta Profesional', upload_to='cv-contractor/', blank=True,
                                           null=True)
    health_certificate = models.ImageField('Afiliacion de Eps', upload_to='cv-contractor', blank=True, null=True)
    social_security = models.ImageField('Seguridad Social', upload_to='cv-contractor', blank=True, null=True)
    fingerprint = models.BinaryField(null=True, blank=True)
    date_of_hire = models.DateField('Fecha de Inicio del Contrato')
    end_date = models.DateField('Fecha de Fin del Contrato', blank=True, null=True)
    salary = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE, blank=True, null=True)
    date_of_birth = models.DateField('Fecha de Nacimiento', blank=True, null=True)
    created_date = models.DateField('Fecha de Creación', auto_now=False, auto_now_add=True)
    modified_date = models.DateField('Fecha de Modificacion', auto_now=True, auto_now_add=False)
    deleted_date = models.DateField('Fecha de Eliminacion', auto_now=True, auto_now_add=False)
    historical = HistoricalRecords(inherit=True)  # Esto hace que los modelos que hereden de este sepa que es abstrac
    # y tambien para que hereden toda su funcionalidad


    @property
    def _history_user(self):
        return self.change_by

    @_history_user.setter
    def _history_user(self, value):
        self.change_by = value

    class Meta:
        abstract = True
        verbose_name = 'Empleado Bases'
        verbose_name_plural = 'Empleados Bases'

    def __str__(self):
        pass

@admin.register(Client)
class ClientAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'paid_until', 'on_trial', 'created_on')
    search_fields = ('name',)

