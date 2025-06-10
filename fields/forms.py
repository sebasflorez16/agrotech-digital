from django import forms
from leaflet.forms.widgets import LeafletWidget
from .models import Field

class FieldForm(forms.ModelForm):
    class Meta:
        model = Field    
        fields = ['name', 'description', 'field_type', 'state', 'gom']
        widgets = {
            'gom': LeafletWidget(), #Wiget para el campo de área geográfica
        }