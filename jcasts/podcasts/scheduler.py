from __future__ import annotations

from datetime import timedelta

from django.db.models import F, Q, QuerySet
from django.utils import timezone
from django_rq import get_queue

from jcasts.podcasts import feed_parser
from jcasts.podcasts.models import Podcast


def schedule_primary_feeds(**kwargs) -> None:
    """Any followed or promoted podcasts"""
    schedule_podcast_feeds(
        Podcast.objects.with_followed().filter(Q(promoted=True) | Q(followed=True)),
        **kwargs,
    )


def schedule_secondary_feeds(
    after: timedelta | None = None, before: timedelta | None = None, **kwargs
) -> None:
    """Any (non-followed/promoted) podcasts with last release date inside timeframe"""

    now = timezone.now()

    q = Q()

    if after:
        q &= Q(pub_date__gte=now - after)
    if before:
        q &= Q(pub_date__lt=now - before)

    q |= Q(pub_date__isnull=True)

    schedule_podcast_feeds(
        Podcast.objects.with_followed().filter(
            q,
            promoted=False,
            followed=False,
        ),
        **kwargs,
    )


def schedule_podcast_feeds(
    podcasts: QuerySet,
    queue: str = "feeds",
    limit: int = 300,
) -> None:

    enqueue(
        *podcasts.filter(
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
        queue=queue,
    )


def enqueue(*args: int, queue: str = "feeds") -> None:

    if not (podcast_ids := list(args)):
        return

    now = timezone.now()

    Podcast.objects.filter(pk__in=podcast_ids).update(
        queued=now,
        updated=now,
        feed_queue=queue,
    )

    job_queue = get_queue(queue)

    for podcast_id in podcast_ids:
        job_queue.enqueue(feed_parser.parse_podcast_feed, podcast_id)


def empty_queue(queue: str) -> int:

    get_queue(queue).empty()

    return Podcast.objects.filter(queued__isnull=False, feed_queue=queue).update(
        queued=None,
        feed_queue=None,
    )


def empty_all_queues() -> int:

    podcasts = Podcast.objects.filter(queued__isnull=False, feed_queue__isnull=False)

    for queue in podcasts.values_list("feed_queue", flat=True).distinct():
        get_queue(queue).empty()

    return podcasts.update(queued=None, feed_queue=None)
