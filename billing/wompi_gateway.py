"""
Wompi Payment Gateway — Colombia.
Integracion via Wompi Payment Links (API v1).

Wompi soporta: Nequi, PSE, tarjetas credito/debito, efectivo (Bancolombia/Baloto).

Variables de entorno requeridas:
    WOMPI_PUBLIC_KEY      — llave publica (para el frontend)
    WOMPI_PRIVATE_KEY     — llave privada (para API calls)
    WOMPI_EVENTS_KEY      — secreto para firmar webhooks
    WOMPI_SANDBOX         — "true" para modo prueba

Referencia: https://docs.wompi.co/docs/colombia
"""

import hashlib
import hmac
import json
import logging
import re
from typing import Dict, Any, Optional

import requests
from django.conf import settings

from .gateways import PaymentGateway

logger = logging.getLogger(__name__)


def _wompi_base():
    sandbox = getattr(settings, "WOMPI_SANDBOX", "true").lower() in ("1", "true", "yes")
    return "https://sandbox.wompi.co/v1" if sandbox else "https://production.wompi.co/v1"


def _wompi_headers():
    return {
        "Authorization": f"Bearer {getattr(settings, 'WOMPI_PRIVATE_KEY', '')}",
        "Content-Type": "application/json",
    }


def _verify_wompi_signature(payload: bytes, signature_header: str) -> bool:
    """Verifica firma HMAC-SHA256 del webhook de Wompi."""
    secret = getattr(settings, "WOMPI_EVENTS_KEY", "")
    if not secret or not signature_header:
        return False
    expected = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


class WompiGateway(PaymentGateway):
    """Pasarela Wompi Colombia (Payment Links)."""

    def create_subscription(self, user, plan, payment_method_token=None) -> Dict[str, Any]:
        """
        Crea un Payment Link en Wompi para el plan seleccionado.
        El pago se confirma via webhook.

        Args:
            user: User Django
            plan: billing.models.Plan
            payment_method_token: no usado (Wompi decide metodos en su checkout)

        Returns:
            dict con success, checkout_url, wompi_link_id
        """
        base = _wompi_base()
        price_cents = int(plan.price_cop * 100)

        import uuid
        reference = f"sub_{user.id}_{uuid.uuid4().hex[:8]}"

        payload = {
            "name": f"Suscripcion AgroTech — {plan.name}",
            "description": plan.description or f"Plan {plan.name}",
            "single_use": False,
            "collect_shipping": False,
            "currency": "COP",
            "amount_in_cents": price_cents,
            "reference": reference,
            "expires_at": None,  # Sin expiracion
            "redirect_url": getattr(settings, "SITE_URL", "http://localhost:8000")
            + "/billing/success/?ref="
            + reference,
        }

        try:
            resp = requests.post(
                f"{base}/payment_links",
                json=payload,
                headers=_wompi_headers(),
                timeout=15,
            )
            data = resp.json()
            if resp.status_code in (200, 201):
                link_data = data.get("data", data)
                return {
                    "success": True,
                    "wompi_link_id": link_data.get("id", ""),
                    "checkout_url": link_data.get("url", link_data.get("checkout_url", "")),
                    "reference": reference,
                }
            else:
                error_msg = data.get("error", {}).get("reason", resp.text)
                logger.error(f"[WOMPI] Error creando payment link: {resp.status_code} — {error_msg}")
                return {"success": False, "error": error_msg}
        except Exception as e:
            logger.error(f"[WOMPI] Excepcion creando payment link: {e}")
            return {"success": False, "error": str(e)}

    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        return {"success": True, "message": "Wompi no maneja cancelacion de payment links"}

    def get_subscription_status(self, wompi_link_id: str) -> Dict[str, Any]:
        base = _wompi_base()
        try:
            resp = requests.get(f"{base}/payment_links/{wompi_link_id}", headers=_wompi_headers(), timeout=10)
            if resp.status_code == 200:
                link = resp.json().get("data", resp.json())
                return {
                    "status": link.get("status", "unknown"),
                    "amount_paid": link.get("amount_in_cents", 0) / 100,
                    "reference": link.get("reference", ""),
                }
            return {"status": "error", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def handle_webhook(self, request) -> Dict[str, Any]:
        payload = request.body
        signature = request.headers.get("X-Event-Checksum", "")

        if not _verify_wompi_signature(payload, signature):
            logger.warning("[WOMPI] Firma de webhook invalida")
            return {"success": False, "error": "invalid_signature"}

        try:
            event = json.loads(payload)
            event_type = event.get("event", "")
            data = event.get("data", {})

            if event_type == "transaction.updated":
                transaction = data.get("transaction", {})
                tx_status = transaction.get("status", "")
                reference = transaction.get("reference", "")

                if tx_status == "APPROVED":
                    return {
                        "success": True,
                        "action": "payment_approved",
                        "reference": reference,
                        "transaction_id": transaction.get("id", ""),
                        "amount_cents": transaction.get("amount_in_cents", 0),
                    }
                elif tx_status == "DECLINED":
                    return {
                        "success": True,
                        "action": "payment_declined",
                        "reference": reference,
                    }
                else:
                    return {"success": True, "action": "payment_pending", "reference": reference}

            return {"success": True, "action": "ignored", "event_type": event_type}
        except Exception as e:
            logger.error(f"[WOMPI] Error procesando webhook: {e}")
            return {"success": False, "error": str(e)}

    def get_payment_method_info(self, subscription_id: str) -> Dict[str, Any]:
        status = self.get_subscription_status(subscription_id)
        return {"gateway": "wompi", "method": "payment_link", "status": status.get("status", "unknown")}


# Registrar Wompi en el factory
def _register():
    from .gateways import PaymentGatewayFactory  # noqa: F811
    PaymentGatewayFactory.register_gateway("wompi", WompiGateway)


_register()
