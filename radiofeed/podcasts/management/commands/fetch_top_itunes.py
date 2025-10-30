from typing import Annotated, Final

import typer
from django_typer.management import TyperCommand

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


class Command(TyperCommand):
    """Command implementation for fetching top iTunes podcasts."""

    help = "Fetch the top iTunes podcasts for a given country."

    def handle(
        self,
        *,
        promote: Annotated[
            str,
            typer.Option(
                help="Country code for promoted iTunes podcasts",
            ),
        ] = "",
        limit: Annotated[
            int,
            typer.Option(
                help="Number of top podcasts to fetch (default: 30)",
            ),
        ] = 30,
    ) -> None:
        """Fetch the top iTunes podcasts for a given country."""
        client = get_client()

        if promote:
            # Clear existing promoted podcasts
            Podcast.objects.filter(promoted=True).update(promoted=False)

        def _fetch_country(country: str) -> None:
            promoted = promote == country

            typer.echo(f"Fetching top {limit} iTunes podcasts for country: {country}")

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

                typer.secho(msg, fg=typer.colors.GREEN)

        execute_thread_pool(_fetch_country, COUNTRIES)
