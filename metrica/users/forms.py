from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django import forms
User = get_user_model()


class UserChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserCreationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email", "name", "last_name", "image", "is_active", "is_staff")

        error_messages = {
            "username": {"unique": _("This username has already been taken.")}
        }

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "name", "last_name", "image", "address", "phone", "is_staff", "is_active", "role"]