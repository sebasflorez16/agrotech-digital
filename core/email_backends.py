"""Backend de email por API HTTPS (Resend).

Railway bloquea la salida SMTP (puerto 587), por lo que Gmail SMTP no es
viable en producción. Resend envía por HTTPS (443) y no requiere abrir puertos.

Configuración:
    RESEND_API_KEY=re_...
    EMAIL_BACKEND=core.email_backends.ResendEmailBackend
    DEFAULT_FROM_EMAIL=AgroTech Digital <noreply@agrotechcolombia.com>

El dominio del remitente debe estar verificado en Resend (SPF/DKIM).
"""

from __future__ import annotations

import base64
import logging
from typing import Iterable

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class ResendEmailBackend(BaseEmailBackend):
    """Envía correos con la API de Resend (HTTPS)."""

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = (getattr(settings, "RESEND_API_KEY", "") or "").strip()
        self.api_url = getattr(settings, "RESEND_API_URL", RESEND_API_URL)

    def _payload(self, message: EmailMessage) -> dict:
        payload = {
            "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
            "to": list(message.to or []),
            "subject": message.subject or "(sin asunto)",
        }

        if message.cc:
            payload["cc"] = list(message.cc)
        if message.bcc:
            payload["bcc"] = list(message.bcc)
        if message.reply_to:
            payload["reply_to"] = list(message.reply_to)

        html_body = None
        if hasattr(message, "alternatives"):
            for content, mimetype in message.alternatives:
                if mimetype == "text/html":
                    html_body = content
                    break

        if html_body:
            payload["html"] = html_body
            payload["text"] = message.body
        else:
            payload["text"] = message.body

        attachments = []
        for attachment in getattr(message, "attachments", []) or []:
            if isinstance(attachment, tuple):
                filename, content, mimetype = attachment
            else:
                filename, content = attachment.filename, attachment.content
            if isinstance(content, str):
                content = content.encode("utf-8")
            attachments.append({
                "filename": filename,
                "content": base64.b64encode(content).decode("ascii"),
            })
        if attachments:
            payload["attachments"] = attachments

        return payload

    def _send_one(self, message: EmailMessage) -> bool:
        payload = self._payload(message)
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15,
            )
        except Exception as exc:
            logger.warning("Resend: error de red enviando '%s': %s", message.subject, exc)
            if self.fail_silently:
                return False
            raise

        if response.status_code >= 400:
            logger.warning(
                "Resend rechazó '%s' (HTTP %s): %s",
                message.subject,
                response.status_code,
                response.text[:500],
            )
            if self.fail_silently:
                return False
            raise ImproperlyConfigured(
                f"Resend HTTP {response.status_code}: {response.text[:300]}"
            )
        return True

    def send_messages(self, email_messages: Iterable[EmailMessage]) -> int:
        if not self.api_key:
            message = (
                "RESEND_API_KEY no está configurada. "
                "Configura el envío de email por API HTTPS."
            )
            logger.error(message)
            if self.fail_silently:
                return 0
            raise ImproperlyConfigured(message)

        sent = 0
        for message in email_messages:
            if self._send_one(message):
                sent += 1
        return sent
