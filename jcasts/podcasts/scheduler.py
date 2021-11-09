from __future__ import annotations

import functools
import statistics

from datetime import datetime, timedelta
from typing import Callable

from django.utils import timezone

DEFAULT_FREQUENCY = timedelta(days=1)
MIN_FREQUENCY = timedelta(hours=3)
MAX_FREQUENCY = timedelta(days=30)


def within_bounds(fn: Callable[..., timedelta | None]) -> Callable:
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if (value := fn(*args, **kwargs)) is None:
            return None
        return min(max(value, MIN_FREQUENCY), MAX_FREQUENCY)

    return wrapper


def schedule(
    pub_date: datetime | None, frequency: timedelta | None = None
) -> datetime | None:
    """Return a new scheduled time."""

    if pub_date is None or frequency is None:
        return None

    now = timezone.now()

    if frequency in (MIN_FREQUENCY, MAX_FREQUENCY):
        return now + frequency

    if (scheduled := pub_date + frequency) < now:

        # if scheduled before current time:
        # take diff between current time and scheduled time
        # and half the distance

        scheduled = now + increment((now - scheduled), 0.5)

    return max(min(scheduled, now + MAX_FREQUENCY), now + MIN_FREQUENCY)


@within_bounds
def increment(frequency: timedelta | None, increment: float = 1.2) -> timedelta:

    if frequency is None:
        return DEFAULT_FREQUENCY

    return timedelta(seconds=frequency.total_seconds() * increment)


@within_bounds
def get_frequency(pub_dates: list[datetime], limit: int = 12) -> timedelta:
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

    return timedelta(seconds=statistics.mean(diffs))
