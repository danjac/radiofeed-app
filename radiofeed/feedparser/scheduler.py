from __future__ import annotations

import itertools

from datetime import timedelta
from typing import Final

import numpy

from django.db.models import Count, F, Q, QuerySet
from django.utils import timezone

from radiofeed.feedparser.models import Feed
from radiofeed.podcasts.models import Podcast

DEFAULT_UPDATE_INTERVAL: Final = timedelta(hours=24)
MIN_UPDATE_INTERVAL: Final = timedelta(hours=3)
MAX_UPDATE_INTERVAL: Final = timedelta(days=30)


def scheduled_podcasts_for_update() -> QuerySet[Podcast]:
    """
    Returns any active podcasts scheduled for feed updates.
    """
    now = timezone.now()
    from_interval = now - F("update_interval")

    return (
        Podcast.objects.alias(subscribers=Count("subscription")).filter(
            Q(parsed__isnull=True)
            | Q(pub_date__isnull=True)
            | Q(parsed__lt=from_interval)
            | Q(
                pub_date__range=(now - MAX_UPDATE_INTERVAL, from_interval),
                parsed__lt=now - MIN_UPDATE_INTERVAL,
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
    """Returns mean interval of episodes in feed."""

    # find the mean distance between episodes

    try:
        interval = _within_bounds(
            timedelta(
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
        )
    except ValueError:
        interval = DEFAULT_UPDATE_INTERVAL

    # automatically increment while less than current time

    now = timezone.now()

    while now > feed.pub_date + interval and MAX_UPDATE_INTERVAL > interval:
        interval = reschedule(interval)

    return interval


def reschedule(interval: timedelta, increment: float = 0.1) -> timedelta:
    """Increments update interval"""

    current_interval = interval.total_seconds()

    return _within_bounds(
        timedelta(seconds=current_interval + (current_interval * increment))
    )


def _within_bounds(interval: timedelta) -> timedelta:
    return max(min(interval, MAX_UPDATE_INTERVAL), MIN_UPDATE_INTERVAL)
