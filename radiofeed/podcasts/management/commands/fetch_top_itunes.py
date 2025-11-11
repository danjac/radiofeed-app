from typing import Annotated

import typer
from django_typer.management import Typer

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool

app = Typer(help="Fetch top iTunes podcasts")


@app.command()
def handle(
    promote: Annotated[
        str,
        typer.Option(
            "--promote",
            "-p",
            help="Country code for promoted iTunes podcasts",
        ),
    ] = "",
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Number of top podcasts to fetch (default: 30)",
        ),
    ] = 30,
) -> None:
    """Fetch the top iTunes podcasts for a given country."""
    client = get_client()

    if promote:
        if promote not in itunes.COUNTRIES:
            typer.secho(f"Invalid country code: {promote}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        # Clear existing promoted podcasts
        Podcast.objects.filter(promoted=True).update(promoted=False)

    def _fetch_country(country: str) -> None:
        promoted = promote == country
        fields = {"promoted": True} if promoted else {}
        try:
            feeds = itunes.fetch_chart(client, country, limit=limit, **fields)
            typer.secho(
                f"Fetched {len(feeds)} iTunes feeds for country {country}",
                fg=typer.colors.GREEN,
            )
        except itunes.ItunesError as exc:
            typer.secho(
                f"Error fetching iTunes feeds for country {country}: {exc}",
                fg=typer.colors.RED,
            )

    execute_thread_pool(_fetch_country, itunes.COUNTRIES)
