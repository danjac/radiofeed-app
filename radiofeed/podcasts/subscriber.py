from __future__ import annotations

import hashlib
import hmac
import uuid

from datetime import timedelta
from typing import Final

import requests

from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone

from radiofeed.podcasts.models import Podcast
from radiofeed.template import build_absolute_uri

DEFAULT_LEASE_SECONDS: Final = 24 * 60 * 60 * 7  # 1 week

_MAX_BODY_SIZE: Final = 1024**2


def subscribe(podcast: Podcast, mode: str = "subscribe") -> requests.Response:
    """Subscribes podcast to provided websub hub.

    Raises:
        requests.RequestException: invalid request
    """
    secret = uuid.uuid4()

    response = requests.post(
        podcast.websub_hub,
        {
            "hub.mode": mode,
            "hub.topic": podcast.rss,
            "hub.secret": secret.hex,
            "hub.lease_seconds": str(DEFAULT_LEASE_SECONDS),
            "hub.callback": build_absolute_uri(
                reverse("podcasts:websub_callback", args=[podcast.pk])
            ),
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": settings.USER_AGENT,
        },
        allow_redirects=True,
        timeout=10,
    )

    response.raise_for_status()

    now = timezone.now()

    podcast.websub_requested = now
    podcast.websub_secret = secret

    podcast.websub_expires = (
        now + timedelta(seconds=DEFAULT_LEASE_SECONDS) if mode == "subscribe" else None
    )

    podcast.save()

    return response


def check_signature(request: HttpRequest, podcast: Podcast) -> bool:
    """Check X-Hub-Signature header against the secret in database."""
    try:
        if int(request.headers["content-length"]) > _MAX_BODY_SIZE:
            return False

        algo, signature = request.headers["X-Hub-Signature"].split("=")
        digest = hmac.new(
            podcast.websub_secret.hex.encode("utf-8"),
            request.body,
            getattr(hashlib, algo),
        ).hexdigest()

    except (AttributeError, KeyError, ValueError):
        return False

    return hmac.compare_digest(signature, digest)
