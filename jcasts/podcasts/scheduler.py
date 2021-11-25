from __future__ import annotations

from datetime import datetime, timedelta

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

    return get_frequency(frequency, 1.0), 1.0


def reschedule(frequency: timedelta | None, modifier: float) -> tuple[timedelta, float]:
    modifier = min(modifier * 1.2, 300.0)
    return get_frequency(frequency or DEFAULT_FREQUENCY, modifier), modifier


def get_frequency(frequency: timedelta, modifier: float) -> timedelta:
    return min(
        max(
            timedelta(seconds=frequency.total_seconds() * modifier),
            MIN_FREQUENCY,
        ),
        MAX_FREQUENCY,
    )


def get_intervals(pub_dates: list[datetime]) -> list[float]:
    latest, *pub_dates = sorted(pub_dates, reverse=True)
    intervals: list[float] = []

    for pub_date in pub_dates:
        intervals.append((latest - pub_date).total_seconds())
        latest = pub_date

    return intervals
