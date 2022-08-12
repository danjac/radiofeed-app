from __future__ import annotations

import itertools

from datetime import datetime, timedelta
from typing import Final

from django.db.models import Count, F, Q, QuerySet
from django.utils import timezone

from radiofeed.feedparser.models import Feed
from radiofeed.podcasts.models import Podcast

_default_frequency: Final = timedelta(hours=24)
_min_frequency: Final = timedelta(hours=3)


def next_scheduled_update(podcast: Podcast) -> datetime:
    """Returns estimated next update."""

    now = timezone.now()

    if podcast.pub_date is None or podcast.parsed is None:
        return now

    from_parsed = podcast.parsed + timedelta(days=15)

    print(
        "from parsed",
        podcast.parsed,
        from_parsed,
        (from_parsed - now).days,
        now > from_parsed,
    )

    from_pub_date = max(
        podcast.pub_date + podcast.frequency,
        podcast.parsed + _min_frequency,
    )

    print(
        "from pub date",
        podcast.pub_date,
        from_pub_date,
        (from_pub_date - now).days,
        now > from_pub_date,
    )

    if now > from_parsed or now > from_pub_date:
        return now

    return min(from_parsed, from_pub_date)


def scheduled_podcasts_for_update() -> QuerySet[Podcast]:
    """Returns any active podcasts scheduled for feed updates."""

    now = timezone.now()

    return (
        Podcast.objects.alias(subscribers=Count("subscription")).filter(
            Q(parsed__isnull=True)
            | Q(pub_date__isnull=True)
            | Q(parsed__lt=now - timedelta(days=15))
            | Q(
                pub_date__lt=now - F("frequency"),
                parsed__lt=now - _min_frequency,
            ),
            active=True,
        )
    ).order_by(
        F("subscribers").desc(),
        F("promoted").desc(),
        F("parsed").asc(nulls_first=True),
        F("pub_date").desc(nulls_first=True),
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
        frequency = _default_frequency

    # increment until pub date + freq > current time

    return reschedule(feed.pub_date, frequency)


def reschedule(pub_date: datetime | None, frequency: timedelta) -> timedelta:
    """Increments update frequency until next scheduled date > current time."""

    if pub_date is None:
        return _default_frequency

    # ensure we don't try to increment zero frequency

    frequency = frequency or _min_frequency

    now = timezone.now()

    while now > pub_date + frequency:
        frequency += frequency * 0.05

    # ensure result falls within bounds

    return max(frequency, _min_frequency)
