from __future__ import annotations

from datetime import datetime, timedelta

DEFAULT_MODIFIER = 0.05

DEFAULT_FREQUENCY = timedelta(days=1)
MIN_FREQUENCY = timedelta(hours=3)
MAX_FREQUENCY = timedelta(days=30)


def schedule(pub_dates: list[datetime]) -> tuple[timedelta, float]:
    try:
        # return the smallest interval between releases
        frequency = timedelta(seconds=min(get_intervals(pub_dates)))
    except ValueError:
        # if insufficient data, just return default
        frequency = DEFAULT_FREQUENCY

    return get_frequency(frequency), DEFAULT_MODIFIER


def reschedule(
    frequency: timedelta | None, modifier: float | None
) -> tuple[timedelta, float]:
    frequency = frequency or DEFAULT_FREQUENCY
    modifier = modifier or DEFAULT_MODIFIER
    seconds = frequency.total_seconds()
    return (
        get_frequency(timedelta(seconds=seconds + (seconds * modifier))),
        modifier * 1.2,
    )


def get_frequency(frequency: timedelta) -> timedelta:
    return min(max(frequency, MIN_FREQUENCY), MAX_FREQUENCY)


def get_intervals(pub_dates: list[datetime]) -> list[float]:
    latest, *pub_dates = sorted(pub_dates, reverse=True)
    intervals: list[float] = []

    for pub_date in pub_dates:
        intervals.append((latest - pub_date).total_seconds())
        latest = pub_date

    return intervals
