from __future__ import annotations

import itertools

from datetime import timedelta

from django.db.models import Count, F, Q, QuerySet
from django.db.models.functions import ExtractDay
from django.utils import timezone
from django_rq import get_queue

from radiofeed.podcasts import feed_updater
from radiofeed.podcasts.models import Podcast


def schedule(limit: int, **job_kwargs) -> frozenset[int]:

    podcast_ids = frozenset(
        itertools.islice(
            get_scheduled_feeds().values_list("pk", flat=True).distinct(),
            limit,
        )
    )

    enqueue(*podcast_ids, **job_kwargs)
    return podcast_ids


def enqueue(*podcast_ids: int, queue_name: str = "feeds", **job_kwargs) -> None:

    queue = get_queue(queue_name)

    Podcast.objects.filter(pk__in=podcast_ids).update(queued=timezone.now())

    for podcast_id in podcast_ids:
        queue.enqueue(feed_updater.update, args=(podcast_id,), **job_kwargs)


def remove_feeds_from_queue(since: timedelta) -> int:
    return Podcast.objects.filter(queued__lt=timezone.now() - since).update(queued=None)


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
