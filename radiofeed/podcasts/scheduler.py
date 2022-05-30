from __future__ import annotations

from datetime import timedelta

from django.db.models import F, Q, QuerySet
from django.utils import timezone

from radiofeed.podcasts.models import Podcast


def schedule_recent_feeds() -> QuerySet[Podcast]:
    """Schedules podcast feeds for update.

    Runs every 6 minutes
    """

    return schedule_podcast_feeds(
        Podcast.objects.filter(
            Q(pub_date__isnull=True)
            | Q(pub_date__gte=timezone.now() - timedelta(days=14)),
        )
    )


def schedule_sporadic_feeds() -> QuerySet[Podcast]:
    """Schedules sporadic podcast feeds for update.

    Runs every 15 and 45 minutes past the hour
    """

    return schedule_podcast_feeds(
        Podcast.objects.filter(
            pub_date__lt=timezone.now() - timedelta(days=14),
        )
    )


def schedule_podcast_feeds(podcasts: QuerySet[Podcast]) -> QuerySet[Podcast]:
    return (
        podcasts.with_subscribed()
        .filter(
            Q(parsed__isnull=True) | Q(parsed__lt=timezone.now() - timedelta(hours=1)),
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
