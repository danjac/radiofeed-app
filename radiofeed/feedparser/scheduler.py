from __future__ import annotations

import itertools

from datetime import datetime, timedelta

import numpy

from django.db.models import Count, F, Q, QuerySet
from django.utils import timezone

from radiofeed.feedparser.models import Feed
from radiofeed.podcasts.models import Podcast


def scheduled_podcasts_for_update() -> QuerySet[Podcast]:
    """
    Returns any active podcasts scheduled for feed updates.
    """
    now = timezone.now()
    since = now - F("frequency")

    return (
        Podcast.objects.alias(subscribers=Count("subscription")).filter(
            Q(parsed__isnull=True)
            | Q(pub_date__isnull=True)
            | Q(parsed__lt=since)
            | Q(
                pub_date__range=(now - Podcast.MAX_FREQUENCY, since),
                parsed__lt=now - Podcast.MIN_FREQUENCY,
            ),
            active=True,
        )
    ).order_by(
        F("subscribers").desc(),
        F("promoted").desc(),
        F("parsed").asc(nulls_first=True),
        F("pub_date").desc(nulls_first=True),
    )


def schedule(feed: Feed) -> timedelta:
    """Estimates frequency of episodes in feed."""

    # get intervals between most recent episodes (max 90 days)
    #

    since = timezone.now() - timedelta(days=90)

    intervals = [
        (a - b).total_seconds()
        for a, b in itertools.pairwise(
            sorted(
                [item.pub_date for item in feed.items if item.pub_date > since],
                reverse=True,
            )
        )
    ]

    # run Monte Carlo simulation

    try:
        frequency = timedelta(
            seconds=float(
                numpy.mean(
                    numpy.random.normal(
                        numpy.mean(intervals),
                        numpy.std(intervals),
                        1000,
                    )
                )
            )
        )

    except ValueError:
        frequency = Podcast.DEFAULT_FREQUENCY

    # adjust until next scheduled update > current time

    return reschedule(feed.pub_date, frequency)


def reschedule(
    pub_date: datetime | None, frequency: timedelta, increment: float = 0.1
) -> timedelta:
    """Increments update frequency."""

    if pub_date is None:
        return Podcast.DEFAULT_FREQUENCY

    now = timezone.now()

    while now > pub_date + frequency and Podcast.MAX_FREQUENCY > frequency:
        seconds = frequency.total_seconds()
        frequency = timedelta(seconds=seconds + (seconds * increment))

    return max(min(frequency, Podcast.MAX_FREQUENCY), Podcast.MIN_FREQUENCY)
