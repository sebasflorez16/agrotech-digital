"""Envío de eventos server-side a Meta Conversions API (CAPI).

Objetivos:
- Medir registros y compras aunque el navegador bloquee el pixel.
- Deduplicar con el pixel usando el mismo `event_id`.
- No romper nunca el flujo de negocio si Meta falla o no está configurado.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.facebook.com/{version}/{pixel_id}/events"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def _normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    # Colombia: si viene sin indicativo, asumir +57.
    if len(digits) == 10 and digits.startswith("3"):
        digits = "57" + digits
    return digits


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _hashed_user_data(
    email: str = "",
    phone: str = "",
    first_name: str = "",
    last_name: str = "",
    external_id: str = "",
    fbp: str = "",
    fbc: str = "",
    client_ip: str = "",
    user_agent: str = "",
) -> dict:
    data = {}
    if email:
        data["em"] = [_sha256(_normalize_email(email))]
    if phone:
        data["ph"] = [_sha256(_normalize_phone(phone))]
    if first_name:
        data["fn"] = [_sha256(_normalize_name(first_name))]
    if last_name:
        data["ln"] = [_sha256(_normalize_name(last_name))]
    if external_id:
        data["external_id"] = [_sha256(str(external_id))]
    if fbp:
        data["fbp"] = fbp
    if fbc:
        data["fbc"] = fbc
    if client_ip:
        data["client_ip_address"] = client_ip
    if user_agent:
        data["client_user_agent"] = user_agent
    return data


def send_event(
    event_name: str,
    event_id: str,
    *,
    email: str = "",
    phone: str = "",
    first_name: str = "",
    last_name: str = "",
    external_id: str = "",
    fbp: str = "",
    fbc: str = "",
    client_ip: str = "",
    user_agent: str = "",
    event_source_url: str = "",
    value: Optional[float] = None,
    currency: str = "COP",
    custom_data: Optional[dict] = None,
) -> bool:
    """Envía un evento a Meta CAPI. Devuelve True si Meta lo aceptó.

    Si `META_CAPI_ENABLED` es False o falta el token, no hace nada. Cualquier
    excepción se registra y se ignora: la medición nunca debe tumbar un pago
    ni un registro.
    """
    if not getattr(settings, "META_CAPI_ENABLED", False):
        return False

    pixel_id = (getattr(settings, "META_PIXEL_ID", "") or "").strip()
    access_token = (getattr(settings, "META_CAPI_ACCESS_TOKEN", "") or "").strip()
    if not pixel_id or not access_token:
        logger.debug("Meta CAPI sin pixel/token configurado")
        return False

    if not event_id:
        event_id = f"{event_name}_{int(time.time() * 1000)}"

    data = custom_data.copy() if custom_data else {}
    if value is not None:
        data["value"] = float(value)
        data["currency"] = currency

    event = {
        "event_name": event_name,
        "event_time": int(time.time()),
        "event_id": str(event_id),
        "action_source": "website",
        "user_data": _hashed_user_data(
            email=email,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            external_id=external_id,
            fbp=fbp,
            fbc=fbc,
            client_ip=client_ip,
            user_agent=user_agent,
        ),
    }
    if event_source_url:
        event["event_source_url"] = event_source_url
    if data:
        event["custom_data"] = data

    payload = {"data": [event]}
    test_code = (getattr(settings, "META_CAPI_TEST_EVENT_CODE", "") or "").strip()
    if test_code:
        payload["test_event_code"] = test_code

    version = (getattr(settings, "META_GRAPH_API_VERSION", "v20.0") or "v20.0").strip()
    url = GRAPH_URL.format(version=version, pixel_id=pixel_id)

    try:
        response = requests.post(
            url,
            params={"access_token": access_token},
            json=payload,
            timeout=5,
        )
        if response.status_code >= 400:
            logger.warning(
                "Meta CAPI rechazó %s (HTTP %s): %s",
                event_name,
                response.status_code,
                response.text[:400],
            )
            return False
        return True
    except Exception as exc:
        logger.warning("Meta CAPI falló para %s: %s", event_name, exc)
        return False


def request_meta_context(request) -> dict:
    """Extrae IP, user-agent, fbp y fbc de un request Django."""
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return {
        "client_ip": forwarded or request.META.get("REMOTE_ADDR", ""),
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        "fbp": request.COOKIES.get("_fbp", ""),
        "fbc": request.COOKIES.get("_fbc", ""),
    }
