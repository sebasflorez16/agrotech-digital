from django.http import JsonResponse
from metrica.users.models import User
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
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


# ❌ ELIMINADAS - CustomLoginView y DashboardView que requerían templates HTML
# Solo mantenemos APIs REST para frontend separado
