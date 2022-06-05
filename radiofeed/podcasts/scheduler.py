from __future__ import annotations

import itertools

from datetime import datetime, timedelta

import numpy

from django.db.models import (
    Case,
    Count,
    DateTimeField,
    ExpressionWrapper,
    F,
    Q,
    QuerySet,
    When,
)
from django.utils import timezone

from radiofeed.podcasts.models import Podcast

MAX_INTERVAL = timedelta(days=14)
MIN_INTERVAL = timedelta(hours=1)


def schedule_podcasts_for_update() -> QuerySet[Podcast]:
    now = timezone.now()

    return (
        Podcast.objects.annotate(
            subscribers=Count("subscription"),
            scheduled=ExpressionWrapper(
                F("pub_date") + F("refresh_interval"),
                output_field=DateTimeField(),
            ),
            priority=Case(
                When(Q(promoted=True) | Q(subscribers__gt=0), then=True),
                default=False,
            ),
        )
        .filter(
            Q(parsed__isnull=True)
            | Q(parsed__lt=now - MAX_INTERVAL)
            | Q(
                Q(pub_date__isnull=True)
                | Q(priority=True)
                | Q(scheduled__lt=now, pub_date__gte=now - MAX_INTERVAL),
                parsed__lt=now - MIN_INTERVAL,
            ),
            active=True,
        )
        .order_by(
            F("subscribers").desc(),
            F("promoted").desc(),
            F("parsed").asc(nulls_first=True),
            F("pub_date").desc(nulls_first=True),
            F("created").desc(),
        )
    )


def increment_refresh_interval(refresh_interval: timedelta) -> timedelta:
    seconds = refresh_interval.total_seconds()
    return min(timedelta(seconds=seconds + (seconds * 0.1)), MAX_INTERVAL)


def calculate_refresh_interval(
    pub_dates: list[datetime], since: timedelta = timedelta(days=90)
) -> timedelta:
    """Calculates the mean time interval between pub dates of individual
    episodes in a podcast.

    If latest pub date > 2 weeks returns max interval of 14 days.
    """

    now = timezone.now()

    try:

        if max(pub_dates) < now - MAX_INTERVAL:
            return MAX_INTERVAL

        relevant = now - since

        intervals = filter(
            None,
            [
                (a - b).total_seconds()
                for a, b in itertools.pairwise(
                    filter(
                        lambda pub_date: pub_date > relevant,
                        sorted(pub_dates + [now], reverse=True),
                    )
                )
            ],
        )

        return min(
            max(
                timedelta(seconds=numpy.mean(numpy.fromiter(intervals, float))),
                MIN_INTERVAL,
            ),
            MAX_INTERVAL,
        )

    except ValueError:
        return MIN_INTERVAL
