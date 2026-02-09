"""
URLs de autenticación para AgroTech Digital SaaS.

Endpoints:
- POST /api/auth/register/  → Registro completo
- POST /api/auth/login/     → Login con JWT
- GET  /api/auth/me/        → Datos del usuario autenticado
"""

from django.urls import path
from .views import RegisterView, LoginView, MeView

app_name = "authentication"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("me/", MeView.as_view(), name="me"),
]