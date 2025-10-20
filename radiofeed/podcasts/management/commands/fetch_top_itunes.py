from typing import Final

from django.core.management import CommandParser
from django.core.management.base import BaseCommand

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool

COUNTRIES: Final = (
    "br",
    "ca",
    "cn",
    "de",
    "dk",
    "es",
    "fi",
    "fr",
    "gb",
    "it",
    "jp",
    "kr",
    "no",
    "pl",
    "sv",
    "us",
)


class Command(BaseCommand):
    """Command implementation for fetching top iTunes podcasts."""

    help = "Fetch the top iTunes podcasts for a given country."

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments."""
        parser.add_argument(
            "--promote",
            "-p",
            type=str,
            help="Country code for promoted iTunes podcasts",
        )

        parser.add_argument(
            "--limit",
            "-l",
            type=int,
            default=30,
            help="Number of top podcasts to fetch (default: 30)",
        )

    def handle(
        self,
        *,
        promote: str,
        limit: int,
        **options,
    ) -> None:
        """Fetch the top iTunes podcasts for a given country."""
        client = get_client()

        if promote:
            # Clear existing promoted podcasts
            Podcast.objects.filter(promoted=True).update(promoted=False)

        def _fetch_country(country: str) -> None:
            promoted = promote == country

            self.stdout.write(
                f"Fetching top {limit} iTunes podcasts for country: {country}",
            )

            fields = {"promoted": True} if promoted else {}

            for feed in itunes.fetch_chart(
                client,
                country,
                limit=limit,
                **fields,
            ):
                msg = f"Fetched iTunes feed {feed.title}"
                if promoted:
                    msg += " (promoted)"

                self.stdout.write(self.style.SUCCESS(msg))

        execute_thread_pool(_fetch_country, COUNTRIES)
