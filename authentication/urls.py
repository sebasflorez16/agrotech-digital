"""
URLs de autenticación para AgroTech Digital SaaS.

Endpoints:
- POST /api/auth/register/          → Registro completo
- POST /api/auth/login/             → Login con JWT
- GET  /api/auth/me/                → Datos del usuario autenticado
- POST /api/auth/logout/            → Cerrar sesión
- POST /api/auth/password/change/   → Cambiar contraseña
- PATCH /api/auth/profile/          → Actualizar perfil
"""

from django.urls import path
from .views import RegisterView, LoginView, MeView, LogoutView, PasswordChangeView, ProfileUpdateView

app_name = "authentication"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("me/", MeView.as_view(), name="me"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password/change/", PasswordChangeView.as_view(), name="password_change"),
    path("profile/", ProfileUpdateView.as_view(), name="profile_update"),
]