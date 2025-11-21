import itertools
import random
import time
from typing import Annotated

import typer
from django.db import transaction
from django_typer.management import Typer

from radiofeed.client import get_client
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

    categories = Category.objects.filter(itunes_genre_id__isnull=False)
    permutations = itertools.product(itunes.COUNTRIES, (None, *categories))
    promoted_feeds: set[itunes.ItunesFeed] = set()

    with get_client() as client:

        def _fetch_feeds(country: str, category: Category | None) -> None:
            try:
                if category is None:
                    typer.secho(f"Most popular feeds [{country}]", fg=typer.colors.BLUE)
                    feeds = itunes.fetch_chart(client, country)
                    # Save promoted feeds separately in one batch
                    promoted_feeds.update(feeds)

                else:
                    typer.secho(
                        f"{category.name} feeds [{country}]",
                        fg=typer.colors.BLUE,
                    )
                    feeds = itunes.fetch_genre(
                        client, country, category.itunes_genre_id
                    )
                    # Save regular feeds immediately
                    itunes.save_feeds_to_db(feeds)
            except itunes.ItunesError as exc:
                typer.secho(f"Error: {exc}", fg=typer.colors.RED)
            # Jitter to avoid hitting rate limits
            time.sleep(random.uniform(jitter_min, jitter_max))  # noqa: S311

        execute_thread_pool(lambda t: _fetch_feeds(*t), permutations)

    if promoted_feeds:
        with transaction.atomic():
            # Demote existing promoted feeds first
            Podcast.objects.filter(promoted=True).update(promoted=False)
            itunes.save_feeds_to_db(promoted_feeds, promoted=True)
