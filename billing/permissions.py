"""
Permisos del panel de operador (super-admin) — AgroTech Digital.

StaffAccessPermission: doble verificación de acceso.
- is_staff=True (factor 1: quién eres)
- X-Staff-Access-Key (factor 2: clave de operador)
"""
import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class StaffAccessPermission(BasePermission):
    """
    Doble verificación de acceso al panel del operador.

    Factor 1: usuario is_staff=True + is_superuser=True
    Factor 2: header X-Staff-Access-Key coincide con settings.STAFF_ACCESS_KEY

    Mensaje de error descriptivo para cada caso.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_staff or not request.user.is_superuser:
            logger.warning(
                f"[STAFF] Acceso denegado: {request.user} no es staff/superuser"
            )
            self.message = (
                "Acceso restringido al panel del operador. "
                "Solo administradores del sistema."
            )
            return False

        access_key = request.headers.get(
            "X-Staff-Access-Key", ""
        ) or request.query_params.get("access_key", "")

        configured_key = getattr(settings, "STAFF_ACCESS_KEY", None)
        if not configured_key:
            logger.warning("[STAFF] STAFF_ACCESS_KEY no configurada en settings!")
            self.message = "Panel del operador no configurado en este entorno."
            return False

        if access_key != configured_key:
            logger.warning(
                f"[STAFF] Clave de acceso inválida para {request.user.username}"
            )
            self.message = (
                "Clave de operador inválida. "
                "Incluye el header X-Staff-Access-Key con tu clave de acceso."
            )
            return False

        return True
