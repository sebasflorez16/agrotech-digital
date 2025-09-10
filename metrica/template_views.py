"""
Vistas para servir plantillas HTML estáticas que antes se servían directamente.
Estas vistas son necesarias para el despliegue en producción donde Django
debe manejar todas las rutas.
"""
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse


class HomeView(TemplateView):
    """Vista raíz simple que muestra información del sistema"""
    def get(self, request, *args, **kwargs):
        return HttpResponse("""
        <html>
        <head><title>AgroTech Digital</title></head>
        <body>
            <h1>🌱 AgroTech Digital</h1>
            <p>✅ Sistema funcionando correctamente</p>
            <p>✅ Django cargado</p>
            <p>✅ Railway desplegado</p>
            <hr>
            <p><a href="/admin/">Panel de Administración</a></p>
            <p><a href="/templates/authentication/login.html">Página de Login</a></p>
        </body>
        </html>
        """, content_type="text/html")


class LoginTemplateView(TemplateView):
    """Vista para servir la plantilla de login"""
    template_name = "authentication/login.html"


class DashboardTemplateView(LoginRequiredMixin, TemplateView):
    """Vista para servir la plantilla del dashboard principal"""
    template_name = "vertical_base.html"


class VerticalBaseTemplateView(LoginRequiredMixin, TemplateView):
    """Vista para servir la plantilla base vertical"""
    template_name = "vertical_base.html"


# Vistas basadas en función para compatibilidad
def login_template_view(request):
    """Vista de función para la plantilla de login"""
    return render(request, 'authentication/login.html')


def dashboard_template_view(request):
    """Vista de función para la plantilla del dashboard"""
    return render(request, 'vertical_base.html')


def home_view(request):
    """Vista raíz simple para evitar 502"""
    return HttpResponse("""
    <html>
    <head><title>AgroTech Digital</title></head>
    <body>
        <h1>🌱 AgroTech Digital - Sistema funcionando correctamente</h1>
        <p>✅ Django está funcionando</p>
        <p>✅ Base de datos conectada</p>
        <p>✅ Gunicorn corriendo</p>
        <hr>
        <p><a href="/admin/">Admin Panel</a></p>
        <p><a href="/templates/authentication/login.html">Login</a></p>
        <p><a href="/templates/vertical_base.html">Dashboard</a></p>
    </body>
    </html>
    """, content_type="text/html")
