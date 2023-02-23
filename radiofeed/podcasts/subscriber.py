from __future__ import annotations

import hashlib
import hmac
import uuid

from datetime import timedelta
from typing import Final

import requests

from django.conf import settings
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone

from radiofeed.podcasts.models import Podcast
from radiofeed.template import build_absolute_uri

DEFAULT_LEASE_SECONDS: Final = 24 * 60 * 60 * 7  # 1 week


def get_podcasts_for_subscribe() -> QuerySet[Podcast]:
    """Return podcasts for websub subscription requests."""
    return Podcast.objects.filter(
        Q(websub_mode="")
        | Q(
            websub_mode="subscribe",
            websub_expires__lt=timezone.now(),
        ),
        websub_hub__isnull=False,
    ).order_by("websub_expires", "parsed")


def subscribe(
    podcast: Podcast,
    mode: str = "subscribe",
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> requests.Response:
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

    podcast.websub_mode = mode
    podcast.websub_secret = secret

    podcast.websub_expires = (
        timezone.now() + timedelta(seconds=lease_seconds)
        if mode == "subscribe"
        else None
    )

    podcast.save()

    return response


def check_signature(
    request: HttpRequest, podcast: Podcast, max_body_size: int = 1024**2
) -> bool:
    """Check X-Hub-Signature header against the secret in database."""
    try:
        if int(request.headers["content-length"]) > max_body_size:
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
