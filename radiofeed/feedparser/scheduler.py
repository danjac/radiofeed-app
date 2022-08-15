from __future__ import annotations

import itertools

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Final, Iterator

from django.db.models import Count, F, Q
from django.utils import timezone

from radiofeed.feedparser.feed_parser import parse_feed
from radiofeed.feedparser.models import Feed
from radiofeed.podcasts.models import Podcast

_DEFAULT_FREQUENCY: Final = timedelta(hours=24)
_MIN_FREQUENCY: Final = timedelta(hours=3)
_MAX_FREQUENCY: Final = timedelta(days=15)


def next_scheduled_update(podcast: Podcast) -> datetime:
    """Returns estimated next update."""

    now = timezone.now()

    if podcast.pub_date is None or podcast.parsed is None:
        return now

    return max(
        min(
            podcast.parsed + _MAX_FREQUENCY,
            max(
                podcast.pub_date + podcast.frequency,
                podcast.parsed + _MIN_FREQUENCY,
            ),
        ),
        now,
    )


def schedule_for_update(limit: int) -> Iterator[bool]:

    now = timezone.now()

    qs = Podcast.objects.filter(
        Q(parsed__isnull=True)
        | Q(pub_date__isnull=True)
        | Q(parsed__lt=now - _MAX_FREQUENCY)
        | Q(
            pub_date__lt=now - F("frequency"),
            parsed__lt=now - _MIN_FREQUENCY,
        ),
        active=True,
    )

    qs.filter(queued__isnull=True).update(queued=now)

    with ThreadPoolExecutor() as executor:
        return executor.map(
            parse_feed,
            itertools.islice(
                qs.alias(subscribers=Count("subscription")).order_by(
                    F("subscribers").desc(),
                    F("promoted").desc(),
                    F("queued").asc(),
                    F("parsed").asc(nulls_first=True),
                    F("pub_date").desc(nulls_first=True),
                ),
                limit,
            ),
        )


def schedule(feed: Feed) -> timedelta:
    """Estimates frequency of episodes in feed."""

    # calculate min interval based on intervals between recent episodes

    try:
        frequency = min(
            [
                (a - b)
                for a, b in itertools.pairwise(
                    sorted(
                        [item.pub_date for item in feed.items],
                        reverse=True,
                    )
                )
            ]
        )
    except ValueError:
        frequency = _DEFAULT_FREQUENCY

    # increment until pub date + freq > current time

    return reschedule(feed.pub_date, frequency)


def reschedule(pub_date: datetime | None, frequency: timedelta) -> timedelta:
    """Increments update frequency until next scheduled date > current time."""

    if pub_date is None:
        return _DEFAULT_FREQUENCY

    # ensure we don't try to increment zero frequency

    frequency = frequency or _MIN_FREQUENCY

    now = timezone.now()

    while now > pub_date + frequency:
        frequency += frequency * 0.05

    # ensure result falls within bounds

    return max(frequency, _MIN_FREQUENCY)
