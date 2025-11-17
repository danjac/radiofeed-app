import itertools
import random
import time
from typing import Annotated

import typer
from django.db import transaction
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

    promoted_feeds: set[itunes.ItunesFeed] = set()
    other_feeds: set[itunes.ItunesFeed] = set()

    def _fetch_itunes_feeds(country: str, category: Category | None) -> None:
        label = f"{category.name if category else 'Top'} feeds [{country}]"
        try:
            typer.secho(f"Fetching {label}...", fg=typer.colors.YELLOW)
            if category is None:
                feeds = itunes.fetch_chart(client, country)
                promoted_feeds.update(feeds)
            else:
                feeds = itunes.fetch_genre(client, country, category.itunes_genre_id)
                other_feeds.update(feeds)
            typer.secho(f"Fetched {label}", fg=typer.colors.GREEN)
        except itunes.ItunesError as exc:
            typer.secho(f"Error {label}: {exc}", fg=typer.colors.RED)

        # Jitter to avoid hitting rate limits
        time.sleep(random.uniform(jitter_min, jitter_max))  # noqa: S311

    categories = Category.objects.filter(itunes_genre_id__isnull=False)

    permutations = itertools.product(itunes.COUNTRIES, (None, *categories))
    execute_thread_pool(lambda t: _fetch_itunes_feeds(*t), permutations)

    # Clear existing promoted podcasts
    typer.secho("Saving feeds to the database...", fg=typer.colors.YELLOW)

    # Save promoted feeds to the database
    with transaction.atomic():
        Podcast.objects.filter(promoted=True).update(promoted=False)
        itunes.save_feeds_to_db(promoted_feeds, promoted=True)

    # Save other feeds to the database
    itunes.save_feeds_to_db(other_feeds)

    typer.secho("Saved feeds to the database", fg=typer.colors.GREEN)
