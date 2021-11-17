from __future__ import annotations

import hmac
import traceback

from datetime import timedelta

import attr
import requests

from django.db.models import Q, QuerySet
from django.urls import reverse
from django.utils import crypto, timezone
from django_rq import job

from jcasts.podcasts.models import Podcast
from jcasts.shared.template import build_absolute_uri

DEFAULT_LEASE_SECONDS = 7 * 24 * 3600


@attr.s
class SubscribeResult:
    podcast_id: int = attr.ib()
    status: str | None = attr.ib(default=None)
    exception: Exception | None = attr.ib(default=None)
    content: bytes | None = None


def subscribe_podcasts():
    for podcast_id in (
        get_podcasts_for_subscription()
        .order_by("websub_status_changed")
        .values_list("pk", flat=True)
    ):
        subscribe.delay(podcast_id)


@job("default")
def subscribe(podcast_id: int) -> SubscribeResult:
    now = timezone.now()

    try:
        podcast = get_podcasts_for_subscription().get(pk=podcast_id)
    except Podcast.DoesNotExist as e:
        return SubscribeResult(podcast_id=podcast_id, exception=e)

    result = SubscribeResult(podcast_id=podcast.id)

    token = crypto.get_random_string(12)

    response = requests.post(
        podcast.websub_hub,
        {
            "hub.callback": build_absolute_uri(
                reverse("podcasts:websub_callback", args=[podcast.id])
            ),
            "hub.mode": "subscribe",
            "hub.verify": "sync",
            "hub.topic": podcast.websub_url,
            "hub.lease_seconds": DEFAULT_LEASE_SECONDS,
            "hub.secret": encode_token(token),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )

    try:
        response.raise_for_status()

        podcast.websub_status = Podcast.WebSubStatus.REQUESTED
        podcast.websub_token = token
        podcast.websub_exception = ""

    except requests.RequestException as e:

        podcast.websub_status = Podcast.WebSubStatus.INACTIVE
        podcast.websub_exception = (
            traceback.format_exc() + "\n" + e.response.content.decode("utf-8")
        )

        result.exception = e
        result.content = e.response.content

    podcast.websub_status_changed = now
    podcast.save()

    result.status = podcast.websub_status  # type: ignore

    return result


def get_podcasts_for_subscription(
    frequency: timedelta = timedelta(hours=1),
) -> QuerySet:
    now = timezone.now()
    return Podcast.objects.active().filter(
        Q(
            websub_status=Podcast.WebSubStatus.PENDING,
        )
        | Q(
            websub_status=Podcast.WebSubStatus.REQUESTED,
            websub_status_changed__lt=now - frequency,
        )
        | Q(
            websub_status=Podcast.WebSubStatus.ACTIVE,
            websub_subscribed__lt=now,
        ),
        websub_hub__isnull=False,
        websub_url__isnull=False,
    )


def compare_signature(token: str, signature: str, method: str) -> bool:
    return (
        hmac.compare_digest(encode_token(token, method), signature) if token else False
    )


def encode_token(token: str, method: str = "sha1") -> str:
    return hmac.new(token.encode(), digestmod=method).hexdigest()
