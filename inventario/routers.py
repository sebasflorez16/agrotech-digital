from rest_framework import routers
from .views import (
    SupplyViewSet, WarehouseViewSet, InventoryMovementViewSet, MachineryViewSet,
    SupplierViewSet, CompanyViewSet, CategoryViewSet, SubcategoryViewSet, PersonViewSet
)

router = routers.DefaultRouter()
router.register(r'supplies', SupplyViewSet)
router.register(r'warehouses', WarehouseViewSet)
router.register(r'inventory-movements', InventoryMovementViewSet)
router.register(r'machinery', MachineryViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'companies', CompanyViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'subcategories', SubcategoryViewSet)
router.register(r'persons', PersonViewSet)

urlpatterns = router.urls
