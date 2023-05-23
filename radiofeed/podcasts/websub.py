from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import timedelta
from typing import Final

import requests
from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models import F, Q, QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone

from radiofeed.podcasts.models import Podcast

DEFAULT_LEASE_SECONDS: Final = 24 * 60 * 60 * 7  # 1 week

MAX_NUM_RETRIES: Final = 3


def get_podcasts_for_subscribe() -> QuerySet[Podcast]:
    """Return podcasts for websub subscription requests."""
    return Podcast.objects.filter(
        Q(websub_mode="")
        | Q(
            websub_mode="subscribe",
            websub_expires__lt=timezone.now(),
        ),
        active=True,
        websub_hub__isnull=False,
        num_websub_retries__lt=MAX_NUM_RETRIES,
    ).order_by(
        F("websub_expires").asc(nulls_first=True),
    )


def subscribe(
    podcast: Podcast,
    mode: str = "subscribe",
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> requests.Response | None:
    """Subscribes podcast to provided websub hub.

    Raises:
        requests.RequestException: invalid request
    """
    if podcast.websub_hub is None:
        return None

    secret = uuid.uuid4()

    callback_url = reverse("podcasts:websub_callback", args=[podcast.pk])
    scheme = "https" if settings.USE_HTTPS else "http"
    site = Site.objects.get_current()

    response = requests.post(
        podcast.websub_hub,
        {
            "hub.mode": mode,
            "hub.topic": podcast.rss,
            "hub.secret": secret.hex,
            "hub.lease_seconds": str(DEFAULT_LEASE_SECONDS),
            "hub.callback": f"{scheme}://{site.domain}{callback_url}",
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": settings.USER_AGENT,
        },
        allow_redirects=True,
        timeout=10,
    )

    try:
        response.raise_for_status()

        podcast.websub_mode = mode
        podcast.websub_secret = secret
        podcast.num_websub_retries = 0

        podcast.websub_expires = (
            timezone.now() + timedelta(seconds=lease_seconds)
            if mode == "subscribe"
            else None
        )

    except requests.RequestException:
        podcast.num_websub_retries += 1
        raise
    finally:
        podcast.save()

    return response


def check_signature(
    request: HttpRequest, podcast: Podcast, max_body_size: int = 1024**2
) -> bool:
    """Check X-Hub-Signature header against the secret in database."""
    try:
        if podcast.websub_secret is None:
            return False

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
