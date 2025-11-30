import itertools
from datetime import datetime, timedelta

from django.utils import timezone

from listenfeed.feedparser.models import Feed
from listenfeed.podcasts.models import Podcast


def schedule(feed: Feed) -> timedelta:
    """Estimates frequency of episodes in feed, based on the minimum of time intervals
    between individual episodes."""
    try:
        frequency = min(
            a - b
            for a, b in itertools.pairwise(
                sorted(
                    feed.pub_dates,
                    reverse=True,
                )
            )
        )
    except ValueError:
        frequency = Podcast.DEFAULT_PARSER_FREQUENCY

    # increment until pub date + freq > current time

    return reschedule(feed.pub_date, frequency)


def reschedule(pub_date: datetime | None, frequency: timedelta | None) -> timedelta:
    """Increments update frequency until next scheduled date > current time."""
    if pub_date is None or frequency is None:
        return Podcast.DEFAULT_PARSER_FREQUENCY

    # ensure we don't try to increment zero frequency

    frequency = frequency or Podcast.MIN_PARSER_FREQUENCY

    now = timezone.now()

    while now > pub_date + frequency:
        frequency += frequency * 0.01

    # ensure result falls within bounds

    return max(frequency, Podcast.MIN_PARSER_FREQUENCY)
