from __future__ import annotations

import statistics

from datetime import datetime, timedelta

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

    qs = Podcast.objects.frequent().filter(scheduled__isnull=True).order_by("-pub_date")

    for_update = []

    for podcast in qs.iterator():
        podcast.scheduled = schedule(podcast)
        for_update.append(podcast)

    Podcast.objects.bulk_update(for_update, fields=["scheduled"], batch_size=1000)

    return len(for_update)


def get_frequency(pub_dates: list[datetime]) -> timedelta | None:
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


def schedule(
    podcast: Podcast,
    pub_dates: list[datetime] | None = None,
) -> datetime | None:
    """Returns next scheduled feed sync time.
    Will calculate based on list of provided pub dates or most recent episodes.
    """
    if not podcast.active or podcast.pub_date is None:
        return None

    now = timezone.now()

    pub_dates = pub_dates or (
        Episode.objects.filter(
            podcast=podcast, pub_date__gte=now - settings.RELEVANCY_THRESHOLD
        )
        .values_list("pub_date", flat=True)
        .order_by("-pub_date")
    )

    if not pub_dates or (frequency := get_frequency(pub_dates)) is None:
        return None

    min_delta = timedelta(hours=1)

    # minimum 1 hour
    frequency = max(frequency, min_delta)

    # should always be in future
    if (scheduled := podcast.pub_date + frequency) > now:
        return scheduled

    # add 5% of frequency to current time (min 1 hour)
    # e.g. 7 days - try again in about 8 hours

    return now + max(timedelta(seconds=frequency.total_seconds() * 0.05), min_delta)
