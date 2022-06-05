from __future__ import annotations

import itertools

from datetime import datetime, timedelta

import numpy

from django.db import models
from django.utils import timezone

from radiofeed.podcasts.models import Podcast

MIN_INTERVAL = timedelta(hours=1)


def schedule_podcasts_for_update() -> models.QuerySet[Podcast]:
    """
    Schedules podcast for updates from RSS feed sources.

    Check all podcasts where their last pub date + update interval
    is less than current time. On each "miss" we increment the
    update interval.

    All active podcasts should also be checked at least weekly.
    """
    now = timezone.now()

    return (
        Podcast.objects.annotate(
            scheduled=models.ExpressionWrapper(
                models.F("pub_date") + models.F("update_interval"),
                output_field=models.DateTimeField(),
            ),
        )
        .filter(
            models.Q(parsed__isnull=True)
            | models.Q(pub_date__isnull=True)
            | models.Q(scheduled__lt=now, parsed__lt=now - MIN_INTERVAL)
            | models.Q(parsed__lt=now - timedelta(days=7)),
            active=True,
        )
        .order_by(
            models.F("parsed").asc(nulls_first=True),
            models.F("pub_date").desc(nulls_first=True),
            models.F("created").desc(),
        )
    )


def increment_update_interval(update_interval: timedelta) -> timedelta:
    seconds = update_interval.total_seconds()
    return timedelta(seconds=seconds + (seconds * 0.1))


def calculate_update_interval(
    pub_dates: list[datetime], since: timedelta = timedelta(days=90)
) -> timedelta:
    """Calculates the mean time interval between pub dates of individual
    episodes in a podcast.
    """

    now = timezone.now()

    intervals = filter(
        None,
        [
            (a - b).total_seconds()
            for a, b in itertools.pairwise(
                sorted(pub_dates + [now], reverse=True),
            )
        ],
    )

    try:

        return max(
            timedelta(seconds=numpy.mean(numpy.fromiter(intervals, float))),
            MIN_INTERVAL,
        )

    except ValueError:
        return MIN_INTERVAL
