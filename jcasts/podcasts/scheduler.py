from __future__ import annotations

import statistics

from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from jcasts.episodes.models import Episode
from jcasts.podcasts.models import Podcast

# minimum number of dates required to accurately predict frequency
DEFAULT_MIN_PUB_DATES = 6

MIN_FREQ = timedelta(hours=1)
MAX_FREQ = timedelta(days=7)


def schedule_podcast_feeds(reset: bool = False) -> int:
    """Sets podcast feed scheduled times. This can be run once to set
    initial scheduling, afterwards should be calibrated automatically after fresh
    pull attempts.
    """
    if reset:
        Podcast.objects.update(scheduled=None)

    qs = Podcast.objects.filter(
        scheduled__isnull=True, active=True, pub_date__isnull=False
    ).order_by("-pub_date")

    for_update = []

    for podcast in qs.iterator():
        podcast.scheduled = schedule(podcast)
        for_update.append(podcast)

    Podcast.objects.bulk_update(for_update, fields=["scheduled"], batch_size=1000)

    return len(for_update)


def get_frequency(
    pub_dates: list[datetime], min_pub_dates: int = DEFAULT_MIN_PUB_DATES
) -> timedelta | None:
    max_date = timezone.now() - settings.RELEVANCY_THRESHOLD
    pub_dates = [
        pub_date for pub_date in sorted(pub_dates, reverse=True) if pub_date > max_date
    ]
    if len(pub_dates) < min_pub_dates:
        return None

    (head, *tail) = pub_dates

    diffs = []

    for pub_date in pub_dates:
        diffs.append((head - pub_date).total_seconds())
        head = pub_date

    freq = timedelta(seconds=round(statistics.mean(diffs)))
    return min(max(freq, MIN_FREQ), MAX_FREQ)


def get_recent_pub_dates(podcast: Podcast) -> list[datetime]:
    return (
        Episode.objects.filter(
            podcast=podcast, pub_date__gte=timezone.now() - settings.RELEVANCY_THRESHOLD
        )
        .values_list("pub_date", flat=True)
        .order_by("-pub_date")
    )


def increment(base: timedelta, value: float = 0.05) -> datetime:
    # add 5% of freq to current time (min 1 hour)
    # e.g. 7 days - try again in about 8 hours

    return timezone.now() + max(
        timedelta(seconds=base.total_seconds() * value), MIN_FREQ
    )


def schedule(
    podcast: Podcast,
    pub_dates: list[datetime] | None = None,
) -> datetime | None:
    """Returns next scheduled feed sync time.
    Will calculate based on list of provided pub dates or most recent episodes.

    Minimum scheduled time otherwise will be 1 hour from now.
    """
    if not podcast.active or podcast.pub_date is None:
        return None

    now = timezone.now()

    # if no pub dates, just use last podcast pub date
    if (freq := get_frequency(pub_dates or get_recent_pub_dates(podcast))) is None:
        return increment(now - podcast.pub_date)

    # will go out in future, should be ok
    if (scheduled := podcast.pub_date + freq) > now:
        return scheduled

    return increment(freq)
