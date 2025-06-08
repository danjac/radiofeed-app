import itertools
from datetime import datetime

import typer
from django.db import transaction
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils import timezone
from django_typer.management import Typer

from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.models import Podcast, Subscription

app = Typer()


@app.command()
def handle(
    *,
    days_since: int = 365,
    batch_size: int = 100,
    noinput: bool = False,
):
    """Deletes podcasts that are no longer active or have a publication date older than a specified number of days.
    If will not remove podcasts that have bookmarks, listening history, or subscriptions.
    """
    since = timezone.now() - timezone.timedelta(days=days_since)

    if noinput or typer.confirm("Are you sure you want to continue?"):
        podcasts = _get_queryset(since)
        if num_podcasts := podcasts.count():
            typer.echo(f"Deleting {num_podcasts} podcasts")
            _delete_podcasts(podcasts, batch_size)
        else:
            typer.echo("No podcasts found to remove.")


def _get_queryset(since: datetime) -> QuerySet["Podcast"]:
    return Podcast.objects.alias(
        has_audio_logs=Exists(
            AudioLog.objects.filter(episode__podcast=OuterRef("pk")),
        ),
        has_bookmarks=Exists(
            Bookmark.objects.filter(episode__podcast=OuterRef("pk")),
        ),
        has_subscriptions=Exists(
            Subscription.objects.filter(podcast=OuterRef("pk")),
        ),
    ).filter(
        Q(active=False) | Q(pub_date__lt=since),
        has_audio_logs=False,
        has_bookmarks=False,
        has_subscriptions=False,
    )


def _delete_podcasts(queryset: QuerySet["Podcast"], batch_size: int) -> None:
    with (
        typer.progressbar(
            itertools.batched(
                queryset.values_list("pk", flat=True).iterator(),
                batch_size,
                strict=False,
            ),
            label="Deleting podcasts",
        ) as progress,
        transaction.atomic(),
    ):
        for batch in progress:
            queryset.filter(pk__in=set(batch)).delete()
