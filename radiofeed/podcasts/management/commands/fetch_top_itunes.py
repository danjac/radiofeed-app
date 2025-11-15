import random
import time

import typer
from django_typer.management import Typer

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Category, Podcast
from radiofeed.thread_pool import execute_thread_pool

app = Typer(help="Fetch top iTunes podcasts")


@app.command()
def handle() -> None:
    """Fetch the top iTunes podcasts for a given country."""
    client = get_client()

    # Clear existing promoted podcasts
    Podcast.objects.filter(promoted=True).update(promoted=False)

    categories = Category.objects.filter(itunes_genre_id__isnull=False)

    feeds = set()

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


def _jitter() -> None:
    # add some pauses to avoid rate limiting
    time.sleep(random.uniform(1.5, 4.8))  # noqa: S311
