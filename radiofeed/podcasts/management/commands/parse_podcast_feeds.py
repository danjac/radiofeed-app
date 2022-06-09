from __future__ import annotations

import itertools
import multiprocessing

from argparse import ArgumentParser
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone

from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tasks import parse_podcast_feed


class Command(BaseCommand):
    help = """
    Parses RSS feeds of all scheduled podcasts
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--limit", help="Limit (per CPU)", type=int, default=100)

    def handle(self, *args, **kwargs) -> None:
        parse_podcast_feed.map(
            itertools.islice(
                self.get_podcasts().values_list("pk").distinct(),
                round(multiprocessing.cpu_count() * kwargs["limit"]),
            )
        )

    def get_podcasts(self) -> models.QuerySet[Podcast]:
        now = timezone.now()

        one_hour_ago = now - timedelta(hours=1)
        three_hours_ago = now - timedelta(hours=3)
        eight_hours_ago = now - timedelta(hours=8)

        one_day_ago = now - timedelta(hours=24)
        one_week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)

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
                    pub_date__gt=one_day_ago,
                    parsed__lt=one_hour_ago,
                )
                # last pub date 1-7 days: check every 3 hours
                | models.Q(
                    pub_date__range=(
                        one_week_ago,
                        one_day_ago,
                    ),
                    parsed__lt=three_hours_ago,
                )
                # last pub date 7-14 days: check every 8 hours
                | models.Q(
                    pub_date__range=(
                        two_weeks_ago,
                        one_week_ago,
                    ),
                    parsed__lt=eight_hours_ago,
                )
                # last pub date > 14 days: check once a day
                | models.Q(
                    pub_date__lt=two_weeks_ago,
                    parsed__lt=one_day_ago,
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
