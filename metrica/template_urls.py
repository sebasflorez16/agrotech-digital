"""
URLs para servir plantillas HTML que antes se accedían directamente.
Necesario para producción donde Django debe manejar todas las rutas.
"""
from django.urls import path
from .template_views import (
    LoginTemplateView, 
    DashboardTemplateView, 
    VerticalBaseTemplateView,
    login_template_view,
    dashboard_template_view
)

app_name = "templates"

urlpatterns = [
    # Rutas para plantillas de autenticación
    path('authentication/login.html', LoginTemplateView.as_view(), name='login'),
    path('authentication/login/', LoginTemplateView.as_view(), name='login_alt'),
    
    # Rutas para dashboard y plantilla base
    path('vertical_base.html', VerticalBaseTemplateView.as_view(), name='vertical_base'),
    path('dashboard.html', DashboardTemplateView.as_view(), name='dashboard'),
    
    # Rutas de función para compatibilidad
    path('auth/login.html', login_template_view, name='login_func'),
    path('base.html', dashboard_template_view, name='base_func'),
]
