from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import CropType, Crop, CropStage, CropProgressPhoto, CropInput, LaborInput, CropEvent
from .serializers import (
    CropTypeSerializer, CropSerializer, CropStageSerializer,
    CropProgressPhotoSerializer, CropInputSerializer, LaborInputSerializer, CropEventSerializer
)

# Create your views here.

class CropTypeViewSet(viewsets.ModelViewSet):
    queryset = CropType.objects.all()
    serializer_class = CropTypeSerializer
    permission_classes = [IsAuthenticated]

    # Permite crear uno o varios tipos de cultivo en una sola petición POST
    # Si el body es una lista, usa many=True en el serializer
    def create(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)

class CropViewSet(viewsets.ModelViewSet):
    queryset = Crop.objects.all()
    serializer_class = CropSerializer
    permission_classes = [IsAuthenticated]

class CropStageViewSet(viewsets.ModelViewSet):
    queryset = CropStage.objects.all()
    serializer_class = CropStageSerializer
    permission_classes = [IsAuthenticated]

class CropProgressPhotoViewSet(viewsets.ModelViewSet):
    queryset = CropProgressPhoto.objects.all()
    serializer_class = CropProgressPhotoSerializer
    permission_classes = [IsAuthenticated]

class CropInputViewSet(viewsets.ModelViewSet):
    queryset = CropInput.objects.all()
    serializer_class = CropInputSerializer
    permission_classes = [IsAuthenticated]

class LaborInputViewSet(viewsets.ModelViewSet):
    queryset = LaborInput.objects.all()
    serializer_class = LaborInputSerializer
    permission_classes = [IsAuthenticated]

class CropEventViewSet(viewsets.ModelViewSet):
    queryset = CropEvent.objects.all()
    serializer_class = CropEventSerializer
    permission_classes = [IsAuthenticated]
