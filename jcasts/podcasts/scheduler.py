from __future__ import annotations

import logging

from typing import Generator

from django.conf import settings
from django.utils import timezone
from django_rq import job

from jcasts.podcasts.feed_parser import parse_feed
from jcasts.podcasts.models import Podcast


def schedule_podcast_feeds() -> None:
    def _schedule_podcast_feeds() -> Generator[Podcast, None, None]:
        """Schedules recent podcasts to run at allotted time."""
        for podcast in (
            Podcast.objects.filter(
                active=True,
                scheduled__isnull=True,
                pub_date__gte=timezone.now() - settings.RELEVANCY_THRESHOLD,
            ).order_by("-pub_date")
        ).iterator():
            podcast.scheduled = podcast.get_next_scheduled()
            yield podcast

    Podcast.objects.bulk_update(
        _schedule_podcast_feeds(), ["scheduled"], batch_size=1000
    )


def sync_podcast_feeds() -> None:
    """Schedules recent podcasts to run at allotted time."""
    now = timezone.now()
    for rss in (
        Podcast.objects.filter(
            active=True,
            scheduled__isnull=False,
            scheduled__lte=now,
            pub_date__gte=now - settings.RELEVANCY_THRESHOLD,
        )
        .order_by("-pub_date")
        .values_list("rss", flat=True)
    ).iterator():
        sync_podcast_feed.delay(rss)


@job
def sync_podcast_feed(rss: str, *, force_update: bool = False) -> None:

    try:

        podcast = Podcast.objects.get(rss=rss, active=True)
    except Podcast.DoesNotExist:
        return

    success = parse_feed(podcast, force_update=force_update)
    logging.info(f"{podcast} pull {'OK' if success else 'FAIL'}")
