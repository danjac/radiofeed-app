from __future__ import annotations

import itertools

from datetime import datetime, timedelta

from django.db.models import Count, F, Q, QuerySet
from django.utils import timezone

from radiofeed.feedparser.models import Feed
from radiofeed.podcasts.models import Podcast


def scheduled_podcasts_for_update() -> QuerySet[Podcast]:
    """Returns any active podcasts scheduled for feed updates."""

    now = timezone.now()

    since = now - F("frequency")

    return (
        Podcast.objects.alias(subscribers=Count("subscription")).filter(
            Q(parsed__isnull=True)
            | Q(pub_date__isnull=True)
            | Q(parsed__lt=since)
            | Q(
                pub_date__range=(now - Podcast.MAX_FREQUENCY, since),
                parsed__lt=now - Podcast.MIN_FREQUENCY,
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
    now = timezone.now()

    # pub date > 30 days, will always be the max value

    if now > feed.pub_date + Podcast.MAX_FREQUENCY:
        return Podcast.MAX_FREQUENCY

    # calculate min interval based on intervals between recent episodes

    since = now - Podcast.MAX_FREQUENCY

    try:
        frequency = min(
            [
                (a - b)
                for a, b in itertools.pairwise(
                    sorted(
                        [item.pub_date for item in feed.items if item.pub_date > since],
                        reverse=True,
                    )
                )
            ]
        )
    except ValueError:
        frequency = Podcast.DEFAULT_FREQUENCY

    # increment until pub date + freq > current time

    return reschedule(feed.pub_date, frequency)


def reschedule(pub_date: datetime | None, frequency: timedelta) -> timedelta:
    """Increments update frequency until next scheduled date > current time."""

    if pub_date is None:
        return Podcast.DEFAULT_FREQUENCY

    # ensure we don't try to increment zero frequency

    frequency = frequency or Podcast.MIN_FREQUENCY

    now = timezone.now()

    while now > pub_date + frequency and Podcast.MAX_FREQUENCY > frequency:
        frequency += frequency * 0.05

    # ensure result falls within bounds

    return max(min(frequency, Podcast.MAX_FREQUENCY), Podcast.MIN_FREQUENCY)
