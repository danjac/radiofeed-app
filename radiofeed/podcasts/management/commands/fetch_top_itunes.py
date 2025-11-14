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

    # Clear existing promoted podcasts
    Podcast.objects.filter(promoted=True).update(promoted=False)

    def _fetch_country(country: str) -> None:
        try:
            feeds = itunes.fetch_chart(client, country, limit=limit, promoted=True)
        except itunes.ItunesError as exc:
            typer.secho(
                f"Error fetching iTunes feeds for country {country}: {exc}",
                fg=typer.colors.RED,
            )
        else:
            typer.secho(
                f"Fetched {len(feeds)} iTunes feeds for country {country}",
                fg=typer.colors.GREEN,
            )

    execute_thread_pool(_fetch_country, itunes.COUNTRIES)
