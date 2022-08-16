from __future__ import annotations

import itertools

from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand

from radiofeed.feedparser import feed_parser, scheduler


class Command(BaseCommand):

    help = """
    Parses RSS feeds of all scheduled podcasts.
    """

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "--limit",
            help="Max number of feeds for update",
            type=int,
            default=360,
        )

    def handle(self, *args, **options) -> None:
        """Command handler implementation."""
        with ThreadPoolExecutor() as executor:
            executor.map(
                feed_parser.parse_feed,
                itertools.islice(
                    scheduler.scheduled_for_update(),
                    options["limit"],
                ),
            )
