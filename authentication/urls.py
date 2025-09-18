from django.urls import path

from .views import LoginView, DashboardView, CustomLoginView
 
app_name = "authentication" 

urlpatterns = [
  path("login/", CustomLoginView.as_view(), name="login"),  # Vista tradicional con formulario
  path("api/login/", LoginView.as_view(), name="api_login"),  # Vista de API para JWT
  path("dashboard/", DashboardView.as_view(), name="dashboard"),
]