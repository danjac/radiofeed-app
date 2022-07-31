from __future__ import annotations

import itertools

from datetime import timedelta
from typing import Final

import numpy

from django.db import models
from django.utils import timezone

from radiofeed.feedparser.models import Feed
from radiofeed.podcasts.models import Podcast

DEFAULT_UPDATE_INTERVAL: Final = timedelta(hours=24)
MIN_UPDATE_INTERVAL: Final = timedelta(hours=3)
MAX_UPDATE_INTERVAL: Final = timedelta(days=30)


def get_scheduled_podcasts_for_update() -> models.QuerySet[Podcast]:
    """
    Returns podcasts scheduled for feed updates.

    Ordered by:
        - number of subscribers
        - promoted
        - last parsed
        - last pub date
    """
    now = timezone.now()

    return (
        Podcast.objects.annotate(
            scheduled=models.ExpressionWrapper(
                models.F("pub_date") + models.F("update_interval"),
                output_field=models.DateTimeField(),
            ),
        )
        .alias(subscribers=models.Count("subscription"))
        .filter(
            models.Q(parsed__isnull=True)
            | models.Q(pub_date__isnull=True)
            | models.Q(parsed__lt=now - models.F("update_interval"))
            | models.Q(scheduled__range=(now - MAX_UPDATE_INTERVAL, now)),
            active=True,
        )
    ).order_by(
        models.F("subscribers").desc(),
        models.F("promoted").desc(),
        models.F("parsed").asc(nulls_first=True),
        models.F("pub_date").desc(nulls_first=True),
    )


def calc_update_interval(feed: Feed) -> timedelta:
    """Returns mean interval of episodes in feed."""

    now = timezone.now()

    # automatically set max interval if older than 30 days

    if now - MAX_UPDATE_INTERVAL > feed.pub_date:
        return MAX_UPDATE_INTERVAL

    intervals = [
        (a - b).total_seconds()
        for a, b in itertools.pairwise([now] + [item.pub_date for item in feed.items])
    ]

    # find the mean and subtract standard deviation
    # e.g. if mean is 3 days and stdev is 1 day result is 2 days

    return _update_interval_within_bounds(
        timedelta(seconds=numpy.mean(intervals) - numpy.std(intervals))
    )


def increment_update_interval(podcast: Podcast, increment: float = 0.1) -> timedelta:
    """Increments update interval"""

    current_interval = podcast.update_interval.total_seconds()

    return _update_interval_within_bounds(
        timedelta(seconds=current_interval + (current_interval * increment))
    )


def _update_interval_within_bounds(interval: timedelta) -> timedelta:
    return max(min(interval, MAX_UPDATE_INTERVAL), MIN_UPDATE_INTERVAL)
