"""
Centralized Developer Mode checker.

All subscription-limit bypass points must use this module so the toggle
(activate / deactivate) is respected everywhere consistently.

Flow:
- settings.DEVELOPER_MODE must be True (env var, only in local dev)
- request.user must be authenticated + superuser
- Cache key `dev_mode_active:<user_id>` must be True (defaults to True
  when the key is missing to preserve backward compatibility)
"""

from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "dev_mode_active"


def is_dev_mode_active(request) -> bool:
    if not getattr(settings, "DEVELOPER_MODE", False):
        return False
    if not (request.user.is_authenticated and request.user.is_superuser):
        return False

    cache_key = f"{CACHE_KEY_PREFIX}:{request.user.id}"
    active = cache.get(cache_key, True)
    logger.debug(
        "DevMode check user=%s cache_key=%s active=%s",
        request.user.username, cache_key, active,
    )
    return active


def set_dev_mode(user_id: int, active: bool) -> None:
    cache_key = f"{CACHE_KEY_PREFIX}:{user_id}"
    cache.set(cache_key, active, timeout=None)
    logger.info("DevMode user_id=%s set to %s", user_id, active)
