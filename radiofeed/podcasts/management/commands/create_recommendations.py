import typer
from django.db.models import QuerySet
from django.db.models.functions import Lower
from django_typer.management import Typer

from radiofeed import tokenizer
from radiofeed.podcasts import recommender
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool

app = Typer()


@app.command()
def handle():
    """Create recommendations for all podcasts"""
    execute_thread_pool(_create_recommendations, _get_languages())


def _create_recommendations(language: str) -> None:
    recommender.recommend(language)
    typer.secho(f"Recommendations created for language: {language}", fg="green")


def _get_languages() -> QuerySet:
    return (
        Podcast.objects.annotate(language_code=Lower("language"))
        .filter(language_code__in=tokenizer.get_language_codes())
        .values_list("language_code", flat=True)
        .order_by("language_code")
        .distinct()
    )
