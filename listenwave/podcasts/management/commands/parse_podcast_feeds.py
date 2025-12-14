from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Case, Count, IntegerField, When

from listenwave.feed_parser.feed_parser import parse_feed
from listenwave.http_client import get_client
from listenwave.podcasts.models import Podcast
from listenwave.thread_pool import map_thread_pool


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

        podcasts = (
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
        )[:limit]

        with get_client() as client:

            def _worker(podcast: Podcast) -> tuple[Podcast, str]:
                result = parse_feed(podcast, client)
                return podcast, result

            for podcast, result in map_thread_pool(_worker, podcasts):
                self.stdout.write(f"Parsed feed for {podcast}: {result}")
