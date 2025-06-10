from django.shortcuts import render
from django.views.generic import TemplateView
# Create your views here.


class FieldView(TemplateView):
    template_name = 'fields/maps-leaflet.html'

