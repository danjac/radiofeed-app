from __future__ import annotations

import secrets
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


def get_frequency(pub_dates: list[datetime]) -> timedelta | None:
    max_date = timezone.now() - settings.RELEVANCY_THRESHOLD
    pub_dates = [
        pub_date for pub_date in sorted(pub_dates, reverse=True) if pub_date > max_date
    ]
    if not pub_dates:
        return None

    # if single date, start with time since that date
    (head, *tail) = pub_dates if len(pub_dates) > 1 else (timezone.now(), pub_dates[0])

    diffs = []

    for pub_date in pub_dates:
        diffs.append((head - pub_date).total_seconds())
        head = pub_date

    return timedelta(seconds=round(statistics.mean(diffs)))


def get_recent_pub_dates(podcast: Podcast) -> list[datetime]:
    return (
        Episode.objects.filter(
            podcast=podcast, pub_date__gte=timezone.now() - settings.RELEVANCY_THRESHOLD
        )
        .values_list("pub_date", flat=True)
        .order_by("-pub_date")
    )


def schedule(
    podcast: Podcast,
    pub_dates: list[datetime] | None = None,
) -> datetime | None:
    """Returns next scheduled feed sync time.
    Will calculate based on list of provided pub dates or most recent episodes.

    Returns None if podcast inactive or has no pub dates. Minimum scheduled time
    otherwise will be 1 hour from now.
    """
    if not podcast.active or podcast.pub_date is None:
        return None

    now = timezone.now()

    # minimum 1 hour
    min_freq = timedelta(hours=1)

    # maximum 7 days
    max_freq = timedelta(days=7)

    if (freq := get_frequency(pub_dates or get_recent_pub_dates(podcast))) is None:
        # past threshold: random 7-14 days
        return (now + max_freq + timedelta(days=secrets.choice(range(0, 8)))).replace(
            hour=secrets.choice(range(0, 24)),
            minute=secrets.choice(range(0, 60)),
        )

    freq = min(max(freq, min_freq), max_freq)

    # will go out in future, should be ok
    if (scheduled := podcast.pub_date + freq) > now:
        return scheduled

    # add 5% of freq to current time (min 1 hour)
    # e.g. 7 days - try again in about 8 hours

    return now + max(timedelta(seconds=freq.total_seconds() * 0.05), min_freq)
