from typing import Annotated

import typer
from django.db.models import Case, Count, IntegerField, When
from django_typer.management import Typer

from listenwave.feedparser.feed_parser import parse_feed
from listenwave.http_client import get_client
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
) -> None:
    """Parse feeds for all active podcasts."""

    podcasts = (
        Podcast.objects.scheduled()
        .annotate(
            subscribers=Count("subscriptions"),
            is_new=Case(
                When(parsed__isnull=True, then=1),
                default=0,
                output_field=IntegerField(),
            ),
        )
        .filter(active=True)
        .order_by(
            "-is_new",
            "-subscribers",
            "-promoted",
            "parsed",
            "updated",
        )[:limit]
    )

    with get_client() as client:
        for podcast in podcasts:
            result = parse_feed(podcast, client)
            typer.secho(
                f"Parsed feed for podcast {podcast}:{result}", fg=typer.colors.GREEN
            )
