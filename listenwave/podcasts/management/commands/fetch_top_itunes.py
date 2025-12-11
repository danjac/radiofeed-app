from typing import Annotated

import typer
from django_typer.management import Typer

from listenwave.http_client import get_client
from listenwave.podcasts import itunes
from listenwave.thread_pool import execute_thread_pool

app = Typer(help="Fetch top iTunes podcasts")


@app.command()
def handle(
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Number of top podcasts to fetch per country",
        ),
    ] = 30,
) -> None:
    """Fetch the top iTunes podcasts for a given country."""

    with get_client() as client:

        def _fetch_feeds(country: str) -> None:
            try:
                typer.echo(f"Fetching most popular iTunes feeds [{country}]")
                for feed in itunes.fetch_chart(client, country, limit, promoted=True):
                    typer.secho(feed.title, fg=typer.colors.GREEN)
            except itunes.ItunesError as exc:
                typer.secho(f"Error fetching iTunes feed: {exc}", fg=typer.colors.RED)

        execute_thread_pool(_fetch_feeds, itunes.COUNTRIES)
