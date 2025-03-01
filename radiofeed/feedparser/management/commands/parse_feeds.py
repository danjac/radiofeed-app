from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Count, F

from radiofeed.feedparser import feed_parser
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.http_client import Client, get_client
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool


class Command(BaseCommand):
    """Django management command to parse RSS feeds of all scheduled podcasts."""

    help = """Parse RSS feeds."""

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command arguments."""
        parser.add_argument(
            "--limit",
            type=int,
            help="Number of feeds to process",
            default=360,
        )

    def handle(
        self,
        **options,
    ) -> None:
        """Parses RSS feeds of all scheduled podcasts."""
        client = get_client()

        podcasts = (
            Podcast.objects.scheduled()
            .alias(subscribers=Count("subscriptions"))
            .filter(active=True)
            .order_by(
                F("subscribers").desc(),
                F("promoted").desc(),
                F("parsed").asc(nulls_first=True),
            )[: options["limit"]]
        )
        execute_thread_pool(
            lambda podcast: self._parse_feed(podcast, client),
            podcasts,
        )

    def _parse_feed(self, podcast: Podcast, client: Client) -> None:
        try:
            feed_parser.parse_feed(podcast, client)
            self.stdout.write(self.style.SUCCESS(f"{podcast}: Success"))
        except FeedParserError as e:
            self.stdout.write(self.style.ERROR(f"{podcast}: {e.parser_error.label}"))
