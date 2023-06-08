import uuid
from datetime import timedelta
from typing import Final, Literal

import requests
from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models import F, Q, QuerySet
from django.utils import timezone

from radiofeed.websub.models import Subscription

SUBSCRIBE: Final = "subscribe"
UNSUBSCRIBE: Final = "unsubscribe"

MODE = Literal["subscribe", "unsubscribe"]

DEFAULT_LEASE_SECONDS: Final = 24 * 60 * 60 * 7  # 1 week
MAX_NUM_RETRIES: Final = 3


def get_subscriptions_for_update() -> QuerySet[Subscription]:
    """Return subscriptions for websub subscription requests."""
    return Subscription.objects.filter(
        Q(
            mode="",
        )
        | Q(
            mode=SUBSCRIBE,
            # check any expiring within one hour
            expires__lt=timezone.now() + timedelta(hours=1),
        ),
        podcast__active=True,
        num_retries__lt=MAX_NUM_RETRIES,
    ).order_by(
        F("expires").asc(nulls_first=True),
        F("created").desc(),
    )


def subscribe(
    subscription: Subscription,
    mode: MODE = SUBSCRIBE,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> requests.Response | None:
    """Subscribes podcast to provided websub hub.

    Raises:
        requests.RequestException: invalid request
    """
    secret = uuid.uuid4()

    scheme = "https" if settings.USE_HTTPS else "http"
    site = Site.objects.get_current()

    payload = {
        "hub.mode": mode,
        "hub.topic": subscription.topic,
        "hub.callback": f"{scheme}://{site.domain}{subscription.get_callback_url()}",
    }

    if mode == SUBSCRIBE:  # type: ignore
        payload = {
            **payload,
            "hub.secret": secret.hex,
            "hub.lease_seconds": str(lease_seconds),
        }

    try:
        response = requests.post(
            subscription.hub,
            payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": settings.USER_AGENT,
            },
            allow_redirects=True,
            timeout=10,
        )

        response.raise_for_status()

        subscription.mode = mode
        subscription.secret = secret if mode == SUBSCRIBE else None
        subscription.requested = timezone.now()
        subscription.num_retries = 0

    except requests.RequestException:
        subscription.num_retries += 1
        raise
    finally:
        subscription.save()

    return response
