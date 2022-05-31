from __future__ import annotations

from datetime import timedelta

from django.db.models import F, Q, QuerySet
from django.utils import timezone

from radiofeed.podcasts.models import Podcast

RECENT_THRESHOLD = timedelta(days=14)


def schedule_recent_feeds(
    threshold: timedelta = RECENT_THRESHOLD,
) -> QuerySet[Podcast]:
    return schedule_podcast_feeds(
        Podcast.objects.filter(
            Q(pub_date__isnull=True) | Q(pub_date__gte=timezone.now() - threshold)
        )
    )


def schedule_sporadic_feeds(
    threshold: timedelta = RECENT_THRESHOLD,
) -> QuerySet[Podcast]:
    return schedule_podcast_feeds(
        Podcast.objects.filter(pub_date__lt=timezone.now() - threshold)
    )


def schedule_podcast_feeds(
    podcasts: QuerySet[Podcast], interval: timedelta = timedelta(hours=1)
) -> QuerySet[Podcast]:
    return (
        podcasts.with_subscribed()
        .filter(
            Q(parsed__isnull=True) | Q(parsed__lt=timezone.now() - interval),
            active=True,
        )
        .order_by(
            F("subscribed").desc(),
            F("promoted").desc(),
            F("parsed").asc(nulls_first=True),
            F("pub_date").desc(nulls_first=True),
            F("created").desc(),
        )
    )
