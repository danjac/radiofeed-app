import random
import time
from concurrent.futures import ThreadPoolExecutor

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
        parser.add_argument(
            "--min-jitter",
            type=float,
            default=0.5,
            help="Minimum jitter time between requests in seconds",
        )

        parser.add_argument(
            "--max-jitter",
            type=float,
            default=2.5,
            help="Maximum jitter time between requests in seconds",
        )

    def handle(
        self,
        *,
        limit: int,
        min_jitter: float,
        max_jitter: float,
        **options,
    ) -> None:
        """Handle the management command."""
        feeds: set[itunes.Feed] = set()

        with get_client() as client:

            def _worker(country: str) -> list[itunes.Feed]:
                feeds = []
                try:
                    feeds = itunes.fetch_chart(client, country, limit)
                    self.stdout.write(f"Fetched feeds for country: {country}")
                except itunes.ItunesError as exc:
                    self.stderr.write(str(exc))
                finally:
                    # Add jitter to avoid hitting rate limits
                    jitter = random.uniform(min_jitter, max_jitter)  # noqa: S311
                    time.sleep(jitter)
                return feeds

            with ThreadPoolExecutor(max_workers=10) as executor:
                for result in executor.map(_worker, itunes.COUNTRIES):
                    feeds.update(result)

        self.stdout.write(f"Saving {len(feeds)} iTunes feeds to database...")
        itunes.save_feeds_to_db(feeds, promoted=True)
