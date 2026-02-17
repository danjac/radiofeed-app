import itertools
from typing import TYPE_CHECKING

from django.utils import timezone

from radiofeed.podcasts.models import Podcast

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from radiofeed.podcasts.feed_parser.models import Feed


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

    return reschedule(feed.pub_date, frequency)


def reschedule(pub_date: datetime | None, frequency: timedelta | None) -> timedelta:
    """Increments update frequency until next scheduled date > current time."""
    if pub_date is None or frequency is None:
        return Podcast.DEFAULT_PARSER_FREQUENCY

    frequency = frequency or Podcast.MIN_PARSER_FREQUENCY

    now = timezone.now()

    while now > pub_date + frequency:
        frequency += frequency * 0.01

    return max(frequency, Podcast.MIN_PARSER_FREQUENCY)
