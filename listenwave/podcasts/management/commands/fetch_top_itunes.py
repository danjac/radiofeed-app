import itertools
import random
import time
from typing import Annotated

import typer
from django.db import transaction
from django_typer.management import Typer

from listenwave.http_client import get_client
from listenwave.podcasts import itunes
from listenwave.podcasts.models import Category
from listenwave.thread_pool import execute_thread_pool

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

    categories = list(Category.objects.filter(itunes_genre_id__isnull=False))
    permutations = itertools.product(itunes.COUNTRIES, (None, *categories))
    promoted_feeds: set[itunes.Feed] = set()
    other_feeds: set[itunes.Feed] = set()

    with get_client() as client:

        def _fetch_feeds(country: str, category: Category | None) -> None:
            try:
                if category:
                    typer.echo(f"Fetching {category.name} iTunes feeds [{country}]")
                    feeds = itunes.fetch_genre(
                        client, country, category.itunes_genre_id
                    )
                    other_feeds.update(feeds)
                else:
                    typer.echo(f"Fetching most popular iTunes feeds [{country}]")
                    feeds = itunes.fetch_chart(client, country)
                    # Save promoted feeds until last
                    promoted_feeds.update(feeds)
            except itunes.ItunesError as exc:
                typer.secho(f"Error fetching iTunes feed: {exc}", fg=typer.colors.RED)

            _jitter(jitter_min, jitter_max)

        execute_thread_pool(lambda t: _fetch_feeds(*t), permutations)

    # remove promoted feeds from other feeds
    other_feeds -= promoted_feeds

    # save feeds to DB
    with transaction.atomic():
        typer.echo(f"Saving {len(other_feeds)} feeds to database...")
        itunes.save_feeds_to_db(other_feeds)
        typer.echo(f"Saving {len(promoted_feeds)} promoted feeds to database...")
        itunes.save_feeds_to_db(promoted_feeds, promoted=True)


def _jitter(min_seconds: float, max_seconds: float) -> None:
    """Jitter by sleeping for a random amount of time.
    This is useful to avoid rate limiting.
    """
    sleep_time = random.uniform(min_seconds, max_seconds)  # noqa: S311
    time.sleep(sleep_time)
