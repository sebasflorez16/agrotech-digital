"""
Permisos personalizados de la capa de trazabilidad/seguridad.

`IsAdminOrReadOnly`: permite lectura a cualquier usuario autenticado y
restringe la escritura (POST/PUT/PATCH/DELETE) solo a administradores
(role='admin') o superusuarios (is_superuser).
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    message = "Solo el administrador puede modificar este registro."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_superuser or getattr(user, "role", None) == "admin"
