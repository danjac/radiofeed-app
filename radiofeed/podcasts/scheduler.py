from __future__ import annotations

from datetime import datetime, timedelta

import numpy

from django.db.models import Count, DateTimeField, ExpressionWrapper, F, Q, QuerySet
from django.utils import timezone

from radiofeed.podcasts.models import Podcast

MAX_INTERVAL = timedelta(days=14)
MIN_INTERVAL = timedelta(hours=1)


def schedule_podcasts_for_update() -> QuerySet[Podcast]:
    """Returns podcasts scheduled for feed update:

    1. Any podcasts with pub_date or parsed NULL (i.e. recently added)
    2. Any subscribed or promoted podcasts last updated > 1 hour ago
    3. Any podcasts where distance between last pub date + refresh interval > current time and
        distance < 14 days
    4. Any podcasts last updated > 14 days ago
    """

    now = timezone.now()

    return (
        Podcast.objects.annotate(
            subscribers=Count("subscription"),
            scheduled=ExpressionWrapper(
                F("pub_date") + F("refresh_interval"),
                output_field=DateTimeField(),
            ),
        )
        .filter(
            Q(parsed__isnull=True)
            | Q(pub_date__isnull=True)
            | Q(scheduled__range=(now - MAX_INTERVAL, now))
            | Q(
                Q(subscribers__gt=0) | Q(promoted=True),
                parsed__lt=now - MIN_INTERVAL,
            )
            | Q(parsed__lt=now - MAX_INTERVAL),
            active=True,
        )
        .order_by(
            F("subscribers").desc(),
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
    """Calculates the mean time interval between pub dates of individual
    episodes in a podcast.

    If the distance between the latest pub date and interval is less than
    the current time, the interval is incremented by 10% until latest pub date+interval
    is > than current time.
    """

    try:
        head, *tail = sorted(pub_dates, reverse=True)
        relevant = timezone.now() - since

        intervals: list[float] = []

        for pub_date in filter(lambda pub_date: pub_date > relevant, tail):
            intervals.append((head - pub_date).total_seconds())
            head = pub_date

        return within_bounds(timedelta(seconds=numpy.mean(intervals)))
    except ValueError:
        return MIN_INTERVAL


def increment_refresh_interval(refresh_interval: timedelta) -> timedelta:
    """Increments refresh interval by 10%"""
    seconds = refresh_interval.total_seconds()
    return within_bounds(timedelta(seconds=seconds + (seconds * 0.1)))


def within_bounds(interval: timedelta) -> timedelta:
    return min(max(interval, MIN_INTERVAL), MAX_INTERVAL)
