from __future__ import annotations

from datetime import datetime, timedelta

import numpy

from django.conf import settings
from django.utils import timezone
from scipy import stats

DEFAULT_MODIFIER = 0.05

DEFAULT_FREQUENCY = timedelta(days=1)
MIN_FREQUENCY = timedelta(hours=3)
MAX_FREQUENCY = timedelta(days=30)


def schedule(pub_dates: list[datetime]) -> tuple[timedelta, float]:
    """Returns the base frequency and initial modifier.

    Call this on each refresh "hit" i.e. when there are new pub dates.

    Calculation is based on intervals between individual release
    dates. If insufficient data, then return the default frequency
    (24 hours).
    """
    try:
        frequency = timedelta(seconds=calc_frequency(pub_dates))
    except ValueError:
        frequency = DEFAULT_FREQUENCY

    return get_frequency(frequency), DEFAULT_MODIFIER


def reschedule(
    frequency: timedelta | None, modifier: float | None
) -> tuple[timedelta, float]:
    """Increment frequency by current modifier, then
    return new frequency and incremented modifier.

    Call this on each refresh "miss" i.e. when there
    are no new pub dates.
    """
    frequency = frequency or DEFAULT_FREQUENCY
    modifier = modifier or DEFAULT_MODIFIER
    seconds = frequency.total_seconds()
    return (
        get_frequency(timedelta(seconds=seconds + (seconds * modifier))),
        modifier * 1.2,
    )


def get_frequency(frequency: timedelta) -> timedelta:
    return min(max(frequency, MIN_FREQUENCY), MAX_FREQUENCY)


def calc_frequency(pub_dates: list[datetime]) -> float:
    """
    Returns the mean - standard error of all relevant release dates
    """
    if len(intervals := get_intervals(pub_dates)) in (0, 1):
        raise ValueError("Insufficient number of intervals")
    return numpy.mean(intervals) - stats.sem(intervals)


def get_intervals(pub_dates: list[datetime]) -> list[float]:
    """Get intervals (in seconds) between individual release dates
    over the past 90 days
    """
    threshold = timezone.now() - settings.FRESHNESS_THRESHOLD

    latest, *pub_dates = sorted(
        [date for date in pub_dates if date > threshold], reverse=True
    )
    intervals: list[float] = []

    for pub_date in pub_dates:
        intervals.append((latest - pub_date).total_seconds())
        latest = pub_date

    return intervals
