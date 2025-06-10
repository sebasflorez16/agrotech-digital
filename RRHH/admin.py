from django.contrib import admin
from .models import Department, Position, Employee, TemporaryEmployee, ContractorEmployee
from base_agrotech.models import PaymentMethod

# Register your models here\


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name')
    search_fields = ('first_name', 'last_name')


@admin.register(TemporaryEmployee)
class TemporaryEmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'description')
    search_fields = ('first_name', 'last_name')


@admin.register(ContractorEmployee)
class ContractorEmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'rut', 'description')
    search_fields = ('first_name', 'last_name', 'rut')


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount', 'description')
    search_fields = ('name',)