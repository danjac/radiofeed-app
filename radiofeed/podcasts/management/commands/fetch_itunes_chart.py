from typing import Annotated

from django_typer.management import TyperCommand
from typer import Argument, Exit, Option

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes


class Command(TyperCommand):
    """Fetch most popular podcasts from iTunes API."""

    def handle(
        self,
        country: Annotated[
            str,
            Argument(
                help="Country code of iTunes chart",
            ),
        ],
        limit: Annotated[
            int,
            Option(
                "-l",
                "--limit",
                help="Number of feeds to fetch",
            ),
        ] = 30,
    ) -> None:
        """Fetch latest iTunes chart feeds"""

        try:
            for feed in itunes.fetch_chart(get_client(), country, limit=limit):
                self.stdout.write(self.style.SUCCESS(f"Fetched iTunes feed: {feed}"))
        except itunes.ItunesError as e:
            self.stderr.write(self.style.ERROR(f"Error fetching iTunes chart: {e}"))
            raise Exit(code=1) from e
