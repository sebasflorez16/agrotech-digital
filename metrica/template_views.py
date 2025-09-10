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
    """Vista raíz que redirige al dashboard o login según autenticación"""
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/templates/vertical_base.html')
        else:
            return redirect('/templates/authentication/login.html')


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
    return HttpResponse("AgroTech Digital - Sistema funcionando correctamente")
