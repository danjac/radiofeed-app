from __future__ import annotations

import functools
import statistics

from datetime import datetime, timedelta
from typing import Callable

from django.utils import timezone

from jcasts.podcasts.models import Podcast

DEFAULT_FREQUENCY = timedelta(days=1)
MIN_FREQUENCY = timedelta(hours=3)
MAX_FREQUENCY = timedelta(days=30)


def with_frequency_bounds(fn: Callable[..., timedelta]) -> Callable:
    @functools.wraps(fn)
    def wrapper(*args, **kwargs) -> timedelta:
        return min(max(fn(*args, **kwargs), MIN_FREQUENCY), MAX_FREQUENCY)

    return wrapper


def reschedule(podcast: Podcast, frequency: timedelta | None = None) -> datetime | None:
    """Return a new scheduled time."""

    if (frequency := frequency or podcast.frequency) is None:
        return None

    now = timezone.now()

    pub_date = podcast.pub_date or now
    scheduled = pub_date + frequency

    if scheduled < now:
        scheduled = now + (now - pub_date) - frequency

    return min(max(scheduled, now + MIN_FREQUENCY), now + MAX_FREQUENCY)


@with_frequency_bounds
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


@with_frequency_bounds
def increment(frequency: timedelta | None, increment: float = 1.2) -> timedelta:
    """Increments the frequency by the provided amount. We should
    do this on each update 'miss'.
    """

    return (
        timedelta(seconds=frequency.total_seconds() * increment)
        if frequency
        else DEFAULT_FREQUENCY
    )
