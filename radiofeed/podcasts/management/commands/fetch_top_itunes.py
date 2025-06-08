import typer
from django_typer.management import Typer

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes

app = Typer()


@app.command()
def handle(country: str, limit: int = 30):
    """Fetch the top iTunes podcasts for a given country."""
    typer.echo(f"Fetching iTunes chart for {country}...")

    try:
        for feed in itunes.fetch_chart(get_client(), country, limit):
            typer.secho(f"Fetched iTunes feed: {feed}", fg="green")
    except itunes.ItunesError as exc:
        typer.secho(f"Error fetching iTunes feed: {exc}", fg="red")
