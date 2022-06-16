from __future__ import annotations

import itertools

from argparse import ArgumentParser
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone

from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tasks import feed_update


class Command(BaseCommand):
    help = """
    Parses RSS feeds of all scheduled podcasts
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--limit", help="Limit", type=int, default=360)

    def handle(self, *args, **options) -> None:

        scheduled = self.get_scheduled_feeds()

        # add podcasts to queue
        # this ensures that podcasts are not stuck forever in queue
        scheduled.filter(queued=None).update(queued=timezone.now())

        feed_update.map(
            itertools.islice(
                scheduled.annotate(subscribers=models.Count("subscription"))
                .order_by(
                    models.F("subscribers").desc(),
                    models.F("promoted").desc(),
                    models.F("queued").asc(nulls_first=True),
                    models.F("parsed").asc(nulls_first=True),
                    models.F("pub_date").desc(nulls_first=True),
                )
                .values_list("pk")
                .distinct(),
                options["limit"],
            )
        )

    def get_scheduled_feeds(self) -> models.QuerySet[Podcast]:
        now = timezone.now()

        return Podcast.objects.annotate(
            days_since_last_pub_date=models.functions.ExtractDay(
                now - models.F("pub_date")
            ),
        ).filter(
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
            active=True,
        )
