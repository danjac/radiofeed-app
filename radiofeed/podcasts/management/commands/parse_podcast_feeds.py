from __future__ import annotations

import itertools
import multiprocessing

from argparse import ArgumentParser
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import models
from django.db.models.functions import ExtractDay
from django.utils import timezone
from django_rq import get_queue

from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.parsers import feed_parser


class Command(BaseCommand):
    help = """
    Parses RSS feeds of all scheduled podcasts
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--limit", help="Limit (per CPU)", type=int, default=100)
        parser.add_argument("--timeout", help="Timeout(seconds)", type=int, default=300)

    def handle(self, *args, **kwargs) -> None:

        # parse podcasts up to CPU-based limit
        # example: if 3xCPU and --limit=100, then parse 300 each time

        podcast_ids = frozenset(
            itertools.islice(
                self.get_podcasts().values_list("pk", flat=True).distinct(),
                round(multiprocessing.cpu_count() * kwargs["limit"]),
            )
        )

        # add to queue

        Podcast.objects.filter(pk__in=podcast_ids).update(queued=timezone.now())

        queue = get_queue("feeds")

        for podcast_id in podcast_ids:
            queue.enqueue(
                feed_parser.parse_podcast_feed,
                args=(podcast_id,),
                on_failure=feed_parser.on_failure,
                timeout=kwargs["timeout"],
            )

        self.stdout.write(f"{len(podcast_ids)} podcasts queued for update")

    def get_podcasts(self) -> models.QuerySet[Podcast]:
        """Retrieve podcasts for update.

        Algorithm: fetch podcasts where number of hours since last updated
        is at least number of days since the last pub date (within range of 1-24 hours).

        Examples:
                last pub date 3 hours ago: last updated > 1 hour ago
                last pub date 3 days ago: last updated > 3 hours ago
                last pub date 30 days ago: last updated > 24 hours ago
        """
        now = timezone.now()

        return (
            Podcast.objects.annotate(
                subscribers=models.Count("subscription"),
                days_since_last_pub_date=ExtractDay(now - models.F("pub_date")),
            )
            .filter(
                models.Q(
                    parsed__isnull=True,
                )
                | models.Q(
                    pub_date__isnull=True,
                )
                | models.Q(
                    days_since_last_pub_date__lt=1,
                    parsed__lt=now - timedelta(hours=1),
                )
                | models.Q(
                    days_since_last_pub_date__gt=24,
                    parsed__lt=now - timedelta(hours=24),
                )
                | models.Q(
                    days_since_last_pub_date__range=(1, 24),
                    parsed__lt=now
                    - timedelta(hours=1) * models.F("days_since_last_pub_date"),
                ),
                queued__isnull=True,
                active=True,
            )
            .order_by(
                models.F("subscribers").desc(),
                models.F("promoted").desc(),
                models.F("parsed").asc(nulls_first=True),
                models.F("pub_date").desc(nulls_first=True),
            )
        )
