from __future__ import annotations

import statistics

from datetime import datetime, timedelta

DEFAULT_FREQUENCY = timedelta(days=1)
MIN_FREQUENCY = timedelta(hours=3)
MAX_FREQUENCY = timedelta(days=14)


def calc_frequency(pub_dates: list[datetime], limit: int = 12) -> timedelta:
    """Calculate the frequency based on avg interval between pub dates
    of individual episodes."""

    if len(pub_dates) in range(0, 2):
        return DEFAULT_FREQUENCY

    # assume default if not enough available dates

    first, *pub_dates = sorted(pub_dates, reverse=True)[:limit]

    # calculate average distance between dates

    diffs: list[float] = []

    for pub_date in pub_dates:
        diffs.append((first - pub_date).total_seconds())
        first = pub_date

    return bound_frequency(timedelta(seconds=statistics.mean(diffs)))


def incr_frequency(frequency: timedelta | None, increment: float = 1.2) -> timedelta:
    """Increments the frequency by the provided amount. We should
    do this on each update 'miss'.
    """

    return bound_frequency(
        timedelta(seconds=frequency.total_seconds() * increment)
        if frequency
        else DEFAULT_FREQUENCY
    )


def bound_frequency(frequency: timedelta) -> timedelta:
    return max(min(frequency, MAX_FREQUENCY), MIN_FREQUENCY)
