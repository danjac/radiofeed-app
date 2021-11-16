from __future__ import annotations

import hmac
import traceback

from datetime import timedelta

import attr
import requests

from django.db.models import Q, QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import crypto, timezone
from django_rq import job

from jcasts.podcasts import feed_parser
from jcasts.podcasts.models import Podcast
from jcasts.shared.response import HttpResponseNoContent
from jcasts.shared.template import build_absolute_uri

DEFAULT_LEASE_SECONDS = 7 * 24 * 3600


@attr.s
class SubscribeRequest:
    podcast_id: int = attr.ib()
    status: str | None = attr.ib(default=None)
    exception: Exception | None = attr.ib(default=None)


def verify_intent(request: HttpRequest, podcast_id: int) -> HttpResponse:
    try:
        mode: str = request.GET["hub.mode"]
        topic: str = request.GET["hub.topic"]
        challenge: str = request.GET["hub.challenge"]

    except KeyError as e:
        raise Http404 from e

    podcast = get_object_or_404(Podcast.objects.active(), pk=podcast_id, rss=topic)

    now = timezone.now()

    if mode == "subscribe":
        try:
            podcast.websub_status = Podcast.WebhubStatus.ACTIVE
            podcast.websub_subscribed = now + timedelta(
                seconds=int(request.GET["hub.lease_seconds"])
            )

        except (KeyError, ValueError) as e:
            raise Http404 from e
    else:
        podcast.websub_status = Podcast.WebhubStatus.INACTIVE

    podcast.websub_status_changed = now
    podcast.save()

    return HttpResponse(challenge)


def handle_content_distribution(request: HttpRequest, podcast_id: int) -> HttpResponse:

    podcast = get_object_or_404(
        Podcast.objects.active(),
        websub_status=Podcast.WebhubStatus.ACTIVE,
        websub_token__isnull=False,
        pk=podcast_id,
    )

    try:
        sig_header = request.headers["X-Hub-Signature"]
        method, signature = sig_header.split("=")
    except (KeyError, ValueError) as e:
        raise Http404 from e

    if not hmac.compare_digest(
        encode_token(podcast.websub_token, method),
        signature,
    ):
        raise Http404("invalid signature")

    feed_parser.parse_podcast_feed.delay(podcast.id, content=request.body)

    return HttpResponseNoContent()


def subscribe_podcasts():
    for podcast_id in get_podcasts_for_subscription().values_list("pk", flat=True):
        request_subscription.delay(podcast_id)


@job("default")
def request_subscription(podcast_id: int) -> SubscribeRequest:
    now = timezone.now()

    try:
        podcast = get_podcasts_for_subscription().get(pk=podcast_id)
    except Podcast.DoesNotExist as e:
        return SubscribeRequest(podcast_id=podcast_id, exception=e)

    token = crypto.random_string(12)

    response = requests.post(
        podcast.rss,
        {
            "hub.callback": build_absolute_uri(
                reverse("podcasts:websub_callback", args=[podcast.id])
            ),
            "hub.mode": "subscribe",
            "hub.verify": "sync",
            "hub.topic": podcast.rss,
            "hub.lease_seconds": DEFAULT_LEASE_SECONDS,
            "hub.secret": encode_token(token),
        },
    )

    result = SubscribeRequest(podcast_id=podcast.id)

    try:
        response.raise_for_status()
        podcast.websub_status = Podcast.WebhubStatus.REQUESTED
        podcast.websub_token = token

    except requests.RequestException as e:
        podcast.websub_status = Podcast.WebhubStatus.INACTIVE
        podcast.websub_exception = traceback.format_exc()
        result.exception = e

    podcast.websub_status_changed = now
    podcast.save()

    result.status = podcast.websub_status

    return result


def get_podcasts_for_subscription() -> QuerySet:
    return Podcast.objects.active().filter(
        Q(
            webhub_status=Podcast.WebhubStatus.PENDING,
        )
        | Q(
            webhub_status=Podcast.WebhubStatus.ACTIVE,
            webhub_subscribed__lt=timezone.now(),
        )
    )


def encode_token(token: str, method: str = "sha1") -> str:
    return hmac.new(token.encode(), digestmod=method).hexdigest()
