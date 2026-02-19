# Create your models here.
#modelo inicial para creacion de usuario se recomienda agregar al crear el superusuario

from datetime import timezone
from uuid import uuid1
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from simple_history.models import HistoricalRecords


class UserManager(BaseUserManager):
    def _create_user(self, username, email, name, last_name, password, is_staff, is_superuser, **extra_fields):
        # Normalizar email a minúsculas SIEMPRE
        email = self.normalize_email(email).lower()
        user = self.model(
            username=username,
            email=email,
            name=name,
            last_name=last_name,
            is_staff=is_staff,
            is_superuser=is_superuser,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self.db)
        return user

    def create_user(self, username, email, name, last_name, password=None, **extra_fields):
        return self._create_user(username, email, name, last_name, password, False, False, **extra_fields)

    def create_superuser(self, username, email, name, last_name, password=None, **extra_fields):
        return self._create_user(username, email, name, last_name, password, True, True, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    # Datos personales
    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField('Correo Electrónico', max_length=255, unique=True)
    name = models.CharField('Nombres', max_length=255, blank=True, null=True)
    last_name = models.CharField('Apellidos', max_length=255, blank=True, null=True)
    phone = models.CharField('Teléfono', max_length=20, blank=True, null=True)
    address = models.TextField('Dirección', blank=True, null=True)
    image = models.ImageField('Imagen de perfil', upload_to='perfil/', max_length=255, null=True, blank=True)
    description = models.TextField('Descripción', blank=True, null=True)

    # Información laboral
    job_title = models.CharField('Título del Puesto', max_length=255, blank=True, null=True)
    department = models.CharField('Departamento', max_length=255, blank=True, null=True)
    salary = models.DecimalField('Salario', max_digits=10, decimal_places=2, blank=True, null=True)
    hire_date = models.DateField('Fecha de Contratación', blank=True, null=True)
    contract_type = models.CharField(
        'Tipo de Contrato',
        max_length=50,
        choices=[
            ('indefinido', 'Indefinido'),
            ('temporal', 'Temporal'),
            ('freelance', 'Freelance'),
        ],
        blank=True,
        null=True,
    )
    work_schedule = models.JSONField('Horario de Trabajo', blank=True, null=True)  # Ejemplo: {"lunes": "8:00-17:00"}

    # Información bancaria
    bank_name = models.CharField('Banco', max_length=255, blank=True, null=True)
    account_number = models.CharField('Número de Cuenta', max_length=50, blank=True, null=True)
    account_type = models.CharField(
        'Tipo de Cuenta',
        max_length=50,
        choices=[
            ('ahorros', 'Ahorros'),
            ('corriente', 'Corriente'),
        ],
        blank=True,
        null=True,
    )

    # Campos de auditoría
    is_active = models.BooleanField('Activo', default=True)
    is_staff = models.BooleanField('Staff', default=False)
    created_on = models.DateField('Fecha de Creación', auto_now_add=True)
    modified_on = models.DateField('Última Modificación', auto_now=True)
    historical = HistoricalRecords()

    # Tenant al que pertenece el usuario
    # Un usuario pertenece a UN solo tenant (organización/finca)
    # null=True para el superusuario y usuarios del schema public
    tenant = models.ForeignKey(
        'base_agrotech.Client',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Organización',
    )

    # Relaciones
    reports_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='direct_reports',
        verbose_name='Reporta a',
    )

    # Gestión avanzada de permisos
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('manager', 'Gerente'),
        ('employee', 'Empleado'),
        ('accountant', 'Contador'),
    ]
    role = models.CharField('Rol', max_length=50, choices=ROLE_CHOICES, default='employee')

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'name', 'last_name']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        constraints = [
            # Unicidad case-insensitive a nivel de BD (PostgreSQL)
            models.UniqueConstraint(
                models.functions.Lower('email'),
                name='unique_email_ci',
                violation_error_message='Ya existe una cuenta con este correo electrónico.',
            ),
        ]

    def save(self, *args, **kwargs):
        # Normalizar email a minúsculas antes de guardar
        if self.email:
            self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} {self.last_name}'

