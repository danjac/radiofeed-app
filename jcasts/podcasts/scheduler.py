from __future__ import annotations

import statistics

from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

DEFAULT_FREQUENCY = timedelta(days=1)
MIN_FREQUENCY = timedelta(hours=3)
MAX_FREQUENCY = timedelta(days=14)


def reschedule(frequency: timedelta, pub_date: datetime | None = None) -> datetime:
    """Get the next scheduled datetime based on update frequency.

    By default, start from the latest pub date of the podcast and add the frequency.

    Keep incrementing by the frequency until we have scheduled time in the
    future.
    """
    now = timezone.now()

    frequency = frequency or DEFAULT_FREQUENCY
    scheduled = (pub_date or now) + frequency

    return max(min(scheduled, now + MAX_FREQUENCY), now + MIN_FREQUENCY)


def calc_frequency(pub_dates: list[datetime], limit: int = 12) -> timedelta:
    """Calculate the frequency based on avg interval between pub dates
    of individual episodes."""

    earliest = timezone.now() - settings.FRESHNESS_THRESHOLD

    pub_dates = [date for date in pub_dates if date > earliest]

    # assume default if not enough available dates

    if len(pub_dates) in range(0, 2):
        return DEFAULT_FREQUENCY

    first, *pub_dates = sorted(pub_dates, reverse=True)[:limit]

    # calculate average distance between dates

    diffs: list[float] = []

    for pub_date in pub_dates:
        diffs.append((first - pub_date).total_seconds())
        first = pub_date

    return timedelta(seconds=statistics.mean(diffs))


def incr_frequency(frequency: timedelta | None, increment: float = 1.2) -> timedelta:
    """Increments the frequency by the provided amount. We should
    do this on each update 'miss'.
    """

    return (
        timedelta(seconds=frequency.total_seconds() * increment)
        if frequency
        else DEFAULT_FREQUENCY
    )
