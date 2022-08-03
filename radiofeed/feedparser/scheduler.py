from __future__ import annotations

import itertools

from datetime import datetime, timedelta

import pandas

from django.db.models import Count, F, Q, QuerySet
from django.utils import timezone
from scipy.stats import zscore

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
            | Q(pub_date__range=(now - Podcast.MAX_FREQUENCY, since)),
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
    now = timezone.now()

    if now > feed.pub_date + Podcast.MAX_FREQUENCY:
        return Podcast.MAX_FREQUENCY

    # calculate median interval based on intervals between recent episodes

    frequency = (
        timedelta(seconds=_calc_median_interval(intervals))
        if (intervals := _calc_intervals(feed, now - timedelta(days=90)))
        else Podcast.DEFAULT_FREQUENCY
    )

    # increment until pub date + freq > current time

    return reschedule(feed.pub_date, frequency)


def reschedule(pub_date: datetime | None, frequency: timedelta) -> timedelta:
    """Increments update frequency until next scheduled date > current time."""

    if pub_date is None:
        return Podcast.DEFAULT_FREQUENCY

    # increment by 10% until last pub date + freq > current time

    now = timezone.now()

    while now > pub_date + frequency and frequency < Podcast.MAX_FREQUENCY:
        seconds = frequency.total_seconds()
        frequency = timedelta(seconds=seconds + (seconds * 0.1))

    # ensure result falls within bounds

    return max(min(frequency, Podcast.MAX_FREQUENCY), Podcast.MIN_FREQUENCY)


def _calc_intervals(feed: Feed, since: datetime) -> list[float]:
    return [
        (a - b).total_seconds()
        for a, b in itertools.pairwise(
            sorted(
                [item.pub_date for item in feed.items if item.pub_date > since],
                reverse=True,
            )
        )
    ]


def _calc_median_interval(intervals: list[float]) -> float:
    # remove any outliers and calculate median interval
    df = pandas.DataFrame(intervals, columns=["intervals"])
    df["zscore"] = zscore(df["intervals"])
    df["outlier"] = df["zscore"].apply(lambda score: score <= 0.96 and score >= 1.96)
    return df[~df["outlier"]]["intervals"].median()
