from __future__ import annotations

from datetime import timedelta

from django.db.models import F, Q, QuerySet
from django.utils import timezone

from podtracker.podcasts.models import Podcast
from podtracker.podcasts.parsers import feed_parser


def schedule_primary_feeds(**kwargs) -> int:
    """Any subscribed or promoted podcasts"""
    return schedule_podcast_feeds(
        Podcast.objects.with_subscribed().filter(Q(promoted=True) | Q(subscribed=True)),
        **kwargs,
    )


def schedule_secondary_feeds(**kwargs) -> int:
    """Any (non-subscribed/promoted) podcasts"""

    return schedule_podcast_feeds(
        Podcast.objects.with_subscribed().filter(
            promoted=False,
            subscribed=False,
        ),
        **kwargs,
    )


def schedule_podcast_feeds(
    podcasts: QuerySet,
    *,
    after: timedelta | None = None,
    before: timedelta | None = None,
    limit: int = 300,
) -> int:
    now = timezone.now()

    q = Q()

    if after:
        q &= Q(pub_date__gte=now - after)

    if before:
        q &= Q(pub_date__lt=now - before)

    if after or before:
        q |= Q(pub_date__isnull=True)

    podcast_ids = (
        podcasts.filter(
            q,
            active=True,
            queued__isnull=True,
        )
        .order_by(
            F("parsed").asc(nulls_first=True),
            F("pub_date").desc(nulls_first=True),
            F("created").desc(),
        )
        .values_list("pk", flat=True)
        .distinct()[:limit],
    )

    now = timezone.now()

    Podcast.objects.filter(pk__in=podcast_ids).update(
        queued=now,
        updated=now,
    )

    for counter, podcast_id in enumerate(podcast_ids, 1):
        feed_parser.parse_podcast_feed.delay(podcast_id)

    return counter
