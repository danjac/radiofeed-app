from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Case, Count, IntegerField, QuerySet, When

from listenwave.feedparser.feed_parser import parse_feed
from listenwave.http_client import get_client
from listenwave.podcasts.models import Podcast
from listenwave.thread_pool import db_threadsafe


class Command(BaseCommand):
    """Parse feeds for all active podcasts."""

    help = "Parse feeds for all active podcasts."

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments."""
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=360,
            help="Number of podcasts to parse",
        )

    def handle(self, *, limit: int, **options) -> None:
        """Handle the command execution."""

        podcasts = self._get_podcasts()[:limit]

        with get_client() as client:

            @db_threadsafe
            def _worker(podcast: Podcast) -> tuple[Podcast, str]:
                result = parse_feed(podcast, client)
                return podcast, result

            with ThreadPoolExecutor() as executor:
                for podcast, result in executor.map(_worker, list(podcasts)):
                    self.stdout.write(f"Parsed feed for {podcast}: {result}")

    def _get_podcasts(self) -> QuerySet[Podcast]:
        """Retrieve podcasts to be parsed."""
        return (
            Podcast.objects.annotate(
                subscribers=Count("subscriptions"),
                is_new=Case(
                    When(parsed__isnull=True, then=1),
                    default=0,
                    output_field=IntegerField(),
                ),
            )
            .scheduled()
            .filter(active=True)
            .order_by(
                "-is_new",
                "-subscribers",
                "-promoted",
                "parsed",
                "updated",
            )
        )
