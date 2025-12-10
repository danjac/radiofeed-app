import itertools

import typer
from django.db import transaction
from django_typer.management import Typer

from listenwave.http_client import get_client
from listenwave.podcasts import itunes
from listenwave.podcasts.models import Category

app = Typer(help="Fetch top iTunes podcasts")


@app.command()
def handle() -> None:
    """Fetch the top iTunes podcasts for a given country."""

    categories = list(Category.objects.filter(itunes_genre_id__isnull=False))
    permutations = itertools.product(itunes.COUNTRIES, (None, *categories))
    promoted_feeds: set[itunes.Feed] = set()

    with get_client() as client:
        for country, category in permutations:
            try:
                if category:
                    typer.echo(f"Fetching {category.name} iTunes feeds [{country}]")
                    feeds = itunes.fetch_genre(
                        client, country, category.itunes_genre_id
                    )
                    itunes.save_feeds_to_db(feeds)
                else:
                    typer.echo(f"Fetching most popular iTunes feeds [{country}]")
                    feeds = itunes.fetch_chart(client, country)
                    # Save promoted feeds until last
                    promoted_feeds.update(feeds)
            except itunes.ItunesError as exc:
                typer.secho(f"Error fetching iTunes feed: {exc}", fg=typer.colors.RED)

    if promoted_feeds:
        with transaction.atomic():
            itunes.save_feeds_to_db(promoted_feeds, promoted=True)
