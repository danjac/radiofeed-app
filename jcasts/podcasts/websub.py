import hashlib
import hmac
import traceback
import uuid

import requests

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django_rq import job

from jcasts.podcasts.models import Podcast
from jcasts.shared.template import build_absolute_uri

MAX_BODY_SIZE = 1024 ** 2


class Invalid(ValueError):
    ...


def subscribe_podcasts():
    counter = 0
    for (counter, podcast_id) in enumerate(
        get_podcasts().values_list("pk", flat=True).iterator(), 1
    ):
        subscribe.delay(podcast_id)
    return counter


def validate(request, podcast):
    if not podcast.websub_secret:
        return

    try:

        content_length = int(request.META["CONTENT_LENGTH"])

        if content_length > MAX_BODY_SIZE:
            raise ValueError("Request body too large")

        if not request.headers.get("X-Hub-Signature"):
            raise ValueError("X-Hub-Signature header required")

        algo, signature = request.headers.get("X-Hub-Signature").split("=")

        if not hmac.compare_digest(
            signature, make_hex_digest(algo, request.body, podcast.websub_secret)
        ):
            raise ValueError("HMAC signature mismatch")

    except (KeyError, ValueError) as e:
        raise Invalid from e


def make_hex_digest(algo, body, secret):
    try:
        return hmac.new(
            secret.hex.encode("utf-8"), body, getattr(hashlib, algo)
        ).hexdigest()
    except AttributeError:
        raise Invalid(f"Unknown hashing algorithm: {algo}")


def get_podcasts():

    return Podcast.objects.websub().filter(
        Q(Q(websub_subscribed__lte=timezone.now()) | Q(websub_subscribed__isnull=True)),
    )


@job("websub")
def subscribe(podcast_id):

    podcast = get_podcasts().get(pk=podcast_id)
    podcast.websub_token = uuid.uuid4()
    podcast.websub_secret = uuid.uuid4()
    podcast.websub_exception = ""
    podcast.websub_requested = timezone.now()

    response = requests.post(
        podcast.websub_hub,
        {
            "hub.mode": "subscribe",
            "hub.topic": podcast.rss,
            "hub.secret": podcast.websub_secret.hex,
            "hub.callback": build_absolute_uri(
                reverse("podcasts:websub_subscribe", args=[podcast.websub_token])
            ),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        response.raise_for_status()
    except requests.RequestException:

        podcast.websub_requested = None
        podcast.websub_subscribed = None
        podcast.websub_token = None
        podcast.websub_secret = None
        podcast.websub_exception = traceback.format_exc()

    podcast.save()

    return response
