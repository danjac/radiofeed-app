import random
import time
from typing import Annotated

import typer
from django_typer.management import Typer

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Category, Podcast
from radiofeed.thread_pool import execute_thread_pool

app = Typer(help="Fetch top iTunes podcasts")


@app.command()
def handle(
    jitter_min: Annotated[
        float,
        typer.Option(
            "--jitter-min",
            help="Minimum jitter time (secs)",
        ),
    ] = 1.5,
    jitter_max: Annotated[
        float,
        typer.Option(
            "--jitter-max",
            help="Maxium jitter time(secs)",
        ),
    ] = 5.0,
) -> None:
    """Fetch the top iTunes podcasts for a given country."""
    client = get_client()

    # Clear existing promoted podcasts
    Podcast.objects.filter(promoted=True).update(promoted=False)

    categories = list(Category.objects.filter(itunes_genre_id__isnull=False))

    feeds = set()

    def _jitter() -> None:
        time.sleep(random.uniform(jitter_min, jitter_max))  # noqa: S311

    def _fetch_country(country: str) -> None:
        typer.secho(
            f"Fetching top podcasts for country: {country}", fg=typer.colors.YELLOW
        )
        try:
            for feed in itunes.fetch_chart(client, country, promoted=True):
                typer.secho(feed.title, fg=typer.colors.BLUE)
                feeds.add(feed)
        except itunes.ItunesError as exc:
            typer.secho(f"ERROR: {exc}", fg=typer.colors.RED)

        _jitter()

        for category in categories:
            typer.secho(
                f"Fetching {category.name} podcasts for country: {country}",
                fg=typer.colors.YELLOW,
            )
            try:
                for feed in itunes.fetch_genre(
                    client, country, category.itunes_genre_id
                ):
                    typer.secho(feed.title, fg=typer.colors.BLUE)
                    feeds.add(feed)
            except itunes.ItunesError as exc:
                typer.secho(f"ERROR: {exc}", fg=typer.colors.RED)

            _jitter()

    execute_thread_pool(_fetch_country, itunes.COUNTRIES)
    typer.secho(f"Fetched total {len(feeds)} feeds from iTunes", fg=typer.colors.GREEN)
