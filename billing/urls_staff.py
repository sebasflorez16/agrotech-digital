"""
URLs de las APIs del Panel de Control del Operador.
Montadas en public_urls bajo el prefijo /staff/.
El HTML del panel está en el frontend (Netlify), no aquí.
"""
from django.urls import path
from billing.views_staff import StaffMetricsAPI, StaffTenantsAPI

urlpatterns = [
    # JSON API — requieren JWT Bearer con is_staff=True
    path("api/metrics/", StaffMetricsAPI.as_view(), name="staff_metrics"),
    path("api/tenants/", StaffTenantsAPI.as_view(), name="staff_tenants"),
]
