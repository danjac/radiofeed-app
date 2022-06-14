from __future__ import annotations

import itertools
import multiprocessing

from argparse import ArgumentParser
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count, F, Q, QuerySet
from django.db.models.functions import ExtractDay
from django.utils import timezone
from django.utils.datastructures import OrderedSet

from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tasks import feed_update


class Command(BaseCommand):
    help = """
    Parses RSS feeds of all scheduled podcasts
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--limit", help="Limit (per CPU)", type=int, default=100)

    def handle(self, *args, **kwargs) -> None:

        # parse podcasts up to CPU-based limit
        # example: if 3xCPU and --limit=100, then parse 300 each time

        podcast_ids = OrderedSet(
            itertools.islice(
                self.get_scheduled_feeds().values_list("pk", flat=True).distinct(),
                round(multiprocessing.cpu_count() * kwargs["limit"]),
            )
        )

        Podcast.objects.filter(pk__in=podcast_ids).update(queued=timezone.now())

        for podcast_id in podcast_ids:
            feed_update.delay(podcast_id)

        self.stdout.write(f"{len(podcast_ids)} podcasts queued for update")

    def get_scheduled_feeds(self) -> QuerySet[Podcast]:
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
