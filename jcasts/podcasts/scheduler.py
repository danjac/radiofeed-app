from __future__ import annotations

import statistics

from datetime import datetime, timedelta

from django.utils import timezone

from jcasts.shared.typedefs import ComparableT

DEFAULT_MODIFIER = 0.05
DEFAULT_FREQUENCY = timedelta(days=1)
MIN_FREQUENCY = timedelta(hours=3)
MAX_FREQUENCY = timedelta(days=30)


"""
Scheduling algorithm:

Scheduling time + modifier should be (re)calculated on every feed pull.

On every "hit" - i.e. we have new episodes - calculate the mean interval
between each episode release date. Add this interval
to the latest release date. If the result is less than the current time,
add the difference between the current time and the estimated time to the current time.

The result should always fall within the min (3 hrs) and max (30d) values, i.e. we
should not pull a feed more than once every 3 hours, and we should pull all feeds
at least once a month.

For example: current date is 7 nov. Last release date is 4 nov. Mean interval
is 7 days. The next scheduled time is in 4 days.

Another example: current date is 8 nov. Last release date is 31 oct. Mean interval
is 7 days. 31 Oct + 7 days = 7th nov, so we are off by one day. Next scheduled time
should be 1 day hence.

On "miss" - i.e. there are no new episodes - we calculate the distance between the
current time and the last known release date, and multiply this amount by a modifier
(between 0.05 and 1). The result is added to the current date. The modifier is
incremented by 1.2, up to a max of 1. The result should be no more than 30d from now.

For example, current date is 7 nov. Our last release date was 7 days ago. Our next
scheduled time is now + (7 days * 0.05) or approx 8.4 hours hence. If that time is
also missed, our next scheduled time will be calculated with a modifier of 0.06,
and so on, up to the max value of 30d.
"""


def schedule(
    pub_date: datetime | None,
    pub_dates: list[datetime],
    limit: int = 12,
) -> tuple[datetime | None, float | None]:
    """Return a new scheduled time and modifier."""

    if pub_date is None:
        return None, None

    now = timezone.now()

    if (scheduled := pub_date + get_frequency(pub_dates, limit)) < now:

        # add the difference between the scheduled time
        # and current time to the current time

        scheduled = now + (now - scheduled)

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
    """Calculate the frequency based on mean interval between pub dates
    of individual episodes."""

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
