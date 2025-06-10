# authentication/forms.py
"""from django import forms
from django.contrib.auth.forms import AuthenticationForm

class CustomLoginForm(forms.Form):
    login = forms.CharField(max_length=150, required=True, label='Email o Username')
    password = forms.CharField(widget=forms.PasswordInput, required=True, label='Contraseña')

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('login')
        password = cleaned_data.get('password')

        if username and password:
            # Aquí puedes agregar lógica adicional de validación si es necesario
            pass

        return cleaned_data"""