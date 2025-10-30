import typer
from django.db.models.functions import Lower
from django_typer.management import Typer

from radiofeed import tokenizer
from radiofeed.podcasts import recommender
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool

app = Typer(help="Create podcast recommendations.")


@app.command()
def handle() -> None:
    """Create recommendations for all podcasts"""
    languages = (
        Podcast.objects.annotate(language_code=Lower("language"))
        .filter(language_code__in=tokenizer.get_language_codes())
        .values_list("language_code", flat=True)
        .order_by("language_code")
        .distinct()
    )

    def _process_language(language) -> None:
        recommender.recommend(language)
        typer.secho(
            f"Recommendations created for language: {language}",
            fg=typer.colors.GREEN,
        )

    execute_thread_pool(_process_language, languages)
