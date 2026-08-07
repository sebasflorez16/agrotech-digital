"""
URLs de las APIs del Panel de Control del Operador.
Montadas en public_urls bajo el prefijo /staff/.
"""
from django.urls import path
from billing.views_staff import (
    StaffDashboardView,
    StaffFinancialsAPI,
    StaffMetricsAPI,
    StaffTenantActionsAPI,
    StaffTenantDetailAPI,
    StaffTenantsAPI,
)

urlpatterns = [
    path("", StaffDashboardView.as_view(), name="staff_dashboard"),
    path("api/metrics/", StaffMetricsAPI.as_view(), name="staff_metrics"),
    path("api/tenants/", StaffTenantsAPI.as_view(), name="staff_tenants"),
    path("api/tenants/<int:tenant_id>/", StaffTenantDetailAPI.as_view(), name="staff_tenant_detail"),
    path("api/tenants/<int:tenant_id>/<str:action>/", StaffTenantActionsAPI.as_view(), name="staff_tenant_action"),
    path("api/financials/", StaffFinancialsAPI.as_view(), name="staff_financials"),
]
