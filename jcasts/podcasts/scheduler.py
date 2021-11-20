from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

DEFAULT_MODIFIER = 0.05

DEFAULT_FREQUENCY = timedelta(days=1)
STALE_FREQUENCY = timedelta(days=30)

MIN_FREQUENCY = timedelta(hours=3)
MAX_FREQUENCY = timedelta(days=14)


def schedule(
    pub_date: datetime, pub_dates: list[datetime]
) -> tuple[datetime | None, timedelta | None, float | None]:
    """Return a new scheduled time and modifier."""

    now = timezone.now()

    # if stale (> 90 days) ping once a month

    if pub_date < now - settings.FRESHNESS_THRESHOLD:

        return (
            now + STALE_FREQUENCY,
            STALE_FREQUENCY,
            DEFAULT_MODIFIER,
        )

    frequency = get_frequency(pub_dates)

    return (
        scheduled_within_bounds(pub_date + frequency),
        frequency,
        DEFAULT_MODIFIER,
    )


def reschedule(
    frequency: timedelta | None, modifier: float | None
) -> tuple[datetime | None, timedelta | None, float | None]:
    """Increment scheduled time if no new updates
    and increment the schedule modifier.
    """
    frequency = frequency or DEFAULT_FREQUENCY
    modifier = modifier or DEFAULT_MODIFIER

    return (
        scheduled_within_bounds(
            timezone.now() + timedelta(seconds=frequency.total_seconds() * modifier)
        ),
        frequency,
        modifier * 1.2,
    )


def get_frequency(pub_dates: list[datetime]) -> timedelta:
    """Calculate the frequency based on smallest interval between pub dates
    of individual episodes."""

    try:
        # return the smallest interval between releases
        # e.g. if release dates are 2, 3, and 5 days apart, then return 2 days
        return frequency_within_bounds(timedelta(seconds=min(get_intervals(pub_dates))))
    except ValueError:
        # if insufficient data, just return default
        return DEFAULT_FREQUENCY


def get_intervals(pub_dates: list[datetime]) -> list[float]:
    threshold = timezone.now() - settings.FRESHNESS_THRESHOLD

    try:
        latest, *pub_dates = sorted(
            [pub_date for pub_date in pub_dates if pub_date > threshold],
            reverse=True,
        )
    except ValueError:
        return []

    intervals: list[float] = []

    for pub_date in pub_dates:
        # smooth out outliers to within min/max boundaries
        intervals.append(frequency_within_bounds(latest - pub_date).total_seconds())
        latest = pub_date

    return intervals


def scheduled_within_bounds(value: datetime) -> datetime:
    now = timezone.now()
    return max(min(value, now + MAX_FREQUENCY), now + MIN_FREQUENCY)


def frequency_within_bounds(value: timedelta) -> timedelta:
    return max(min(value, MAX_FREQUENCY), MIN_FREQUENCY)
