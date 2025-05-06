from django.core.management import BaseCommand, CommandError, CommandParser

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes


class Command(BaseCommand):
    """Command implementation."""

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command line arguments."""
        parser.add_argument(
            "country",
            type=str,
            help="Country code of iTunes chart",
        )
        parser.add_argument(
            "-l",
            "--limit",
            type=int,
            default=30,
            help="Number of feeds to fetch",
        )

    def handle(self, country: str, **options) -> None:
        """Handle implementation."""

        try:
            for feed in itunes.fetch_chart(
                get_client(),
                country,
                limit=options["limit"],
            ):
                self.stdout.write(self.style.SUCCESS(f"Fetched iTunes feed: {feed}"))
        except itunes.ItunesError as exc:
            raise CommandError(str(exc)) from exc
