from django.core.management import BaseCommand, CommandParser

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes


class Command(BaseCommand):
    """Command implementation."""

    help = """
    Fetch the top iTunes podcasts for all available countries.
    """

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments."""

        parser.add_argument(
            "country",
            type=str,
            help="2-char country code (e.g. 'us' for United States).",
        )

        parser.add_argument(
            "-l",
            "--limit",
            type=int,
            default=30,
            help="Number of feeds to fetch",
        )

    def handle(self, country, **options) -> None:
        """Handle implementation."""

        self.stdout.write(f"Fetching iTunes chart for {country}...")

        try:
            for feed in itunes.fetch_chart(get_client(), country, options["limit"]):
                self.stdout.write(self.style.SUCCESS(f"Fetched iTunes feed: {feed}"))
        except itunes.ItunesError:
            self.stdout.write(
                self.style.ERROR(f"Error fetching iTunes chart: {country}")
            )
