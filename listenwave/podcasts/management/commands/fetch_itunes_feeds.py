import dataclasses
import random
import time

from django.core.management.base import BaseCommand, CommandParser

from listenwave.http_client import get_client
from listenwave.podcasts import itunes
from listenwave.thread_pool import map_thread_pool


@dataclasses.dataclass(kw_only=True, frozen=True)
class Result:
    """Result of fetching iTunes feeds for a country."""

    country: str
    error: itunes.ItunesError | None = None

    feeds: list[itunes.Feed] = dataclasses.field(default_factory=list)


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

            def _worker(country: str) -> Result:
                try:
                    feeds = itunes.fetch_chart(client, country, limit)
                    return Result(country=country, feeds=feeds)
                except itunes.ItunesError as exc:
                    return Result(country=country, error=exc)
                finally:
                    # Add jitter to avoid hitting rate limits
                    jitter = random.uniform(min_jitter, max_jitter)  # noqa: S311
                    time.sleep(jitter)

            for result in map_thread_pool(_worker, itunes.COUNTRIES):
                if result.error:
                    self.stderr.write(
                        f"Error fetching iTunes feeds for country {result.country}: {result.error}"
                    )
                else:
                    self.stdout.write(
                        f"Fetched {len(result.feeds)} iTunes feeds for country {result.country}"
                    )
                    feeds.update(result.feeds)

        itunes.save_feeds_to_db(feeds, promoted=True)
        self.stdout.write(f"Saved {len(feeds)} iTunes feeds to database")
