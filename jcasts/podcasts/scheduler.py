from __future__ import annotations

import functools
import statistics

from datetime import datetime, timedelta
from typing import Callable

from django.utils import timezone

DEFAULT_FREQUENCY = timedelta(days=1)
MIN_FREQUENCY = timedelta(hours=3)
MAX_FREQUENCY = timedelta(days=30)


def within_bounds(fn: Callable[..., datetime | None]) -> Callable:
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if (value := fn(*args, **kwargs)) is None:
            return None
        now = timezone.now()
        return min(max(value, now + MIN_FREQUENCY), now + MAX_FREQUENCY)

    return wrapper


@within_bounds
def schedule(
    pub_date: datetime | None, frequency: timedelta | None = None
) -> datetime | None:
    """Return a new scheduled time."""

    if pub_date is None or frequency is None:
        return None

    now = timezone.now()

    if (scheduled := pub_date + frequency) > now:
        return scheduled

    return now + (now - pub_date - frequency)


@within_bounds
def reschedule(
    scheduled: datetime | None,
    frequency: timedelta | None,
    increment: float = 0.05,
) -> datetime | None:

    if scheduled is None or frequency is None:
        return None
    return scheduled + timedelta(seconds=frequency.total_seconds() * 0.05)


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

    return min(
        max(timedelta(seconds=statistics.mean(diffs)), MIN_FREQUENCY), MAX_FREQUENCY
    )
