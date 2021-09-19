import traceback
import uuid

from datetime import timedelta

import requests

from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django_rq import job

from jcasts.podcasts.models import Podcast
from jcasts.shared.template import build_absolute_uri


def subscribe_podcasts(**retry_options):
    counter = 0
    for (counter, podcast_id) in enumerate(
        get_podcasts(**retry_options).values_list("pk", flat=True).iterator(), 1
    ):
        subscribe.delay(podcast_id, **retry_options)
    return counter


def get_podcasts(retry=False, retry_from=timedelta(hours=1)):

    now = timezone.now()

    qs = Podcast.objects.filter(
        Q(Q(websub_subscribed__lte=now) | Q(websub_subscribed__isnull=True)),
        websub_hub__isnull=False,
        websub_hub__in=settings.WEBSUB_CONFIG["hubs"],
        websub_exception="",
    )

    if retry:
        qs = qs.filter(
            websub_requested__isnull=False, websub_requested__lt=now - retry_from
        )

    else:

        qs = qs.filter(websub_requested__isnull=True)

    return qs


@job("websub")
def subscribe(podcast_id, **retry_options):

    podcast = get_podcasts(**retry_options).get(pk=podcast_id)
    podcast.websub_token = uuid.uuid4()
    podcast.websub_exception = ""
    podcast.websub_requested = timezone.now()

    response = requests.post(
        podcast.websub_hub,
        {
            "hub.mode": "subscribe",
            "hub.topic": podcast.rss,
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
        podcast.websub_exception = traceback.format_exc()

    podcast.save()

    return response
