from __future__ import annotations

import itertools

from datetime import timedelta

import numpy

from django.db import models
from django.utils import timezone

from radiofeed.feedparser.models import Feed
from radiofeed.podcasts.models import Podcast


def get_scheduled_podcasts_for_update() -> models.QuerySet[Podcast]:
    return (
        Podcast.objects.annotate(
            scheduled=models.ExpressionWrapper(
                models.F("parsed") + models.F("update_interval"),
                output_field=models.DateTimeField(),
            ),
        )
        .alias(subscribers=models.Count("subscription"))
        .filter(
            models.Q(parsed__isnull=True) | models.Q(scheduled__lt=timezone.now()),
            active=True,
        )
    ).order_by(
        models.F("subscribers").desc(),
        models.F("promoted").desc(),
        models.F("parsed").asc(nulls_first=True),
        models.F("pub_date").desc(nulls_first=True),
    )


def calc_update_interval(feed: Feed) -> timedelta:
    return _update_interval_within_bounds(
        timedelta(
            seconds=float(
                numpy.mean(
                    [
                        (a - b).total_seconds()
                        for a, b in itertools.pairwise(
                            [timezone.now()] + [item.pub_date for item in feed.items]
                        )
                    ]
                )
            )
        )
    )


def increment_update_interval(podcast: Podcast) -> timedelta:

    current_interval = podcast.update_interval.total_seconds()

    return _update_interval_within_bounds(
        timedelta(seconds=current_interval + (current_interval * 0.1))
    )


def _update_interval_within_bounds(interval: timedelta) -> timedelta:
    return max(min(interval, Podcast.MAX_UPDATE_INTERVAL), Podcast.MIN_UPDATE_INTERVAL)
