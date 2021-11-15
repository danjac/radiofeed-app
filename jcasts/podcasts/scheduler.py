from __future__ import annotations

import statistics

from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from jcasts.shared.typedefs import ComparableT

DEFAULT_MODIFIER = 0.05
DEFAULT_FREQUENCY = timedelta(days=1)
MIN_FREQUENCY = timedelta(hours=3)
MAX_FREQUENCY = timedelta(days=30)


def schedule(
    pub_date: datetime | None,
    pub_dates: list[datetime],
    limit: int = 12,
) -> tuple[datetime | None, float | None]:
    """Return a new scheduled time and modifier."""

    if pub_date is None:
        return None, None

    now = timezone.now()
    frequency = get_frequency(pub_dates, limit)
    scheduled = pub_date + frequency

    while scheduled < now:
        scheduled += frequency

    return (
        within_bounds(
            scheduled,
            now + MIN_FREQUENCY,
            now + MAX_FREQUENCY,
        ),
        DEFAULT_MODIFIER,
    )


def reschedule(
    pub_date: datetime | None, modifier: float | None
) -> tuple[datetime, float]:
    """Increment scheduled time if no new updates
    and increment the schedule modifier.
    """

    now = timezone.now()

    pub_date = pub_date or now - DEFAULT_FREQUENCY
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
    """Calculate the frequency based on mean interval between pub dates
    of individual episodes."""

    now = timezone.now()

    # ignore any < 90 days

    earliest = now - settings.FRESHNESS_THRESHOLD

    if pub_dates and max(pub_dates) < earliest:
        return MAX_FREQUENCY

    pub_dates = [pub_date for pub_date in pub_dates if pub_date > earliest]

    # assume default if not enough available dates

    if len(pub_dates) in (0, 1):
        return DEFAULT_FREQUENCY

    latest, *pub_dates = sorted(pub_dates, reverse=True)[:limit]

    # calculate mean interval between dates

    intervals: list[float] = []

    for pub_date in pub_dates:
        intervals.append((latest - pub_date).total_seconds())
        latest = pub_date

    return within_bounds(
        timedelta(seconds=statistics.mean(intervals)),
        MIN_FREQUENCY,
        MAX_FREQUENCY,
    )


def within_bounds(
    value: ComparableT, min_value: ComparableT, max_value: ComparableT
) -> ComparableT:
    return max(min(value, max_value), min_value)
