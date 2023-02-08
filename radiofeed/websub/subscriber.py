from __future__ import annotations

import hashlib
import hmac
import http

from datetime import timedelta
from typing import Final

import requests

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone

from radiofeed.websub.models import Subscription

_DEFAULT_LEASE_SECONDS: Final = 24 * 60 * 60 * 7  # 1 week
_MAX_BODY_SIZE: Final = 1024**2


def subscribe(
    subscription: Subscription,
    mode: str = "subscribe",  # type: ignore
) -> None:
    """Subscribes podcast to provided websub hub.

    Raises:
        requests.RequestException: invalid request
    """
    response = requests.get(
        subscription.hub,
        {
            "hub.mode": mode,
            "hub.topic": subscription.topic,
            "hub.secret": subscription.secret.hex,
            "hub.callback": subscription.get_callback_url(),
            "hub.lease_seconds": str(_DEFAULT_LEASE_SECONDS),
            # these two fields are not present in websub v4+
            # but keeping around for feeds using older hubs
            "hub.verify_token": str(subscription.pk),
            "hub.verify": "async",
        },
        headers={
            "User-Agent": settings.USER_AGENT,
        },
        timeout=10,
    )

    response.raise_for_status()

    now = timezone.now()

    subscription.requested = now

    if response.status_code != http.HTTPStatus.ACCEPTED:
        subscription.expires = (
            now + timedelta(seconds=_DEFAULT_LEASE_SECONDS)
            if mode == "subscribe"
            else None
        )

    subscription.save()


def check_signature(request: HttpRequest, subscription: Subscription) -> bool:
    """Check X-Hub-Signature header against the secret in database."""
    try:
        if int(request.headers["content-length"]) > _MAX_BODY_SIZE:
            return False

        algo, signature = request.headers["X-Hub-Signature"].split("=")
        digest = hmac.new(
            subscription.secret.hex.encode("utf-8"),
            request.body,
            getattr(hashlib, algo),
        ).hexdigest()

    except (AttributeError, KeyError, ValueError):
        return False

    return hmac.compare_digest(signature, digest)
