from __future__ import annotations

import statistics

from datetime import datetime, timedelta

from django.db.models import DateTimeField, ExpressionWrapper, F, Q, QuerySet
from django.utils import timezone

from radiofeed.podcasts.models import Podcast

DEFAULT_INTERVAL = timedelta(hours=1)


def schedule_podcasts_for_update() -> QuerySet[Podcast]:

    now = timezone.now()

    return (
        Podcast.objects.with_subscribed()
        .annotate(
            scheduled=ExpressionWrapper(
                F("pub_date") + F("refresh_interval"),
                output_field=DateTimeField(),
            )
        )
        .filter(
            Q(parsed__isnull=True)
            | Q(pub_date__isnull=True)
            | Q(scheduled__lte=now)
            | Q(
                Q(subscribed=True) | Q(promoted=True),
                parsed__lt=now - DEFAULT_INTERVAL,
            ),
            active=True,
        )
        .order_by(
            F("subscribed").desc(),
            F("promoted").desc(),
            F("scheduled").asc(nulls_first=True),
            F("parsed").asc(nulls_first=True),
            F("pub_date").desc(nulls_first=True),
            F("created").desc(),
        )
    )


def calculate_refresh_interval(
    pub_dates: list[datetime], since: timedelta = timedelta(days=90)
) -> timedelta:

    try:
        head, *tail = sorted(pub_dates, reverse=True)
    except ValueError:
        return DEFAULT_INTERVAL

    latest = head

    now = timezone.now()
    relevant = now - since

    intervals: list[float] = []

    for pub_date in filter(lambda pub_date: pub_date > relevant, tail):
        intervals.append((head - pub_date).total_seconds())
        head = pub_date

    try:
        interval = max(timedelta(seconds=statistics.mean(intervals)), DEFAULT_INTERVAL)
    except ValueError:
        interval = DEFAULT_INTERVAL

    while latest + interval < now:
        interval = increment_refresh_interval(interval)

    return interval


def increment_refresh_interval(refresh_interval: timedelta) -> timedelta:
    seconds = refresh_interval.total_seconds()
    return timedelta(seconds=seconds + (seconds * 0.1))
