import traceback
import uuid

import requests

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django_rq import job

from jcasts.podcasts.models import Podcast
from jcasts.shared.template import build_absolute_uri


def get_podcasts():

    return Podcast.objects.filter(
        Q(Q(subscribed__lte=timezone.now()) | Q(subscribed__isnull=True)),
        hub__isnull=False,
        hub_exception="",
    )


@job
def subscribe(podcast_id):

    podcast = get_podcasts().get(pk=podcast_id)
    podcast.hub_token = uuid.uuid4()
    podcast.hub_exception = ""

    response = requests.post(
        podcast.hub,
        {
            "hub.mode": "subscribe",
            "hub.topic": podcast.rss,
            "hub.callback": build_absolute_uri(
                reverse("podcasts:websub_subscribe", args=[podcast.hub_token])
            ),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        response.raise_for_status()
    except requests.RequestException:

        podcast.subscribed = None
        podcast.hub_token = None
        podcast.hub_exception = traceback.format_exc()

    podcast.save()

    return response
