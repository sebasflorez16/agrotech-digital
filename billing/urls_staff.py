"""
URLs del Panel de Control del Operador (Staff Dashboard).
Montadas en public_urls bajo el prefijo /staff/.
"""
from django.urls import path
from billing.views_staff import StaffDashboardHTML, StaffMetricsAPI, StaffTenantsAPI

urlpatterns = [
    # HTML
    path("", StaffDashboardHTML, name="staff_dashboard"),
    # JSON API
    path("api/metrics/", StaffMetricsAPI.as_view(), name="staff_metrics"),
    path("api/tenants/", StaffTenantsAPI.as_view(), name="staff_tenants"),
]
