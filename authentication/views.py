
from django.http import JsonResponse
from metrica.users.models import User
from rest_framework.response import Response
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework import status

from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

class LoginView(ObtainAuthToken):
    permission_classes = [AllowAny]  # Permitir acceso sin autenticación

    def options(self, request, *args, **kwargs):
        """ Manejar preflight de CORS """
        response = JsonResponse({"message": "CORS preflight OK"})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    def post(self, request):
        """Vista basada en clase para autenticación con JWT"""
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)

        if user:
            refresh = RefreshToken.for_user(user)
            response = Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            })
        else:
            response = Response({"error": "Credenciales inválidas"}, status=401)

        # Agregar cabeceras CORS a la respuesta
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "message": "Bienvenido al dashboard",
            "user_count": User.objects.count()
        })






"""login_view = AuthenticationView.as_view(template_name = "authentication/auth-login.html")
loginAlt_view = AuthenticationView.as_view(template_name = "authentication/auth-login-alt.html")
register_view = AuthenticationView.as_view(template_name = "authentication/auth-register.html")
registerAlt_view = AuthenticationView.as_view(template_name = "authentication/auth-register-alt.html")
recoverPW_view = AuthenticationView.as_view(template_name = "authentication/auth-recover-pw.html")
recoverPWAlt_view = AuthenticationView.as_view(template_name = "authentication/auth-recover-pw-alt.html")
lockscreen_view = AuthenticationView.as_view(template_name = "authentication/auth-lock-screen.html")
lockscreenAlt_view = AuthenticationView.as_view(template_name = "authentication/auth-lock-screen-alt.html")
auth404_view = AuthenticationView.as_view(template_name = "authentication/auth-404.html")
auth404Alt_view = AuthenticationView.as_view(template_name = "authentication/auth-404-alt.html")
auth500_view = AuthenticationView.as_view(template_name = "authentication/auth-500.html")
auth500Alt_view = AuthenticationView.as_view(template_name = "authentication/auth-500Alt.html")"""