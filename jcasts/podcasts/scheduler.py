from __future__ import annotations

import bisect

from datetime import datetime, timedelta

from django.utils import timezone

DEFAULT_FREQUENCY = timedelta(days=1)

BUCKETS = (
    timedelta(hours=24),
    timedelta(days=3),
    timedelta(days=7),
    timedelta(days=14),
    timedelta(days=30),
)

INTERVALS = (
    timedelta(hours=3),
    timedelta(hours=8),
    timedelta(hours=12),
    timedelta(hours=24),
    timedelta(hours=48),
)


def schedule(pub_dates: list[datetime]) -> tuple[datetime, timedelta]:
    """Return a new scheduled time and modifier."""

    frequency = get_frequency(pub_dates)
    return get_scheduled(frequency), frequency


def reschedule(frequency: timedelta | None) -> tuple[datetime, timedelta]:
    frequency = frequency or DEFAULT_FREQUENCY
    return get_scheduled(frequency), frequency


def get_scheduled(frequency: timedelta) -> datetime:
    return timezone.now() + get_scheduled_interval(frequency)


def get_scheduled_interval(frequency: timedelta) -> timedelta:
    index = bisect.bisect(BUCKETS, frequency, hi=len(BUCKETS) - 1)
    return INTERVALS[index]


def get_frequency(pub_dates: list[datetime]) -> timedelta:
    """Calculate the frequency based on smallest interval between pub dates
    of individual episodes."""

    try:
        # return the smallest interval between releases
        # e.g. if release dates are 2, 3, and 5 days apart, then return 2 days
        return timedelta(seconds=min(get_intervals(pub_dates)))
    except ValueError:
        # if insufficient data, just return default
        return DEFAULT_FREQUENCY


def get_intervals(pub_dates: list[datetime]) -> list[float]:
    latest, *pub_dates = sorted(pub_dates, reverse=True)
    intervals: list[float] = []

    for pub_date in pub_dates:
        intervals.append((latest - pub_date).total_seconds())
        latest = pub_date

    return intervals
