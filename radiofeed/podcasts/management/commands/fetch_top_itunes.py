import itertools
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

    def _fetch_itunes_feeds(country: str, category: Category | None) -> None:
        msg = (
            f"Fetching {category.name} podcasts for country: {country}"
            if category
            else f"Fetching top podcasts for country: {country}"
        )
        typer.secho(msg, fg=typer.colors.YELLOW)
        try:
            if category:
                feeds = itunes.fetch_genre(client, country, category.itunes_genre_id)
            else:
                feeds = itunes.fetch_chart(client, country, promoted=True)
            for feed in feeds:
                typer.secho(feed.title, fg=typer.colors.BLUE)
        except itunes.ItunesError as exc:
            typer.secho(f"ERROR: {exc}", fg=typer.colors.RED)

        # Jitter to avoid hitting rate limits
        time.sleep(random.uniform(jitter_min, jitter_max))  # noqa: S311

    # Clear existing promoted podcasts
    Podcast.objects.filter(promoted=True).update(promoted=False)
    categories = Category.objects.filter(itunes_genre_id__isnull=False)

    permutations = itertools.product(itunes.COUNTRIES, (None, *categories))
    execute_thread_pool(lambda t: _fetch_itunes_feeds(*t), permutations)
