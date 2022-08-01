from __future__ import annotations

import itertools

from datetime import datetime, timedelta
from typing import Final

import numpy

from django.db.models import Count, F, Q, QuerySet
from django.utils import timezone

from radiofeed.feedparser.models import Feed
from radiofeed.podcasts.models import Podcast

DEFAULT_FREQUENCY: Final = timedelta(hours=24)
MIN_FREQUENCY: Final = timedelta(hours=3)
MAX_FREQUENCY: Final = timedelta(days=30)


def scheduled_podcasts_for_update() -> QuerySet[Podcast]:
    """
    Returns any active podcasts scheduled for feed updates.
    """
    now = timezone.now()
    since = now - F("frequency")

    return (
        Podcast.objects.alias(subscribers=Count("subscription")).filter(
            Q(parsed__isnull=True)
            | Q(pub_date__isnull=True)
            | Q(parsed__lt=since)
            | Q(
                pub_date__range=(now - MAX_FREQUENCY, since),
                parsed__lt=now - MIN_FREQUENCY,
            ),
            active=True,
        )
    ).order_by(
        F("subscribers").desc(),
        F("promoted").desc(),
        F("parsed").asc(nulls_first=True),
        F("pub_date").desc(nulls_first=True),
    )


def schedule(feed: Feed) -> timedelta:
    """Returns mean frequency of episodes in feed."""

    # find the mean distance between episodes

    try:
        frequency = timedelta(
            seconds=float(
                numpy.mean(
                    [
                        (a - b).total_seconds()
                        for a, b in itertools.pairwise(
                            item.pub_date for item in feed.items
                        )
                    ]
                )
            )
        )
    except ValueError:
        frequency = DEFAULT_FREQUENCY

    return reschedule(feed.pub_date, frequency)


def reschedule(
    pub_date: datetime | None, frequency: timedelta, increment: float = 0.1
) -> timedelta:
    """Increments update frequency."""

    now = timezone.now()
    pub_date = pub_date or now

    while now > pub_date + frequency and MAX_FREQUENCY > frequency:
        seconds = frequency.total_seconds()
        frequency = timedelta(seconds=seconds + (seconds * increment))

    return max(min(frequency, MAX_FREQUENCY), MIN_FREQUENCY)
