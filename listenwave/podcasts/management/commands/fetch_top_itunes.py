import itertools

import typer
from django.db import transaction
from django_typer.management import Typer

from listenwave.http_client import get_client
from listenwave.podcasts import itunes
from listenwave.podcasts.models import Category, Podcast

app = Typer(help="Fetch top iTunes podcasts")


@app.command()
def handle() -> None:
    """Fetch the top iTunes podcasts for a given country."""

    categories = Category.objects.filter(itunes_genre_id__isnull=False)
    permutations = itertools.product(itunes.COUNTRIES, (None, *categories))

    promoted_feeds: set[itunes.Feed] = set()

    with get_client() as client:
        for country, category in permutations:
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

    if promoted_feeds:
        with transaction.atomic():
            # Demote existing promoted feeds first
            Podcast.objects.filter(promoted=True).update(promoted=False)
            itunes.save_feeds_to_db(promoted_feeds, promoted=True)
