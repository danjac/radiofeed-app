from __future__ import annotations

import logging

from typing import Generator

from django.conf import settings
from django.utils import timezone
from django_rq import job

from jcasts.podcasts.feed_parser import parse_feed
from jcasts.podcasts.models import Podcast


def schedule_podcast_feeds(reset: bool = False) -> int:
    if reset:
        Podcast.objects.update(scheduled=None)
    qs = Podcast.objects.filter(
        active=True,
        scheduled__isnull=True,
        pub_date__gte=timezone.now() - settings.RELEVANCY_THRESHOLD,
    ).order_by("-pub_date")
    total = qs.count()

    def _schedule_podcast_feeds() -> Generator[Podcast, None, None]:
        """Schedules recent podcasts to run at allotted time."""
        for podcast in qs.iterator():
            podcast.scheduled = podcast.get_next_scheduled()
            yield podcast

    Podcast.objects.bulk_update(
        _schedule_podcast_feeds(), ["scheduled"], batch_size=1000
    )
    return total


def sync_frequent_feeds() -> int:
    now = timezone.now()
    counter = 0
    for counter, rss in enumerate(
        Podcast.objects.filter(
            active=True,
            scheduled__isnull=False,
            scheduled__lte=now,
            pub_date__gte=now - settings.RELEVANCY_THRESHOLD,
        )
        .order_by("-pub_date")
        .values_list("rss", flat=True)
        .iterator(),
        1,
    ):
        sync_podcast_feed.delay(rss)

    return counter


def sync_sporadic_feeds() -> int:
    now = timezone.now()
    counter = 0
    for counter, rss in enumerate(
        Podcast.objects.filter(
            active=True,
            pub_date__lte=now - settings.RELEVANCY_THRESHOLD,
        )
        .order_by("-pub_date")
        .values_list("rss", flat=True)
        .iterator(),
        1,
    ):
        sync_podcast_feed.delay(rss)

    return counter


@job
def sync_podcast_feed(rss: str, *, force_update: bool = False) -> None:

    try:

        podcast = Podcast.objects.get(rss=rss, active=True)
    except Podcast.DoesNotExist:
        return

    success = parse_feed(podcast, force_update=force_update)
    logging.info(f"{podcast} pull {'OK' if success else 'FAIL'}")
    if podcast.scheduled:
        logging.info(f"{podcast} next pull scheduled at {podcast.scheduled}")
