import traceback

import requests

from django.db.models import Q
from django.urls import reverse
from django.utils import crypto, timezone
from django_rq import job

from jcasts.podcasts.models import Podcast
from jcasts.shared.template import build_absolute_uri


def subscribe_podcasts():

    podcasts = (
        Podcast.objects.active()
        .filter(
            Q(websub_status__isnull=True)
            | Q(
                websub_status=Podcast.WebSubStatus.Active,
                websub_lease__lt=timezone.now(),
            ),
            websub_hub__isnull=False,
            websub_url__isnull=False,
        )
        .order_by("websub_status_changed")
    )

    for podcast_id in podcasts.values_list("id", flat=True):
        subscribe.delay(podcast_id)


@job("default")
def subscribe(podcast_id: int, mode: str = "subscribe") -> None:

    try:
        podcast = (
            Podcast.objects.active()
            .filter(websub_hub__isnull=False, websub_url__isnull=False)
            .exclude(websub_status=Podcast.WebSubStatus.Requested)
            .get(pk=podcast_id)
        )
    except Podcast.DoesNotExist:
        return

    podcast.websub_token = crypto.get_random_string(
        Podcast._meta.get_field("websub_token").max_length
    )

    podcast.websub_mode = mode

    response = requests.post(
        podcast.websub_hub,
        {
            "hub.callback": build_absolute_uri(
                reverse("podcasts:websub_callback", args=[podcast.id])
            ),
            "hub.verify": "sync",
            "hub.mode": podcast.websub_mode,
            "hub.topic": podcast.websub_url,
            "hub.verify_token": podcast.websub_token,
            "hub.lease_seconds": Podcast.DEFAULT_WEBSUB_LEASE.total_seconds(),
        },
    )

    try:
        response.raise_for_status()
        podcast.websub_status = Podcast.WebsubStatus.Requested
    except requests.RequestException:
        podcast.websub_exception = traceback.format_exc()
        podcast.websub_status = Podcast.WebsubStatus.Error

    podcast.websub_status_changed = timezone.now()
    podcast.save()
