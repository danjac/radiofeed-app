from __future__ import annotations

import itertools
import multiprocessing

from argparse import ArgumentParser
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone

from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.parsers.feed_parser import parse_podcast_feed


class Command(BaseCommand):
    help = """
    Parses RSS feeds of all scheduled podcasts
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--limit", help="Limit (per CPU)", type=int, default=100)

    def handle(self, *args, **kwargs) -> None:
        for podcast_id in itertools.islice(
            self.get_podcasts().values_list("pk", flat=True).distinct(),
            round(multiprocessing.cpu_count() * kwargs["limit"]),
        ):
            parse_podcast_feed.delay(podcast_id)

    def get_podcasts(self) -> models.QuerySet[Podcast]:
        now = timezone.now()

        return (
            Podcast.objects.annotate(
                subscribers=models.Count("subscription"),
            )
            .filter(
                models.Q(
                    parsed__isnull=True,
                )
                | models.Q(
                    pub_date__isnull=True,
                )
                # last pub date < 24 hours: check every hour
                | models.Q(
                    pub_date__gt=now - timedelta(hours=24),
                    parsed__lt=now - timedelta(hours=1),
                )
                # last pub date 1-7 days: check every 3 hours
                | models.Q(
                    pub_date__range=(
                        now - timedelta(days=7),
                        now - timedelta(hours=24),
                    ),
                    parsed__lt=now - timedelta(hours=3),
                )
                # last pub date 7-14 days: check every 8 hours
                | models.Q(
                    pub_date__range=(
                        now - timedelta(days=14),
                        now - timedelta(days=7),
                    ),
                    parsed__lt=now - timedelta(hours=8),
                )
                # last pub date > 14 days: check once a day
                | models.Q(
                    pub_date__lt=now - timedelta(days=14),
                    parsed__lt=now - timedelta(hours=24),
                ),
                active=True,
            )
            .order_by(
                models.F("subscribers").desc(),
                models.F("promoted").desc(),
                models.F("parsed").asc(nulls_first=True),
                models.F("pub_date").desc(nulls_first=True),
            )
        )
