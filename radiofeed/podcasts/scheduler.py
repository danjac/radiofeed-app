from __future__ import annotations

import itertools

from datetime import datetime, timedelta
from typing import Generator

import numpy

from django.db import models
from django.utils import timezone

from radiofeed.episodes.models import Episode
from radiofeed.podcasts.models import Podcast


def schedule_podcast_feeds() -> models.QuerySet[Podcast]:
    now = timezone.now()

    return (
        Podcast.objects.annotate(
            subscribers=models.Count("subscription"),
            scheduled=models.ExpressionWrapper(
                models.F("pub_date") + models.F("update_interval"),
                output_field=models.DateTimeField(),
            ),
        )
        .filter(
            models.Q(
                parsed__isnull=True,
            )
            | models.Q(
                pub_date__isnull=True,
            )
            | models.Q(
                scheduled__range=(now - Podcast.MAX_UPDATE_INTERVAL, now),
                parsed__lt=now - Podcast.MIN_UPDATE_INTERVAL,
            )
            | models.Q(parsed__lt=now - Podcast.MAX_UPDATE_INTERVAL),
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


def calculate_update_interval(pub_dates: list[datetime]) -> timedelta:

    try:

        intervals = filter(
            None,
            [
                (a - b).total_seconds()
                for a, b in itertools.pairwise(
                    sorted(pub_dates + [timezone.now()], reverse=True)
                )
            ],
        )

        return min(
            max(
                timedelta(seconds=numpy.mean(numpy.fromiter(intervals, float))),
                Podcast.MIN_UPDATE_INTERVAL,
            ),
            Podcast.MAX_UPDATE_INTERVAL,
        )

    except ValueError:
        return Podcast.MIN_UPDATE_INTERVAL


def increment_update_interval(interval: timedelta, increment: float = 1.2) -> timedelta:
    return min(
        timedelta(seconds=interval.total_seconds() * increment),
        Podcast.MAX_UPDATE_INTERVAL,
    )


def reschedule_podcast_feeds() -> int:
    def _get_podcasts() -> Generator[Podcast, None, None]:
        for podcast in Podcast.objects.filter(active=True):
            pub_dates = list(
                Episode.objects.filter(podcast=podcast).values_list(
                    "pub_date", flat=True
                )
            )
            podcast.update_interval = calculate_update_interval(pub_dates)
            yield podcast

    return Podcast.objects.bulk_update(
        _get_podcasts(), fields=["update_interval"], batch_size=100
    )
