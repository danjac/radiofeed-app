import typer
from django.db.models.functions import Lower
from django_typer.management import Typer

from listenwave import tokenizer
from listenwave.podcasts import recommender
from listenwave.podcasts.models import Podcast

app: Typer = Typer(help="Create podcast recommendations")


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

    for language in languages:
        typer.secho(
            f"Recommendations for language: {language}",
            fg=typer.colors.GREEN,
        )

        recommender.recommend(language)
