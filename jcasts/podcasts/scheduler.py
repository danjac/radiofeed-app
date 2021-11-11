from __future__ import annotations

import statistics

from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone

DEFAULT_MODIFIER = 0.05
DEFAULT_FREQUENCY = timedelta(days=1)
MIN_FREQUENCY = timedelta(hours=3)
MAX_FREQUENCY = timedelta(days=30)


def schedule(
    pub_date: datetime | None, pub_dates: list[datetime], limit: int = 12
) -> tuple[datetime | None, float | None]:
    """Return a new scheduled time and modifier."""

    if pub_date is None:
        return None, None

    now = timezone.now()

    # new pub dates, recalculate frequency

    frequency = get_frequency(pub_dates, limit)

    if (scheduled := pub_date + frequency) < now:
        scheduled = now + frequency

    return (
        within_bounds(
            scheduled,
            now + MIN_FREQUENCY,
            now + MAX_FREQUENCY,
        ),
        DEFAULT_MODIFIER,
    )


def reschedule(
    pub_date: datetime | None,
    modifier: float | None,
) -> tuple[datetime | None, float | None]:
    """Increment scheduled time if no new updates
    and increment the schedule modifier.
    """

    if pub_date is None:
        return None, None

    now = timezone.now()

    modifier = modifier or DEFAULT_MODIFIER

    return (
        within_bounds(
            now + timedelta(seconds=(now - pub_date).total_seconds() * modifier),
            now + MIN_FREQUENCY,
            now + MAX_FREQUENCY,
        ),
        within_bounds(modifier * 1.2, DEFAULT_MODIFIER, 1.0),
    )


def get_frequency(pub_dates: list[datetime], limit: int = 12) -> timedelta:
    """Calculate the frequency based on avg interval between pub dates
    of individual episodes."""

    if not pub_dates:
        return DEFAULT_FREQUENCY

    # assume default if not enough available dates

    first, *pub_dates = sorted([timezone.now()] + pub_dates, reverse=True)[:limit]

    # calculate average distance between dates

    intervals: list[float] = []

    for pub_date in pub_dates:
        intervals.append((first - pub_date).total_seconds())
        first = pub_date

    return within_bounds(
        timedelta(seconds=statistics.mean(intervals)),
        MIN_FREQUENCY,
        MAX_FREQUENCY,
    )


def within_bounds(value: Any, min_value: Any, max_value: Any) -> Any:
    return max(min(value, max_value), min_value)
