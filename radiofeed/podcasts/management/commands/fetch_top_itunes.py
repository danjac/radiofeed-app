import typer
from django_typer.management import Typer

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool

app = Typer(help="Fetch top iTunes podcasts")


@app.command()
def handle() -> None:
    """Fetch the top iTunes podcasts for a given country."""
    client = get_client()

    # Clear existing promoted podcasts
    Podcast.objects.filter(promoted=True).update(promoted=False)
    feeds = set()

    def _fetch_country(country: str) -> None:
        try:
            for feed in itunes.fetch_chart(client, country, promoted=True):
                typer.secho(feed.title, fg=typer.colors.BLUE)
                feeds.add(feed)
        except itunes.ItunesError as exc:
            typer.secho(exc, fg=typer.colors.RED)

    execute_thread_pool(_fetch_country, itunes.COUNTRIES)
    typer.secho(f"Fetched total {len(feeds)} feeds from iTunes", fg=typer.colors.GREEN)
