import itertools

import typer
from django.db import transaction
from django.utils import timezone
from django_typer.management import Typer

from listenwave.http_client import get_client
from listenwave.podcasts import itunes
from listenwave.podcasts.models import Category, Podcast

app = Typer(help="Fetch top iTunes podcasts")


@app.command()
def handle() -> None:
    """Fetch the top iTunes podcasts for a given country."""

    genres = list(
        Category.objects.filter(itunes_genre_id__isnull=False).values_list(
            "itunes_genre_id", flat=True
        )
    )
    permutations = itertools.product(itunes.COUNTRIES, (None, *genres))
    promoted_feeds: set[itunes.Feed] = set()

    with get_client() as client:
        try:
            for country, itunes_genre_id in permutations:
                if itunes_genre_id:
                    typer.echo(
                        f"Fetching iTunes feed for genre {itunes_genre_id} [{country}]"
                    )
                    feeds = itunes.fetch_genre(client, country, itunes_genre_id)
                    itunes.save_feeds_to_db(feeds)

                else:
                    typer.echo(f"Fetching most popular iTunes feed [{country}]")
                    feeds = itunes.fetch_chart(client, country)
                    # Save promoted feeds until last
                    promoted_feeds.update(feeds)
        except itunes.ItunesError as exc:
            typer.secho(f"Error fetching iTunes feed: {exc}", fg=typer.colors.RED)

    if promoted_feeds:
        with transaction.atomic():
            # Demote existing podcasts
            Podcast.objects.filter(promoted__isnull=False).update(promoted=None)
            itunes.save_feeds_to_db(promoted_feeds, promoted=timezone.now().today())
