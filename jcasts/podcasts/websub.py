import hashlib
import hmac
import traceback
import uuid

import requests

from django.db.models import Q
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django_rq import job

from jcasts.podcasts.models import Podcast
from jcasts.shared.template import build_absolute_uri


class InvalidSignature(ValueError):
    ...


def subscribe_podcasts():

    podcasts = Podcast.objects.active().filter(
        Q(websub_status__isnull=True)
        | Q(
            websub_status=Podcast.WebSubStatus.ACTIVE,
            websub_timeout__lt=timezone.now(),
        ),
        websub_hub__isnull=False,
    )

    for podcast_id in podcasts.values_list("id", flat=True):
        subscribe.delay(podcast_id)


@job("default")
def subscribe(podcast_id: int, mode: str = "subscribe") -> None:

    try:
        podcast = (
            Podcast.objects.active()
            .filter(websub_hub__isnull=False)
            .exclude(websub_status=Podcast.WebSubStatus.REQUESTED)
            .get(pk=podcast_id)
        )
    except Podcast.DoesNotExist:
        return

    now = timezone.now()

    podcast.websub_mode = mode
    podcast.websub_secret = uuid.uuid4()
    podcast.websub_status = Podcast.WebSubStatus.REQUESTED
    podcast.websub_exception = ""
    podcast.websub_status_changed = now

    podcast.save()

    response = requests.post(
        podcast.websub_hub,
        {
            "hub.callback": build_absolute_uri(
                reverse("podcasts:websub_callback", args=[podcast.id])
            ),
            "hub.verify": "sync",
            "hub.mode": podcast.websub_mode,
            "hub.topic": podcast.websub_url or podcast.rss,
            "hub.secret": podcast.websub_secret,
            "hub.lease_seconds": Podcast.DEFAULT_WEBSUB_TIMEOUT.total_seconds(),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        response.raise_for_status()
    except requests.RequestException:
        podcast.websub_exception = (
            traceback.format_exc() + "\n" + response.content.decode("utf-8")
        )
        podcast.websub_status = Podcast.WebSubStatus.ERROR
        podcast.websub_status_changed = now
        podcast.websub_secret = None
        podcast.save()


def make_signature(secret: uuid.UUID, body: bytes, algo: str) -> str:
    return hmac.new(secret.hex.encode("utf-8"), body, algo).hexdigest()


def check_signature(request: HttpRequest, secret: uuid.UUID) -> None:

    try:
        header = request.headers["X-Hub-Signature"]
        algo, signature = header.split("=")
        algo = getattr(hashlib, algo)
    except KeyError:
        raise InvalidSignature("X-Hub-Signature is missing")
    except ValueError:
        raise InvalidSignature(f"X-Hub-Signature is invalid: {header}")
    except AttributeError:
        raise InvalidSignature(f"X-Hub-Signature algo unknown: {header}")

    if not hmac.compare_digest(signature, make_signature(secret, request.body, algo)):
        raise InvalidSignature(f"X-Hub-Signature does not match: {header}")
