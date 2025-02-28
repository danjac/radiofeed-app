from typing import Final

from django.core.management.base import BaseCommand

from radiofeed.http_client import get_client
from radiofeed.podcasts.itunes import fetch_top_chart

_LOCATIONS: Final = (
    "au",
    "ca",
    "de",
    "fi",
    "fr",
    "gb",
    "nz",
    "us",
)


class Command(BaseCommand):
    """Django command to crawl iTunes Top Chart."""

    help = "Crawl iTunes Top Chart"

    def add_arguments(self, parser):
        """Add command arguments."""

        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of podcasts to fetch",
            default=50,
        )

    def handle(self, *args, **options):
        """Crawl iTunes Top Chart."""
        for location in _LOCATIONS:
            self.stdout.write(
                self.style.NOTICE(f"Fetching iTunes Top Chart for {location}")
            )
            for podcast in fetch_top_chart(
                get_client(),
                location=location,
                limit=options["limit"],
            ):
                self.stdout.write(self.style.SUCCESS(f"Podcast {podcast}"))
