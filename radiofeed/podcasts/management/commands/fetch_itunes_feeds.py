import dataclasses
import itertools
import random
import time

from django.core.management.base import BaseCommand, CommandParser

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Category
from radiofeed.thread_pool import db_threadsafe, thread_pool_map


@dataclasses.dataclass(kw_only=True, frozen=True)
class Result:
    """Result of fetching iTunes feeds for a country."""

    country: str
    category: Category | None = None

    feeds: list[itunes.Feed] = dataclasses.field(default_factory=list)
    error: itunes.ItunesError | None = None


class Command(BaseCommand):
    """Fetch the top iTunes podcasts for a given country."""

    help = "Fetch the top iTunes podcasts for a given country."

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments to the management command."""
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
        min_jitter: float,
        max_jitter: float,
        **options,
    ) -> None:
        """Handle the management command."""

        categories = Category.objects.filter(itunes_genre_id__isnull=False)

        combinations = itertools.product(itunes.COUNTRIES, (None, *categories))

        with get_client() as client:

            @db_threadsafe
            def _worker(args: tuple[str, Category | None]) -> Result:
                country, category = args
                try:
                    itunes_genre_id = category.itunes_genre_id if category else None
                    if feeds := itunes.fetch_top_feeds(
                        client, country, itunes_genre_id
                    ):
                        if itunes_genre_id is None:
                            itunes.save_feeds_to_db(feeds, promoted=True)
                        else:
                            itunes.save_feeds_to_db(feeds)

                    return Result(country=country, category=category, feeds=feeds)

                except itunes.ItunesError as exc:
                    return Result(country=country, category=category, error=exc)
                finally:
                    # Add jitter to avoid hitting rate limits
                    jitter = random.uniform(min_jitter, max_jitter)  # noqa: S311
                    time.sleep(jitter)

            for result in thread_pool_map(_worker, combinations):
                category = result.category.name if result.category else "Most Popular"
                if result.error:
                    self.stderr.write(
                        f"Error fetching iTunes {category} feeds for country {result.country}: {result.error}"
                    )
                else:
                    self.stdout.write(
                        f"Fetched iTunes {category} feeds for country {result.country}"
                    )
