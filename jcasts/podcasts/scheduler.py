from __future__ import annotations

from datetime import datetime, timedelta

import numpy

from django.utils import timezone
from scipy import stats

from jcasts.podcasts.models import Podcast


def schedule(pub_dates: list[datetime]) -> tuple[timedelta, float]:
    """Returns the base frequency and initial modifier.

    Call this on each refresh "hit" i.e. when there are new pub dates.

    Calculation is based on intervals between individual release
    dates. If insufficient data, then return the default frequency
    (24 hours).

    All frequencies must fall between the min (3 hours) and max (30 days).

    """
    try:
        frequency = (
            Podcast.MAX_FREQUENCY
            if timezone.now() - max(pub_dates) > Podcast.MAX_FREQUENCY
            else within_bounds(timedelta(seconds=calc_frequency(pub_dates)))
        )
    except ValueError:
        # insufficient interval data, assume default
        frequency = Podcast.DEFAULT_FREQUENCY
    return frequency, Podcast.DEFAULT_MODIFIER


def reschedule(
    frequency: timedelta | None, modifier: float | None = None
) -> tuple[timedelta, float]:
    """Increment frequency by current modifier, then
    return new frequency and incremented modifier.

    Call this on each refresh "miss" i.e. when there
    are no new pub dates.
    """

    frequency = frequency or Podcast.DEFAULT_FREQUENCY
    modifier = modifier or Podcast.DEFAULT_MODIFIER

    seconds = frequency.total_seconds()

    return (
        within_bounds(timedelta(seconds=seconds + (seconds * modifier))),
        min(modifier * 1.2, 300.00),
    )


def calc_frequency(pub_dates: list[datetime]) -> float:
    """
    Returns the mean - standard error of all relevant release dates
    """
    if len(intervals := get_intervals(pub_dates)) in (0, 1):
        raise ValueError
    return numpy.mean(intervals) - stats.sem(intervals)


def get_intervals(pub_dates: list[datetime]) -> list[float]:
    """Get intervals (in seconds) between individual release dates
    over the past 90 days
    """
    threshold = timezone.now() - Podcast.RELEVANCY_THRESHOLD

    latest, *pub_dates = sorted(
        [date for date in pub_dates if date > threshold], reverse=True
    )
    intervals: list[float] = []

    for pub_date in pub_dates:
        intervals.append((latest - pub_date).total_seconds())
        latest = pub_date

    return intervals


def within_bounds(frequency: timedelta) -> timedelta:
    return min(max(frequency, Podcast.MIN_FREQUENCY), Podcast.MAX_FREQUENCY)
