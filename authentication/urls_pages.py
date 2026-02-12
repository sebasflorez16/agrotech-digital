"""
URLs de páginas de autenticación (HTML templates).

Page Endpoints:
- GET /auth/login/          → Página de login
- GET /auth/register/       → Página de registro
- GET /auth/recover-password/  → Página de recuperación de contraseña
"""

from django.urls import path
from .views import (
    LoginPage, RegisterPage, RecoverPasswordPage, Error404Page, Error500Page
)

urlpatterns = [
    path("login/", LoginPage.as_view(), name="login_page"),
    path("register/", RegisterPage.as_view(), name="register_page"),
    path("recover-password/", RecoverPasswordPage.as_view(), name="recover_password_page"),
    path("404/", Error404Page.as_view(), name="error_404"),
    path("500/", Error500Page.as_view(), name="error_500"),
]
