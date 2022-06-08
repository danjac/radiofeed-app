from __future__ import annotations

import multiprocessing

from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from radiofeed.podcasts import scheduler
from radiofeed.podcasts.tasks import parse_podcast_feed


class Command(BaseCommand):
    help = """
    Parses RSS feeds of all scheduled podcasts
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("limit", help="Limit (per CPU)", type=int)

    def handle(self, *args, **kwargs) -> None:
        limit = round(multiprocessing.cpu_count() * (kwargs["limit"]))

        parse_podcast_feed.map(
            scheduler.schedule_podcast_feeds().values_list("pk").distinct()[:limit]
        )
