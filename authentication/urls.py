from django.urls import path

from .views import LoginView, DashboardView
 
app_name = "authentication" 

urlpatterns = [
  path("api/login/", LoginView.as_view(), name="login"),  # Vista de API para JWT
  path("dashboard/", DashboardView.as_view(), name="dashboard"),
]