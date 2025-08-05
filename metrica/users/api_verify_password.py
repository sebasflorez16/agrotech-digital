from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework import status

class VerifyPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        password = request.data.get('password')
        user = request.user
        if user.check_password(password):
            return Response({'valido': True})
        return Response({'valido': False}, status=status.HTTP_401_UNAUTHORIZED)
