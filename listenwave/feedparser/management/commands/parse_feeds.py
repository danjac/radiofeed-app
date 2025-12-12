from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Case, Count, IntegerField, When

from listenwave.feedparser.feed_parser import parse_feed
from listenwave.http_client import get_client
from listenwave.podcasts.models import Podcast


class Command(BaseCommand):
    """Parse feeds for all active podcasts."""

    help = "Parse feeds for all active podcasts."

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments to the management command."""
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=360,
            help="Number of podcasts to parse",
        )

    def handle(self, *, limit: int, **options) -> None:
        """Handle the management command."""
        podcasts = (
            Podcast.objects.scheduled()
            .annotate(
                subscribers=Count("subscriptions"),
                is_new=Case(
                    When(parsed__isnull=True, then=1),
                    default=0,
                    output_field=IntegerField(),
                ),
            )
            .filter(active=True)
            .order_by(
                "-is_new",
                "-subscribers",
                "-promoted",
                "parsed",
                "updated",
            )[:limit]
        )

        with get_client() as client:
            for podcast in podcasts:
                result = parse_feed(podcast, client)
                self.stdout.write(f"Parsed feed for {podcast}: {result}")
