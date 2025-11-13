import itertools

import typer
from django.db import transaction
from django.db.models.functions import Lower
from django_typer.management import Typer

from radiofeed import tokenizer
from radiofeed.podcasts import recommender
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool

app = Typer(help="Create podcast recommendations")


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

    Podcast.objects.filter(has_similar_podcasts=True).update(has_similar_podcasts=False)

    execute_thread_pool(_recommend, languages)


def _recommend(language: str) -> None:
    podcast_ids = {
        recommendation.podcast_id for recommendation in recommender.recommend(language)
    }

    for batch in itertools.batched(podcast_ids, 500, strict=False):
        with transaction.atomic():
            Podcast.objects.select_for_update(skip_locked=True).filter(
                has_similar_podcasts=False,
                id__in=batch,
            ).update(has_similar_podcasts=True)
    typer.secho(
        f"Recommendations created for language: {language}",
        fg=typer.colors.GREEN,
    )
