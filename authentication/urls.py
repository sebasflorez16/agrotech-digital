from django.urls import path

from .views import LoginView
 
app_name = "authentication" 

urlpatterns = [
  # 🔹 Solo API endpoints - Sin vistas tradicionales HTML
  path("login/", LoginView.as_view(), name="api_login"),  # Vista de API para JWT
]