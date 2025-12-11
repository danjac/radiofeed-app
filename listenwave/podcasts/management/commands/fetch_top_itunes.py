from typing import Annotated

import typer
from django_typer.management import Typer

from listenwave.http_client import get_client
from listenwave.podcasts import itunes

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

    feeds: set[itunes.Feed] = set()

    with get_client() as client:
        for country in itunes.COUNTRIES:
            try:
                typer.echo(f"Fetching most popular iTunes feeds [{country}]")
                feeds.update(itunes.fetch_chart(client, country, limit))
            except itunes.ItunesError:
                typer.secho(
                    f"Error fetching iTunes feed [{country}]",
                    fg=typer.colors.RED,
                )

    typer.echo("Saving feeds to database...")
    itunes.save_feeds_to_db(feeds, promoted=True)
