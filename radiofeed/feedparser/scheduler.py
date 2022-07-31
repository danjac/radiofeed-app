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
    Returns podcasts scheduled for feed updates:

    1. Any podcast with parsed or pub_date NULL (i.e. recently added)
    2. Any podcast with scheduled date > 30 days and less than current time (scheduled date = pub_date + update_interval)
    3. any podcast with parsed < current time - update_interval

    Example 1: podcast with last pub date 3 days ago, last parsed 2 days ago, update interval 7 days.

    Next scheduled update will be in 4 days.

    Example 2: podcast with last pub date 90 days ago, update interval 30 days, last parsed 15 days ago.

    Next scheduled update will be in 15 days.

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
            | models.Q(
                parsed__lt=now - MIN_UPDATE_INTERVAL,
                scheduled__range=(now - MAX_UPDATE_INTERVAL, now),
            ),
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

    # find the mean distance between episodes

    try:
        interval = _update_interval_within_bounds(
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

    while now > feed.pub_date + interval and MAX_UPDATE_INTERVAL > interval:
        interval = increment_update_interval(interval)

    return interval


def increment_update_interval(interval: timedelta, increment: float = 0.1) -> timedelta:
    """Increments update interval"""

    current_interval = interval.total_seconds()

    return _update_interval_within_bounds(
        timedelta(seconds=current_interval + (current_interval * increment))
    )


def _update_interval_within_bounds(interval: timedelta) -> timedelta:
    return max(min(interval, MAX_UPDATE_INTERVAL), MIN_UPDATE_INTERVAL)
