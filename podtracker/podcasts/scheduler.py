from __future__ import annotations

from datetime import timedelta

from django.db.models import F, Q, QuerySet
from django.utils import timezone
from django.utils.datastructures import OrderedSet

from podtracker.podcasts.models import Podcast


def schedule_primary_feeds(**kwargs) -> list[int]:
    """Any subscribed or promoted podcasts"""
    return schedule_podcast_feeds(
        Podcast.objects.with_subscribed().filter(Q(promoted=True) | Q(subscribed=True)),
        **kwargs,
    )


def schedule_secondary_feeds(**kwargs) -> list[int]:
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
) -> OrderedSet:
    now = timezone.now()

    q = Q()

    if after:
        q &= Q(pub_date__gte=now - after)

    if before:
        q &= Q(pub_date__lt=now - before)

    if after or before:
        q |= Q(pub_date__isnull=True)

    qs = (
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

    if not (podcast_ids := OrderedSet(qs)):
        return OrderedSet()

    now = timezone.now()

    Podcast.objects.filter(pk__in=podcast_ids).update(
        queued=now,
        updated=now,
    )

    return podcast_ids
