import typer
from django.db.models import QuerySet
from django.db.models.functions import Lower
from django_typer.management import Typer

from radiofeed.podcasts import recommender
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool

app = Typer()


@app.command()
def handle() -> None:
    """Generate podcast recommendations"""
    execute_thread_pool(_create_recommendations, _get_languages())


def _create_recommendations(language: str) -> None:
    """Create recommendations for a specific language"""
    recommender.recommend(language)
    typer.secho(
        f"Recommendations created for language: {language}",
        fg=typer.colors.GREEN,
    )


def _get_languages() -> QuerySet:
    return (
        Podcast.objects.annotate(language_code=Lower("language"))
        .values_list(
            "language_code",
            flat=True,
        )
        .distinct()
    )
