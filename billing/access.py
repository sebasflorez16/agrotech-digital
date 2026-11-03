"""Reglas de acceso especiales (dueño / superusuario sin límites de plan)."""
from django.conf import settings


def is_unlimited_user(user):
    """True para el dueño/superusuario: no se le aplican límites de plan."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) is True:
        return True

    owner = (getattr(settings, "OWNER_USERNAME", "") or "").strip().lower()
    if owner:
        for value in (getattr(user, "username", ""), getattr(user, "email", "")):
            if value and value.strip().lower() == owner:
                return True
    return False
