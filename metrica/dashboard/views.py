"""import json
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

User = get_user_model()

class DashboardView(LoginRequiredMixin, TemplateView):
    pass

index_dashboard_view = DashboardView.as_view(template_name="dashboard/index.html")
crypto_view = DashboardView.as_view(template_name="dashboard/crypto.html")
crm_view = DashboardView.as_view(template_name="dashboard/crm.html")
project_view = DashboardView.as_view(template_name="dashboard/ecommerce.html")
ecommerce_view = DashboardView.as_view(template_name="dashboard/project.html")
#helpdesk_view = DashboardView.as_view(template_name="dashboard/helpdesk.html")
hospital_view = DashboardView.as_view(template_name="dashboard/hospital.html")
"""