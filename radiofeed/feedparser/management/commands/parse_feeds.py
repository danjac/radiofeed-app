from django.core.management import CommandParser
from django.core.management.base import BaseCommand
from django.db.models import Count, F

from radiofeed.feedparser.exceptions import FeedParserError
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
            .alias(subscribers=Count("subscriptions"))
            .filter(active=True)
            .order_by(
                F("subscribers").desc(),
                F("promoted").asc(),
                F("parsed").asc(nulls_first=True),
            )[:limit]
        )

        client = get_client()
        num_podcasts = podcasts.count()

        for podcast in podcasts:
            try:
                parse_feed(podcast, client)
                self.stdout.write(self.style.SUCCESS(f"{podcast}: Success"))
            except FeedParserError as exc:
                self.stderr.write(self.style.NOTICE(f"{podcast}: {exc.result.label}"))
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"{podcast}: {exc}"))

        self.stdout.write(self.style.SUCCESS(f"{num_podcasts} podcasts parsed"))
