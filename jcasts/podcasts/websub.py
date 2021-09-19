import traceback
import uuid

import requests

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django_rq import job

from jcasts.podcasts.models import Podcast
from jcasts.shared.template import build_absolute_uri


def subscribe_podcasts():
    counter = 0
    for (counter, podcast_id) in enumerate(
        get_podcasts().values_list("pk", flat=True).iterator(), 1
    ):
        subscribe.delay(podcast_id)
    return counter


def get_podcasts():

    return Podcast.objects.websub().filter(
        Q(Q(websub_subscribed__lte=timezone.now()) | Q(websub_subscribed__isnull=True)),
    )


@job("websub")
def subscribe(podcast_id):

    podcast = get_podcasts().get(pk=podcast_id)
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
