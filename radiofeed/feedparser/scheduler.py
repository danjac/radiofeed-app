from __future__ import annotations

import itertools

from datetime import timedelta
from typing import Final

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

    This includes podcasts with last pub date + update interval. If this is more than 30 days, then
    we check last parsed date

    Example:

    - pub date 3 days ago, interval 7 days: next scheduled date is in 4 days
    - pub date 90 days ago, last parsed 15 days ago, interval 30 days: next scheduled date in 15 days

    Ordered by:
        - number of subscribers
        - promoted
        - last parsed
        - last pub date
    """

    now = timezone.now()
    from_date = now - MAX_UPDATE_INTERVAL

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
            | models.Q(parsed__lt=from_date)
            | models.Q(scheduled__range=(from_date, now)),
            active=True,
        )
    ).order_by(
        models.F("subscribers").desc(),
        models.F("promoted").desc(),
        models.F("parsed").asc(nulls_first=True),
        models.F("pub_date").desc(nulls_first=True),
    )


def calc_update_interval(feed: Feed) -> timedelta:
    """Returns min interval of episodes in feed."""
    try:
        return _update_interval_within_bounds(
            timedelta(
                seconds=min(
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
        return DEFAULT_UPDATE_INTERVAL


def increment_update_interval(podcast: Podcast, increment: float = 0.1) -> timedelta:
    """Increments update interval"""

    current_interval = podcast.update_interval.total_seconds()

    return _update_interval_within_bounds(
        timedelta(seconds=current_interval + (current_interval * increment))
    )


def _update_interval_within_bounds(interval: timedelta) -> timedelta:
    return max(min(interval, MAX_UPDATE_INTERVAL), MIN_UPDATE_INTERVAL)
