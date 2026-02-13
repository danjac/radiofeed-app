import itertools
from typing import Annotated

import typer
from django.conf import settings
from django.db.models import Case, Count, IntegerField, When
from django.db.models.functions import Lower
from django_typer.management import Typer

from radiofeed.podcasts import recommender, tasks, tokenizer
from radiofeed.podcasts.models import Category, Podcast

app = Typer()


@app.command()
def parse_feeds(
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="The maximum number of podcasts to parse.",
        ),
    ] = 360,
) -> None:
    """Parse feeds for all active podcasts."""
    podcast_ids = (
        Podcast.objects.annotate(
            subscribers=Count("subscriptions"),
            is_new=Case(
                When(parsed__isnull=True, then=1),
                default=0,
                output_field=IntegerField(),
            ),
        )
        .scheduled()
        .filter(active=True)
        .order_by(
            "-is_new",
            "-subscribers",
            "-promoted",
            "parsed",
            "updated",
        )
    ).values_list("pk", flat=True)[:limit]

    for podcast_id in podcast_ids:
        tasks.parse_podcast_feed.enqueue(podcast_id=podcast_id)


@app.command()
def fetch_itunes(
    countries: Annotated[
        list[str] | None,
        typer.Option(
            "--countries",
            "-c",
            help="List of country codes to fetch iTunes podcasts for.",
        ),
    ] = None,
) -> None:
    """Fetch the top iTunes podcasts for a given country."""

    countries = countries or list(settings.ITUNES_COUNTRIES)

    genre_ids = Category.objects.filter(itunes_genre_id__isnull=False).values_list(
        "itunes_genre_id", flat=True
    )

    # Create combinations of countries and genre IDs, including a None genre ID for fetching
    # most popular across all genres.
    combinations = itertools.product(countries, (None, *genre_ids))

    for country, genre_id in combinations:
        tasks.fetch_itunes_feeds.enqueue(country=country, genre_id=genre_id)


@app.command()
def create_recommendations() -> None:
    """Create podcast recommendations for all languages."""
    languages = (
        Podcast.objects.annotate(language_code=Lower("language"))
        .filter(language_code__in=tokenizer.get_language_codes())
        .values_list("language_code", flat=True)
        .order_by("language_code")
        .distinct()
    )

    for language in languages:
        recommender.recommend(language)
        typer.echo(f"Recommendations created for language: {language}")
