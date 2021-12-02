from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone
from scipy import stats

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

    # if > 14 days ago just return the max freq

    if now - latest > Podcast.MAX_FREQUENCY:
        return Podcast.MAX_FREQUENCY

    try:
        frequency = get_frequency(pub_dates)
    except ValueError:
        frequency = now - latest

    # make sure we're within the min/max bounds

    frequency = within_bounds(frequency)

    # increment until next scheduled is > current time

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


def get_frequency(pub_dates: list[datetime]) -> timedelta:
    """Gets the min mean Bayes confidence interval of all pub dates.
    If insufficient data will raise a ValueError.
    """
    mean, _, _ = stats.bayes_mvs(list(set(get_intervals(pub_dates))))
    return timedelta(seconds=min(mean.minmax))


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
