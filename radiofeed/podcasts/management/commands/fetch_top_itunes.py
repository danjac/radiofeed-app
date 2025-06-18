from django.core.management import CommandParser
from django.core.management.base import BaseCommand

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes


class Command(BaseCommand):
    """Command implementation for fetching top iTunes podcasts."""

    help = "Fetch the top iTunes podcasts for a given country."

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments."""
        parser.add_argument(
            "country",
            type=str,
            help="Country code for fetching iTunes podcasts",
        )
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=30,
            help="Number of top podcasts to fetch (default: 30)",
        )

    def handle(self, country: str, *, limit: int, **options) -> None:
        """Fetch the top iTunes podcasts for a given country."""
        self.stdout.write(
            f"Fetching top {limit} iTunes podcasts for country: {country}"
        )

        try:
            for feed in itunes.fetch_chart(get_client(), country, limit):
                self.stdout.write(self.style.SUCCESS(f"Fetched iTunes feed: {feed}"))
        except itunes.ItunesError as exc:
            self.stdout.write(self.style.ERROR(f"Error fetching iTunes feed: {exc}"))
