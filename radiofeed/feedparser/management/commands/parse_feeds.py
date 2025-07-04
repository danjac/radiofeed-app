from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.db.models import Case, Count, IntegerField, When

from radiofeed.feedparser.feed_parser import parse_feed
from radiofeed.http_client import get_client
from radiofeed.podcasts.models import Podcast


class Command(BaseCommand):
    """Parse feeds for all active podcasts."""

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments for the parse_feeds command."""
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=360,
            help="Limit the number of podcasts to parse (default: 360)",
        )

    def handle(self, *, limit: int, **options) -> None:
        """Parse feeds for all active podcasts."""
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

        client = get_client()

        for podcast in podcasts:
            result = parse_feed(podcast, client)
            self.stdout.write(f"{podcast}: {result.label}")
