from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand

from radiofeed.feedparser import feed_parser, scheduler
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.iterators import batcher
from radiofeed.podcasts.models import Podcast


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
            scheduler.get_podcasts_for_update()[: options["limit"]], 100
        ):
            with ThreadPoolExecutor() as executor:
                executor.map(self._parse_feed, podcasts)

    def _parse_feed(self, podcast: Podcast) -> None:
        try:
            feed_parser.FeedParser(podcast).parse()

        except FeedParserError:
            self.stdout.write(self.style.ERROR(f"{podcast} not updated"))
        else:
            self.stdout.write(self.style.SUCCESS(f"{podcast} updated"))
