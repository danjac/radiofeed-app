from __future__ import annotations

import statistics

from datetime import datetime, timedelta

from django.utils import timezone

DEFAULT_FREQUENCY = timedelta(days=1)
MIN_FREQUENCY = timedelta(hours=3)
MAX_FREQUENCY = timedelta(days=30)


def calc_frequency(pub_dates: list[datetime], limit: int = 12) -> timedelta:
    """Calculate the frequency based on avg interval between pub dates
    of individual episodes."""

    if not pub_dates:
        return DEFAULT_FREQUENCY

    # assume default if not enough available dates

    first, *pub_dates = sorted([timezone.now()] + pub_dates, reverse=True)[:limit]

    # calculate average distance between dates

    diffs: list[float] = []

    for pub_date in pub_dates:
        diffs.append((first - pub_date).total_seconds())
        first = pub_date

    frequency = timedelta(seconds=statistics.mean(diffs))
    return max(min(frequency, MAX_FREQUENCY), MIN_FREQUENCY)


def incr_frequency(frequency: timedelta | None, increment: float = 1.2) -> timedelta:
    """Increments the frequency by the provided amount. We should
    do this on each update 'miss'.
    """

    return (
        min(timedelta(seconds=frequency.total_seconds() * increment), MAX_FREQUENCY)
        if frequency
        else DEFAULT_FREQUENCY
    )
