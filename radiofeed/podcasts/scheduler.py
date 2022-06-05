from __future__ import annotations

import itertools

from datetime import datetime, timedelta

import numpy

from django.db import models
from django.utils import timezone

from radiofeed.podcasts.models import Podcast

MAX_INTERVAL = timedelta(days=14)
MIN_INTERVAL = timedelta(hours=1)


def schedule_podcasts_for_update() -> models.QuerySet[Podcast]:
    now = timezone.now()

    return (
        Podcast.objects.annotate(
            subscribers=models.Count("subscription"),
            scheduled=models.ExpressionWrapper(
                models.F("pub_date") + models.F("update_interval"),
                output_field=models.DateTimeField(),
            ),
            priority=models.Case(
                models.When(
                    models.Q(promoted=True) | models.Q(subscribers__gt=0), then=True
                ),
                default=False,
            ),
        )
        .filter(
            models.Q(parsed__isnull=True)
            | models.Q(parsed__lt=now - MAX_INTERVAL)
            | models.Q(
                models.Q(pub_date__isnull=True)
                | models.Q(priority=True)
                | models.Q(scheduled__lt=now, pub_date__gte=now - MAX_INTERVAL),
                parsed__lt=now - MIN_INTERVAL,
            ),
            active=True,
        )
        .order_by(
            models.F("subscribers").desc(),
            models.F("promoted").desc(),
            models.F("parsed").asc(nulls_first=True),
            models.F("pub_date").desc(nulls_first=True),
            models.F("created").desc(),
        )
    )


def increment_update_interval(update_interval: timedelta) -> timedelta:
    seconds = update_interval.total_seconds()
    return min(timedelta(seconds=seconds + (seconds * 0.1)), MAX_INTERVAL)


def calculate_update_interval(
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
