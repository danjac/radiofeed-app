from datetime import timedelta
from typing import Annotated

import typer
from django.db.models import Case, Count, IntegerField, Q, When
from django.utils import timezone
from django_typer.management import Typer

from listenwave.feedparser.tasks import parse_feed
from listenwave.podcasts.models import Podcast

app = Typer(help="Parse feeds for all active podcasts")


@app.command()
def handle(
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Number of podcasts to parse",
        ),
    ] = 360,
    requeue_after_hours: Annotated[
        int,
        typer.Option(
            "--requeue-after-hours",
            "-r",
            help="Requeue podcast if queued more than {n} hours",
        ),
    ] = 3,
) -> None:
    """Parse feeds for all active podcasts."""

    podcast_ids = list(
        Podcast.objects.scheduled()
        .annotate(
            subscribers=Count("subscriptions"),
            is_new=Case(
                When(parsed__isnull=True, then=1),
                default=0,
                output_field=IntegerField(),
            ),
            is_queued=Case(
                When(queued__isnull=False, then=1),
                default=0,
                output_field=IntegerField(),
            ),
        )
        .filter(
            Q(queued__isnull=True)
            | Q(
                queued__lt=timezone.now() - timedelta(hours=requeue_after_hours),
            ),
            active=True,
        )
        .order_by(
            "-is_queued",
            "-is_new",
            "-subscribers",
            "-promoted",
            "parsed",
            "updated",
        )
        .values_list("pk", flat=True)[:limit]
    )

    Podcast.objects.filter(pk__in=podcast_ids).update(queued=timezone.now())

    for podcast_id in podcast_ids:
        parse_feed.enqueue(podcast_id=podcast_id, queued=None)
