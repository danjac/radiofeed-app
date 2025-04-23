from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Count, F, QuerySet

from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.feedparser.feed_parser import parse_feed
from radiofeed.http_client import Client, get_client
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool


class Command(BaseCommand):
    """Implementation of command"""

    help = """Parse RSS feeds."""

    def add_arguments(self, parser: CommandParser) -> None:
        """Add arugments to the command parser."""
        parser.add_argument(
            "-l",
            "--limit",
            type=int,
            default=360,
            help="Number of feeds to parse",
        )

    def handle(self, **options) -> None:
        """Handle the command."""
        client = get_client()

        execute_thread_pool(
            lambda podcast: self._parse_feed(podcast, client),
            self._get_scheduled_podcasts(
                options["limit"],
            ),
        )

    def _parse_feed(self, podcast: Podcast, client: Client) -> None:
        """Parse a single feed."""
        try:
            parse_feed(podcast, client)
            self.stdout.write(self.style.SUCCESS(f"{podcast}: Success"))
        except FeedParserError as error:
            self.stderr.write(
                self.style.ERROR(f"{podcast}: {error.parser_error.label}")
            )

    def _get_scheduled_podcasts(self, limit: int) -> QuerySet[Podcast]:
        return (
            Podcast.objects.scheduled()
            .alias(subscribers=Count("subscriptions"))
            .filter(active=True)
            .order_by(
                F("subscribers").desc(),
                F("promoted").desc(),
                F("parsed").asc(nulls_first=True),
            )[:limit]
        )
