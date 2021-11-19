from __future__ import annotations

import statistics

from datetime import datetime, timedelta

import numpy

from django.conf import settings
from django.utils import timezone

from jcasts.shared.typedefs import ComparableT

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
    scheduled = pub_date + frequency

    # if less than current time, increment by freq
    # until we have a time > now

    while scheduled < now:
        scheduled += frequency

    return (
        within_bounds(
            scheduled,
            now + MIN_FREQUENCY,
            now + MAX_FREQUENCY,
        ),
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

    now = timezone.now()

    return (
        within_bounds(
            now + timedelta(seconds=frequency.total_seconds() * modifier),
            now + MIN_FREQUENCY,
            now + MAX_FREQUENCY,
        ),
        frequency,
        within_bounds(modifier * 1.2, DEFAULT_MODIFIER, 1.0),
    )


def get_frequency(pub_dates: list[datetime]) -> timedelta:
    """Calculate the frequency based on mean interval between pub dates
    of individual episodes."""

    # ignore any < 90 days

    earliest = timezone.now() - settings.FRESHNESS_THRESHOLD
    pub_dates = [pub_date for pub_date in pub_dates if pub_date > earliest]

    # assume default if not enough available dates

    if len(pub_dates) in (0, 1):
        return DEFAULT_FREQUENCY

    # get interval times between each release date

    latest, *pub_dates = sorted(pub_dates, reverse=True)

    intervals: list[float] = []

    for pub_date in pub_dates:
        # smooth out outliers to within min/max boundaries
        interval = within_bounds(
            latest - pub_date,
            MIN_FREQUENCY,
            MAX_FREQUENCY,
        )
        intervals.append(interval.total_seconds())
        latest = pub_date

    # get a randomized sample of frequencies

    numpy.random.seed(1)

    frequency = statistics.mean(
        numpy.random.normal(
            statistics.mean(intervals),
            statistics.pstdev(intervals),
            1000,
        ).round(2),
    )

    # final value should fall within min/max bounds

    return within_bounds(
        timedelta(seconds=frequency),
        MIN_FREQUENCY,
        MAX_FREQUENCY,
    )


def within_bounds(
    value: ComparableT, min_value: ComparableT, max_value: ComparableT
) -> ComparableT:
    return max(min(value, max_value), min_value)
