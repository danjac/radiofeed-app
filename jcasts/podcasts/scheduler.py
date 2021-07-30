from __future__ import annotations

import statistics

from datetime import datetime, timedelta
from typing import Generator

from django.conf import settings
from django.utils import timezone

from jcasts.episodes.models import Episode
from jcasts.podcasts.models import Podcast


def schedule_podcast_feeds(reset: bool = False) -> int:
    """Sets podcast feed scheduled times. This can be run once to set
    initial scheduling, afterwards should be calibrated automatically after fresh
    pull attempts.

    Run calc_podcast_frequencies() to set the initial frequencies first.
    """
    if reset:
        Podcast.objects.update(scheduled=None)

    qs = (
        Podcast.objects.frequent()
        .filter(scheduled__isnull=True, frequency__isnull=False)
        .order_by("-pub_date")
    )

    total = qs.count()

    def _schedule_podcast_feeds() -> Generator[Podcast, None, None]:
        """Schedules recent podcasts to run at allotted time."""
        for podcast in qs.iterator():
            podcast.scheduled = get_next_scheduled(
                pub_date=podcast.pub_date, frequency=podcast.frequency
            )
            yield podcast

    Podcast.objects.bulk_update(
        _schedule_podcast_feeds(), fields=["scheduled"], batch_size=1000
    )

    return total


def calc_podcast_frequencies(reset: bool = False) -> int:
    if reset:
        Podcast.objects.update(frequency=None)

    qs = Podcast.objects.frequent().filter(frequency__isnull=True).order_by("-pub_date")

    total = qs.count()

    def _calc_frequencies() -> Generator[Podcast, None, None]:
        """Schedules recent podcasts to run at allotted time."""
        for podcast in qs.iterator():
            podcast.frequency = calc_frequency_from_podcast(podcast)
            yield podcast

    Podcast.objects.bulk_update(
        _calc_frequencies(), fields=["frequency"], batch_size=1000
    )

    return total


def calc_frequency(pub_dates: list[datetime]) -> timedelta | None:
    max_date = timezone.now() - settings.RELEVANCY_THRESHOLD
    pub_dates = [
        pub_date for pub_date in sorted(pub_dates, reverse=True) if pub_date > max_date
    ]
    if not pub_dates:
        return None
    diffs = []
    prev = timezone.now()
    for pub_date in pub_dates:
        diffs.append((prev - pub_date).days)
        prev = pub_date
    days = round(statistics.mean(diffs))
    return timedelta(days=days)


def calc_frequency_from_podcast(podcast: Podcast) -> timedelta | None:
    return calc_frequency(
        Episode.objects.filter(
            podcast=podcast, pub_date__gte=timezone.now() - settings.RELEVANCY_THRESHOLD
        )
        .values_list("pub_date", flat=True)
        .order_by("-pub_date")
    )


def get_next_scheduled(
    *,
    pub_date: datetime | None,
    frequency: timedelta | None,
) -> datetime | None:
    """Returns next scheduled feed sync time.
    If frequency is set, will return last pub date + frequency or current time +
    frequency, whichever is greater (minimum: 1 hour).

    If feed inactive or no frequency set, returns None.
    """
    if None in (pub_date, frequency):
        return None

    now = timezone.now()
    min_delta = timedelta(hours=1)

    # minimum 1 hour
    frequency = max(frequency, min_delta)

    # should always be in future
    if (scheduled := pub_date + frequency) > now:
        return scheduled

    # add 5% of frequency to current time (min 1 hour)
    # e.g. 7 days - try again in about 8 hours

    return now + max(timedelta(seconds=frequency.total_seconds() * 0.05), min_delta)
