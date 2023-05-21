from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand

from radiofeed.feedparser import feed_parser, scheduler
from radiofeed.iterators import batcher


class Command(BaseCommand):
    """Parses RSS feeds."""

    help = """Parses RSS feeds of all scheduled podcasts."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Parse command args."""
        parser.add_argument(
            "--limit",
            help="Max number of feeds for update",
            type=int,
            default=360,
        )

    def handle(self, **options) -> None:
        """Command handler implementation."""
        for podcasts in batcher(
            scheduler.get_podcasts_for_update()[: options["limit"]].iterator(),
            30,
        ):
            with ThreadPoolExecutor() as executor:
                executor.map(feed_parser.parse_feed, podcasts)
