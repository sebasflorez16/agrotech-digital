from django.contrib import admin
from .models import Category, Subcategory, Supplier, Company, Warehouse, Supply, Machinery, InventoryMovement

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created", "updated")
    search_fields = ("name",)

@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "created", "updated")
    search_fields = ("name",)
    list_filter = ("category",)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "contact", "phone", "email", "created", "updated")
    search_fields = ("name", "company__name")
    list_filter = ("company",)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "rut", "address", "phone", "email", "created", "updated")
    search_fields = ("name", "rut")

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "is_active", "created", "updated")
    search_fields = ("name", "location")
    list_filter = ("is_active",)

@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    list_display = ("name", "warehouse", "quantity", "unit_value", "created", "updated")
    search_fields = ("name", "warehouse__name")
    list_filter = ("warehouse",)

@admin.register(Machinery)
class MachineryAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "model", "serial_number", "year", "warehouse", "category", "subcategory", "created", "updated")
    search_fields = ("name", "brand", "model", "serial_number")
    list_filter = ("warehouse", "category", "subcategory")

@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ("movement_type", "asset", "quantity", "unit_value", "origin_location", "destination_location", "date", "user", "created", "updated")
    search_fields = ("user", "origin_location", "destination_location", "notes")
    list_filter = ("movement_type", "origin_location", "destination_location", "user")
