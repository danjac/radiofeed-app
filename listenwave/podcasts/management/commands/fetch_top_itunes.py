import itertools

from django_typer.management import Typer

from listenwave.podcasts import itunes
from listenwave.podcasts.models import Category
from listenwave.podcasts.tasks import fetch_itunes_feeds

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

    for country, itunes_genre_id in permutations:
        fetch_itunes_feeds.enqueue(country=country, itunes_genre_id=itunes_genre_id)
