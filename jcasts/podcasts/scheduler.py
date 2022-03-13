from __future__ import annotations

from datetime import timedelta

from django.db.models import F, Q, QuerySet
from django.utils import timezone
from django.utils.datastructures import OrderedSet
from django_rq import get_queue

from jcasts.podcasts.models import Podcast
from jcasts.podcasts.parsers import feed_parser


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
    queue: str = "feeds",
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

    return enqueue(
        *podcasts.filter(
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
        queue=queue,
    )


def enqueue(*args: int, queue: str = "feeds") -> int:

    if not (podcast_ids := OrderedSet(args)):
        return 0

    now = timezone.now()

    Podcast.objects.filter(pk__in=podcast_ids).update(
        queued=now,
        updated=now,
        feed_queue=queue,
    )

    job_queue = get_queue(queue)

    for counter, podcast_id in enumerate(podcast_ids, 1):
        job_queue.enqueue(feed_parser.parse_podcast_feed, podcast_id)

    return counter


def empty_queue(queue: str) -> int:

    get_queue(queue).empty()

    return Podcast.objects.filter(queued__isnull=False, feed_queue=queue).update(
        queued=None,
        feed_queue=None,
        updated=timezone.now(),
    )


def empty_all_queues() -> int:

    podcasts = Podcast.objects.filter(queued__isnull=False, feed_queue__isnull=False)

    for queue in podcasts.values_list("feed_queue", flat=True).distinct():
        get_queue(queue).empty()

    return podcasts.update(queued=None, feed_queue=None, updated=timezone.now())
