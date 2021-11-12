from __future__ import annotations

import hashlib
import hmac
import traceback

from datetime import datetime, timedelta

import requests

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils import crypto, timezone
from django_rq import job

from jcasts.podcasts import feed_parser
from jcasts.podcasts.models import Podcast
from jcasts.shared.template import build_absolute_uri


@job("default")
def subscribe(podcast_id: int) -> None:
    try:
        podcast = get_subscribable_podcasts().get(
            pk=podcast_id,
        )
    except Podcast.DoesNotExist:
        return

    podcast.subscribe_secret = crypto.get_random_string(length=30)

    payload = {
        "hub.mode": "subscribe",
        "hub.topic": podcast.rss,
        "hub.callback": build_absolute_uri(
            reverse("podcasts:websub_callback", args=[podcast.id])
        ),
        "hub.secret": create_hexdigest(podcast.subscribe_secret),
        "hub.lease_seconds": settings.WEBSUB_LEASE_TIMEOUT.total_seconds(),
        "hub.verify": "async",
    }

    response = requests.post(podcast.hub, payload)

    try:
        response.raise_for_status()
    except requests.RequestException:
        podcast.hub_exception = traceback.format_exc()
        podcast.subscribe_status = Podcast.SubscribeStatus.ERROR
        podcast.subscribe_secret = None
    else:
        podcast.subscribe_status = Podcast.SubscribeStatus.REQUESTED
        podcast.subscribe_requested = timezone.now()

    podcast.save()


def subscribe_podcasts() -> None:
    for podcast_id in (
        get_subscribable_podcasts()
        .order_by("subscribed", "-pk")
        .values_list("pk", flat=True)
    ):
        subscribe.delay(podcast_id)


def get_subscribable_podcasts() -> QuerySet:
    return Podcast.objects.active().filter(
        Q(
            subscribe_status=Podcast.SubscribeStatus.UNSUBSCRIBED,
        )
        | Q(
            subscribed__lt=timezone.now(),
            subscribe_status=Podcast.SubscribeStatus.SUBSCRIBED,
        ),
        hub__isnull=False,
    )


def handle_content_distribution(request: HttpRequest, podcast: Podcast) -> None:

    if podcast.subscribe_status != Podcast.SubscribeStatus.SUBSCRIBED:
        raise ValidationError("podcast has invalid status")

    try:
        sig_header = request.headers["X-Hub-Signature"]
        method, signature = sig_header.split("=")
    except (KeyError, ValueError):
        raise ValidationError("X-Hub-Signature missing")

    if not matches_signature(podcast.subscribe_secret, signature, method):
        raise ValidationError(
            f"signature {signature} does not match with method {method}"
        )

    # content distribution should contain entire body, so we can
    # just handle immediately

    feed_parser.parse_podcast_feed.delay(podcast.id, request.body)


def verify_intent(
    request: HttpRequest, podcast: Podcast
) -> tuple[str | None, str, datetime | None]:
    # https://w3c.github.io/websub/#hub-verifies-intent
    if (mode := request.GET.get("hub.mode")) not in (
        "subscribe",
        "unsubscribe",
        "denied",
    ):
        raise ValidationError("hub.mode missing or invalid")

    if not (challenge := request.GET.get("hub.challenge")):
        raise ValidationError("hub.challenge is missing")

    if request.GET.get("hub.topic") != podcast.rss:
        raise ValidationError("hub.topic does not match podcast topic")

    if mode == "denied":
        return challenge, Podcast.SubscribeStatus.DENIED, None  # type: ignore

    if mode == "unsubscribe":
        return challenge, Podcast.SubscribeStatus.UNSUBSCRIBED, None  # type: ignore

    try:
        lease_seconds = int(request.GET["hub.lease_seconds"])
    except (KeyError, ValueError, TypeError):
        raise ValidationError("hub.lease_seconds missing or invalid")

    return (
        challenge,
        Podcast.SubscribeStatus.SUBSCRIBED,
        timezone.now() + timedelta(seconds=lease_seconds),
    )  # type: ignore


def create_hexdigest(secret: str, method: str | None = None) -> str:
    return hmac.new(secret.encode(), digestmod=hashlib.sha512).hexdigest()


def matches_signature(secret: str | None, signature: str, method: str) -> bool:
    return (
        hmac.compare_digest(create_hexdigest(secret, method), signature)
        if secret
        else False
    )
