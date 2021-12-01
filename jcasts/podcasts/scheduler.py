from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from jcasts.podcasts.models import Podcast


def schedule(pub_dates: list[datetime]) -> timedelta:
    """Returns the initial frequency.

    Call this on each refresh "hit" i.e. when there are new pub dates.

    Calculation is based on intervals between individual release
    dates. If insufficient data, then return the default frequency
    (24 hours).

    All frequencies must fall between the min (1 hour) and max (14 days).

    """
    now = timezone.now()

    try:
        latest = max(pub_dates)
    except ValueError:
        # no pub dates yet, just return default
        return Podcast.DEFAULT_FREQUENCY

    # if > 30 days ago just return the max freq

    if now - latest > Podcast.MAX_FREQUENCY:
        return Podcast.MAX_FREQUENCY

    try:
        frequency = within_bounds(timedelta(seconds=min(get_intervals(pub_dates))))
    except ValueError:
        frequency = Podcast.DEFAULT_FREQUENCY

    while latest + frequency < now and frequency < Podcast.MAX_FREQUENCY:
        frequency = reschedule(frequency)

    return frequency


def reschedule(frequency: timedelta | None) -> timedelta:
    """Increment frequency.

    Call this on each refresh "miss" i.e. when there
    are no new pub dates.
    """

    frequency = frequency or Podcast.DEFAULT_FREQUENCY

    seconds = frequency.total_seconds()

    return within_bounds(timedelta(seconds=seconds + (seconds * 0.05)))


def calc_frequency(pub_dates: list[datetime]) -> timedelta:
    """Return smallest frequency between release dates"""

    try:
        return within_bounds(timedelta(seconds=min(get_intervals(pub_dates))))
    except ValueError:
        return Podcast.DEFAULT_FREQUENCY


def get_intervals(pub_dates: list[datetime]) -> list[float]:
    """Get intervals (in seconds) between individual release dates
    over the past 90 days
    """
    threshold = timezone.now() - Podcast.RELEVANCY_THRESHOLD

    latest, *pub_dates = sorted(
        [date for date in pub_dates if date > threshold], reverse=True
    )
    intervals: list[float] = []

    for pub_date in pub_dates:
        intervals.append((latest - pub_date).total_seconds())
        latest = pub_date

    return intervals


def within_bounds(frequency: timedelta) -> timedelta:
    return min(max(frequency, Podcast.MIN_FREQUENCY), Podcast.MAX_FREQUENCY)
