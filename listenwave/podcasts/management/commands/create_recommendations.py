import itertools

import typer
from django.db import transaction
from django.db.models.functions import Lower
from django_typer.management import Typer

from listenwave import tokenizer
from listenwave.podcasts import recommender
from listenwave.podcasts.models import Podcast
from listenwave.thread_pool import execute_thread_pool

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

    Podcast.objects.filter(has_similar_podcasts=True).update(has_similar_podcasts=False)

    execute_thread_pool(_recommend, languages)


def _recommend(language: str) -> None:
    podcast_ids = (rec.podcast_id for rec in recommender.recommend(language))  # type: ignore[attr-defined]

    for batch in itertools.batched(podcast_ids, 500, strict=False):
        _update_recommendations_batch(batch)

    typer.secho(
        f"Recommendations created for language: {language}",
        fg=typer.colors.GREEN,
    )


def _update_recommendations_batch(podcast_ids: tuple[int, ...]) -> None:
    with transaction.atomic():
        Podcast.objects.select_for_update(skip_locked=True).filter(
            has_similar_podcasts=False,
            id__in=podcast_ids,
        ).update(has_similar_podcasts=True)
