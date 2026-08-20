from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django import forms
User = get_user_model()


class UserChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserCreationForm(forms.ModelForm):
    """
    Formulario de creación de usuarios dentro de un tenant.

    Incluye contraseña (con set_password) y rol. El tenant se asigna en la vista
    (request.tenant), no desde el formulario.
    """
    password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput, min_length=8)
    password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput)
    role = forms.ChoiceField(label='Rol', choices=User.ROLE_CHOICES, initial='employee')

    class Meta:
        model = User
        fields = ("username", "email", "name", "last_name", "image", "role", "is_active")

        error_messages = {
            "username": {"unique": _("Este nombre de usuario ya está en uso.")}
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "name", "last_name", "image", "address", "phone", "is_staff", "is_active", "role"]
