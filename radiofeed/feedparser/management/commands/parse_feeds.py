import typer
from django.db.models import Count, F, QuerySet
from django_typer.management import Typer

from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.feedparser.feed_parser import parse_feed
from radiofeed.http_client import Client, get_client
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool

app = Typer()


@app.command()
def handle(limit: int = 360) -> None:
    """Parse feeds for all active podcasts."""

    client = get_client()

    execute_thread_pool(
        lambda podcast: _parse_feed(podcast, client),
        _get_scheduled_podcasts(limit),
    )


def _parse_feed(podcast: Podcast, client: Client) -> None:
    """Parse a single feed."""
    try:
        parse_feed(podcast, client)
        typer.secho(f"{podcast}: Success", fg="green")
    except FeedParserError as exc:
        typer.secho(f"{podcast}: {exc.parser_error.label}", fg="red")


def _get_scheduled_podcasts(limit: int) -> QuerySet[Podcast]:
    return (
        Podcast.objects.scheduled()
        .alias(subscribers=Count("subscriptions"))
        .filter(active=True)
        .order_by(
            F("subscribers").desc(),
            F("itunes_ranking").asc(nulls_last=True),
            F("parsed").asc(nulls_first=True),
        )[:limit]
    )
