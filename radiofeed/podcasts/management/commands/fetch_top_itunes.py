from typing import Final

from django.core.management import CommandParser
from django.core.management.base import BaseCommand

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes

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
            "--countries",
            "-c",
            nargs="+",
            default=COUNTRIES,
            help=f"List of country codes to fetch top podcasts for (default {COUNTRIES})",
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
        countries: list[str],
        promote: str,
        limit: int,
        **options,
    ) -> None:
        """Fetch the top iTunes podcasts for a given country."""

        for country in countries:
            self.stdout.write(
                f"Fetching top {limit} iTunes podcasts for country: {country}"
            )

            try:
                for feed in itunes.fetch_chart(
                    get_client(),
                    country,
                    limit=limit,
                    promote=promote == country,
                ):
                    self.stdout.write(
                        self.style.SUCCESS(f"Fetched iTunes feed: {feed}")
                    )
            except itunes.ItunesError as exc:
                self.stdout.write(
                    self.style.ERROR(f"Error fetching iTunes feed: {exc}")
                )
