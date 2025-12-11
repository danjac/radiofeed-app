from django.core.management.base import BaseCommand, CommandParser

from listenwave.http_client import get_client
from listenwave.podcasts import itunes


class Command(BaseCommand):
    """Fetch the top iTunes podcasts for a given country."""

    help = "Fetch the top iTunes podcasts for a given country."

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments to the management command."""
        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=30,
            help="Number of top podcasts to fetch per country",
        )

    def handle(self, *, limit: int, **options) -> None:
        """Handle the management command."""
        feeds: set[itunes.Feed] = set()

        with get_client() as client:
            for country in itunes.COUNTRIES:
                try:
                    self.stdout.write(f"Fetching most popular iTunes feeds [{country}]")
                    feeds.update(itunes.fetch_chart(client, country, limit))
                except itunes.ItunesError as exc:
                    self.stderr.write(f"Error fetching iTunes feed [{country}]:{exc}")

        self.stdout.write("Saving feeds to database...")
        itunes.save_feeds_to_db(feeds, promoted=True)
