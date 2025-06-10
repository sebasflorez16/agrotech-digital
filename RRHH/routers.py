
from rest_framework.routers import DefaultRouter
from .views import (
    DepartamentoViewSet, PosicionViewSet, EmployeeViewSet,
    TemporaryViewSet, ContractorViewSet, ContractorEmployeeViewSet, PaymentMethodViewSet
)
app_name = 'RRHH'

router = DefaultRouter()

router.register(r'empleados', EmployeeViewSet)
router.register(r'departamentos', DepartamentoViewSet)
router.register(r'posiciones', PosicionViewSet)
router.register(r'empleados-temporales', TemporaryViewSet)
router.register(r'contratistas', ContractorViewSet)
router.register(r'contratistas-empleados', ContractorEmployeeViewSet, basename="contratorempleado")
router.register(r'metodos-pago', PaymentMethodViewSet, basename="metodopago")


urlpatterns = router.urls