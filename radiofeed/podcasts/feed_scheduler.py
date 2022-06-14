from __future__ import annotations

import itertools

from datetime import timedelta

from django.db.models import Count, F, Q, QuerySet
from django.db.models.functions import ExtractDay
from django.utils import timezone

from radiofeed.podcasts import feed_updater
from radiofeed.podcasts.models import Podcast


def schedule(limit: int, **job_kwargs) -> frozenset[int]:

    podcast_ids = frozenset(
        itertools.islice(
            get_scheduled_feeds().values_list("pk", flat=True).distinct(),
            limit,
        )
    )

    feed_updater.enqueue(*podcast_ids, **job_kwargs)
    return podcast_ids


def get_scheduled_feeds() -> QuerySet[Podcast]:
    now = timezone.now()

    return (
        Podcast.objects.annotate(
            subscribers=Count("subscription"),
            days_since_last_pub_date=ExtractDay(now - F("pub_date")),
        )
        .filter(
            Q(
                parsed__isnull=True,
            )
            | Q(
                pub_date__isnull=True,
            )
            | Q(
                days_since_last_pub_date__lt=1,
                parsed__lt=now - timedelta(hours=1),
            )
            | Q(
                days_since_last_pub_date__gt=24,
                parsed__lt=now - timedelta(hours=24),
            )
            | Q(
                days_since_last_pub_date__range=(1, 24),
                parsed__lt=now - timedelta(hours=1) * F("days_since_last_pub_date"),
            ),
            queued__isnull=True,
            active=True,
        )
        .order_by(
            F("subscribers").desc(),
            F("promoted").desc(),
            F("parsed").asc(nulls_first=True),
            F("pub_date").desc(nulls_first=True),
        )
    )
