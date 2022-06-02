from __future__ import annotations

import statistics

from datetime import datetime, timedelta

from django.db.models import F, Q, QuerySet
from django.utils import timezone

from radiofeed.podcasts.models import Podcast

DEFAULT_INTERVAL = timedelta(hours=1)
MAX_INTERVAL = timedelta(hours=24)


def schedule_podcasts_for_update() -> QuerySet[Podcast]:

    now = timezone.now()

    return (
        Podcast.objects.with_subscribed()
        .filter(
            Q(parsed__isnull=True)
            | Q(parsed__lt=now - F("refresh_interval"))
            | Q(
                Q(subscribed=True) | Q(promoted=True),
                parsed__lt=now - DEFAULT_INTERVAL,
            ),
            active=True,
        )
        .order_by(
            F("subscribed").desc(),
            F("promoted").desc(),
            F("parsed").asc(nulls_first=True),
            F("pub_date").desc(nulls_first=True),
            F("created").desc(),
        )
    )


def calculate_refresh_interval(pub_dates: list[datetime]) -> timedelta:
    try:
        head, *tail = sorted(pub_dates, reverse=True)
        intervals: list[float] = []

        for pub_date in tail:
            intervals.append((head - pub_date).total_seconds())
            head = pub_date

        return max(timedelta(seconds=statistics.mean(intervals)), DEFAULT_INTERVAL)

    except ValueError:
        return timedelta(hours=1)


def increment_refresh_interval(refresh_interval: timedelta) -> timedelta:
    seconds = refresh_interval.total_seconds()
    return min(timedelta(seconds=seconds + (seconds * 0.1)), MAX_INTERVAL)
