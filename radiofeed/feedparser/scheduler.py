import itertools
from datetime import datetime, timedelta
from typing import Final

from django.db.models import F, Q, QuerySet
from django.utils import timezone

from radiofeed.feedparser.models import Feed
from radiofeed.podcasts.models import Podcast

_DEFAULT_FREQUENCY: Final = timedelta(hours=24)
_MIN_FREQUENCY: Final = timedelta(hours=1)
_MAX_FREQUENCY: Final = timedelta(days=3)


def get_scheduled_podcasts() -> QuerySet[Podcast]:
    """Returns all podcasts scheduled for feed parser update.

    1. If parsed is NULL, should be ASAP.
    2. If pub date is NULL, add frequency to last parsed
    3. If pub date is not NULL, add frequency to pub date
    4. Scheduled time should always be in range of 1-24 hours.

    Podcasts should not be parsed more than once per hour.
    """
    now = timezone.now()
    return Podcast.objects.filter(
        Q(parsed__isnull=True)
        | Q(frequency__isnull=True)
        | Q(
            Q(parsed__lt=now - _MAX_FREQUENCY)
            | Q(
                pub_date__isnull=True,
                parsed__lt=now - F("frequency"),
            )
            | Q(
                pub_date__isnull=False,
                pub_date__lt=now - F("frequency"),
            ),
            parsed__lt=now - _MIN_FREQUENCY,
        )
    )


def schedule(feed: Feed) -> timedelta:
    """Estimates frequency of episodes in feed, based on the minimum of time intervals
    between individual episodes."""
    try:
        frequency = min(
            a - b
            for a, b in itertools.pairwise(
                sorted(
                    [item.pub_date for item in feed.items],
                    reverse=True,
                )
            )
        )

    except ValueError:
        frequency = _DEFAULT_FREQUENCY

    # increment until pub date + freq > current time

    return reschedule(feed.pub_date, frequency)


def reschedule(pub_date: datetime | None, frequency: timedelta | None) -> timedelta:
    """Increments update frequency until next scheduled date > current time."""
    if pub_date is None or frequency is None:
        return _DEFAULT_FREQUENCY

    # ensure we don't try to increment zero frequency

    frequency = frequency or _MIN_FREQUENCY

    now = timezone.now()

    while now > pub_date + frequency:
        frequency += frequency * 0.01

    # ensure result falls within bounds

    return max(frequency, _MIN_FREQUENCY)


def next_scheduled_update(podcast: Podcast) -> datetime:
    """Returns estimated next update:

    1. If parsed is NULL, should be ASAP.
    2. If pub date is NULL, add frequency to last parsed
    3. If pub date is not NULL, add frequency to pub date
    4. Scheduled time should always be in range of 1-24 hours.

    Note that this is a rough estimate: the precise update time depends
    on the frequency of the parse feeds cron and the number of other
    scheduled podcasts in the queue.
    """

    if podcast.parsed is None or podcast.frequency is None:
        return timezone.now()

    return min(
        podcast.parsed + _MAX_FREQUENCY,
        max(
            (podcast.pub_date or podcast.parsed) + podcast.frequency,
            podcast.parsed + _MIN_FREQUENCY,
        ),
    )
