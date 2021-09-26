import hashlib
import hmac
import logging
import traceback
import uuid

import requests

from django.urls import reverse
from django.utils import timezone
from django_rq import job

from jcasts.podcasts.models import Podcast
from jcasts.shared.template import build_absolute_uri

logger = logging.getLogger(__name__)

MAX_BODY_SIZE = 1024 ** 2


class InvalidSignature(ValueError):
    ...


def subscribe_podcasts():
    counter = 0
    for (counter, podcast_id) in enumerate(
        get_podcasts()
        .order_by("websub_requested")
        .values_list("pk", flat=True)
        .iterator(),
        1,
    ):
        subscribe.delay(podcast_id)
    return counter


def check_signature(request, podcast):
    if not podcast.websub_secret:
        return

    try:

        content_length = int(request.META["CONTENT_LENGTH"])

        if content_length > MAX_BODY_SIZE:
            raise ValueError("Request body too large")

        if not (header := request.headers.get("X-Hub-Signature")):
            raise ValueError("X-Hub-Signature header required")

        algo, signature = header.split("=")

        if not hmac.compare_digest(
            signature, make_hex_digest(algo, request.body, podcast.websub_secret)
        ):
            raise ValueError(f"HMAC signature mismatch:{header}")

    except (AttributeError, KeyError, ValueError) as e:
        raise InvalidSignature from e


def make_hex_digest(algo, body, secret):
    return hmac.new(
        secret.hex.encode("utf-8"), body, getattr(hashlib, algo)
    ).hexdigest()


def get_podcasts(reverify=False):
    qs = Podcast.objects.websub()
    if not reverify:
        qs = qs.unsubscribed().filter(websub_exception="")

    return qs


@job("websub")
def subscribe(podcast_id, reverify=False):

    try:
        podcast = get_podcasts(reverify).get(pk=podcast_id)
        logger.error(f"No podcast found for {podcast_id}")
    except Podcast.DoesNotExist:
        return None

    podcast.websub_token = uuid.uuid4()
    podcast.websub_secret = uuid.uuid4()
    podcast.websub_exception = ""
    podcast.websub_requested = timezone.now()
    podcast.websub_subscribed = None

    response = requests.post(
        podcast.websub_hub,
        {
            "hub.mode": "subscribe",
            "hub.verify": "async",
            "hub.topic": podcast.websub_url or podcast.rss,
            "hub.secret": podcast.websub_secret.hex,
            "hub.callback": build_absolute_uri(
                reverse("podcasts:websub_subscribe", args=[podcast.websub_token])
            ),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        response.raise_for_status()
    except requests.RequestException as e:

        podcast.websub_requested = None
        podcast.websub_token = None
        podcast.websub_secret = None
        podcast.websub_exception = "\n".join(
            (
                traceback.format_exc(),
                response.content.decode("utf-8"),
            )
        )
        logger.exception(e)

    podcast.save()

    return response
