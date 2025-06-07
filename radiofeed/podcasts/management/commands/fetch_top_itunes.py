from django.core.management import BaseCommand, CommandParser

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes
from radiofeed.thread_pool import execute_thread_pool


class Command(BaseCommand):
    """Command implementation."""

    help = """
    Fetch the top iTunes podcasts for all available countries.
    """

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments."""

        parser.add_argument(
            "-l",
            "--limit",
            type=int,
            default=100,
            help="Number of feeds to fetch",
        )

    def handle(self, **options) -> None:
        """Handle implementation."""

        countries = itunes.get_countries()

        limit = options["limit"]

        execute_thread_pool(
            lambda country: self._fetch_itunes_chart(
                country,
                limit,
            ),
            countries,
        )

    def _fetch_itunes_chart(self, country: str, limit: int) -> None:
        self.stdout.write(f"Fetching iTunes chart for {country}...")
        try:
            for feed in itunes.fetch_chart(get_client(), country, limit, promoted=True):
                self.stdout.write(self.style.SUCCESS(f"Fetched iTunes feed: {feed}"))
        except itunes.ItunesError:
            self.stdout.write(
                self.style.ERROR(f"Error fetching iTunes chart: {country}")
            )
