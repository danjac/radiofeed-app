from typing import Annotated

import typer
from django.core.management import CommandError
from django_typer.management import Typer

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes

app = Typer()


@app.command()
def handle(
    country: Annotated[
        str,
        typer.Argument(
            help="Country code of iTunes chart",
        ),
    ],
    limit: Annotated[
        int,
        typer.Option(
            "-l",
            "--limit",
            help="Number of feeds to fetch",
        ),
    ] = 30,
) -> None:
    """Fetch latest iTunes chart feeds"""

    try:
        for feed in itunes.fetch_chart(get_client(), country, limit=limit):
            typer.secho(f"Fetched iTunes feed: {feed}", fg=typer.colors.GREEN)
    except itunes.ItunesError as exc:
        raise CommandError(f"Unable to fetch itunes chart: {exc}") from exc
