from __future__ import annotations

import hashlib
import hmac
import traceback

from datetime import datetime, timedelta

import requests

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet
from django.http import HttpRequest, QueryDict
from django.urls import reverse
from django.utils import crypto, timezone
from django_rq import job

from jcasts.podcasts import feed_parser
from jcasts.podcasts.models import Podcast
from jcasts.shared.template import build_absolute_uri


@job("default")
def subscribe(self, podcast_id: int) -> None:
    try:
        podcast = get_subscribable_podcasts().get(
            pk=podcast_id,
        )
    except Podcast.DoesNotExist:
        return

    podcast.subscribe_secret = crypto.get_random_string(length=12)

    payload = {
        "hub.mode": "subscribe",
        "hub.topic": podcast.rss,
        "hub.callback": build_absolute_uri(
            reverse("podcasts:websub_callback", args=[podcast.id])
        ),
        "hub.secret": create_hexdigest(podcast.subscribe_secret),
        "hub.lease_seconds": settings.WEBSUB_LEASE_TIMEOUT.total_seconds(),
    }

    response = requests.post(podcast.hub, payload)

    try:
        response.raise_for_status()
    except requests.RequestException:
        podcast.hub_exception = traceback.format_exc()
        podcast.subscribe_status = Podcast.SubscribeStatus.Error
    else:
        podcast.subscribe_status = Podcast.SubscribeStatus.Requested
        podcast.subscribe_requested = timezone.now()

    podcast.save()


def subscribe_podcasts() -> None:
    for podcast_id in (
        get_subscribable_podcasts()
        .order_by("subscribed", "-pk")
        .values_list("pk", flat=True)
    ):
        subscribe.delay(podcast_id)


def handle_callback(request: HttpRequest, podcast: Podcast) -> str:

    try:

        if not (challenge := get_challenge(request)):
            raise ValidationError("hub.challenge is missing")

        if not matches_topic(request, podcast):
            raise ValidationError("hub.topic does not match podcast topic")

        if request.method == "GET":
            podcast.status, podcast.subscribed = verify_intent(request, podcast)
        else:
            handle_update_notification(request, podcast)

    except ValidationError:
        podcast.hub_exception = traceback.format_exc()
        podcast.subscribe_status = Podcast.SubscribeStatus.Error
        raise
    finally:
        podcast.last_subscribe_callback = timezone.now()
        podcast.save()

    return challenge


def get_subscribable_podcasts() -> QuerySet:
    return Podcast.objects.active().filter(
        Q(
            subscribe_status=Podcast.SubscribeStatus.Unsubscribed,
        )
        | Q(
            subscribed__lt=timezone.now(),
            subscribe_status=Podcast.SubscribeStatus.Subscribed,
        ),
        hub__isnull=False,
    )


def handle_update_notification(request: HttpRequest, podcast: Podcast) -> None:

    if podcast.subscribe_status != Podcast.SubscribeStatus.Subscribed:
        raise ValidationError("podcast has invalid status")

    try:
        sig_header = request.headers["x-hub-signature"]
        method, signature = sig_header.split("=")
    except (KeyError, ValueError):
        raise ValidationError("X-Hub-Signature missing")

    if method != hashlib.sha512:
        raise ValidationError("invalid signature method, must be sha512")

    if not matches_signature(podcast.subscribe_secret, signature):
        raise ValidationError("signature does not match")

    feed_parser.parse_podcast_feed.delay(podcast.id)


def verify_intent(
    request: HttpRequest, podcast: Podcast
) -> tuple[str, datetime | None]:
    # https://w3c.github.io/websub/#hub-verifies-intent
    if (mode := request.GET.get("hub.mode")) not in ("subscribe", "unsubscribe"):
        raise ValidationError("hub.mode missing or invalid")

    if mode == "subscribe":
        if podcast.status != Podcast.SubscribeStatus.Requested:
            raise ValidationError("podcast has invalid status")

        try:
            lease_seconds = int(request.GET["hub.lease_seconds"])
        except (KeyError, ValueError, TypeError):
            raise ValidationError("hub.lease_seconds missing or invalid")
        return Podcast.SubscribeStatus.Subscribed, timezone.now() + timedelta(
            seconds=lease_seconds
        )
    return Podcast.SubscribeStatus.Unsubscribed, None


def get_params(request: HttpRequest) -> QueryDict:
    return request.POST if request.method == "POST" else request.GET


def create_hexdigest(secret: str) -> str:
    return hmac.new(secret.encode(), digestmod=hashlib.sha512).hexdigest()


def get_challenge(request: HttpRequest) -> str | None:
    return get_params(request).get("hub.challenge")


def matches_topic(request: HttpRequest, podcast: Podcast) -> bool:
    return get_params(request).get("hub.topic") == podcast.rss


def matches_signature(secret: str, signature: str) -> bool:
    return hmac.compare_digest(create_hexdigest(secret), signature)
