from __future__ import annotations

import itertools

from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from radiofeed.feedparser import scheduler
from radiofeed.feedparser.tasks import parse_feed


class Command(BaseCommand):
    """Django management command."""

    help = """
    Parses RSS feeds of all scheduled podcasts
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "--limit", help="Number of feeds for update", type=int, default=360
        )

    def handle(self, *args, **options) -> None:
        """Command handler implmentation."""
        parse_feed.map(
            itertools.islice(
                scheduler.get_scheduled_podcasts_for_update()
                .values_list("pk")
                .distinct(),
                options["limit"],
            )
        )
